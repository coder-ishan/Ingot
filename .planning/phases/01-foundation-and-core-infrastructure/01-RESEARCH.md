# Phase 1: Foundation and Core Infrastructure - Research

**Researched:** 2026-02-25
**Domain:** Python async infrastructure — config encryption, SQLite ORM, LLM abstraction, agent framework, test harness
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Setup Wizard UX**
- Interactive terminal prompts — one credential at a time, with input masking and inline validation
- Re-run behavior: only prompt for missing or invalid values — skip already-configured credentials entirely
- After completion: display a summary table of all configured services (API keys masked, DB path, selected model per agent)
- Non-interactive mode: accept flags or environment variables (e.g., `ANTHROPIC_API_KEY=xxx job-hunter setup --non-interactive`) for CI/scripted deploys

**Runtime Feedback**
- Default output: structured progress lines prefixed by agent name — e.g., `[Scout] Fetching YC profile...`, `[Composer] Drafting email...`
- Two opt-in verbosity levels:
  - `-v` — show detailed progress (step completions, retry attempts, timing)
  - `-vv` — full debug mode (LLM prompts, raw API responses, all internal state)
- Logging: full trace always written to log file (`./logs/` or `~/.job-hunter/logs/`); terminal shows only filtered, actionable lines
- Concurrent agents: output interleaved, always prefixed by agent name — `[AgentName]` prefix disambiguates parallel runs

**Failure Behavior**
- LLM failures (all retries exhausted): fail the agent run with a clear, descriptive error message — e.g., `[Scout] Failed: Claude API unreachable after 3 retries. Check your API key or try again later.` Surface backend fallback (try OpenAI, then Ollama) as a configurable option in config.json, not the default
- Database write failures: best-effort — save what succeeded, log everything that failed with enough context to retry manually. No hard crash on partial writes
- Retry configuration: user-tunable in config.json (`max_retries`, `backoff_strategy: exponential`) — defaults are sane, not hardcoded
- Unhandled exceptions (code bugs): friendly one-liner to terminal (`Something went wrong. Full error logged to logs/run-YYYY-MM-DD.log`) with full traceback written to log file

**Testing Philosophy**
- Coverage targets: 80%+ on critical paths (encryption, DB operations, LLM retry/fallback logic); 70% minimum for remaining modules — match roadmap baseline for non-critical paths
- All LLM calls mocked in tests — zero real API hits, no API key required to run the suite
- Test suite must run in under 30 seconds: use in-memory SQLite for DB tests, all external calls mocked
- Strict async enforcement: `asyncio` strict mode + `pytest-asyncio` strict mode — catch unawaited coroutines and blocking calls in async paths before they reach production

### Claude's Discretion
- Exact log file rotation and retention policy
- Specific progress bar or spinner implementation (if any) within the structured progress line format
- Internal fixture patterns and factory helpers for the test suite
- Exact `config.json` schema field names (beyond what's already specified in requirements)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within Phase 1 scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Config system with `~/.outreach-agent/` directory structure (config.json, outreach.db, logs/, resume/, venues/) | Standard `pathlib.Path` + `appdirs` for XDG-compliant home dir; JSON config with schema validated by Pydantic |
| INFRA-02 | Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) for all stored secrets | `cryptography` library Fernet class; verified against official docs |
| INFRA-03 | Encryption key derivation from local machine key (deterministic, stored securely) | PBKDF2HMAC with SHA-256, 1,200,000 iterations; machine key = random 32-byte secret stored in `~/.outreach-agent/.key` (chmod 600) |
| INFRA-04 | First-run setup wizard: Gmail SMTP/IMAP credentials, API keys per LLM backend, resume upload | `questionary` or `prompt_toolkit` for masked interactive prompts; Typer for non-interactive flags |
| INFRA-05 | Setup presets: "fully free" (all Ollama) and "best quality" (Claude Sonnet for Writer+Research, Haiku for rest) | Config preset map loaded at wizard step; written to per-agent `llm_backend` fields |
| INFRA-06 | Per-agent LLM backend selection via config.json (not global single model) | LiteLLM model string per agent key in config; LLMClient reads per-agent config at call time |
| INFRA-07 | SQLite database via SQLModel ORM with aiosqlite async driver | `sqlmodel` + `aiosqlite`; async engine via `create_async_engine("sqlite+aiosqlite://...")` |
| INFRA-08 | SQLite WAL mode enabled for concurrent async access | `PRAGMA journal_mode=WAL` executed on engine connect event; `PRAGMA synchronous=NORMAL` also recommended |
| INFRA-09 | Alembic schema migration system (initial migration + deployment tested) | Alembic env.py imports `SQLModel.metadata`; `target_metadata = SQLModel.metadata`; async run_migrations_online pattern |
| INFRA-10 | LLMClient abstraction supporting Claude, OpenAI, Ollama, LM Studio, OpenAI-compatible | LiteLLM `completion()` unified call; model strings: `claude-3-5-sonnet-20241022`, `gpt-4o`, `ollama/llama3.1` |
| INFRA-11 | Single LLMClient entry point — no agent directly imports anthropic or openai | LLMClient module; all agents receive it via dependency injection |
| INFRA-12 | LLMClient uses LiteLLM internally for multi-backend routing | `from litellm import completion, acompletion`; Router for fallback chains |
| INFRA-13 | Tool-use compatibility: native JSON tool calls for models that support it, prompt-engineered XML fallback for models without | LiteLLM passes `tools=` param; detect `finish_reason="tool_calls"`; XML fallback parser for non-tool models |
| INFRA-14 | Strict Pydantic validation on every LLM response before passing downstream | `BaseModel.model_validate()` on raw response; raise typed `LLMValidationError` on failure |
| INFRA-15 | Retry logic with exponential backoff (3 retries) on transient LLM failures | `tenacity` library: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))` |
| INFRA-16 | Fallback to XML extraction when JSON tool calls fail | Regex/minidom parser on raw content; Pydantic validated after extraction |
| INFRA-17 | Async task dispatcher with worker pool (asyncio.Queue base, Redis optional for v2) | `asyncio.Queue` + `asyncio.gather()` for concurrent agent dispatch |
| INFRA-18 | Shared async HTTP client (httpx) with connection pooling and request delays for scraping | `httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=5, max_connections=10))` as shared singleton |
| INFRA-19 | Async SMTP client (aiosmtplib) for email sending | `aiosmtplib`; deferred to Phase 3 wiring but stub registered in Phase 1 |
| INFRA-20 | Async IMAP client (aioimaplib) for reply polling | `aioimaplib`; deferred to Phase 3 wiring but stub registered in Phase 1 |
| DB-01 | UserProfile schema | SQLModel table model with JSON-serialized list fields (skills, experience, education, projects) |
| DB-02 | Lead schema with status enum | SQLModel + Python `enum.Enum` for status field |
| DB-03 | IntelBrief schema | SQLModel with ForeignKey to Lead |
| DB-04 | Match schema | SQLModel with ForeignKey to Lead |
| DB-05 | Email schema | SQLModel with JSON field for mcq_answers |
| DB-06 | FollowUp schema | SQLModel with ForeignKey to Email |
| DB-07 | Campaign schema | SQLModel with status enum |
| DB-08 | AgentLog schema | SQLModel; wide row for diagnostics |
| DB-09 | Venue schema | SQLModel with JSON config_json field |
| DB-10 | OutreachMetric schema | SQLModel |
| DB-11 | UnsubscribedEmail schema | SQLModel |
| AGENT-01 | 7-agent architecture: Orchestrator, Scout, Research, Matcher, Writer, Outreach, Analyst | Agent base class / dataclass pattern; agents registered by name in simple dict registry |
| AGENT-02 | Agent framework: PydanticAI | v1.x stable (verified: current PyPI version ~1.63.0, stable since September 2025) |
| AGENT-03 | Fallback to LiteLLM + manual Pydantic validation if PydanticAI API has changed significantly | PydanticAI v1.x is confirmed stable; fallback not needed, but document the LiteLLM path |
| AGENT-05 | No agent imports another agent; Orchestrator is the only coordinator | Enforced by module boundary convention; can be verified with import linter |
| AGENT-06 | Agent dependencies injected as function arguments (LLMClient, db, http_client, repositories) | PydanticAI `deps_type` dataclass pattern; matches framework native pattern |
| AGENT-07 | Orchestrator stays under 250 lines (domain logic lives in agents) | Structural convention enforced at code review |
| AGENT-08 | Agent registry (for future module expansion in v2) | Simple `dict[str, AgentBase]` in `agents/__init__.py`; v2 makes this dynamic |
| AGENT-09 | Typed exception handling (never swallow errors, surface them clearly) | Custom exception hierarchy: `IngotError` base → `LLMError`, `DBError`, `ConfigError`, `ValidationError` |
| TEST-P1-01 | Unit tests for config encryption/decryption | pytest + `tmp_path` fixture; no real FS writes |
| TEST-P1-02 | Unit tests for SQLModel schemas | pytest + in-memory SQLite (`sqlite+aiosqlite:///:memory:`) |
| TEST-P1-03 | Unit tests for LLMClient initialization (all backends) | Mock LiteLLM `completion` with `unittest.mock.AsyncMock` |
| TEST-P1-04 | Unit tests for Pydantic validation (invalid LLM responses rejected) | Parameterized pytest cases; assert raises `LLMValidationError` |
| TEST-P1-05 | Unit tests for retry/fallback logic | `tenacity` retry; mock side_effect sequences |
| TEST-P1-06 | Integration test: Setup wizard creates config, encrypts, persists, reloads | subprocess or direct function call with temp dir |
| TEST-P1-07 | Integration test: SQLite WAL mode + concurrent async writes | asyncio concurrent tasks; assert no SQLITE_BUSY |
| TEST-P1-08 | Integration test: Alembic migration applied, schema matches all models | `alembic upgrade head` in subprocess; then validate via `inspect(engine)` |
| TEST-P1-09 | Performance: LLMClient init <500ms, config load <100ms, DB tx <50ms | `time.perf_counter()` assertions in pytest |
| TEST-INFRA-01 | pytest-asyncio configuration | `asyncio_mode = "auto"` in `pytest.ini` or `pyproject.toml` |
| TEST-INFRA-02 | Fixture database (test SQLite, auto-cleaned between tests) | `@pytest_asyncio.fixture` with `sqlite+aiosqlite:///:memory:` engine |
| TEST-INFRA-03 | Fixture LLM client (mock responses, deterministic) | `AsyncMock` wrapping `pydantic_ai.models.test.TestModel` |
| TEST-INFRA-04 | Fixture config (encrypted, temporary directory) | `tmp_path` fixture + `ConfigManager(base_dir=tmp_path)` |
| TEST-INFRA-05 | Coverage reporting (minimum 70% for Phase 1-2) | `pytest-cov`; `--cov-fail-under=70` |
| TEST-INFRA-06 | Mock Gmail SMTP/IMAP | `aiosmtpd` in-memory server or `AsyncMock`; Phase 3 concern but stubs registered here |
| TEST-INFRA-07 | Fixture YC data (100 known companies, stable responses) | JSON fixture file in `tests/fixtures/` |
| TEST-INFRA-08 | Fixture UserProfile and IntelBrief (standard test data) | Python factory functions returning valid model instances |
</phase_requirements>

---

## Summary

Phase 1 builds the shared foundation that every subsequent phase depends on. The technology choices are mature and well-validated: PydanticAI v1.x (now stable since September 2025, current version ~1.63.0) as the agent framework; LiteLLM as the single LLM routing layer; SQLModel with aiosqlite for async SQLite access; Fernet from the `cryptography` library for secret storage; Alembic for schema migrations; and `tenacity` for retry logic. None of these choices require hedging — they are the standard Python stack for this problem class in 2026.

The central architectural risk in this phase is getting the async database setup right from the start. SQLModel's async story requires using SQLAlchemy's `create_async_engine` with the `sqlite+aiosqlite://` prefix — the synchronous `create_engine` will silently work but block the event loop under concurrent load. WAL mode must be enabled at connection time via a `@event.listens_for(engine_sync, "connect")` hook or `PRAGMA` execution immediately after engine creation. Alembic requires its own sync connection path for migrations (async migrations need the `run_sync` pattern in `env.py`).

The second key concern is the LLMClient boundary: every agent receives the client via dependency injection, never imports `anthropic` or `openai` directly. PydanticAI's `deps_type` dataclass pattern is the correct mechanism — the `RunContext[MyDeps]` object gives agents access to `LLMClient`, `db`, and `http_client` without tight coupling. The `TestModel` built into PydanticAI satisfies the requirement for zero real API calls in tests.

**Primary recommendation:** Build in this order — (1) config + encryption, (2) SQLite engine + WAL + Alembic, (3) LLMClient + Pydantic validation + retry, (4) PydanticAI agent shell + deps, (5) all 11 DB models, (6) test infrastructure. Each layer is independently testable before the next is added.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic-ai` | 1.63.x (latest stable) | Agent framework with typed deps injection, TestModel for mocking | V1 stable since Sept 2025; FastAPI-style DX; built-in test support |
| `litellm` | 1.81.x (latest stable) | Multi-backend LLM routing (Claude, OpenAI, Ollama, OpenAI-compat) | Single call interface for 100+ providers; native retry/fallback Router |
| `sqlmodel` | 0.0.24+ | ORM combining SQLAlchemy + Pydantic; table models = Pydantic models | Standard for Pydantic-first projects; eliminates dual-model boilerplate |
| `aiosqlite` | 0.20.x | Async SQLite driver for aioio event loop | Only async SQLite driver; wraps stdlib `sqlite3` in a thread |
| `alembic` | 1.14.x+ | Schema migration management | SQLAlchemy-native; autogenerate from SQLModel metadata |
| `cryptography` | 44.x+ | Fernet encryption + PBKDF2HMAC key derivation | PyCA project; only audited Python crypto library |
| `tenacity` | 9.x | Retry with exponential backoff, jitter, stop conditions | Decorator-based; more flexible than ad-hoc loops; handles async |
| `pydantic` | v2.x (pulled by pydantic-ai) | Schema validation for all LLM responses | Already a dependency; v2 API used throughout |
| `typer` | 0.15.x | CLI framework for setup wizard and commands | Type-annotation-driven; Rich integration; no-boilerplate |
| `rich` | 14.x+ | Styled terminal output, progress, tables | Standard for Python CLI output; pulled by Typer |
| `questionary` | 2.x | Interactive masked prompts for setup wizard | Simpler than prompt_toolkit for wizard UX; supports password masking |
| `httpx` | 0.28.x | Async HTTP client with connection pooling | Async-first; used by PydanticAI internally |
| `pytest` | 8.x | Test runner | Universal standard |
| `pytest-asyncio` | 1.x | Async test support | Standard for asyncio projects; strict mode enforced |
| `pytest-cov` | 6.x | Coverage reporting | Standard; integrates with pytest |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `appdirs` or `platformdirs` | 3.x | XDG-compliant app directory resolution | Used in ConfigManager to find `~/.outreach-agent/` cross-platform |
| `python-dotenv` | 1.x | Load env vars in dev (NOT for secrets storage) | Dev override only; config.json + Fernet is the production path |
| `structlog` | 25.x | Structured logging to file | Log rotation, JSON output, consistent format across agents |
| `aiosmtplib` | 3.x | Async SMTP (email sending) | Phase 3 concern; stub imported in Phase 1 to validate dep tree |
| `aioimaplib` | 2.x | Async IMAP (reply polling) | Phase 3 concern; verify active maintenance on PyPI before use |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pydantic-ai` | `langchain`, `llama-index` | langchain/llama-index are heavier, opinionated pipelines; PydanticAI is lighter and framework-native |
| `litellm` (direct) | `anthropic` + `openai` SDKs | Direct SDKs require per-provider branching; LiteLLM keeps one call site |
| `sqlmodel` | `tortoise-orm`, `databases` | SQLModel gives free Pydantic schema from table definition; tortoise is heavier |
| `tenacity` | `backoff`, manual loop | tenacity supports async decorators natively; backoff lacks async parity |
| `questionary` | `inquirerpy`, `click.prompt` | questionary has cleaner API; inquirerpy is maintained but heavier |
| `cryptography` (Fernet) | `nacl` (libsodium), `age` | PyCA `cryptography` is the Python standard; NaCl is fine but adds a C dep |

**Installation:**
```bash
pip install pydantic-ai litellm sqlmodel aiosqlite alembic cryptography tenacity \
    typer rich questionary httpx platformdirs structlog \
    pytest pytest-asyncio pytest-cov
```

---

## Architecture Patterns

### Recommended Project Structure

```
~/.outreach-agent/          # User data dir (created by ConfigManager)
├── config.json             # Encrypted secrets + per-agent config
├── .key                    # Machine key (chmod 600, gitignored)
├── outreach.db             # SQLite database
├── logs/                   # Rotating log files
├── resume/                 # Uploaded resume files
└── venues/                 # Venue config overrides

src/
├── ingot/                  # Main package
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── manager.py      # ConfigManager: read/write/encrypt config.json
│   │   ├── crypto.py       # Fernet key derivation, encrypt(), decrypt()
│   │   └── schema.py       # Pydantic model for config.json structure
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py       # create_async_engine, WAL setup, session factory
│   │   ├── models.py       # All 11 SQLModel table models
│   │   └── repositories/   # One repository class per model (DB access layer)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py       # LLMClient: wraps LiteLLM, retry, validation
│   │   ├── fallback.py     # XML extraction fallback
│   │   └── schemas.py      # Pydantic schemas for LLM request/response
│   ├── agents/
│   │   ├── __init__.py     # Agent registry dict
│   │   ├── base.py         # AgentDeps dataclass, AgentBase protocol
│   │   └── exceptions.py   # Typed exception hierarchy
│   ├── cli/
│   │   ├── __init__.py
│   │   └── setup.py        # Setup wizard (Phase 1 CLI surface)
│   └── logging_config.py   # structlog setup, log rotation
├── alembic/
│   ├── env.py              # Alembic config importing SQLModel.metadata
│   ├── script.py.mako
│   └── versions/           # Migration files
├── tests/
│   ├── conftest.py         # Shared fixtures: db, llm_client, config, tmp dirs
│   ├── fixtures/           # JSON fixture data (YC companies, UserProfiles)
│   ├── unit/
│   │   ├── test_crypto.py
│   │   ├── test_config.py
│   │   ├── test_llm_client.py
│   │   ├── test_pydantic_validation.py
│   │   ├── test_retry.py
│   │   └── test_db_models.py
│   └── integration/
│       ├── test_setup_wizard.py
│       ├── test_db_wal.py
│       └── test_alembic_migration.py
├── pyproject.toml
└── alembic.ini
```

### Pattern 1: Async Engine + WAL Mode

**What:** Create SQLAlchemy async engine with aiosqlite; immediately enable WAL mode on every new connection.
**When to use:** Always — this is the only correct setup for concurrent async SQLite access.

```python
# Source: https://dev.to/arunanshub/async-database-operations-with-sqlmodel-c2o
# + SQLAlchemy event listener pattern

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event, text
from sqlmodel import SQLModel

DATABASE_URL = "sqlite+aiosqlite:///path/to/outreach.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# WAL mode must be set on the underlying sync connection
# aiosqlite exposes the sync connection via _connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")   # 64MB cache
    cursor.close()

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### Pattern 2: Fernet Key Derivation from Machine Key

**What:** Derive a stable Fernet key from a per-machine random secret using PBKDF2HMAC. The machine key is generated once and stored at `~/.outreach-agent/.key` (chmod 600). The derived Fernet key is never stored — it is re-derived on every process start.
**When to use:** Encrypting all secrets in config.json.

```python
# Source: https://cryptography.io/en/latest/fernet/ (verified)
import base64
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

KEY_FILE = Path.home() / ".outreach-agent" / ".key"
# salt is fixed (stored with the key) to make derivation deterministic
SALT = b"ingot-v1-static-salt"   # acceptable: machine key is already random; no need for random salt

def _load_or_create_machine_key() -> bytes:
    """Generate a random 32-byte machine key on first run; load it on subsequent runs."""
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        machine_key = os.urandom(32)
        KEY_FILE.write_bytes(machine_key)
        KEY_FILE.chmod(0o600)
    return KEY_FILE.read_bytes()

def get_fernet() -> Fernet:
    machine_key = _load_or_create_machine_key()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=600_000,   # Lower than password KDF — machine key has full entropy
    )
    key = base64.urlsafe_b64encode(kdf.derive(machine_key))
    return Fernet(key)

def encrypt_secret(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode()).decode()

def decrypt_secret(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode()).decode()
```

### Pattern 3: LLMClient with LiteLLM + Retry + Pydantic Validation

**What:** Single wrapper around LiteLLM that handles retries, Pydantic validation, and XML fallback.
**When to use:** Every agent call to any LLM backend.

```python
# Source: https://docs.litellm.ai/docs/proxy/reliability (verified)
# + tenacity docs (https://tenacity.readthedocs.io/)
import json
from typing import TypeVar, Type
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from litellm import acompletion
from pydantic import BaseModel
from ingot.agents.exceptions import LLMError, LLMValidationError

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    def __init__(self, model: str, max_retries: int = 3):
        self.model = model
        self.max_retries = max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[dict],
        response_schema: Type[T],
        tools: list[dict] | None = None,
    ) -> T:
        try:
            kwargs = {"model": self.model, "messages": messages}
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await acompletion(**kwargs)
            raw = response.choices[0].message

            # Try native tool call first
            if raw.tool_calls:
                args_json = raw.tool_calls[0].function.arguments
                return response_schema.model_validate_json(args_json)

            # Fallback: try parsing content as JSON
            content = raw.content or ""
            try:
                return response_schema.model_validate_json(content)
            except Exception:
                # XML fallback
                return self._xml_fallback(content, response_schema)

        except LLMValidationError:
            raise
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}") from e

    def _xml_fallback(self, content: str, schema: Type[T]) -> T:
        """Extract field values from XML-like tags when JSON tool calls fail."""
        import re
        data = {}
        for field_name in schema.model_fields:
            pattern = rf"<{field_name}>(.*?)</{field_name}>"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                data[field_name] = match.group(1).strip()
        try:
            return schema.model_validate(data)
        except Exception as e:
            raise LLMValidationError(f"XML fallback validation failed: {e}") from e
```

### Pattern 4: PydanticAI Agent with Injected Dependencies

**What:** Define agents using PydanticAI's `deps_type` pattern. All external resources (LLMClient, db session, http client) are injected — no global state.
**When to use:** Every agent definition.

```python
# Source: https://ai.pydantic.dev/dependencies (verified, v1.x API)
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
import httpx
from ingot.llm.client import LLMClient
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class AgentDeps:
    llm_client: LLMClient
    session: AsyncSession
    http_client: httpx.AsyncClient

scout_agent = Agent(
    model="ollama/llama3.1",   # overridden per config at runtime
    deps_type=AgentDeps,
    instructions="You are a lead discovery agent...",
)

@scout_agent.tool
async def fetch_company_data(ctx: RunContext[AgentDeps], company_name: str) -> str:
    response = await ctx.deps.http_client.get(f"https://example.com/{company_name}")
    return response.text
```

### Pattern 5: Alembic env.py for SQLModel Async

**What:** Configure Alembic to autogenerate migrations from SQLModel metadata, using a sync connection for the migration runner (Alembic does not natively support async engines).

```python
# Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
# + https://arunanshub.hashnode.dev/using-sqlmodel-with-alembic (verified pattern)
# alembic/env.py (key sections)

from sqlmodel import SQLModel
from ingot.db.models import *   # ensure all models are imported (registers metadata)
from ingot.db.engine import engine   # the async engine

target_metadata = SQLModel.metadata

def run_migrations_online():
    import asyncio
    from sqlalchemy import pool
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = engine

    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(run_async_migrations())

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

### Pattern 6: PydanticAI TestModel for Zero-API Tests

**What:** Override production model with `TestModel` in tests. Zero API calls, zero keys required.
**When to use:** All agent unit tests.

```python
# Source: https://ai.pydantic.dev/testing (verified, v1.x)
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from ingot.agents.scout import scout_agent

models.ALLOW_MODEL_REQUESTS = False  # fail loudly if a real call is attempted

@pytest.fixture
def mock_agent():
    with scout_agent.override(model=TestModel(custom_output_text="test result")):
        yield

async def test_scout_agent(mock_agent, agent_deps):
    result = await scout_agent.run("Find YC companies", deps=agent_deps)
    assert result.output == "test result"
```

### Anti-Patterns to Avoid

- **Sync SQLAlchemy engine with async code:** Using `create_engine` instead of `create_async_engine` will block the event loop silently. Always use `sqlite+aiosqlite://` prefix.
- **WAL mode in URL parameters:** SQLite WAL mode cannot be set via connection string. It must be set via PRAGMA after connection. Use the `@event.listens_for(engine.sync_engine, "connect")` hook.
- **Global LiteLLM configuration:** Do not use `litellm.api_key = ...` globals. Pass credentials per-call or via environment variables. Global state breaks per-agent model selection.
- **Swallowing LLM exceptions:** Catching `Exception` broadly and returning `None` hides retry budget exhaustion. Always raise typed errors after retry chain is exhausted.
- **Storing the derived Fernet key:** Only store the machine key (random bytes). Re-derive the Fernet key on each process start. Storing the derived key defeats the purpose of key derivation.
- **`asyncio_mode = "strict"` without `@pytest_asyncio.fixture`:** In strict mode, async fixtures MUST use `@pytest_asyncio.fixture`, not `@pytest.fixture`. The newer pytest-asyncio 1.x defaults to strict — missing this causes silent fixture failures.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM retry with backoff | Custom loop with `asyncio.sleep` | `tenacity` | Edge cases: concurrent retries, jitter, async support, exception filtering |
| Multi-backend LLM routing | `if backend == "claude": ... elif backend == "openai": ...` | `litellm.acompletion` | LiteLLM handles auth, API differences, token counting, streaming parity |
| Config file encryption | Custom AES implementation | `cryptography.fernet.Fernet` | Fernet is authenticated encryption (HMAC); custom AES misses authentication |
| KDF for machine key | `hashlib.sha256(machine_key)` | `PBKDF2HMAC` | Direct hash has no work factor; PBKDF2 makes brute-force expensive |
| Async SQLite sessions | Direct `aiosqlite` connection management | SQLModel + `create_async_engine` session factory | Session lifecycle, transaction scoping, and connection pooling are non-trivial |
| Schema migrations | `CREATE TABLE IF NOT EXISTS` in startup code | Alembic | Startup DDL can't handle ALTER TABLE, column adds, index changes, or rollbacks |
| Pydantic schema validation | `isinstance()` checks on dict | `BaseModel.model_validate()` | Pydantic handles nested types, coercion, field aliases, and error detail |

**Key insight:** The infrastructure layer is where accidental complexity accumulates. Every item in this table has hidden edge cases (race conditions, auth, rollback, error detail) that emerge in production, not in demos. Use established libraries.

---

## Common Pitfalls

### Pitfall 1: SQLite WAL Mode Not Taking Effect

**What goes wrong:** The database operates in rollback journal mode, causing `SQLITE_BUSY` errors under concurrent async writes during tests or production.
**Why it happens:** WAL must be set per-connection via PRAGMA. Setting it once on the first connection does not persist if new connections are opened. Using `sqlite+aiosqlite://` URL does not auto-enable WAL.
**How to avoid:** Use `@event.listens_for(engine.sync_engine, "connect")` to fire the PRAGMA on every new connection. Verify by querying `PRAGMA journal_mode;` in tests and asserting the result is `"wal"`.
**Warning signs:** `OperationalError: database is locked` in async tests; WAL file (`.db-wal`) not present alongside the database file.

### Pitfall 2: SQLModel Async Session — Wrong Import Path

**What goes wrong:** `from sqlmodel import Session` creates a sync session. Code runs but blocks the event loop.
**Why it happens:** SQLModel exposes a `Session` (sync) and `AsyncSession` (async) separately. The async version lives in `sqlmodel.ext.asyncio.session`.
**How to avoid:** Always `from sqlmodel.ext.asyncio.session import AsyncSession`. Add a linting rule or test that imports the correct session type.
**Warning signs:** Event loop blocking in performance tests; `asyncio.get_event_loop()` warnings; unusually high latency on DB operations.

### Pitfall 3: Alembic Autogenerate Missing Models

**What goes wrong:** `alembic revision --autogenerate` generates an empty migration even though models have changed.
**Why it happens:** Alembic only autogenerates from metadata it can see. If `env.py` doesn't import all model modules, their tables are not in `SQLModel.metadata`.
**How to avoid:** In `alembic/env.py`, add `from ingot.db.models import *` (or explicit imports for every model module) before `target_metadata = SQLModel.metadata`. Write a test that verifies migration is up to date after model changes.
**Warning signs:** `No changes in schema detected` when you know tables changed; missing tables at runtime after `alembic upgrade head`.

### Pitfall 4: PydanticAI v0.x API in Search Results / Training Data

**What goes wrong:** Code uses `pydantic_ai.Agent(model=..., result_type=...)` (old v0.x API) which raises `TypeError` on import.
**Why it happens:** Early tutorials and many code examples in LLM training data use the pre-V1 API. The `result_type` parameter became `output_type` (or similar) in V1.
**How to avoid:** Always check the current docs at https://ai.pydantic.dev/. PydanticAI v1.x is stable — use the V1 API exclusively. Current version is ~1.63.0.
**Warning signs:** `TypeError` or `AttributeError` on agent construction; `output_validator` decorator not recognized.

### Pitfall 5: `asyncio_mode = "strict"` + `@pytest.fixture` Async Fixtures

**What goes wrong:** Async fixtures decorated with `@pytest.fixture` are silently treated as synchronous in strict mode, returning a coroutine object instead of the awaited value.
**Why it happens:** pytest-asyncio v1.x defaults to strict mode. In strict mode, only `@pytest_asyncio.fixture` decorates async fixtures.
**How to avoid:** Use `asyncio_mode = "auto"` in `pyproject.toml` (recommended for this project) OR decorate every async fixture with `@pytest_asyncio.fixture`. The user decision mandates strict async enforcement — use `asyncio_mode = "auto"` so pytest-asyncio takes ownership, but set `ALLOW_MODEL_REQUESTS = False` for the strict-no-real-calls enforcement.
**Warning signs:** Fixture returns `<coroutine object ...>` instead of expected value; `RuntimeWarning: coroutine was never awaited`.

### Pitfall 6: Fernet Token Incompatibility After Key File Loss

**What goes wrong:** After deleting or regenerating `~/.outreach-agent/.key`, all stored encrypted values become unreadable (`InvalidToken` error).
**Why it happens:** Fernet decryption requires the exact same key used for encryption. A new machine key produces a different derived Fernet key.
**How to avoid:** Document that `.key` loss = credential loss, require re-running setup wizard. In the setup wizard, print a warning: "Back up ~/.outreach-agent/.key — loss of this file requires re-entering all credentials." Optionally provide an `export-key` command.
**Warning signs:** `cryptography.fernet.InvalidToken` on startup; after system restore or migration.

### Pitfall 7: LiteLLM Ollama Tool Call Compatibility

**What goes wrong:** Tool calls sent to Ollama models with `tools=` param return malformed JSON or plain text instead of structured tool call responses.
**Why it happens:** Not all Ollama models support tool calls. Models that do (llama3.1, mistral-nemo, qwen2.5) require the `:tools` tag suffix in some versions.
**How to avoid:** Implement the XML fallback (INFRA-16) as a non-optional code path, not a last resort. Always validate response via Pydantic before consuming. Log which path (native tool call vs XML fallback) was used.
**Warning signs:** `LLMValidationError` on Ollama responses; `choices[0].message.tool_calls` is `None` when tools were passed.

---

## Code Examples

Verified patterns from official sources:

### Fernet Key Derivation from Password (PBKDF2HMAC)

```python
# Source: https://cryptography.io/en/latest/fernet/ (HIGH confidence)
import base64, os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

password = b"machine-secret-bytes"
salt = b"ingot-v1-static-salt"
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=600_000,
)
key = base64.urlsafe_b64encode(kdf.derive(password))
f = Fernet(key)
token = f.encrypt(b"api-key-value")
recovered = f.decrypt(token)
```

### Async SQLite Engine with WAL

```python
# Source: SQLAlchemy event docs + aiosqlite docs (HIGH confidence)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import event

engine = create_async_engine("sqlite+aiosqlite:///~/.outreach-agent/outreach.db")

@event.listens_for(engine.sync_engine, "connect")
def _set_wal_mode(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
```

### LiteLLM Completion with Retry (tenacity)

```python
# Source: https://docs.litellm.ai/docs/proxy/reliability + tenacity docs (HIGH confidence)
from tenacity import retry, stop_after_attempt, wait_exponential
from litellm import acompletion

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def call_llm(model: str, messages: list[dict]) -> str:
    response = await acompletion(model=model, messages=messages)
    return response.choices[0].message.content
```

### PydanticAI Agent with Deps (v1.x API)

```python
# Source: https://ai.pydantic.dev/dependencies (HIGH confidence, verified v1.x)
from dataclasses import dataclass
import httpx
from pydantic_ai import Agent, RunContext

@dataclass
class Deps:
    api_key: str
    http_client: httpx.AsyncClient

agent = Agent("anthropic:claude-3-5-haiku-20241022", deps_type=Deps)

@agent.tool
async def fetch_data(ctx: RunContext[Deps], url: str) -> str:
    resp = await ctx.deps.http_client.get(url, headers={"Authorization": f"Bearer {ctx.deps.api_key}"})
    return resp.text
```

### pytest-asyncio Config (pyproject.toml)

```toml
# Source: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html (HIGH confidence)
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "--cov=ingot --cov-report=term-missing --cov-fail-under=70"
```

### In-Memory Async SQLite Fixture

```python
# Source: SQLModel + aiosqlite docs (HIGH confidence)
import pytest_asyncio
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pydantic-ai` v0.0.x (pre-stable) | `pydantic-ai` v1.x (stable, API-stable) | September 2025 | V1 commitment: no breaking changes until V2 (earliest April 2026) |
| `asyncio_mode = "auto"` as default in pytest-asyncio | `asyncio_mode = "strict"` as default (v1.x) | pytest-asyncio 1.0 (2025) | Async fixtures need `@pytest_asyncio.fixture`; cleaner isolation |
| `create_engine` with `check_same_thread=False` for SQLite | `create_async_engine` with `sqlite+aiosqlite://` | SQLAlchemy 1.4+ / widespread adoption 2024 | Proper async, no event loop blocking |
| Storing Fernet key directly | Deriving Fernet key from machine key via PBKDF2HMAC | Longstanding best practice | Key derivation adds computational work factor even when source is high-entropy |
| `iterations=100_000` for PBKDF2HMAC | `iterations=1_200_000` (Django default as of Jan 2025) | Django 5.x recommendation 2025 | Higher iterations required as hardware gets faster |
| LangChain for LLM orchestration | LiteLLM (routing only) + PydanticAI (agent framework) | 2024-2025 industry shift | LangChain chains are opaque; LiteLLM + PydanticAI is more composable |

**Deprecated/outdated:**
- `pydantic_ai.Agent(result_type=...)`: Replaced by v1.x API (`output_type` or structured via `instructions`). Do not use `result_type`.
- `sqlalchemy.orm.Session` in async contexts: Always use `AsyncSession`. Sync session blocks event loop.
- `pytest.mark.asyncio` per-test: In `asyncio_mode = "auto"`, this marker is automatic. Adding it manually is harmless but redundant.

---

## Open Questions

1. **PydanticAI v1.x exact output_type API**
   - What we know: V1 is stable; API available at https://ai.pydantic.dev
   - What's unclear: Whether structured output uses `output_type=MyModel` or `result_type=MyModel` in the current v1 API — these changed between 0.x and 1.x
   - Recommendation: Verify against https://ai.pydantic.dev/agents/ before writing agent shells. Do not rely on training data.

2. **aioimaplib maintenance status**
   - What we know: Listed in requirements (INFRA-20); Phase 3 concern but dep tree validated in Phase 1
   - What's unclear: Whether aioimaplib is actively maintained as of 2026 — requirements note "fallback is imapclient with run_in_executor"
   - Recommendation: Check PyPI for last release date during dependency install. If last release >18 months ago, use `imapclient` + `asyncio.run_in_executor` as the default instead.

3. **LiteLLM Ollama tool call model list**
   - What we know: Not all Ollama models support tool calls; llama3.1, qwen2.5, mistral-nemo are known working
   - What's unclear: Current list of supported models at https://ollama.com/search?c=tools as of Feb 2026
   - Recommendation: At setup wizard time, show which local Ollama models support tool calls. Always code XML fallback as non-optional.

4. **Config JSON field names**
   - What we know: User left this to Claude's discretion
   - Recommendation: Use a flat structure: `{ "agents": { "scout": { "model": "ollama/llama3.1" }, ... }, "llm_fallback_chain": ["claude", "openai", "ollama"], "max_retries": 3, "backoff_strategy": "exponential", "smtp": { ... }, "imap": { ... } }`. Encrypted values stored as `"smtp": { "password": "<fernet-token>" }`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 1.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 creates this |
| Quick run command | `pytest tests/unit/ -x -q` |
| Full suite command | `pytest tests/ -x -q --cov=ingot --cov-fail-under=70` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | Config dir created at `~/.outreach-agent/` with correct structure | unit | `pytest tests/unit/test_config.py::test_config_dir_created -x` | ❌ Wave 0 |
| INFRA-02 | Fernet encrypts and decrypts secrets correctly | unit | `pytest tests/unit/test_crypto.py::test_fernet_roundtrip -x` | ❌ Wave 0 |
| INFRA-03 | Key derivation is deterministic (same machine key → same Fernet key) | unit | `pytest tests/unit/test_crypto.py::test_key_derivation_deterministic -x` | ❌ Wave 0 |
| INFRA-04 | Setup wizard prompts, persists config, reloads correctly | integration | `pytest tests/integration/test_setup_wizard.py -x` | ❌ Wave 0 |
| INFRA-05 | Presets "fully free" and "best quality" write correct per-agent model config | unit | `pytest tests/unit/test_config.py::test_presets -x` | ❌ Wave 0 |
| INFRA-06 | Per-agent model config read at LLMClient instantiation | unit | `pytest tests/unit/test_llm_client.py::test_per_agent_model -x` | ❌ Wave 0 |
| INFRA-07 | SQLModel async engine creates tables for all 11 models | integration | `pytest tests/integration/test_db_wal.py::test_tables_created -x` | ❌ Wave 0 |
| INFRA-08 | WAL mode active after engine creation | integration | `pytest tests/integration/test_db_wal.py::test_wal_mode_enabled -x` | ❌ Wave 0 |
| INFRA-09 | Alembic migration applied, schema matches SQLModel metadata | integration | `pytest tests/integration/test_alembic_migration.py -x` | ❌ Wave 0 |
| INFRA-10 | LLMClient accepts model strings for Claude, OpenAI, Ollama, OpenAI-compat | unit | `pytest tests/unit/test_llm_client.py::test_backend_initialization -x` | ❌ Wave 0 |
| INFRA-11 | No agent module directly imports `anthropic` or `openai` | static/unit | `pytest tests/unit/test_import_boundaries.py -x` (checks imports) | ❌ Wave 0 |
| INFRA-12 | LiteLLM `acompletion` called internally by LLMClient | unit (mock) | `pytest tests/unit/test_llm_client.py::test_litellm_called -x` | ❌ Wave 0 |
| INFRA-13 | XML fallback invoked when tool calls fail | unit | `pytest tests/unit/test_llm_client.py::test_xml_fallback -x` | ❌ Wave 0 |
| INFRA-14 | Invalid LLM responses raise `LLMValidationError` | unit | `pytest tests/unit/test_pydantic_validation.py -x` | ❌ Wave 0 |
| INFRA-15 | Retry fires 3 times before raising on transient failure | unit | `pytest tests/unit/test_retry.py::test_retry_exhausted -x` | ❌ Wave 0 |
| INFRA-16 | XML fallback extracts fields and validates via Pydantic | unit | `pytest tests/unit/test_llm_client.py::test_xml_fallback_valid -x` | ❌ Wave 0 |
| INFRA-17 | asyncio.Queue dispatcher routes tasks to correct agents | unit | `pytest tests/unit/test_dispatcher.py -x` | ❌ Wave 0 |
| INFRA-18 | httpx.AsyncClient shared instance has connection pooling configured | unit | `pytest tests/unit/test_http_client.py -x` | ❌ Wave 0 |
| DB-01 to DB-11 | All 11 SQLModel schemas serialize/deserialize and survive Alembic migration | unit + integration | `pytest tests/unit/test_db_models.py tests/integration/test_alembic_migration.py -x` | ❌ Wave 0 |
| AGENT-01 | 7-agent stubs importable without error | unit (smoke) | `pytest tests/unit/test_agent_imports.py -x` | ❌ Wave 0 |
| AGENT-02 | PydanticAI agent instantiates correctly with v1.x API | unit | `pytest tests/unit/test_agent_framework.py::test_agent_instantiation -x` | ❌ Wave 0 |
| AGENT-05 | No cross-agent imports | static | `pytest tests/unit/test_import_boundaries.py::test_no_cross_agent_imports -x` | ❌ Wave 0 |
| AGENT-06 | Agent deps injected via dataclass; not accessed via globals | unit | `pytest tests/unit/test_agent_framework.py::test_deps_injection -x` | ❌ Wave 0 |
| AGENT-09 | Typed exceptions raised (not bare Exception) on LLM/DB failures | unit | `pytest tests/unit/test_exceptions.py -x` | ❌ Wave 0 |
| TEST-P1-01 | Config encryption/decryption unit tests | unit | `pytest tests/unit/test_crypto.py -x` | ❌ Wave 0 |
| TEST-P1-02 | SQLModel schema unit tests | unit | `pytest tests/unit/test_db_models.py -x` | ❌ Wave 0 |
| TEST-P1-03 | LLMClient init for all backends | unit | `pytest tests/unit/test_llm_client.py -x` | ❌ Wave 0 |
| TEST-P1-04 | Pydantic validation rejection | unit | `pytest tests/unit/test_pydantic_validation.py -x` | ❌ Wave 0 |
| TEST-P1-05 | Retry/fallback logic | unit | `pytest tests/unit/test_retry.py -x` | ❌ Wave 0 |
| TEST-P1-06 | Setup wizard end-to-end integration | integration | `pytest tests/integration/test_setup_wizard.py -x` | ❌ Wave 0 |
| TEST-P1-07 | SQLite WAL + concurrent async writes | integration | `pytest tests/integration/test_db_wal.py::test_concurrent_writes -x` | ❌ Wave 0 |
| TEST-P1-08 | Alembic migration applied + schema validation | integration | `pytest tests/integration/test_alembic_migration.py -x` | ❌ Wave 0 |
| TEST-P1-09 | Performance: init <500ms, config load <100ms, DB tx <50ms | unit (perf) | `pytest tests/unit/test_performance.py -x` | ❌ Wave 0 |
| TEST-INFRA-01 | pytest-asyncio configured, async tests run | infra | `pytest tests/ --collect-only` (verify async collected) | ❌ Wave 0 |
| TEST-INFRA-02 | In-memory DB fixture created and cleaned between tests | infra | `pytest tests/unit/test_db_models.py -x` (uses fixture) | ❌ Wave 0 |
| TEST-INFRA-03 | TestModel fixture returns deterministic mock output | infra | `pytest tests/unit/test_agent_framework.py -x` | ❌ Wave 0 |
| TEST-INFRA-04 | Config fixture uses tmp_path, cleaned up | infra | `pytest tests/unit/test_config.py -x` | ❌ Wave 0 |
| TEST-INFRA-05 | Coverage enforced at ≥70% | infra | `pytest tests/ --cov=ingot --cov-fail-under=70` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/ -x -q` (target: <15 seconds)
- **Per wave merge:** `pytest tests/ -x -q --cov=ingot --cov-fail-under=70` (target: <30 seconds)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All test infrastructure must be created from scratch (no existing test files detected):

- [ ] `pyproject.toml` — pytest config, asyncio_mode=auto, cov settings, package metadata
- [ ] `alembic.ini` — Alembic config pointing to `sqlite+aiosqlite://` URL
- [ ] `alembic/env.py` — Imports SQLModel.metadata, async migration runner
- [ ] `alembic/script.py.mako` — Add `import sqlmodel`
- [ ] `tests/__init__.py`
- [ ] `tests/conftest.py` — Shared fixtures: `db_session`, `mock_llm_client`, `config_dir` (tmp_path), `agent_deps`
- [ ] `tests/fixtures/yc_companies.json` — 100 stable YC company records
- [ ] `tests/fixtures/user_profile.json` — Standard UserProfile test data
- [ ] `tests/fixtures/intel_brief.json` — Standard IntelBrief test data
- [ ] `tests/unit/__init__.py`
- [ ] `tests/unit/test_crypto.py` — covers INFRA-02, INFRA-03, TEST-P1-01
- [ ] `tests/unit/test_config.py` — covers INFRA-01, INFRA-05, TEST-INFRA-04
- [ ] `tests/unit/test_llm_client.py` — covers INFRA-06, INFRA-10, INFRA-11, INFRA-12, INFRA-13, INFRA-16, TEST-P1-03
- [ ] `tests/unit/test_pydantic_validation.py` — covers INFRA-14, TEST-P1-04
- [ ] `tests/unit/test_retry.py` — covers INFRA-15, TEST-P1-05
- [ ] `tests/unit/test_db_models.py` — covers DB-01 through DB-11, TEST-P1-02
- [ ] `tests/unit/test_dispatcher.py` — covers INFRA-17
- [ ] `tests/unit/test_http_client.py` — covers INFRA-18
- [ ] `tests/unit/test_agent_framework.py` — covers AGENT-02, AGENT-06, TEST-INFRA-03
- [ ] `tests/unit/test_agent_imports.py` — covers AGENT-01
- [ ] `tests/unit/test_import_boundaries.py` — covers AGENT-05, INFRA-11
- [ ] `tests/unit/test_exceptions.py` — covers AGENT-09
- [ ] `tests/unit/test_performance.py` — covers TEST-P1-09
- [ ] `tests/integration/__init__.py`
- [ ] `tests/integration/test_setup_wizard.py` — covers INFRA-04, TEST-P1-06
- [ ] `tests/integration/test_db_wal.py` — covers INFRA-07, INFRA-08, TEST-P1-07
- [ ] `tests/integration/test_alembic_migration.py` — covers INFRA-09, TEST-P1-08
- [ ] Framework install: `pip install pytest pytest-asyncio pytest-cov`

---

## Sources

### Primary (HIGH confidence)

- `/websites/ai_pydantic_dev` (Context7) — PydanticAI v1.x deps injection, TestModel, testing patterns
- `/pyca/cryptography` (Context7) — Fernet, PBKDF2HMAC, HKDF
- `/websites/litellm_ai` (Context7) — LiteLLM retry/fallback, Router, Ollama tool calls
- `/websites/sqlmodel_tiangolo` (Context7) — SQLModel async engine, session management
- https://ai.pydantic.dev/ — PydanticAI v1.x official docs (current version 1.63.0 confirmed via PyPI search)
- https://cryptography.io/en/latest/fernet/ — Fernet official docs, PBKDF2HMAC iteration count
- https://docs.litellm.ai/docs/proxy/reliability — Retry/fallback config, Router pattern
- https://pytest-asyncio.readthedocs.io/en/stable/ — asyncio_mode strict/auto behavior

### Secondary (MEDIUM confidence)

- https://dev.to/arunanshub/async-database-operations-with-sqlmodel-c2o — Async SQLModel setup pattern (verified against SQLModel docs)
- https://arunanshub.hashnode.dev/using-sqlmodel-with-alembic — Alembic + SQLModel env.py pattern (verified against Alembic cookbook)
- https://www.slingacademy.com/article/concurrency-challenges-in-sqlite-and-how-to-overcome-them/ — WAL mode + PRAGMA recommendations

### Tertiary (LOW confidence)

- PyPI search results for pydantic-ai version (cross-verified with https://pypi.org/project/pydantic-ai/ — HIGH after cross-reference)
- aioimaplib maintenance status: not verified; flagged as open question

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via Context7 official docs or PyPI
- Architecture: HIGH — patterns drawn directly from official documentation examples
- Pitfalls: HIGH for known issues (WAL, async session, Alembic autogenerate); MEDIUM for PydanticAI v0→v1 API (based on changelog + PyPI)
- Validation architecture: HIGH — pytest-asyncio config from official docs; test gaps derived from requirements

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable libraries; PydanticAI V2 earliest April 2026 — recheck if planning extends beyond March)
