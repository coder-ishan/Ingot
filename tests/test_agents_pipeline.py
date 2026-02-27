"""Tests for agent pipeline contracts: run(), run_step(), error propagation.

These tests verify the behavioral contracts the Orchestrator relies on:
- run() executes steps in declared order
- run() stops at the first failed step
- run() respects a subset of steps when passed explicitly
- run_step() dispatches to the correct step implementation
- run_step() raises ValueError for unknown step names
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ingot.agents.base import AgentDeps, AgentRunResult, StepResult
from ingot.llm.client import LLMClient


def make_deps() -> AgentDeps:
    return AgentDeps(
        llm_client=MagicMock(spec=LLMClient),
        session=MagicMock(),
        http_client=MagicMock(spec=httpx.AsyncClient),
    )


# ─── ScoutAgent ───────────────────────────────────────────────────────────────

class TestScoutPipeline:
    @pytest.fixture
    def scout(self):
        from ingot.agents.scout import ScoutAgent
        return ScoutAgent()

    async def test_run_executes_all_steps(self, scout):
        result = await scout.run(make_deps())
        assert result.success
        assert [s.step for s in result.steps] == ["discover", "deduplicate", "score"]

    async def test_run_stops_on_first_failure(self, scout):
        """If 'deduplicate' fails, 'score' must not run."""
        fail = StepResult(step="deduplicate", success=False, error=RuntimeError("db error"))
        with patch.object(scout, "_deduplicate", AsyncMock(return_value=fail)):
            result = await scout.run(make_deps())
        assert not result.success
        step_names = [s.step for s in result.steps]
        assert "score" not in step_names

    async def test_run_partial_steps(self, scout):
        result = await scout.run(make_deps(), steps=["discover"])
        assert len(result.steps) == 1
        assert result.steps[0].step == "discover"

    async def test_run_step_invalid_raises_value_error(self, scout):
        with pytest.raises(ValueError, match="Scout has no step"):
            await scout.run_step("nonexistent", make_deps())

    async def test_run_step_discover(self, scout):
        result = await scout.run_step("discover", make_deps())
        assert result.success
        assert result.step == "discover"


# ─── AnalystAgent ─────────────────────────────────────────────────────────────

class TestAnalystPipeline:
    @pytest.fixture
    def analyst(self):
        from ingot.agents.analyst import AnalystAgent
        return AnalystAgent()

    async def test_run_executes_all_steps(self, analyst):
        result = await analyst.run(make_deps())
        assert result.success
        assert [s.step for s in result.steps] == ["aggregate", "identify_patterns", "generate_insights"]

    async def test_run_step_invalid_raises_value_error(self, analyst):
        with pytest.raises(ValueError, match="Analyst has no step"):
            await analyst.run_step("nonexistent", make_deps())

    async def test_run_step_aggregate(self, analyst):
        result = await analyst.run_step("aggregate", make_deps())
        assert result.success


# ─── MatcherAgent ─────────────────────────────────────────────────────────────

class TestMatcherPipeline:
    @pytest.fixture
    def matcher(self):
        from ingot.agents.matcher import MatcherAgent
        return MatcherAgent()

    async def test_run_executes_all_steps(self, matcher):
        result = await matcher.run(make_deps())
        assert result.success
        assert [s.step for s in result.steps] == ["load_profile", "compare", "score"]

    async def test_run_step_invalid_raises_value_error(self, matcher):
        with pytest.raises(ValueError, match="Matcher has no step"):
            await matcher.run_step("nonexistent", make_deps())

    async def test_all_steps_reachable(self, matcher):
        deps = make_deps()
        for step in ["load_profile", "compare", "score"]:
            r = await matcher.run_step(step, deps)
            assert r.success, f"Step '{step}' returned failure unexpectedly"


# ─── ResearchAgent ────────────────────────────────────────────────────────────

class TestResearchPipeline:
    @pytest.fixture
    def research(self):
        from ingot.agents.research import ResearchAgent
        return ResearchAgent()

    async def test_run_executes_all_steps(self, research):
        result = await research.run(make_deps())
        assert result.success

    async def test_run_step_invalid_raises_value_error(self, research):
        with pytest.raises(ValueError):
            await research.run_step("nonexistent", make_deps())


# ─── WriterAgent ──────────────────────────────────────────────────────────────

class TestWriterPipeline:
    """Tests for Phase 2 Writer: run_writer() async function with WriterDeps.

    Writer uses factory pattern (create_writer_agent(model)) — no WriterAgent class.
    """

    def test_run_writer_is_importable(self):
        from ingot.agents.writer import run_writer, WriterDeps, create_writer_agent
        import inspect
        assert callable(run_writer)
        assert WriterDeps is not None
        assert callable(create_writer_agent)
        assert inspect.iscoroutinefunction(run_writer)


# ─── OutreachAgent ────────────────────────────────────────────────────────────

class TestOutreachPipeline:
    @pytest.fixture
    def outreach(self):
        from ingot.agents.outreach import OutreachAgent
        return OutreachAgent()

    async def test_run_executes_all_steps(self, outreach):
        result = await outreach.run(make_deps())
        assert result.success

    async def test_run_step_invalid_raises_value_error(self, outreach):
        with pytest.raises(ValueError):
            await outreach.run_step("nonexistent", make_deps())
