"""INGOT models package — Pydantic output schemas for all Phase 2 agents."""
from ingot.models.schemas import (
    EmailDraft,
    IntelBriefFull,
    IntelBriefPhase1,
    MatchResult,
    MCQAnswers,
    UserProfile,
)

__all__ = [
    "UserProfile",
    "IntelBriefPhase1",
    "IntelBriefFull",
    "MatchResult",
    "MCQAnswers",
    "EmailDraft",
]
