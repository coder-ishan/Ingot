"""Tests for agent pipeline contracts.

Phase 1: run(), run_step(), error propagation for PydanticAI-based agents.
Phase 2: New function-based agent contracts (scout_run, run_writer, etc.).

These tests verify the behavioral contracts the Orchestrator relies on.
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


# ─── Scout (Phase 2 function-based) ──────────────────────────────────────────

class TestScoutPipeline:
    """Tests for Phase 2 Scout: plain async function, typed ScoutDeps, no LLM."""

    def test_scout_run_is_importable(self):
        from ingot.agents.scout import scout_run, ScoutDeps
        import asyncio
        assert callable(scout_run)
        assert ScoutDeps is not None

    def test_scout_deps_has_required_fields(self):
        from ingot.agents.scout import ScoutDeps
        import dataclasses
        fields = {f.name for f in dataclasses.fields(ScoutDeps)}
        assert "http_client" in fields
        assert "session" in fields
        assert "user_skills" in fields
        assert "max_leads" in fields
        assert "min_leads" in fields

    def test_validate_company_record_accepts_complete_record(self):
        from ingot.agents.scout import _validate_company_record
        valid, reason = _validate_company_record({"name": "Acme", "website": "acme.com"})
        assert valid
        assert reason == ""

    def test_validate_company_record_rejects_empty_name_and_website(self):
        from ingot.agents.scout import _validate_company_record
        valid, reason = _validate_company_record({"name": "", "website": ""})
        assert not valid
        assert reason != ""

    def test_scout_registered_in_registry(self):
        from ingot.agents.registry import AGENT_REGISTRY
        import ingot.agents.scout  # noqa — trigger registration
        assert "scout" in AGENT_REGISTRY


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


# ─── Writer (Phase 2 function-based) ─────────────────────────────────────────

class TestWriterPipeline:
    """Tests for Phase 2 Writer: run_writer() async function with WriterDeps.

    Writer is implemented in Phase 2 plan 02-07. These tests verify basic
    importability; full behavioral tests are added in that plan.
    """

    def test_run_writer_is_importable(self):
        """Writer module should import without errors."""
        import ingot.agents.writer  # noqa — verify importable
        assert ingot.agents.writer is not None


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
