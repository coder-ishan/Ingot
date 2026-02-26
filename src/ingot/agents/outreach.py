# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
"""
Outreach agent — manages send queue, IMAP reply polling, and follow-up scheduling.

Pipeline:  send → poll_replies → classify_replies → schedule_followups

Tools the LLM can call during this pipeline:
  - classify_reply: classify an IMAP reply as positive/negative/ooo/auto-reply

Phase 3 wiring: aiosmtplib and aioimaplib are imported here to validate that
the Phase 3 dependencies are installed. Actual SMTP/IMAP usage is implemented
in Phase 3.
"""
from __future__ import annotations

from typing import ClassVar

import aiosmtplib  # noqa: F401 — Phase 3 dependency validation
import aioimaplib  # noqa: F401 — Phase 3 dependency validation
from pydantic_ai import Agent, RunContext

from ingot.agents.base import AgentDeps, AgentRunResult, StepResult
from ingot.agents.registry import register_agent

_agent: Agent[AgentDeps, str] = Agent(
    "ollama:llama3.1",
    deps_type=AgentDeps,
    defer_model_check=True,
    system_prompt=(
        "You are an outreach execution agent for INGOT. "
        "Manage email sending (rate limiting, business-hours windows), "
        "poll IMAP for replies, classify responses, and schedule follow-ups. "
        "Use classify_reply to label each incoming reply."
    ),
)


@_agent.tool
async def classify_reply(ctx: RunContext[AgentDeps], email_body: str) -> str:
    """
    Classify an inbound reply into one of: positive, negative, ooo, auto_reply.
    Returns the classification label as a string.
    """
    # Phase 3: LLM classification with confidence threshold
    raise NotImplementedError("Phase 3")


class OutreachAgent:
    """Sends emails, polls IMAP, classifies replies, and queues follow-ups."""

    STEPS: ClassVar[list[str]] = [
        "send",
        "poll_replies",
        "classify_replies",
        "schedule_followups",
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
            agent_name="outreach",
            success=all(r.success for r in completed),
            steps=completed,
            final_output=completed[-1].output if completed else None,
        )

    async def run_step(self, step: str, deps: AgentDeps, **kwargs) -> StepResult:
        """Dispatch a single named step to its implementation method."""
        match step:
            case "send":
                return await self._send(deps, **kwargs)
            case "poll_replies":
                return await self._poll_replies(deps, **kwargs)
            case "classify_replies":
                return await self._classify_replies(deps, **kwargs)
            case "schedule_followups":
                return await self._schedule_followups(deps, **kwargs)
            case _:
                raise ValueError(f"Outreach has no step '{step}'. Valid: {self.STEPS}")

    async def _send(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 3: aiosmtplib send with rate limiting and business-hours gating
        return StepResult(step="send", success=True, output={})

    async def _poll_replies(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 3: aioimaplib IDLE or polling for new messages
        return StepResult(step="poll_replies", success=True, output={})

    async def _classify_replies(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 3: run classify_reply tool on each new message
        return StepResult(step="classify_replies", success=True, output={})

    async def _schedule_followups(self, deps: AgentDeps, **kwargs) -> StepResult:
        # Phase 3: APScheduler jobs for Day-3 and Day-7 follow-ups
        return StepResult(step="schedule_followups", success=True, output={})


outreach = OutreachAgent()
register_agent("outreach", outreach)
