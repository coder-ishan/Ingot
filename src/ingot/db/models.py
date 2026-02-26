"""All 11 SQLModel table models for INGOT.

Import this module (or individual models) to register them in SQLModel.metadata
before calling create_all() or running Alembic autogenerate.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Enum types (stored as str in SQLite — no database-level enum)
# ---------------------------------------------------------------------------

class LeadStatus(str, enum.Enum):
    discovered = "discovered"
    researching = "researching"
    matched = "matched"
    drafted = "drafted"
    sent = "sent"
    replied = "replied"


class EmailStatus(str, enum.Enum):
    drafted = "drafted"
    approved = "approved"
    sent = "sent"
    bounced = "bounced"
    opened = "opened"


class FollowUpStatus(str, enum.Enum):
    queued = "queued"
    sent = "sent"
    skipped = "skipped"


class CampaignStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UserProfile(SQLModel, table=True):
    """DB-01 — Candidate profile parsed from resume / LinkedIn."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    headline: str = ""
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    experience: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    education: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    projects: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    github_url: str = ""
    linkedin_url: str = ""
    resume_raw_text: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Lead(SQLModel, table=True):
    """DB-02 — A company / person discovered by the Scout agent."""
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str
    person_name: str = ""
    person_email: str = ""
    person_role: str = ""
    company_website: str = ""
    source_venue: str = ""
    status: LeadStatus = LeadStatus.discovered
    initial_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IntelBrief(SQLModel, table=True):
    """DB-03 — Research brief created by the Research agent for a lead."""
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str
    company_signals: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    person_name: str = ""
    person_role: str = ""
    company_website: str = ""
    person_background: str = ""
    talking_points: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    company_product_description: str = ""
    lead_id: Optional[int] = Field(default=None, foreign_key="lead.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Match(SQLModel, table=True):
    """DB-04 — Match score and value prop produced by the Matcher agent."""
    id: Optional[int] = Field(default=None, primary_key=True)
    match_score: float
    value_proposition: str
    confidence_level: str
    lead_id: Optional[int] = Field(default=None, foreign_key="lead.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Email(SQLModel, table=True):
    """DB-05 — Outreach email drafted by the Writer agent."""
    id: Optional[int] = Field(default=None, primary_key=True)
    subject_a: str
    subject_b: str = ""
    body: str
    tone_adapted_for: str = ""
    mcq_answers_json: str = "{}"
    status: EmailStatus = EmailStatus.drafted
    lead_id: Optional[int] = Field(default=None, foreign_key="lead.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FollowUp(SQLModel, table=True):
    """DB-06 — Scheduled follow-up messages for an email thread."""
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_email_id: Optional[int] = Field(default=None, foreign_key="email.id")
    scheduled_for_day: int
    body: str
    status: FollowUpStatus = FollowUpStatus.queued
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None


class Campaign(SQLModel, table=True):
    """DB-07 — A named outreach campaign grouping many leads."""
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    total_leads: int = 0
    total_sent: int = 0
    total_replied: int = 0
    status: CampaignStatus = CampaignStatus.active


class AgentLog(SQLModel, table=True):
    """DB-08 — Per-step execution log for each agent run."""
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_name: str
    step_description: str
    status: str
    duration_ms: int = 0
    error_message: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_estimate: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Venue(SQLModel, table=True):
    """DB-09 — Scout venue config (YC, LinkedIn, etc.)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    venue_name: str
    venue_type: str
    config_json: str = "{}"
    last_run_at: Optional[datetime] = None
    lead_count_discovered: int = 0
    last_error: str = ""


class OutreachMetric(SQLModel, table=True):
    """DB-10 — Rolling send-rate metrics for bounce / spam guard."""
    id: Optional[int] = Field(default=None, primary_key=True)
    sent_today: int = 0
    sent_this_hour: int = 0
    bounce_count: int = 0
    bounce_rate: float = 0.0
    last_sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UnsubscribedEmail(SQLModel, table=True):
    """DB-11 — Permanently unsubscribed addresses; never contact again."""
    id: Optional[int] = Field(default=None, primary_key=True)
    email_address: str = Field(index=True)
    unsubscribe_reason: str = ""
    unsubscribed_at: datetime = Field(default_factory=datetime.utcnow)
