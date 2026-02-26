# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""Scout agent — discovers and qualifies startup leads from configured venues."""
from __future__ import annotations

from pydantic_ai import Agent

from ingot.agents.base import AgentDeps
from ingot.agents.registry import register_agent

scout_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",  # Overridden at runtime from per-agent config
    deps_type=AgentDeps,
    defer_model_check=True,  # Model is injected from config; not validated at import time
    system_prompt=(
        "You are a lead discovery agent for INGOT. "
        "You discover and qualify startup leads from venues for personalized outreach."
    ),
)

register_agent("scout", scout_agent)
