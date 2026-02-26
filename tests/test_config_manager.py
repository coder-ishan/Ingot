"""Tests for ingot.config.manager.ConfigManager."""
import json

import pytest

from ingot.config.manager import ConfigManager, _ENCRYPTED_PREFIX
from ingot.config.schema import AppConfig


@pytest.fixture(autouse=True)
def _patch_key_file(tmp_path, monkeypatch):
    monkeypatch.setattr("ingot.config.crypto.KEY_FILE", tmp_path / ".key")


def test_load_returns_default_when_missing(tmp_config_dir):
    cm = ConfigManager(base_dir=tmp_config_dir)
    cfg = cm.load()
    assert isinstance(cfg, AppConfig)
    assert cfg.smtp.host == "smtp.gmail.com"


def test_save_and_load_roundtrip(tmp_config_dir):
    cm = ConfigManager(base_dir=tmp_config_dir)
    cfg = AppConfig(mailing_address="123 Main St")
    cfg.smtp.password = "my-password"
    cm.save(cfg)
    loaded = cm.load()
    assert loaded.mailing_address == "123 Main St"
    assert loaded.smtp.password == "my-password"


def test_secrets_are_encrypted_on_disk(tmp_config_dir):
    cm = ConfigManager(base_dir=tmp_config_dir)
    cfg = AppConfig()
    cfg.smtp.password = "plaintext-password"
    cm.save(cfg)
    raw = json.loads((tmp_config_dir / "config.json").read_text())
    assert raw["smtp"]["password"].startswith(_ENCRYPTED_PREFIX)


def test_ensure_dirs_creates_subdirectories(tmp_config_dir):
    cm = ConfigManager(base_dir=tmp_config_dir)
    cm.ensure_dirs()
    for sub in ["logs", "resume", "venues"]:
        assert (tmp_config_dir / sub).is_dir()


def test_get_db_path(tmp_config_dir):
    cm = ConfigManager(base_dir=tmp_config_dir)
    assert cm.get_db_path() == tmp_config_dir / "outreach.db"


def test_empty_secret_not_encrypted(tmp_config_dir):
    """Empty string secrets should not be encrypted (skipped)."""
    cm = ConfigManager(base_dir=tmp_config_dir)
    cfg = AppConfig()  # all secrets are empty strings
    cm.save(cfg)
    raw = json.loads((tmp_config_dir / "config.json").read_text())
    assert raw["smtp"]["password"] == ""  # not encrypted
