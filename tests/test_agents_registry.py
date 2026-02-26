"""Tests for ingot.agents.registry."""
import pytest

from ingot.agents.registry import AGENT_REGISTRY, get_agent, list_agents, register_agent


@pytest.fixture(autouse=True)
def _clean_registry():
    """Backup and restore AGENT_REGISTRY around each test."""
    snapshot = dict(AGENT_REGISTRY)
    yield
    AGENT_REGISTRY.clear()
    AGENT_REGISTRY.update(snapshot)


def test_register_and_get():
    mock_agent = object()
    register_agent("test_agent", mock_agent)
    assert get_agent("test_agent") is mock_agent


def test_get_missing_raises_key_error():
    with pytest.raises(KeyError, match="not in registry"):
        get_agent("nonexistent_agent_xyz")


def test_list_agents_sorted():
    AGENT_REGISTRY.clear()
    register_agent("zebra", object())
    register_agent("apple", object())
    register_agent("mango", object())
    assert list_agents() == ["apple", "mango", "zebra"]
