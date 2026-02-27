"""Resume parsing pipeline and UserProfile extraction agent.

Provides:
    - extract_pdf_text()  — multi-column-aware PDF text extraction
    - extract_docx_text() — paragraph/table order-preserving DOCX extraction
    - parse_resume()      — dispatcher: PDF | DOCX | plain-text fallback
    - ResumeParseError    — typed exception for all parse failures
    - ProfileDeps         — PydanticAI deps dataclass
    - profile_agent       — PydanticAI agent, output_type=UserProfile
    - validate_profile()  — PROFILE-09 completeness check
    - extract_profile()   — async orchestration: run agent, validate, persist
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pymupdf  # PyMuPDF >=1.24
from docx import Document  # python-docx >=1.1; iter_inner_content() tested against >=1.1
from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

import ingot.db.models as db_models
from ingot.models.schemas import UserProfile

# column_boxes location varies by PyMuPDF version — resolve once at import time.
try:
    from pymupdf import column_boxes as _column_boxes
except ImportError:
    try:
        from pymupdf.utils import column_boxes as _column_boxes  # type: ignore[no-redef]
    except ImportError:
        _column_boxes = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ResumeParseError(Exception):
    """Raised when resume parsing or extraction fails."""


# ---------------------------------------------------------------------------
# PDF parser — multi-column aware (PROFILE-02)
# ---------------------------------------------------------------------------


def extract_pdf_text(path: str | Path) -> str:
    """Extract text from PDF with multi-column layout support.

    CRITICAL: Do NOT use page.get_text(sort=True) alone — it interleaves
    columns on two-column resumes.  Uses _column_boxes() to detect column
    Rects, then extracts per-column in reading order.  Falls back to
    single-column get_text() if _column_boxes is unavailable or returns
    nothing.
    """
    doc = pymupdf.open(str(path))
    full_text: list[str] = []
    for page in doc:
        if _column_boxes is not None:
            cols = _column_boxes(page, footer_margin=50, no_image_text=True)
        else:
            cols = []
        if cols:
            for col_rect in cols:
                col_text = page.get_text(clip=col_rect, sort=True)
                full_text.append(col_text.strip())
        else:
            full_text.append(page.get_text(sort=True).strip())
    doc.close()
    return "\n\n".join(t for t in full_text if t)


# ---------------------------------------------------------------------------
# DOCX parser — paragraph/table interleave order preserved (PROFILE-03)
# ---------------------------------------------------------------------------


def extract_docx_text(path: str | Path) -> str:
    """Extract text from DOCX preserving paragraph/table interleave order.

    Uses iter_inner_content() rather than doc.paragraphs so that table rows
    are included in their correct position relative to surrounding paragraphs.
    """
    from docx import Document  # python-docx

    doc = Document(str(path))
    parts: list[str] = []
    for item in doc.element.body.iter_inner_content():
        # Paragraphs expose .text; tables expose .rows
        if hasattr(item, "text") and item.text.strip():
            parts.append(item.text.strip())
        elif hasattr(item, "rows"):
            for row in item.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                )
                if row_text:
                    parts.append(row_text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main dispatcher (PROFILE-01, PROFILE-04)
# ---------------------------------------------------------------------------


def parse_resume(path: str | Path | None, fallback_text: str | None = None) -> str:
    """Parse resume from file or fall back to plain text.

    Args:
        path: Absolute or relative path to a .pdf or .docx file.
        fallback_text: Raw resume text pasted by the user (used when path
            is None or file parsing fails).

    Returns:
        Raw text string ready for LLM extraction.

    Raises:
        ResumeParseError: If no input is provided, the file type is
            unsupported, or the file cannot be parsed.
    """
    if path is not None:
        path = Path(path)
        if path.suffix.lower() == ".pdf":
            try:
                return extract_pdf_text(path)
            except Exception as exc:
                raise ResumeParseError(f"PDF parsing failed: {exc}") from exc
        elif path.suffix.lower() == ".docx":
            try:
                return extract_docx_text(path)
            except Exception as exc:
                raise ResumeParseError(f"DOCX parsing failed: {exc}") from exc
        else:
            raise ResumeParseError(
                f"Unsupported file type: {path.suffix}. Use PDF or DOCX (.doc files must be converted to .docx first)."
            )
    if fallback_text:
        return fallback_text
    raise ResumeParseError("No resume file or fallback text provided.")


# ---------------------------------------------------------------------------
# PydanticAI extraction agent (PROFILE-05, PROFILE-06)
# ---------------------------------------------------------------------------


@dataclass
class ProfileDeps:
    """Dependency container injected into profile_agent at runtime."""

    resume_text: str


profile_agent: Agent[ProfileDeps, UserProfile] = Agent(
    "anthropic:claude-3-5-haiku-latest",  # overridden per config in production
    deps_type=ProfileDeps,
    output_type=UserProfile,
    defer_model_check=True,  # allow import without ANTHROPIC_API_KEY set
    system_prompt=(
        "Extract a structured UserProfile from the resume text provided in "
        "your context. "
        "skills must be specific technologies and tools only (Python, React, "
        "PostgreSQL) — not soft skills (leadership, communication). "
        "experience entries should be concise: 'Role at Company, Year-Year'. "
        "If a field cannot be determined, return null for optional fields "
        "(github_url, linkedin_url). "
        "resume_raw_text must contain the full raw text passed to you."
    ),
)


@profile_agent.system_prompt
async def inject_resume(ctx: RunContext[ProfileDeps]) -> str:
    """Append resume text to the agent's system prompt at each run."""
    return f"\n\nRESUME TEXT:\n{ctx.deps.resume_text}"


# ---------------------------------------------------------------------------
# Completeness validation (PROFILE-09)
# ---------------------------------------------------------------------------


def validate_profile(profile: UserProfile) -> tuple[bool, str]:
    """Reject extraction if fewer than 10 % of the 9 UserProfile fields
    are meaningfully populated.

    The 9 tracked fields are: name, headline, skills, experience, education,
    projects, github_url, linkedin_url, resume_raw_text.

    Returns:
        (True, "")           — profile is acceptable
        (False, reason_str)  — profile too sparse; reason explains why
    """
    fields: list[object] = [
        profile.name,
        profile.headline,
        profile.skills,
        profile.experience,
        profile.education,
        profile.projects,
        profile.github_url,
        profile.linkedin_url,
        profile.resume_raw_text,
    ]
    populated = sum(
        1
        for f in fields
        if f is not None
        and (
            (isinstance(f, list) and len(f) > 0)
            or (isinstance(f, str) and f.strip() != "")
        )
    )
    threshold = max(1, int(len(fields) * 0.10))  # 10 % of 9 == 0 → at least 1
    if populated < threshold:
        return (
            False,
            f"Only {populated}/{len(fields)} fields extracted. "
            "Retry with plain text.",
        )
    return True, ""


# ---------------------------------------------------------------------------
# Orchestration (PROFILE-07, PROFILE-08)
# ---------------------------------------------------------------------------


async def extract_profile(
    resume_text: str,
    session: AsyncSession,
    model_override: str | None = None,
) -> db_models.UserProfile:
    """Run profile_agent, validate, and persist UserProfile to SQLite.

    Steps:
        1. Run profile_agent with resume_text as deps.
        2. Validate completeness via validate_profile().
        3. Map Pydantic BaseModel -> SQLModel table row.
        4. Persist and refresh the record.

    Args:
        resume_text:    Raw resume text (from parse_resume or plain-text
                        fallback).
        session:        Open AsyncSession for the current request.
        model_override: Optional Anthropic model string to override the
                        default.  Wired in Plan 02-06 (Orchestrator).

    Returns:
        Persisted db_models.UserProfile row (with auto-assigned id).

    Raises:
        ResumeParseError: If extraction result fails validate_profile().
    """
    agent = profile_agent
    result = await agent.run(
        "Extract the UserProfile from the resume text in your system prompt.",
        deps=ProfileDeps(resume_text=resume_text),
    )
    profile_schema: UserProfile = result.output

    is_valid, reason = validate_profile(profile_schema)
    if not is_valid:
        raise ResumeParseError(f"Extraction rejected: {reason}")

    # Map Pydantic schema -> SQLModel table row
    now = datetime.utcnow()
    db_profile = db_models.UserProfile(
        name=profile_schema.name,
        headline=profile_schema.headline or "",
        skills=profile_schema.skills,
        experience=[{"entry": e} for e in profile_schema.experience],
        education=[{"entry": e} for e in profile_schema.education],
        projects=[{"entry": p} for p in profile_schema.projects],
        github_url=profile_schema.github_url or "",
        linkedin_url=profile_schema.linkedin_url or "",
        resume_raw_text=profile_schema.resume_raw_text or resume_text,
        created_at=now,
        updated_at=now,
    )
    session.add(db_profile)
    await session.commit()
    await session.refresh(db_profile)
    return db_profile
