"""ConfigManager: read/write config.json with Fernet-encrypted secrets.

Secrets are stored with a "__encrypted__:" prefix so the manager knows
which fields to decrypt on load. Example on disk:

    {
      "smtp": {
        "password": "__encrypted__:gAAAAABh..."
      }
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ingot.config.crypto import decrypt_secret, encrypt_secret
from ingot.config.schema import AppConfig

# Fields whose values must be encrypted at rest.
# Format: list of dot-separated key paths into the serialized JSON dict.
_SECRET_FIELDS: list[str] = [
    "smtp.password",
    "imap.password",
    "anthropic_api_key",
    "openai_api_key",
]

_ENCRYPTED_PREFIX: str = "__encrypted__:"


class ConfigManager:
    """Manages loading and saving INGOT's config.json.

    Usage::

        cm = ConfigManager()          # uses ~/.ingot/
        cfg = cm.load()               # returns AppConfig (decrypts secrets)
        cfg.smtp.password = "secret"
        cm.save(cfg)                  # encrypts secrets, writes atomically
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir: Path = base_dir or Path.home() / ".ingot"
        self.config_path: Path = self.base_dir / "config.json"

    # ------------------------------------------------------------------
    # Directory management
    # ------------------------------------------------------------------

    def ensure_dirs(self) -> None:
        """Create ~/.ingot/ and required subdirectories.

        Called on first run before saving config. Safe to call repeatedly
        (uses exist_ok=True).
        """
        for subdir in ["", "logs", "resume", "venues"]:
            (self.base_dir / subdir if subdir else self.base_dir).mkdir(
                parents=True, exist_ok=True
            )

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------

    def load(self) -> AppConfig:
        """Load and parse config.json.

        Returns a default AppConfig if the file does not exist.
        Secret fields carrying the __encrypted__: prefix are decrypted
        in-memory before returning.
        """
        if not self.config_path.exists():
            return AppConfig()

        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        self._decrypt_in_place(raw)
        return AppConfig.model_validate(raw)

    def save(self, config: AppConfig) -> None:
        """Encrypt secret fields and write config.json atomically.

        The write is atomic: data is first written to a .tmp file,
        then renamed over the real config.json. This prevents partial
        writes from corrupting the config.

        Args:
            config: The AppConfig instance to persist.
        """
        self.ensure_dirs()
        raw = config.model_dump()
        self._encrypt_in_place(raw)

        # Atomic write: write to .tmp, then rename
        tmp_path = self.config_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        tmp_path.replace(self.config_path)

    # ------------------------------------------------------------------
    # Helper: DB path
    # ------------------------------------------------------------------

    def get_db_path(self) -> Path:
        """Return the canonical SQLite database path."""
        return self.base_dir / "outreach.db"

    # ------------------------------------------------------------------
    # Internal: encrypt/decrypt helpers
    # ------------------------------------------------------------------

    def _encrypt_in_place(self, raw: dict[str, Any]) -> None:
        """Encrypt all secret fields in the raw dict (mutates in place)."""
        for field_path in _SECRET_FIELDS:
            self._set_encrypted(raw, field_path)

    def _decrypt_in_place(self, raw: dict[str, Any]) -> None:
        """Decrypt all secret fields in the raw dict (mutates in place)."""
        for field_path in _SECRET_FIELDS:
            self._set_decrypted(raw, field_path)

    def _set_encrypted(self, raw: dict[str, Any], field_path: str) -> None:
        """Encrypt a single field given its dot-separated path."""
        keys = field_path.split(".")
        obj = raw
        for key in keys[:-1]:
            if not isinstance(obj, dict) or key not in obj:
                return
            obj = obj[key]

        leaf = keys[-1]
        if not isinstance(obj, dict) or leaf not in obj:
            return

        value = obj[leaf]
        if isinstance(value, str) and value and not value.startswith(_ENCRYPTED_PREFIX):
            obj[leaf] = _ENCRYPTED_PREFIX + encrypt_secret(value)

    def _set_decrypted(self, raw: dict[str, Any], field_path: str) -> None:
        """Decrypt a single field given its dot-separated path."""
        keys = field_path.split(".")
        obj = raw
        for key in keys[:-1]:
            if not isinstance(obj, dict) or key not in obj:
                return
            obj = obj[key]

        leaf = keys[-1]
        if not isinstance(obj, dict) or leaf not in obj:
            return

        value = obj[leaf]
        if isinstance(value, str) and value.startswith(_ENCRYPTED_PREFIX):
            ciphertext = value[len(_ENCRYPTED_PREFIX):]
            obj[leaf] = decrypt_secret(ciphertext)
