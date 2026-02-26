"""Tests for ingot.config.crypto."""
import stat

import pytest

from ingot.config.crypto import (
    ConfigError,
    _load_or_create_machine_key,
    decrypt_secret,
    encrypt_secret,
)


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("ingot.config.crypto.KEY_FILE", tmp_path / ".key")
    plaintext = "super-secret-api-key"
    ciphertext = encrypt_secret(plaintext)
    assert decrypt_secret(ciphertext) == plaintext


def test_encrypt_nondeterministic(tmp_path, monkeypatch):
    monkeypatch.setattr("ingot.config.crypto.KEY_FILE", tmp_path / ".key")
    c1 = encrypt_secret("hello")
    c2 = encrypt_secret("hello")
    assert c1 != c2  # Fernet uses random IV


def test_decrypt_bad_ciphertext_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("ingot.config.crypto.KEY_FILE", tmp_path / ".key")
    with pytest.raises(ConfigError):
        decrypt_secret("not-a-valid-fernet-token")


def test_machine_key_created_with_correct_permissions(tmp_path, monkeypatch):
    key_path = tmp_path / ".key"
    monkeypatch.setattr("ingot.config.crypto.KEY_FILE", key_path)
    _load_or_create_machine_key()
    assert key_path.exists()
    mode = stat.S_IMODE(key_path.stat().st_mode)
    assert mode == 0o600


def test_machine_key_idempotent(tmp_path, monkeypatch):
    key_path = tmp_path / ".key"
    monkeypatch.setattr("ingot.config.crypto.KEY_FILE", key_path)
    k1 = _load_or_create_machine_key()
    k2 = _load_or_create_machine_key()
    assert k1 == k2
