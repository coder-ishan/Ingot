"""Tests for ingot.agents.exceptions."""
import pytest

from ingot.agents.exceptions import (
    AgentError,
    ConfigError,
    DBError,
    IngotError,
    LLMError,
    LLMValidationError,
    ValidationError,
)


def test_ingot_error_str_no_cause():
    e = IngotError("something broke")
    assert str(e) == "something broke"


def test_ingot_error_str_with_cause():
    cause = ValueError("bad value")
    e = IngotError("wrapper", cause=cause)
    assert "bad value" in str(e)
    assert "ValueError" in str(e)


def test_llm_validation_error_stores_raw():
    e = LLMValidationError("parse failed", raw_content="<bad>xml")
    assert e.raw_content == "<bad>xml"


def test_agent_error_stores_agent_name():
    e = AgentError("scout", "scrape failed")
    assert e.agent_name == "scout"
    assert "scout" in str(e)


def test_hierarchy():
    assert issubclass(LLMError, IngotError)
    assert issubclass(LLMValidationError, IngotError)
    assert issubclass(DBError, IngotError)
    assert issubclass(ConfigError, IngotError)
    assert issubclass(ValidationError, IngotError)
    assert issubclass(AgentError, IngotError)
