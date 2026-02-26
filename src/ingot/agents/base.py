"""
Agent dependency injection types.

All agents receive resources via AgentDeps — never via global state.
This makes agents testable (inject mocks) and independently deployable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

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


@runtime_checkable
class AgentBase(Protocol):
    """
    Protocol that all 7 agent modules must satisfy.
    Not enforced at runtime (duck typing), but documents the contract.
    """

    async def run(self, deps: AgentDeps, **kwargs) -> dict: ...
