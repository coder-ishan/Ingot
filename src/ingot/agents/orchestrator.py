"""
Orchestrator — campaign coordinator and sole agent router.

AGENT-07: This file must stay under 250 lines. Domain logic belongs in agents.
AGENT-05: Orchestrator is the ONLY module that imports multiple agents.

Phase 1 skeleton: run() and run_step() delegate to the named agent.
Phase 2 adds: campaign memory, natural language routing, checkpoint logic.
"""
from __future__ import annotations

from ingot.agents.base import AgentDeps, AgentRunResult, StepResult
from ingot.agents.exceptions import AgentError
from ingot.agents.registry import get_agent, list_agents
from ingot.logging_config import get_logger

# AGENT-05 exception: Orchestrator imports all agents to ensure they register.
from ingot.agents import (  # noqa: F401
    analyst,
    matcher,
    outreach,
    research,
    scout,
    writer,
)

logger = get_logger("ingot.orchestrator")


class Orchestrator:
    """
    Routes tasks to agents by name. Maintains campaign state (Phase 2).

    Phase 1 skeleton: run() and run_step() delegate directly to the named agent.
    Each agent exposes STEPS and run_step() — Orchestrator can execute a full
    pipeline or individual steps for checkpointing, retry, and partial runs.
    """

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps

    async def run(
        self,
        agent_name: str,
        prompt: str = "",
        steps: list[str] | None = None,
        **kwargs,
    ) -> AgentRunResult:
        """
        Run a named agent's full pipeline (or a subset of steps).

        Args:
            agent_name: Key in AGENT_REGISTRY.
            prompt: Optional natural-language instruction passed to the agent.
            steps: If provided, only execute these steps (must be subset of agent.STEPS).

        Returns:
            AgentRunResult with per-step results and final output.

        Raises:
            AgentError: Wraps any exception raised by the agent.
        """
        logger.info("dispatching", agent=agent_name, steps=steps)
        agent = get_agent(agent_name)
        try:
            return await agent.run(self.deps, prompt=prompt, steps=steps, **kwargs)
        except Exception as exc:
            raise AgentError(
                "Orchestrator",
                f"Agent '{agent_name}' failed: {exc}",
                cause=exc,
            ) from exc

    async def run_step(
        self, agent_name: str, step: str, **kwargs
    ) -> StepResult:
        """
        Execute a single step on a named agent.

        Used for: checkpointing long pipelines, retrying a failed step,
        and Phase 2 conditional routing between steps.

        Raises:
            AgentError: Wraps any exception raised by the step.
        """
        logger.info("dispatching step", agent=agent_name, step=step)
        agent = get_agent(agent_name)
        try:
            return await agent.run_step(step, self.deps, **kwargs)
        except Exception as exc:
            raise AgentError(
                "Orchestrator",
                f"Agent '{agent_name}' step '{step}' failed: {exc}",
                cause=exc,
            ) from exc

    def list_available_agents(self) -> list[str]:
        """Return sorted list of all registered agent names."""
        return list_agents()

    def list_steps(self, agent_name: str) -> list[str]:
        """Return the STEPS sequence declared by the named agent."""
        agent = get_agent(agent_name)
        return list(agent.STEPS)
