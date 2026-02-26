---
plan: 01-01
phase: 01-foundation-and-core-infrastructure
status: complete
completed: 2026-02-26
---

# Plan 01-01 Summary: Config System, Crypto, Setup Wizard

## What Was Built

Fernet-encrypted config system, setup wizard CLI, and package scaffold — the shared config layer every other module will import.

## Key Files Created

- `pyproject.toml` — hatchling build, all deps, `asyncio_mode = "auto"`, `job-hunter` entry point
- `src/ingot/__init__.py` — `__version__ = "0.1.0"`
- `src/ingot/config/crypto.py` — PBKDF2HMAC key derivation (600k iterations), `get_fernet()`, `encrypt_secret()`, `decrypt_secret()`
- `src/ingot/config/schema.py` — `AppConfig`, `AgentConfig`, `SmtpConfig`, `ImapConfig` (Pydantic v2)
- `src/ingot/config/manager.py` — `ConfigManager.load()/save()` with atomic write, `__encrypted__:` prefix for secrets
- `src/ingot/cli/setup.py` — full setup wizard: interactive (questionary) + non-interactive (env vars), `--preset fully_free/best_quality`, skips existing values, Rich summary table
- `src/ingot/cli/__init__.py` — Typer app with `setup` subcommand
- `src/ingot/logging_config.py` — structlog dual handlers (stderr WARNING+, rotating file DEBUG+ JSON)

## Verification

- `python3 -c "import ingot; print(ingot.__version__)"` → `0.1.0` ✓
- Fernet roundtrip: `decrypt_secret(encrypt_secret("hello")) == "hello"` ✓
- All module imports clean: `ConfigManager`, `AppConfig`, `setup_app` ✓

## Commits

- `a53d0a8` feat(01-01): project scaffold, pyproject.toml, and package structure
- `b4b1f02` feat(01-01): Fernet crypto module and ConfigManager
- `fa2d6b7` feat(01-01): setup wizard CLI with interactive + non-interactive modes

## Self-Check: PASSED
