from ingot.agents.exceptions import (
    AgentError,
    ConfigError,
    DBError,
    IngotError,
    LLMError,
    LLMValidationError,
    ValidationError,
)

# Populated by Plan 01-04 when agent shells are registered
AGENT_REGISTRY: dict = {}

__all__ = [
    "AGENT_REGISTRY",
    "IngotError",
    "LLMError",
    "LLMValidationError",
    "DBError",
    "ConfigError",
    "ValidationError",
    "AgentError",
]
