# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""
Scout agent — discovers and qualifies startup leads from configured venues.

Pipeline:  discover → deduplicate → score

Tools the LLM can call during this pipeline:
  - fetch_venue_page: HTTP GET a venue listing (YC, etc.)
  - extract_company_list: parse HTML into structured company entries
"""
from __future__ import annotations

from typing import ClassVar

from pydantic_ai import Agent, RunContext

from ingot.agents.base import AgentDeps, AgentRunResult, StepResult
from ingot.agents.registry import register_agent

# Module-level PydanticAI Agent — tools must be registered here (not inside the class).
_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are a lead discovery agent for INGOT. "
        "You discover and qualify startup leads from venues for personalized outreach. "
        "Use the available tools to fetch venue pages and extract company listings."
    ),
)


@_agent.tool
async def fetch_venue_page(ctx: RunContext[AgentDeps], url: str) -> str:
    """Fetch a venue listing page (e.g. YC batch page). Returns raw HTML."""
    # Phase 2: real HTTP fetch with rate limiting
    raise NotImplementedError("Phase 2")


@_agent.tool
async def extract_company_list(ctx: RunContext[AgentDeps], html: str) -> list[str]:
    """Parse a venue page HTML into a list of company name strings."""
    # Phase 2: CSS-selector or LLM-based extraction
    raise NotImplementedError("Phase 2")


class ScoutAgent:
    """Discovers leads, deduplicates against DB, and applies initial scoring."""

    STEPS: ClassVar[list[str]] = ["discover", "deduplicate", "score"]

    async def run(
        self,
        deps: AgentDeps,
        prompt: str = "",
        steps: list[str] | None = None,
        **kwargs,
    ) -> AgentRunResult:
        targets = steps if steps is not None else self.STEPS
        completed: list[StepResult] = []
        for step in targets:
            result = await self.run_step(step, deps, **kwargs)
            completed.append(result)
            if not result.success:
                break
        return AgentRunResult(
            agent_name="scout",
            success=all(r.success for r in completed),
            steps=completed,
            final_output=completed[-1].output if completed else None,
        )

    async def run_step(self, step: str, deps: AgentDeps, **kwargs) -> StepResult:
        match step:
            case "discover":
                return await self._discover(deps, **kwargs)
            case "deduplicate":
                return await self._deduplicate(deps, **kwargs)
            case "score":
                return await self._score(deps, **kwargs)
            case _:
                raise ValueError(f"Scout has no step '{step}'. Valid: {self.STEPS}")

    async def _discover(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: call _agent.run() with fetch_venue_page + extract_company_list tools
        return StepResult(step="discover", success=True, output={})

    async def _deduplicate(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: cross-reference discovered companies against leads already in DB
        return StepResult(step="deduplicate", success=True, output={})

    async def _score(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: apply initial qualification score (funding stage, team size, role fit)
        return StepResult(step="score", success=True, output={})


scout = ScoutAgent()
register_agent("scout", scout)
