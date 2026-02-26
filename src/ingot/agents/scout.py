"""
Scout Agent — YC lead discovery via yc-oss JSON API.

Pipeline:
  1. Fetch YC companies from yc-oss GitHub Pages API (batch or all)
  2. Score each company against UserProfile skills using weighted formula
  3. Validate output: reject company if >20% required fields are None (SCOUT-04)
  4. Deduplicate against existing SQLite Lead records by email (SCOUT-06)
  5. Persist top 10-20 leads sorted by score as status="discovered" (SCOUT-08)

No LLM call — data is structured JSON; LLM is used in Research agent.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ingot.db.models import Lead, LeadStatus
from ingot.venues.yc import fetch_yc_companies
from ingot.scoring.scorer import ScoringWeights, score_lead, DEFAULT_WEIGHTS
from ingot.agents.registry import register_agent


@dataclass
class ScoutDeps:
    http_client: httpx.AsyncClient
    session: AsyncSession
    user_skills: list[str]                       # from UserProfile.skills
    resume_text: str = ""                        # for semantic scoring
    weights: ScoringWeights = field(default_factory=lambda: DEFAULT_WEIGHTS)
    batch: str | None = None                     # YC batch filter, None = recent batches
    max_leads: int = 20                          # CONTEXT.md: 10-20 leads per run
    min_leads: int = 10


_REQUIRED_FIELDS = ["name", "website"]  # fields checked for >20% None validation


def _validate_company_record(company: dict) -> tuple[bool, str]:
    """
    SCOUT-04: Reject if >20% of required fields are None/empty.
    Required fields: name, website.
    Returns (is_valid, reason).
    """
    none_count = sum(1 for f in _REQUIRED_FIELDS if not company.get(f))
    threshold = len(_REQUIRED_FIELDS) * 0.20
    if none_count > threshold:
        return False, f"{none_count}/{len(_REQUIRED_FIELDS)} required fields empty"
    return True, ""


async def _is_duplicate(session: AsyncSession, person_email: str) -> bool:
    """
    SCOUT-06: Case-insensitive email deduplication against existing Lead records.
    Returns True if this email already exists in any status.
    """
    if not person_email or person_email.strip() == "":
        return False  # No email = can't dedup; allow through
    result = await session.execute(
        select(Lead).where(Lead.person_email.ilike(person_email.strip()))
    )
    return result.scalars().first() is not None


def _company_to_lead_dict(company: dict, score: float) -> dict:
    """Map a yc-oss company dict to Lead table fields."""
    return {
        "company_name": company.get("name", ""),
        "person_name": "",            # populated in Research Phase 2
        "person_email": "",           # populated in Research Phase 2
        "person_role": "",            # populated in Research Phase 2
        "company_website": company.get("website", ""),
        "source_venue": "yc-oss",
        "status": LeadStatus.discovered,
        "initial_score": round(score, 4),
        "created_at": datetime.utcnow(),
        # Store yc-oss metadata as a note for Research agent
        "_yc_one_liner": company.get("one_liner", ""),
        "_yc_batch": company.get("batch", ""),
        "_yc_stage": company.get("stage", ""),
        "_yc_tags": ",".join(company.get("tags", [])),
        "_yc_is_hiring": company.get("isHiring", False),
    }


async def scout_run(deps: ScoutDeps) -> list[Lead]:
    """
    Run the Scout pipeline. Returns persisted Lead records sorted by score desc.

    SCOUT-01: Discovers leads from venues in parallel (asyncio.gather, YC only in v1)
    SCOUT-02: YC venue as primary discovery source
    SCOUT-05: User-agent set in fetch_yc_companies() via YC_HEADERS
    """
    # Step 1: Fetch — try recent batches first for fresher leads; fall back to all
    batches_to_try = ["winter-2025", "summer-2024"] if not deps.batch else [deps.batch]

    all_companies: list[dict] = []
    for batch in batches_to_try:
        try:
            companies = await fetch_yc_companies(deps.http_client, batch=batch)
            all_companies.extend(companies)
            if len(all_companies) >= 200:
                break
            await asyncio.sleep(0.5)  # SCOUT-05: request delay between fetches
        except Exception:
            continue  # Try next batch

    if not all_companies:
        # Ultimate fallback: all companies
        all_companies = await fetch_yc_companies(deps.http_client, batch=None)

    # Step 2: Score all companies
    scored: list[tuple[float, dict]] = []
    for company in all_companies:
        valid, _ = _validate_company_record(company)
        if not valid:
            continue
        s = score_lead(
            company,
            deps.user_skills,
            resume_text=deps.resume_text,
            weights=deps.weights,
        )
        scored.append((s, company))

    # Step 3: Sort by score descending, take top candidates for dedup check
    scored.sort(key=lambda x: x[0], reverse=True)
    top_candidates = scored[:deps.max_leads * 3]  # Check 3x to account for dedup losses

    # Step 4 + 5: Dedup and persist — update status BEFORE expensive operation (Pitfall 7)
    persisted_leads: list[Lead] = []
    for score, company in top_candidates:
        if len(persisted_leads) >= deps.max_leads:
            break

        company_website = company.get("website", "")
        # person_email is empty at Scout stage; dedup by website as proxy
        is_dup = await _is_duplicate(deps.session, company_website)
        if is_dup:
            continue

        lead_data = _company_to_lead_dict(company, score)
        # Remove internal _yc_* keys before creating Lead (not in schema)
        clean_data = {k: v for k, v in lead_data.items() if not k.startswith("_")}
        lead = Lead(**clean_data)
        deps.session.add(lead)
        await deps.session.commit()
        await deps.session.refresh(lead)
        persisted_leads.append(lead)

    return persisted_leads


# Register scout_run in the agent registry for Orchestrator discovery.
# Phase 2 note: Scout is a plain async function (no LLM needed for structured JSON data).
register_agent("scout", scout_run)
