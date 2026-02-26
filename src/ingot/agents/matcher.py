# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""
Matcher agent — cross-references UserProfile against IntelBrief.

Pipeline:  load_profile → compare → score

Tools the LLM can call during this pipeline:
  - get_user_profile: load the UserProfile from DB as JSON
  - extract_requirements: parse a lead's context into structured requirements
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
        "You are a qualification matching agent for INGOT. "
        "Cross-reference the user's resume and skills against each lead's opportunity. "
        "Produce a 0-100 match score and a tailored value proposition. "
        "Use get_user_profile to load the user's background and extract_requirements "
        "to parse what the lead is looking for."
    ),
)


@_agent.tool
async def get_user_profile(ctx: RunContext[AgentDeps]) -> dict:
    """Load the UserProfile record from the database as a dict."""
    # Phase 2: query UserProfile table via ctx.deps.session
    raise NotImplementedError("Phase 2")


@_agent.tool
async def extract_requirements(ctx: RunContext[AgentDeps], lead_context: str) -> dict:
    """Parse a lead's job post / company context into structured hiring requirements."""
    # Phase 2: LLM extraction into {role, skills, experience_years, culture_signals}
    raise NotImplementedError("Phase 2")


class MatcherAgent:
    """Scores how well the user's profile matches a lead and generates a value prop."""

    STEPS: ClassVar[list[str]] = ["load_profile", "compare", "score"]

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
            agent_name="matcher",
            success=all(r.success for r in completed),
            steps=completed,
            final_output=completed[-1].output if completed else None,
        )

    async def run_step(self, step: str, deps: AgentDeps, **kwargs) -> StepResult:
        match step:
            case "load_profile":
                return await self._load_profile(deps, **kwargs)
            case "compare":
                return await self._compare(deps, **kwargs)
            case "score":
                return await self._score(deps, **kwargs)
            case _:
                raise ValueError(f"Matcher has no step '{step}'. Valid: {self.STEPS}")

    async def _load_profile(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: hydrate UserProfile from DB
        return StepResult(step="load_profile", success=True, output={})

    async def _compare(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: LLM compares UserProfile fields against lead requirements
        return StepResult(step="compare", success=True, output={})

    async def _score(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: produce match_score (0-100) + value_proposition string
        return StepResult(step="score", success=True, output={})


matcher = MatcherAgent()
register_agent("matcher", matcher)
