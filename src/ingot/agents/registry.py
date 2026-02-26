"""
Agent registry — dict[str, Any] mapping agent names to PydanticAI Agent instances.

In v2, this becomes dynamic discovery via entry points or a plugin dir scan.
In v1, agents register explicitly by calling register_agent() at import time.
"""
from __future__ import annotations

from typing import Any

AGENT_REGISTRY: dict[str, Any] = {}


def register_agent(name: str, agent: Any) -> None:
    """Register an agent by name. Called from each agent module at import time."""
    AGENT_REGISTRY[name] = agent


def get_agent(name: str) -> Any:
    """Retrieve agent by name. Raises KeyError if not registered."""
    if name not in AGENT_REGISTRY:
        registered = list(AGENT_REGISTRY.keys())
        raise KeyError(
            f"Agent '{name}' not in registry. Registered: {registered}"
        )
    return AGENT_REGISTRY[name]


def list_agents() -> list[str]:
    """Return sorted list of registered agent names."""
    return sorted(AGENT_REGISTRY.keys())
