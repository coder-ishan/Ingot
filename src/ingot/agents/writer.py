# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""
Writer agent — composes personalized cold emails from Lead + IntelBrief + ValueProp.

Pipeline:  draft → generate_subjects → draft_followups

Tools the LLM can call during this pipeline:
  - load_intel_brief: fetch IntelBrief record from DB for a given lead
  - get_tone_guide: return tone and style instructions for a recipient role
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
        "You are an email composition agent for INGOT. "
        "Write highly personalized cold outreach emails using the lead's IntelBrief "
        "and the user's matched value proposition. "
        "Use load_intel_brief to retrieve research and get_tone_guide to adapt style. "
        "Produce 2 subject line variants and Day-3 and Day-7 follow-up drafts."
    ),
)


@_agent.tool
async def load_intel_brief(ctx: RunContext[AgentDeps], lead_id: int) -> dict:
    """Fetch the IntelBrief for a lead from the database."""
    # Phase 2: query IntelBrief table via ctx.deps.session
    raise NotImplementedError("Phase 2")


@_agent.tool
async def get_tone_guide(ctx: RunContext[AgentDeps], recipient_role: str) -> str:
    """
    Return tone and length guidance for a given recipient role.
    recipient_role: one of 'ceo', 'cto', 'recruiter', 'hiring_manager', 'engineer'
    """
    # Phase 2: role → tone template (formal/casual, short/long, CTA style)
    raise NotImplementedError("Phase 2")


class WriterAgent:
    """Drafts email body, 2 subject variants, and Day-3/Day-7 follow-up sequences."""

    STEPS: ClassVar[list[str]] = ["draft", "generate_subjects", "draft_followups"]

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
            agent_name="writer",
            success=all(r.success for r in completed),
            steps=completed,
            final_output=completed[-1].output if completed else None,
        )

    async def run_step(self, step: str, deps: AgentDeps, **kwargs) -> StepResult:
        match step:
            case "draft":
                return await self._draft(deps, **kwargs)
            case "generate_subjects":
                return await self._generate_subjects(deps, **kwargs)
            case "draft_followups":
                return await self._draft_followups(deps, **kwargs)
            case _:
                raise ValueError(f"Writer has no step '{step}'. Valid: {self.STEPS}")

    async def _draft(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: LLM drafts email body using IntelBrief + ValueProp + tone guide
        return StepResult(step="draft", success=True, output={})

    async def _generate_subjects(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: generate 2 subject line variants for A/B testing
        return StepResult(step="generate_subjects", success=True, output={})

    async def _draft_followups(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 2: draft Day-3 and Day-7 follow-up emails for non-replies
        return StepResult(step="draft_followups", success=True, output={})


writer = WriterAgent()
register_agent("writer", writer)
