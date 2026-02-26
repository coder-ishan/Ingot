"""Pydantic v2 models for INGOT's config.json structure.

These are plain BaseModel instances (not SQLModel table=True) — they represent
the application configuration, not the database schema.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# Default agent names used throughout the system
_DEFAULT_AGENT_NAMES: list[str] = [
    "orchestrator",
    "scout",
    "research",
    "matcher",
    "writer",
    "outreach",
    "analyst",
]


class AgentConfig(BaseModel):
    """Per-agent LLM backend configuration."""

    model: str = "ollama/llama3.1"
    """LiteLLM model string, e.g. 'ollama/llama3.1' or 'anthropic/claude-3-5-sonnet-20241022'."""


class SmtpConfig(BaseModel):
    """SMTP connection settings for sending emails."""

    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""
    """Fernet-encrypted when stored on disk. Plaintext in memory."""


class ImapConfig(BaseModel):
    """IMAP connection settings for reading/polling reply emails."""

    host: str = "imap.gmail.com"
    port: int = 993
    username: str = ""
    password: str = ""
    """Fernet-encrypted when stored on disk. Plaintext in memory."""


def _default_agents() -> dict[str, AgentConfig]:
    """Build the default agent config dict with all 7 agents."""
    return {name: AgentConfig() for name in _DEFAULT_AGENT_NAMES}


class AppConfig(BaseModel):
    """Root configuration model for INGOT.

    Serialized to ~/.outreach-agent/config.json. Secret fields (smtp.password,
    imap.password, and any api_key fields) are Fernet-encrypted before writing
    and decrypted after reading by ConfigManager.
    """

    agents: dict[str, AgentConfig] = Field(default_factory=_default_agents)
    """Map of agent name → AgentConfig. Defaults include all 7 core agents."""

    smtp: SmtpConfig = Field(default_factory=SmtpConfig)
    imap: ImapConfig = Field(default_factory=ImapConfig)

    max_retries: int = 3
    backoff_strategy: str = "exponential"
    llm_fallback_chain: list[str] = Field(
        default_factory=lambda: ["claude", "openai", "ollama"]
    )

    db_path: str = ""
    log_dir: str = ""
    resume_dir: str = ""
    venues_dir: str = ""

    # CAN-SPAM compliance — physical mailing address required in footer
    mailing_address: str = ""

    # API keys (Fernet-encrypted on disk)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
