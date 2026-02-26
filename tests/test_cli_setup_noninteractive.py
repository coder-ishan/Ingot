"""Tests for non-interactive setup validation in ingot.cli.setup."""
import pytest
import typer

from ingot.cli.setup import _run_non_interactive
from ingot.config.schema import AppConfig


def _fresh_cfg() -> AppConfig:
    return AppConfig()


def test_fully_free_preset_needs_no_api_keys(monkeypatch, tmp_path):
    """fully_free uses Ollama only — no API keys required."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GMAIL_USERNAME", raising=False)
    cfg = _fresh_cfg()
    # Should not raise
    _run_non_interactive(cfg, preset="fully_free")
    assert all("ollama" in a.model for a in cfg.agents.values())


def test_best_quality_without_anthropic_key_exits(monkeypatch):
    """best_quality preset selects Anthropic models; missing key must error."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GMAIL_USERNAME", raising=False)
    cfg = _fresh_cfg()
    with pytest.raises(typer.Exit):
        _run_non_interactive(cfg, preset="best_quality")


def test_best_quality_with_anthropic_key_succeeds(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("GMAIL_USERNAME", raising=False)
    cfg = _fresh_cfg()
    _run_non_interactive(cfg, preset="best_quality")
    assert cfg.anthropic_api_key == "sk-ant-test"


def test_gmail_username_without_password_exits(monkeypatch):
    """Providing Gmail username but no app password must error."""
    monkeypatch.setenv("GMAIL_USERNAME", "user@gmail.com")
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = _fresh_cfg()
    with pytest.raises(typer.Exit):
        _run_non_interactive(cfg, preset="fully_free")


def test_gmail_username_with_password_succeeds(monkeypatch):
    monkeypatch.setenv("GMAIL_USERNAME", "user@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-pass")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = _fresh_cfg()
    _run_non_interactive(cfg, preset="fully_free")
    assert cfg.smtp.username == "user@gmail.com"
    assert cfg.smtp.password == "app-pass"
