---
phase: 01-foundation-and-core-infrastructure
plan: 04
status: complete
completed: 2026-02-26
branch: feature/01-04-agent-framework
commit: a8c921d
---

# Plan 01-04 Summary — Agent Framework

## What Was Built

### Files Created

| File | Purpose |
|------|---------|
| `src/ingot/agents/base.py` | `AgentDeps` dataclass + `AgentBase` protocol |
| `src/ingot/agents/registry.py` | `AGENT_REGISTRY` dict, `register_agent`, `get_agent`, `list_agents` |
| `src/ingot/agents/orchestrator.py` | Orchestrator skeleton (70 lines — well under 250 AGENT-07 limit) |
| `src/ingot/agents/scout.py` | Scout agent shell |
| `src/ingot/agents/research.py` | Research agent shell |
| `src/ingot/agents/matcher.py` | Matcher agent shell |
| `src/ingot/agents/writer.py` | Writer agent shell |
| `src/ingot/agents/outreach.py` | Outreach agent shell (imports aiosmtplib + aioimaplib) |
| `src/ingot/agents/analyst.py` | Analyst agent shell |
| `src/ingot/http_client.py` | Shared `httpx.AsyncClient` singleton with connection pooling |
| `src/ingot/dispatcher.py` | `AsyncTaskDispatcher` over `asyncio.Queue` with worker pool |

### Files Modified

| File | Change |
|------|--------|
| `src/ingot/agents/__init__.py` | Rewired to import all 6 agent modules (triggers self-registration) |

## PydanticAI v1.63.0 API Discoveries

**Confirmed v1.x API** (deviations from RESEARCH.md v0.x examples):

| Parameter | v0.x (old) | v1.x (v1.63.0) |
|-----------|-----------|----------------|
| Return type | `result_type=` | `output_type=` |
| Model format | `"ollama/llama3.1"` (slash) | `"ollama:llama3.1"` (colon) |
| Deferred validation | not available | `defer_model_check=True` |

**Critical finding**: `Agent.__init__` validates the model at construction time by default. For shells where the model is injected from runtime config, `defer_model_check=True` is required — otherwise `import ingot.agents` would fail in environments without Ollama's env vars set.

## Agent Registration Pattern

All 6 non-Orchestrator agents self-register at import time:

```python
from ingot.agents.registry import register_agent
scout_agent = Agent("ollama:llama3.1", deps_type=AgentDeps, defer_model_check=True, ...)
register_agent("scout", scout_agent)
```

`agents/__init__.py` imports all 6 modules, so `from ingot.agents import *` populates the full registry. Orchestrator imports them explicitly with the AGENT-05 exception comment.

## AgentDeps Fields (for Plan 01-05 fixture setup)

```python
@dataclass
class AgentDeps:
    llm_client: LLMClient       # from ingot.llm.client
    session: AsyncSession        # SQLAlchemy async session
    http_client: httpx.AsyncClient  # from get_http_client()
    verbosity: int = 0           # 0=normal, 1=-v, 2=-vv
    agent_name: str = ""         # set by Orchestrator before dispatch
```

For test fixtures: mock `LLMClient`, use in-memory SQLite `AsyncSession`, and `httpx.AsyncClient` (or `httptest` mock transport).

## Constraints Satisfied

- **AGENT-05**: No agent file imports from another agent file — AST-verified at test time
- **AGENT-06**: AgentDeps carries injected resources — no global state in agents
- **AGENT-07**: Orchestrator is 70 lines (limit: 250)
- **INFRA-17**: AsyncTaskDispatcher drains queue correctly with N concurrent workers
- **INFRA-18**: Shared httpx.AsyncClient singleton with pooling (max_connections=10)
- **INFRA-19/20**: aiosmtplib + aioimaplib importable (validated in outreach.py)

## Decisions Made

- `defer_model_check=True` on all agent shells — model name is config-driven
- `"ollama:llama3.1"` as the default — matches v1.63.0 `provider:model` format
- SMTP/IMAP stubs live in `outreach.py` (most natural home) rather than `__init__.py`
- Registry is a plain `dict` in v1 — no dynamic discovery needed until v2
