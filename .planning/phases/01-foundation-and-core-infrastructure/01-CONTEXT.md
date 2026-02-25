# Phase 1: Foundation and Core Infrastructure - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

All shared services that every future agent builds on: config system, Fernet encryption, setup wizard, SQLite database (11 models), LLMClient (LiteLLM), agent framework (PydanticAI or fallback), and the Phase 1 test suite. No user-facing features beyond the setup wizard CLI. All other agent functionality (Scout, Composer, etc.) is out of scope for this phase.

</domain>

<decisions>
## Implementation Decisions

### Setup Wizard UX
- Interactive terminal prompts — one credential at a time, with input masking and inline validation
- Re-run behavior: only prompt for missing or invalid values — skip already-configured credentials entirely
- After completion: display a summary table of all configured services (API keys masked, DB path, selected model per agent)
- Non-interactive mode: accept flags or environment variables (e.g., `ANTHROPIC_API_KEY=xxx job-hunter setup --non-interactive`) for CI/scripted deploys

### Runtime Feedback
- Default output: structured progress lines prefixed by agent name — e.g., `[Scout] Fetching YC profile...`, `[Composer] Drafting email...`
- Two opt-in verbosity levels:
  - `-v` — show detailed progress (step completions, retry attempts, timing)
  - `-vv` — full debug mode (LLM prompts, raw API responses, all internal state)
- Logging: full trace always written to log file (`./logs/` or `~/.job-hunter/logs/`); terminal shows only filtered, actionable lines
- Concurrent agents: output interleaved, always prefixed by agent name — `[AgentName]` prefix disambiguates parallel runs

### Failure Behavior
- LLM failures (all retries exhausted): fail the agent run with a clear, descriptive error message — e.g., `[Scout] Failed: Claude API unreachable after 3 retries. Check your API key or try again later.` Surface backend fallback (try OpenAI, then Ollama) as a configurable option in config.json, not the default
- Database write failures: best-effort — save what succeeded, log everything that failed with enough context to retry manually. No hard crash on partial writes
- Retry configuration: user-tunable in config.json (`max_retries`, `backoff_strategy: exponential`) — defaults are sane, not hardcoded
- Unhandled exceptions (code bugs): friendly one-liner to terminal (`Something went wrong. Full error logged to logs/run-YYYY-MM-DD.log`) with full traceback written to log file

### Testing Philosophy
- Coverage targets: 80%+ on critical paths (encryption, DB operations, LLM retry/fallback logic); 70% minimum for remaining modules — match roadmap baseline for non-critical paths
- All LLM calls mocked in tests — zero real API hits, no API key required to run the suite
- Test suite must run in under 30 seconds: use in-memory SQLite for DB tests, all external calls mocked
- Strict async enforcement: `asyncio` strict mode + `pytest-asyncio` strict mode — catch unawaited coroutines and blocking calls in async paths before they reach production

### Claude's Discretion
- Exact log file rotation and retention policy
- Specific progress bar or spinner implementation (if any) within the structured progress line format
- Internal fixture patterns and factory helpers for the test suite
- Exact `config.json` schema field names (beyond what's already specified in requirements)

</decisions>

<specifics>
## Specific Ideas

- Verbosity flags follow Unix convention: `-v` / `-vv` — consistent with tools developers already know (curl, git, ansible)
- Setup wizard should complete in under 5 minutes (this is a stated success criterion from the roadmap — keep prompts minimal and smart defaults generous)
- Log file location should be discoverable: wizard summary table should include the log file path so users know where to look when things break

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within Phase 1 scope

</deferred>

---

*Phase: 01-foundation-and-core-infrastructure*
*Context gathered: 2026-02-25*
