# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""Matcher agent — cross-references UserProfile against IntelBrief, produces match score."""
from __future__ import annotations

from pydantic_ai import Agent

from ingot.agents.base import AgentDeps
from ingot.agents.registry import register_agent

matcher_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are a qualification matching agent for INGOT. "
        "You cross-reference the user's resume and skills against each lead's "
        "opportunity, producing a 0-100 match score and a tailored value proposition."
    ),
)

register_agent("matcher", matcher_agent)
