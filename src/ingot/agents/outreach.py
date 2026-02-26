# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""Outreach agent — manages send queue, IMAP reply polling, and follow-up scheduling."""
from __future__ import annotations

from pydantic_ai import Agent

from ingot.agents.base import AgentDeps
from ingot.agents.registry import register_agent

# Phase 3 wiring — imported here to validate dependency is installed.
# Actual SMTP/IMAP usage is implemented in Phase 3.
import aiosmtplib  # noqa: F401
import aioimaplib  # noqa: F401

outreach_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are an outreach execution agent for INGOT. "
        "You manage email sending (rate limiting, business-hours windows), "
        "poll IMAP for replies, classify responses, and schedule follow-ups."
    ),
)

register_agent("outreach", outreach_agent)
