"""
INGOT typed exception hierarchy.

Rule: Never raise bare Exception. Always raise the most specific subclass.
Callers must catch specific types — catching IngotError is only acceptable
at the top-level CLI handler that formats user-visible error messages.
"""


class IngotError(Exception):
    """Base exception for all INGOT errors. Carries a user-friendly message."""

    def __init__(self, message: str, *, cause: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {type(self.cause).__name__}: {self.cause})"
        return self.message


class LLMError(IngotError):
    """LLM backend unreachable, timeout, or all retries exhausted."""
    pass


class LLMValidationError(IngotError):
    """LLM returned a response that failed Pydantic validation."""

    def __init__(self, message: str, *, raw_content: str = "", cause: Exception | None = None):
        super().__init__(message, cause=cause)
        self.raw_content = raw_content


class DBError(IngotError):
    """Database read/write failure. Best-effort recovery may apply."""
    pass


class ConfigError(IngotError):
    """Configuration missing, invalid, or encryption key lost."""
    pass


class ValidationError(IngotError):
    """Input data failed schema validation (distinct from LLM response validation)."""
    pass


class AgentError(IngotError):
    """Agent-level failure (agent-specific logic error, not LLM or DB)."""

    def __init__(self, agent_name: str, message: str, *, cause: Exception | None = None):
        super().__init__(f"[{agent_name}] {message}", cause=cause)
        self.agent_name = agent_name
