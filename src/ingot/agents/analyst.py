# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""
Analyst agent — tracks campaign metrics and feeds insights back to Writer.

Pipeline:  aggregate → identify_patterns → generate_insights

Tools the LLM can call during this pipeline:
  - query_campaign_stats: pull open/reply/bounce counts from DB for a campaign
  - compare_cohorts: compare two cohorts of emails (e.g., different subject variants)
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
        "You are a campaign analytics agent for INGOT. "
        "Track open rates, reply rates, and response patterns. "
        "Identify what resonates and produce actionable insights for the Writer agent. "
        "Use query_campaign_stats to pull metrics and compare_cohorts to spot patterns."
    ),
)


@_agent.tool
async def query_campaign_stats(ctx: RunContext[AgentDeps], campaign_id: int) -> dict:
    """Return open/reply/bounce counts and rates for a campaign from the database."""
    # Phase 4: aggregate AgentLog + Email rows for the given campaign
    raise NotImplementedError("Phase 4")


@_agent.tool
async def compare_cohorts(
    ctx: RunContext[AgentDeps], cohort_a: str, cohort_b: str
) -> dict:
    """
    Compare two named email cohorts (e.g., subject variant A vs B).
    Returns delta metrics: open_rate_diff, reply_rate_diff, sample_sizes.
    """
    # Phase 4: DB aggregation + statistical significance check
    raise NotImplementedError("Phase 4")


class AnalystAgent:
    """Aggregates campaign metrics, finds patterns, and generates Writer feedback."""

    STEPS: ClassVar[list[str]] = ["aggregate", "identify_patterns", "generate_insights"]

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
            agent_name="analyst",
            success=all(r.success for r in completed),
            steps=completed,
            final_output=completed[-1].output if completed else None,
        )

    async def run_step(self, step: str, deps: AgentDeps, **kwargs) -> StepResult:
        """Dispatch a single named step to its implementation method."""
        match step:
            case "aggregate":
                return await self._aggregate(deps, **kwargs)
            case "identify_patterns":
                return await self._identify_patterns(deps, **kwargs)
            case "generate_insights":
                return await self._generate_insights(deps, **kwargs)
            case _:
                raise ValueError(f"Analyst has no step '{step}'. Valid: {self.STEPS}")

    async def _aggregate(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 4: pull open/reply/bounce stats from DB
        return StepResult(step="aggregate", success=True, output={})

    async def _identify_patterns(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 4: LLM + cohort comparison to find what subject lines/tones perform best
        return StepResult(step="identify_patterns", success=True, output={})

    async def _generate_insights(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 4: structured insight dict fed back to Writer's context
        return StepResult(step="generate_insights", success=True, output={})


analyst = AnalystAgent()
register_agent("analyst", analyst)
