"""Tests for ingot.agents.orchestrator.Orchestrator.

These tests verify the routing and error-wrapping contracts that make
Orchestrator the single coordination point in the pipeline:
- run() delegates to the correct registered agent
- run() wraps non-AgentError exceptions in AgentError (typed error boundary)
- run_step() delegates to the correct agent's run_step()
- run_step() wraps exceptions in AgentError
- list_available_agents() reflects what's in the registry
- list_steps() returns the agent's declared STEPS
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ingot.agents.base import AgentDeps, AgentRunResult, StepResult
from ingot.agents.exceptions import AgentError
from ingot.agents.orchestrator import Orchestrator
from ingot.llm.client import LLMClient


def make_deps() -> AgentDeps:
    return AgentDeps(
        llm_client=MagicMock(spec=LLMClient),
        session=MagicMock(),
        http_client=MagicMock(spec=httpx.AsyncClient),
    )


@pytest.fixture
def orc() -> Orchestrator:
    return Orchestrator(deps=make_deps())


async def test_run_delegates_to_registered_agent(orc):
    """run() must pass through to the named agent in the registry."""
    expected = AgentRunResult(agent_name="scout", success=True, steps=[])
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=expected)

    with patch("ingot.agents.orchestrator.get_agent", return_value=mock_agent):
        result = await orc.run("scout", prompt="find leads")

    mock_agent.run.assert_awaited_once()
    assert result is expected


async def test_run_wraps_exception_in_agent_error(orc):
    """Unexpected exceptions from agents must be wrapped as AgentError."""
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(side_effect=RuntimeError("agent blew up"))

    with patch("ingot.agents.orchestrator.get_agent", return_value=mock_agent):
        with pytest.raises(AgentError) as exc_info:
            await orc.run("scout")

    assert "scout" in str(exc_info.value)


async def test_run_step_delegates_to_agent(orc):
    """run_step() must delegate to the named agent's run_step()."""
    expected = StepResult(step="discover", success=True)
    mock_agent = MagicMock()
    mock_agent.run_step = AsyncMock(return_value=expected)

    with patch("ingot.agents.orchestrator.get_agent", return_value=mock_agent):
        result = await orc.run_step("scout", "discover")

    mock_agent.run_step.assert_awaited_once_with("discover", orc.deps)
    assert result is expected


async def test_run_step_wraps_exception_in_agent_error(orc):
    """Step-level exceptions must be wrapped as AgentError."""
    mock_agent = MagicMock()
    mock_agent.run_step = AsyncMock(side_effect=ValueError("bad step state"))

    with patch("ingot.agents.orchestrator.get_agent", return_value=mock_agent):
        with pytest.raises(AgentError) as exc_info:
            await orc.run_step("scout", "discover")

    assert "discover" in str(exc_info.value)


def test_list_available_agents_uses_registry(orc):
    """list_available_agents() must reflect the registry contents."""
    agents = orc.list_available_agents()
    # All 6 non-orchestrator agents should be registered
    for name in ["scout", "research", "matcher", "writer", "outreach", "analyst"]:
        assert name in agents


def test_list_steps_returns_agent_steps(orc):
    """list_steps() must return the STEPS declared by the named agent."""
    steps = orc.list_steps("scout")
    assert steps == ["discover", "deduplicate", "score"]


def test_list_steps_matcher(orc):
    steps = orc.list_steps("matcher")
    assert steps == ["load_profile", "compare", "score"]
