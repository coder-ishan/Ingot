"""Pydantic output schemas for all Phase 2 PydanticAI agents.

These are the LLM extraction contracts (BaseModel) — distinct from the
SQLModel table models in src/ingot/db/models.py (the persistence layer).

All agents import their output_type from here. Nothing imports from agents.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class UserProfile(BaseModel):
    """Extracted from resume. Injected into Matcher and Writer as deps."""

    name: str
    headline: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)  # free-text entries, e.g. "Senior SWE at Stripe 2021-2023"
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    github_url: str | None = None
    linkedin_url: str | None = None
    resume_raw_text: str = ""


class IntelBriefPhase1(BaseModel):
    """Phase 1 Research output — lightweight, produced before approval gate."""

    company_name: str
    company_signals: list[str] = Field(default_factory=list)  # funding stage, size, growth signals
    person_name: str = ""
    person_role: str = ""
    company_website: str = ""


class IntelBriefFull(BaseModel):
    """Phase 2 Research output — full intel with talking points and person background."""

    company_name: str
    company_signals: list[str] = Field(default_factory=list)
    person_name: str = ""
    person_role: str = ""
    company_website: str = ""
    person_background: str = ""
    talking_points: list[str] = Field(default_factory=list, min_length=1, max_length=3)
    company_product_description: str = ""


class MatchResult(BaseModel):
    """Matcher agent output."""

    match_score: float = Field(ge=0.0, le=100.0)
    value_proposition: str  # specific to this company/role, not generic
    confidence_level: str  # "high" | "medium" | "low"


class MCQAnswers(BaseModel):
    """MCQ flow answers passed to Writer."""

    answers: dict[str, str] = Field(default_factory=dict)  # question -> answer
    skipped: bool = False


class EmailDraft(BaseModel):
    """Writer agent output — full draft set for one lead."""

    subject_a: str
    subject_b: str
    body: str
    tone_adapted_for: str  # "hr" | "cto" | "ceo" | "default"
    followup_day3: str
    followup_day7: str
    can_spam_footer: str

    @field_validator("body")
    @classmethod
    def body_must_be_sufficiently_long(cls, v: str, info: ValidationInfo) -> str:
        # Length heuristic — fails only if body is suspiciously short (< 100 chars). Not a company-name check.
        if len(v) < 100:
            raise ValueError("Email body is too short to be personalized (< 100 chars)")
        return v
