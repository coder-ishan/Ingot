# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""Research agent — builds deep IntelBrief per lead (company, person, signals)."""
from __future__ import annotations

from pydantic_ai import Agent

from ingot.agents.base import AgentDeps
from ingot.agents.registry import register_agent

research_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are a deep research agent for INGOT. "
        "You build comprehensive IntelBriefs per lead: company intelligence, "
        "person intelligence, recent signals, and personalized talking points."
    ),
)

register_agent("research", research_agent)
