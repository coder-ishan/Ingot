"""
Agent dependency injection types and pipeline contracts.

All agents receive resources via AgentDeps — never via global state.
This makes agents testable (inject mocks) and independently deployable.

AgentBase documents the contract every agent class must satisfy:
  - STEPS: ordered pipeline steps the agent executes
  - run_step(): execute one named step (enables checkpointing + retry)
  - run(): execute the full pipeline in sequence
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol, runtime_checkable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ingot.llm.client import LLMClient


@dataclass
class AgentDeps:
    """
    Dependency container injected into every agent via PydanticAI's deps_type.
    Construct once per agent invocation; do not share across concurrent runs.
    """

    llm_client: LLMClient
    session: AsyncSession
    http_client: httpx.AsyncClient
    verbosity: int = 0    # 0=normal, 1=-v, 2=-vv
    agent_name: str = ""  # Set by Orchestrator before dispatch


@dataclass
class StepResult:
    """
    Result of one pipeline step.

    Agents return this from run_step(). Orchestrator uses it to decide
    whether to continue, retry, or abort the pipeline.
    """

    step: str
    success: bool
    output: Any = None
    error: Exception | None = None


@dataclass
class AgentRunResult:
    """
    Full result of an agent pipeline run.

    Contains one StepResult per executed step. If a step fails, the pipeline
    stops and subsequent steps are absent from `steps`.
    """

    agent_name: str
    success: bool
    steps: list[StepResult] = field(default_factory=list)
    final_output: Any = None

    @property
    def failed_step(self) -> StepResult | None:
        """Return the first failed step, or None if all succeeded."""
        return next((s for s in self.steps if not s.success), None)


@runtime_checkable
class AgentBase(Protocol):
    """
    Contract every INGOT agent class must satisfy.

    Agents are not bare PydanticAI Agent instances — they are classes that
    wrap a PydanticAI Agent and expose a structured pipeline. This enables:

    1. Tool/function calling — each agent registers @agent.tool functions
       that the LLM can invoke during a step (web fetch, DB query, etc.)

    2. Step sequences — STEPS declares the ordered pipeline. Orchestrator
       can execute a subset (e.g., skip "score" if already scored), retry
       a single step without rerunning the whole pipeline, or checkpoint
       between steps for long-running runs.

    3. Testability — run_step() can be tested in isolation with mock deps,
       without standing up a full LLM or DB connection.

    Usage::

        class ScoutAgent:
            STEPS = ["discover", "deduplicate", "score"]

            async def run_step(self, step, deps, **kwargs) -> StepResult: ...
            async def run(self, deps, prompt="", **kwargs) -> AgentRunResult: ...

        # Tools are registered on the module-level PydanticAI Agent:
        @_agent.tool
        async def fetch_venue_page(ctx: RunContext[AgentDeps], url: str) -> str: ...
    """

    STEPS: ClassVar[list[str]]
    """
    Ordered list of pipeline step names.
    Orchestrator may pass a subset to run() to skip completed steps.
    """

    async def run(
        self,
        deps: AgentDeps,
        prompt: str = "",
        steps: list[str] | None = None,
        **kwargs: Any,
    ) -> AgentRunResult:
        """
        Execute the full pipeline (or a subset if `steps` is provided).

        Args:
            deps: Injected resources. Never passed as global state.
            prompt: Optional natural-language instruction for the run.
            steps: If given, only execute these steps (must be subset of STEPS).
        """
        ...

    async def run_step(
        self, step: str, deps: AgentDeps, **kwargs: Any
    ) -> StepResult:
        """
        Execute a single named step. Must be in STEPS.

        Orchestrator calls this for checkpointing, retry, and partial runs.
        Each step may invoke the agent's registered tools internally.
        """
        ...
