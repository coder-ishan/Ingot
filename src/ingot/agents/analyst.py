# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""Analyst agent — tracks open/reply rates and feeds insights back to Writer context."""
from __future__ import annotations

from pydantic_ai import Agent

from ingot.agents.base import AgentDeps
from ingot.agents.registry import register_agent

analyst_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are a campaign analytics agent for INGOT. "
        "You track open rates, reply rates, and response patterns, "
        "identifying what resonates and feeding actionable insights back to the Writer."
    ),
)

register_agent("analyst", analyst_agent)
