# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""
Research agent — builds deep IntelBrief per lead.

Pipeline:  fetch_company → fetch_person → identify_signals → synthesise

Tools the LLM can call during this pipeline:
  - search_web: run a web search query, returns list of result snippets
  - fetch_page: HTTP GET an arbitrary URL, returns text content
"""
from __future__ import annotations

from typing import ClassVar

from pydantic_ai import Agent, RunContext

from ingot.agents.base import AgentDeps, AgentRunResult, StepResult
from ingot.agents.registry import register_agent

_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are a deep research agent for INGOT. "
        "Build comprehensive IntelBriefs per lead: company intelligence, "
        "person intelligence, recent signals, and personalized talking points. "
        "Use search_web and fetch_page to gather current information."
    ),
)


@_agent.tool
async def search_web(ctx: RunContext[AgentDeps], query: str) -> list[str]:
    """Run a web search and return a list of result snippets."""
    # Phase 2: DuckDuckGo or SerpAPI via http_client
    raise NotImplementedError("Phase 2")


@_agent.tool
async def fetch_page(ctx: RunContext[AgentDeps], url: str) -> str:
    """Fetch and return the text content of a web page."""
    # Phase 2: httpx GET with optional Playwright fallback for SPAs
    raise NotImplementedError("Phase 2")


class ResearchAgent:
    """Builds IntelBrief for a single lead: company, person, signals, talking points."""

    STEPS: ClassVar[list[str]] = [
        "fetch_company",
        "fetch_person",
        "identify_signals",
        "synthesise",
    ]

    async def run(
        self,
        deps: AgentDeps,
        prompt: str = "",
        steps: list[str] | None = None,
        **kwargs,
    ) -> AgentRunResult:
        """Execute the full pipeline or a specified subset of steps."""
        targets = steps if steps is not None else self.STEPS
        completed: list[StepResult] = []
        for step in targets:
            result = await self.run_step(step, deps, **kwargs)
            completed.append(result)
            if not result.success:
                break
        return AgentRunResult(
            agent_name="research",
            success=all(r.success for r in completed),
            steps=completed,
            final_output=completed[-1].output if completed else None,
        )

    async def run_step(self, step: str, deps: AgentDeps, **kwargs) -> StepResult:
        """Dispatch a single named step to its implementation method."""
        match step:
            case "fetch_company":
                return await self._fetch_company(deps, **kwargs)
            case "fetch_person":
                return await self._fetch_person(deps, **kwargs)
            case "identify_signals":
                return await self._identify_signals(deps, **kwargs)
            case "synthesise":
                return await self._synthesise(deps, **kwargs)
            case _:
                raise ValueError(f"Research has no step '{step}'. Valid: {self.STEPS}")

    async def _fetch_company(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: search + fetch company page → structured company intel
        return StepResult(step="fetch_company", success=True, output={})

    async def _fetch_person(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: search LinkedIn/Twitter/GitHub for target person
        return StepResult(step="fetch_person", success=True, output={})

    async def _identify_signals(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: recent funding, hiring posts, blog posts, GitHub activity
        return StepResult(step="identify_signals", success=True, output={})

    async def _synthesise(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: LLM synthesises company + person + signals → IntelBrief + talking points
        return StepResult(step="synthesise", success=True, output={})


research = ResearchAgent()
register_agent("research", research)
