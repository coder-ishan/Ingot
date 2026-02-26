# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""Writer agent — composes personalized cold emails from Lead + IntelBrief + ValueProp."""
from __future__ import annotations

from pydantic_ai import Agent

from ingot.agents.base import AgentDeps
from ingot.agents.registry import register_agent

writer_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are an email composition agent for INGOT. "
        "You write highly personalized cold outreach emails using the lead's IntelBrief "
        "and the user's matched value proposition. Tone adapts by recipient role "
        "(HR, CEO, CTO). You produce 2 subject line variants and follow-up sequences."
    ),
)

register_agent("writer", writer_agent)
