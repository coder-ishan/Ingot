"""
INGOT agent package.

Importing this package triggers register_agent() for all 6 non-Orchestrator agents.
The Orchestrator class is available via ingot.agents.orchestrator.Orchestrator.
"""
# Import all agent modules to populate AGENT_REGISTRY at package import time.
from ingot.agents import (  # noqa: F401
    analyst,
    matcher,
    outreach,
    research,
    scout,
    writer,
)
from ingot.agents.base import AgentBase, AgentDeps
from ingot.agents.exceptions import (
    AgentError,
    ConfigError,
    DBError,
    IngotError,
    LLMError,
    LLMValidationError,
    ValidationError,
)
from ingot.agents.registry import AGENT_REGISTRY, get_agent, list_agents

__all__ = [
    # deps / protocol
    "AgentDeps",
    "AgentBase",
    # registry
    "AGENT_REGISTRY",
    "get_agent",
    "list_agents",
    # exceptions
    "IngotError",
    "LLMError",
    "LLMValidationError",
    "DBError",
    "ConfigError",
    "ValidationError",
    "AgentError",
]
