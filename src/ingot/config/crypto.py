"""Fernet encryption for INGOT config secrets.

Uses PBKDF2HMAC to derive a Fernet key from a machine-generated random key
stored at ~/.ingot/.key. The machine key has full entropy so
600_000 PBKDF2 iterations are sufficient (not 1,200,000 which is for
low-entropy passwords).

Pattern: KEY_FILE holds 32 random bytes (os.urandom). PBKDF2HMAC derives
a deterministic Fernet key from those bytes using a static salt.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Location of the machine-specific random key file
KEY_FILE: Path = Path.home() / ".ingot" / ".key"

# Static salt — unique per application, not per user
SALT: bytes = b"ingot-v1-static-salt"

# PBKDF2 iteration count — machine key has full entropy, so 600k is sufficient
_PBKDF2_ITERATIONS: int = 600_000


class ConfigError(Exception):
    """Raised when configuration or encryption operations fail.

    Note: Plan 01-04 will create a full exception hierarchy; this is a
    local stub used only within the config subsystem.
    """


def _load_or_create_machine_key() -> bytes:
    """Load the machine key from KEY_FILE, creating it if it does not exist.

    On first run:
      - Creates the parent directory (~/.ingot/) if needed.
      - Generates 32 cryptographically random bytes via os.urandom(32).
      - Writes the key file with chmod 0o600 (owner read/write only).

    Returns:
        32 random bytes used as the master secret for Fernet key derivation.
    """
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)

    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()

    # Generate and persist a fresh machine key with atomic 0o600 permissions.
    # O_EXCL + mode=0o600 ensures the file is created with restricted permissions
    # from the start, eliminating the TOCTOU window that write_bytes + chmod has.
    key_bytes = os.urandom(32)
    fd = os.open(str(KEY_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key_bytes)
    return key_bytes


def get_fernet() -> Fernet:
    """Derive a Fernet instance from the machine key via PBKDF2HMAC.

    The derivation is deterministic: the same machine key always produces
    the same Fernet key, so previously encrypted secrets can always be
    decrypted on the same machine.

    Returns:
        A ready-to-use Fernet instance.
    """
    machine_key = _load_or_create_machine_key()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=_PBKDF2_ITERATIONS,
    )
    fernet_key = base64.urlsafe_b64encode(kdf.derive(machine_key))
    return Fernet(fernet_key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext string using the machine Fernet key.

    Args:
        plaintext: The secret value to encrypt (e.g., an API key or password).

    Returns:
        A base64-encoded ciphertext string (safe to store in config.json).
    """
    fernet = get_fernet()
    ciphertext_bytes = fernet.encrypt(plaintext.encode("utf-8"))
    return ciphertext_bytes.decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a ciphertext string produced by encrypt_secret().

    Args:
        ciphertext: The base64-encoded ciphertext string from encrypt_secret().

    Returns:
        The original plaintext string.

    Raises:
        ConfigError: If decryption fails (wrong key, corrupted data, etc.).
    """
    fernet = get_fernet()
    try:
        plaintext_bytes = fernet.decrypt(ciphertext.encode("utf-8"))
        return plaintext_bytes.decode("utf-8")
    except Exception as exc:
        raise ConfigError(f"Failed to decrypt secret: {exc}") from exc
