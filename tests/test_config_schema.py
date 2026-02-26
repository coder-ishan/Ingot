"""Tests for ingot.config.schema.AppConfig."""
from ingot.config.schema import AgentConfig, AppConfig, ImapConfig, SmtpConfig

EXPECTED_AGENTS = {"orchestrator", "scout", "research", "matcher", "writer", "outreach", "analyst"}


def test_default_agents():
    cfg = AppConfig()
    assert set(cfg.agents.keys()) == EXPECTED_AGENTS


def test_agent_default_model():
    cfg = AgentConfig()
    assert cfg.model == "ollama/llama3.1"


def test_smtp_default_port():
    assert SmtpConfig().port == 587


def test_imap_default_port():
    assert ImapConfig().port == 993


def test_appconfig_dump_validate_roundtrip():
    cfg = AppConfig(mailing_address="456 Oak Ave")
    cfg.smtp.username = "user@example.com"
    dumped = cfg.model_dump()
    restored = AppConfig.model_validate(dumped)
    assert restored.mailing_address == "456 Oak Ave"
    assert restored.smtp.username == "user@example.com"
