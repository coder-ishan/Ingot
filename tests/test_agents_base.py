"""Tests for ingot.agents.base."""
from unittest.mock import MagicMock

import httpx

from ingot.agents.base import AgentDeps, AgentRunResult, StepResult
from ingot.llm.client import LLMClient


def make_deps():
    return AgentDeps(
        llm_client=MagicMock(spec=LLMClient),
        session=MagicMock(),
        http_client=MagicMock(spec=httpx.AsyncClient),
    )


def test_agent_deps_construction():
    deps = make_deps()
    assert deps.verbosity == 0
    assert deps.agent_name == ""


def test_step_result_success():
    s = StepResult(step="fetch", success=True, output={"data": 42})
    assert s.success
    assert s.output["data"] == 42


def test_step_result_failure():
    err = RuntimeError("boom")
    s = StepResult(step="score", success=False, error=err)
    assert not s.success
    assert s.error is err


def test_agent_run_result_failed_step_none():
    run = AgentRunResult(
        agent_name="scout",
        success=True,
        steps=[StepResult("a", True), StepResult("b", True)],
    )
    assert run.failed_step is None


def test_agent_run_result_failed_step_returns_first():
    run = AgentRunResult(
        agent_name="scout",
        success=False,
        steps=[
            StepResult("a", True),
            StepResult("b", False, error=RuntimeError("err1")),
            StepResult("c", False, error=RuntimeError("err2")),
        ],
    )
    assert run.failed_step.step == "b"
