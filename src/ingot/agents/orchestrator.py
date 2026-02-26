"""
Orchestrator — campaign coordinator and sole agent router.

AGENT-07: This file must stay under 250 lines. Domain logic belongs in agents.
AGENT-05: Orchestrator is the ONLY module that imports multiple agents.

Phase 1 skeleton: run() delegates to the named agent.
Phase 2 adds: campaign memory, natural language routing, checkpoint logic.
"""
from __future__ import annotations

from ingot.agents.base import AgentDeps
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

    In Phase 1 this is a skeleton: run() delegates to the named agent and
    returns its raw output. Error handling and retry logic are added in Phase 2.
    """

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps

    async def run(self, agent_name: str, prompt: str = "", **kwargs: object) -> dict:
        """
        Dispatch a task to the named agent and return its result dict.

        Args:
            agent_name: Key in AGENT_REGISTRY.
            prompt: Input string passed to the PydanticAI agent.
            **kwargs: Additional keyword arguments forwarded to the agent run call.

        Returns:
            {"agent": agent_name, "success": True, "output": <agent output>}

        Raises:
            AgentError: Wraps any exception raised by the agent.
        """
        logger.info("dispatching", agent=agent_name)
        agent = get_agent(agent_name)
        try:
            result = await agent.run(prompt, deps=self.deps, **kwargs)
            return {"agent": agent_name, "success": True, "output": result.output}
        except Exception as exc:
            raise AgentError(
                "Orchestrator",
                f"Agent '{agent_name}' failed: {exc}",
                cause=exc,
            ) from exc

    def list_available_agents(self) -> list[str]:
        """Return sorted list of all registered agent names."""
        return list_agents()
