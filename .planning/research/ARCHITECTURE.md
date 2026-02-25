# Architecture

**Project:** INGOT — INtelligent Generation & Outreach Tool
**Researched:** 2026-02-25
**Dependencies:** PROJECT.md, STACK.md, PITFALLS.md

---

## 1. Recommended Architecture Pattern

**Use a parallel-capable pipeline with async queues and direct function calls for v1.**

No event bus. No message queue broker. No DAG engine.

**Rationale:**

INGOT's pipeline is not a simple linear chain — it has natural parallelism points and a two-phase research split with a user approval gate in the middle. The architecture must support:

- **Parallel scouting** across venues (concurrent tool calls and scraping).
- **Parallel lightweight research** per discovered lead (company profile, role analysis).
- **User approval gate** after initial research + matching (saves computation on rejected leads).
- **Parallel deep research** only for approved leads (email/social discovery — the expensive part).
- **Sequential writing and outreach** per approved lead.

This is a **fan-out / gate / fan-out / sequential** pattern, not a linear chain or an arbitrary DAG. It is implemented with `asyncio.Queue` for producer-consumer handoff and `asyncio.gather` / `asyncio.TaskGroup` for parallel execution within each phase. No external infrastructure needed.

**Why not an event bus:** One subscriber per event in v1. The bus adds indirection with zero benefit. Debug with stack traces, not event logs.

**Why not a message queue (Redis/RabbitMQ):** INGOT is a single-process asyncio application on one machine. `asyncio.Queue` is the in-process equivalent with zero setup.

**Why not a DAG engine (Prefect/Airflow):** Scheduled batch workflow engines. INGOT is an interactive CLI tool. The overhead of a DAG engine dwarfs the 10-lead v1 target.

**When to revisit:** Add an event bus in v2 when the hook system and module registry need to observe pipeline events. Add Redis queue in v2 if multi-process parallelism is needed for large campaigns.

---

## 2. Component Boundaries

### What belongs in each agent

Each agent is a single module with one or more public async entry points. Agents own their prompts, tool definitions, and output schemas. Agents do NOT own database access, LLM client instantiation, or configuration loading.

| Agent | Owns | Does NOT Own |
|-------|------|--------------|
| **Orchestrator** | Pipeline coordination, fan-out/gather logic, queue management, user approval flow, checkpoint/resume, user chat interface | LLM calls for other agents, direct DB writes for leads/emails |
| **Scout** | Venue scraping logic (parallel tool calls per venue), lead deduplication, initial lead summary generation, queue publishing | HTTP client configuration, venue plugin discovery (v2) |
| **Research** | Two-phase research logic: Phase 1 (lightweight company/role intel) and Phase 2 (deep contact discovery — email, social profiles). Token budget management. | Raw HTTP fetching (uses shared httpx client), HTML parsing (uses shared utility) |
| **Matcher** | Matching prompt, scoring rubric, ValueProp generation, match score calculation against Phase 1 research | UserProfile loading (receives as input), IntelBrief loading (receives as input) |
| **Writer** | Email generation prompts, tone adaptation by role (HR/CEO/CTO), subject line variants, follow-up sequence drafts, CAN-SPAM footer injection | Email sending, template storage |
| **Outreach** | Send scheduling, rate limiting, IMAP polling, reply classification, follow-up queue management, bounce tracking | SMTP/IMAP connection setup (uses shared email client), email content generation |
| **Analyst** | Metric aggregation queries, pattern detection prompts, insight generation | Data collection (reads from DB), real-time event monitoring (v2) |

### What belongs in shared infrastructure

```
ingot/
  core/
    llm.py          # LLMClient — single abstraction over all backends via LiteLLM
    db.py           # Engine creation, session factory, WAL mode setup
    config.py       # Config loading, Fernet decryption, per-agent model resolution
    models.py       # All SQLModel definitions (Lead, IntelBrief, Email, Campaign, etc.)
    schemas.py      # Pure Pydantic models for inter-agent data (not DB-bound)
    http.py         # Shared httpx.AsyncClient with UA rotation, rate limiting
    exceptions.py   # Typed exceptions for the entire pipeline
    repositories.py # All DB read/write operations (repository pattern)
  agents/
    orchestrator.py
    scout.py
    research.py
    matcher.py
    writer.py
    outreach.py
    analyst.py
  cli/
    ...
  tui/
    ...
```

**Rules:**
- No agent imports another agent. The Orchestrator calls agents; agents never call each other.
- All agents receive dependencies as function arguments (dependency injection), not by importing globals.
- `core/` modules have zero imports from `agents/`. The dependency arrow is one-way: agents -> core.

---

## 3. Data Flow

The pipeline has five distinct phases with two parallelism fan-outs and one user approval gate. The key insight: **split Research into two phases to avoid wasting computation on leads the user rejects.**

```
┌──────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATOR                                │
│  Manages fan-out, queues, approval gates, and pipeline resumption.   │
└──────┬───────────────────────────────────────────────────────────────┘
       │
       ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 1: PARALLEL SCOUTING                                        ║
║                                                                      ║
║  Scout spawns concurrent tasks per venue (v1: YC only, but the       ║
║  architecture supports multiple). Each task:                         ║
║    - Scrapes venue via httpx (parallel tool calls)                   ║
║    - Extracts raw lead data                                          ║
║    - Deduplicates against existing leads in DB                       ║
║    - Creates a LeadSummary per lead                                  ║
║    - Pushes LeadSummary onto research_queue (asyncio.Queue)         ║
║                                                                      ║
║  Output: research_queue populated with LeadSummary objects           ║
║  Persists: Lead rows in SQLite with status=discovered                ║
╚══════════════════════════════════════════════════════════════════════╝
       │
       │ asyncio.Queue[LeadSummary]
       ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 2: PARALLEL LIGHTWEIGHT RESEARCH (Research Phase 1)          ║
║                                                                      ║
║  Orchestrator spawns N research workers (configurable concurrency,   ║
║  default 3). Each worker pulls from research_queue and runs:         ║
║    - Company profile lookup (website, mission, size, stage)          ║
║    - Role analysis (what they're hiring for, team structure)         ║
║    - Initial signal detection (funding, launches, growth indicators) ║
║    - Talking point extraction                                        ║
║                                                                      ║
║  This phase does NOT search for:                                     ║
║    - Specific person email addresses                                 ║
║    - Social media profiles                                           ║
║    - Deep contact information                                        ║
║  (Those are expensive and only done for approved leads.)             ║
║                                                                      ║
║  Output: IntelBrief (partial — company_intel + signals, no contact)  ║
║  Persists: IntelBrief rows with status=phase1_complete               ║
║  Lead status: discovered -> researched_phase1                        ║
╚══════════════════════════════════════════════════════════════════════╝
       │
       │ Lead + IntelBrief (phase 1)
       ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 3: MATCHING + USER APPROVAL GATE                             ║
║                                                                      ║
║  Matcher runs on each Phase 1 researched lead:                       ║
║    - Cross-references UserProfile against IntelBrief                 ║
║    - Generates match score (0-100) and ValueProp                     ║
║    - Applies threshold filter (default: 40)                          ║
║                                                                      ║
║  Leads above threshold are presented to user for approval:           ║
║    - Interactive mode: per-lead review with company summary,         ║
║      match score, value prop. User approves/rejects/skips.           ║
║    - Batch mode: auto-approve above threshold (after patterns        ║
║      learned from interactive sessions).                             ║
║                                                                      ║
║  Output: Approved lead IDs                                           ║
║  Persists: match_score + value_prop on Lead row                      ║
║  Lead status: researched_phase1 -> matched -> approved OR shelved    ║
╚══════════════════════════════════════════════════════════════════════╝
       │
       │ List[Lead] (approved only)
       ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 4: PARALLEL DEEP RESEARCH (Research Phase 2)                 ║
║                                                                      ║
║  Only for approved leads. Spawns workers to find:                    ║
║    - Best person to contact (decision maker for this role)           ║
║    - Email address (patterns, verification)                          ║
║    - LinkedIn / Twitter / GitHub profiles                            ║
║    - Person-specific intel (recent posts, talks, interests)          ║
║    - Refined talking points based on person + company context        ║
║                                                                      ║
║  This is the expensive phase — saved only for leads worth pursuing.  ║
║                                                                      ║
║  Output: IntelBrief (complete — company + person + contact)          ║
║  Persists: IntelBrief updated with contact details and person intel  ║
║  Lead status: approved -> researched_phase2                          ║
╚══════════════════════════════════════════════════════════════════════╝
       │
       │ Lead + IntelBrief (complete) + MatchResult + UserProfile
       ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 5: WRITING                                                    ║
║                                                                      ║
║  Writer generates per approved lead:                                 ║
║    - Personalized email body (tone adapts to recipient role)         ║
║    - 2 subject line variants for A/B testing                         ║
║    - Follow-up sequence (Day 3, Day 7)                               ║
║    - CAN-SPAM compliant footer                                       ║
║                                                                      ║
║  In interactive mode: MCQ questions per lead before generation.      ║
║  Draft enters review queue: approve, edit, reject, regenerate.       ║
║                                                                      ║
║  Output: EmailDraft                                                  ║
║  Persists: Email row with status=draft                               ║
║  Lead status: researched_phase2 -> drafted                           ║
╚══════════════════════════════════════════════════════════════════════╝
       │
       │ Email (status=approved after review)
       ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 6: OUTREACH                                                   ║
║                                                                      ║
║  Outreach agent handles approved emails:                             ║
║    - Send via SMTP with rate limiting and business-hours enforcement  ║
║    - Schedule follow-ups (Day 3, Day 7) via AsyncIOScheduler         ║
║    - Poll IMAP for replies                                           ║
║    - Classify replies: positive, negative, auto-reply, OOO, unsub    ║
║    - On positive reply: notify user, suggest response                ║
║                                                                      ║
║  Persists: Email status -> sent, reply rows                          ║
║  Lead status: drafted -> approved -> sent -> replied                 ║
╚══════════════════════════════════════════════════════════════════════╝
       │
       ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 7: ANALYSIS (post-campaign, not inline)                      ║
║                                                                      ║
║  Analyst reads from DB after sends complete:                         ║
║    - Open rates (caveat: unreliable due to Gmail proxy / Apple MPP)  ║
║    - Reply rates (primary reliable signal)                           ║
║    - Pattern detection across campaigns                              ║
║    - Insights written back to DB for Writer context in future runs   ║
║                                                                      ║
║  Persists: CampaignReport row                                       ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key design decisions:**

- **Persist before passing.** Every phase writes output to SQLite before the next phase reads it. A crash at any point resumes from the last persisted Lead status.
- **Two-phase Research saves computation.** Phase 1 is cheap (company/role lookup). Phase 2 is expensive (contact discovery, person-level research). The user approval gate between them means you never waste deep research on leads that get rejected.
- **Parallel within phases, sequential between phases.** Scout tasks run in parallel. Research Phase 1 workers run in parallel. Research Phase 2 workers run in parallel. But phases themselves are sequential — you cannot match before researching.
- **asyncio.Queue as the handoff mechanism.** Scout pushes to the queue, Research workers pull from it. No external broker needed. Queue depth is bounded (default 50) to apply backpressure.
- **Analyst runs post-campaign**, not inline. It is a reporting tool, not a pipeline stage.

### Lead Status State Machine

```
discovered
  -> researched_phase1       (lightweight research complete)
    -> matched               (matcher scored the lead)
      -> shelved             (below threshold OR user rejected)
      -> approved            (user approved for deep research)
        -> researched_phase2 (deep research complete — contact info found)
          -> drafted         (email written, in review queue)
            -> approved      (user approved email for sending)  [email status, not lead]
              -> sent        (email sent via SMTP)
                -> replied   (reply received and classified)
```

---

## 4. Agent Communication

**Use direct async function calls with asyncio.Queue for fan-out phases.**

The Orchestrator imports each agent's entry point and coordinates execution:

```python
# orchestrator.py — simplified pipeline execution
async def run_pipeline(campaign_id: int, deps: PipelineDeps) -> None:
    # Phase 1: Parallel scouting
    research_queue: asyncio.Queue[LeadSummary] = asyncio.Queue(maxsize=50)
    await scout.discover(deps.venue_configs, deps.llm, deps.db, research_queue)

    # Phase 2: Parallel lightweight research (fan-out)
    phase1_leads = []
    async with asyncio.TaskGroup() as tg:
        for _ in range(deps.config.research_concurrency):  # default 3
            tg.create_task(
                research.run_phase1(research_queue, deps.llm, deps.db, deps.http)
            )
    # Workers exit when queue is drained (sentinel pattern)

    phase1_leads = await repos.get_leads_by_status(deps.db, "researched_phase1")

    # Phase 3: Matching + user approval gate
    approved_leads = []
    for lead in phase1_leads:
        brief = await repos.get_intel_brief(deps.db, lead.id)
        match = await matcher.evaluate(lead, brief, deps.profile, deps.llm, deps.db)

        if match.score < deps.config.match_threshold:
            await repos.update_lead_status(deps.db, lead.id, "shelved")
            continue

        # Present to user for approval
        approved = await deps.approval_flow.present(lead, brief, match)
        if approved:
            approved_leads.append(lead)
            await repos.update_lead_status(deps.db, lead.id, "approved")
        else:
            await repos.update_lead_status(deps.db, lead.id, "shelved")

    # Phase 4: Parallel deep research (fan-out, approved leads only)
    deep_queue: asyncio.Queue[Lead] = asyncio.Queue()
    for lead in approved_leads:
        await deep_queue.put(lead)

    async with asyncio.TaskGroup() as tg:
        for _ in range(deps.config.research_concurrency):
            tg.create_task(
                research.run_phase2(deep_queue, deps.llm, deps.db, deps.http)
            )

    # Phase 5: Writing (per lead, sequential for interactive MCQ flow)
    for lead in approved_leads:
        brief = await repos.get_intel_brief(deps.db, lead.id)  # now complete
        match = await repos.get_match_result(deps.db, lead.id)
        draft = await writer.draft_email(
            lead, brief, match, deps.profile, deps.llm, deps.db
        )
        await deps.review_queue.put(draft)
        # Interactive mode: user reviews each draft here
        # Batch mode: drafts accumulate in review queue

    # Phase 6 & 7: Outreach and Analyst run separately via CLI commands
```

**What `PipelineDeps` contains:**

```python
@dataclass
class PipelineDeps:
    llm: LLMClient
    db: AsyncSession
    http: httpx.AsyncClient
    profile: UserProfile
    config: CampaignConfig
    venue_configs: list[VenueConfig]
    review_queue: asyncio.Queue
    approval_flow: ApprovalFlow  # interactive or batch
```

**Migration path to event bus (v2):**

When the hook system and module registry land, wrap each phase transition:

```python
# v2 — event bus added alongside direct calls
await research.run_phase1(...)
await event_bus.emit(ResearchPhase1Complete(lead_id=lead.id))
```

The event bus is additive. Direct calls remain the primary execution path.

---

## 5. Build Order

Build in this exact order. Each phase produces a testable, runnable artifact.

### Phase 1: Foundation (no agents yet)

1. **`core/config.py`** — Config loading from `~/.outreach-agent/config.json`, Fernet encryption/decryption with passphrase+salt, per-agent model resolution. This unblocks everything else.
2. **`core/models.py` + `core/db.py`** — SQLModel definitions for all models (UserProfile, Lead, IntelBrief, Email, Campaign, AgentLog, Venue). Async engine with aiosqlite + WAL mode. Alembic initialization and first migration. Lead status field with the full state machine.
3. **`core/llm.py`** — LLMClient wrapping LiteLLM. Supports `completion()` and `tool_call()` with Pydantic validation on every tool response. Retry with backoff (3 attempts tool-use, then XML fallback, then error). Context window estimation.
4. **`core/schemas.py`** — Pure Pydantic models for inter-agent data: `LeadSummary`, `IntelBrief` (with phase1/phase2 distinction), `MatchResult`, `EmailDraft`, `ValueProp`, `CampaignReport`.
5. **`core/repositories.py`** — All DB operations: save/get/update for Lead, IntelBrief, Email, Campaign, AgentLog. Status transitions.
6. **`core/http.py`** — Shared httpx.AsyncClient with UA rotation, configurable delays, timeout defaults.
7. **Setup wizard (minimal)** — Collect and encrypt: LLM backend selection, API keys, Gmail credentials. Resume upload deferred to Phase 2.

**Testable artifact:** `python -m ingot config show` displays decrypted config. `python -m ingot db check` confirms migrations and WAL mode.

### Phase 2: Core Pipeline (Scout through Writer)

1. **Resume parsing + UserProfile extraction** — PyMuPDF + python-docx -> raw text -> LLM structured extraction -> validated UserProfile with sanity checks (min 200 words, at least 1 experience, 3 skills).
2. **Scout agent + YC venue** — Implement YC scraping directly (no plugin system). Parallel tool calls for scraping. Validate output: reject if >20% fields are None. Push LeadSummary objects onto research_queue.
3. **Research agent Phase 1** — Lightweight company/role research. Parallel workers pulling from queue. Token budget management. IntelBrief (partial) assembly.
4. **Matcher agent** — Cross-reference UserProfile against Phase 1 IntelBrief. Score 0-100. Generate ValueProp. Threshold filter.
5. **Research agent Phase 2** — Deep contact discovery. Email finding, social profiles, person-level intel. Only runs for approved leads. Completes the IntelBrief.
6. **Writer agent** — Email generation with tone adaptation, 2 subject variants, CAN-SPAM footer, follow-up sequences. Interactive MCQ flow.
7. **Orchestrator (v1)** — Wire all phases: parallel scouting -> parallel Phase 1 research -> matching + approval gate -> parallel Phase 2 research -> writing. Checkpoint/resume via Lead status in DB.

**Testable artifact:** `python -m ingot run scout` discovers leads from YC. `python -m ingot run pipeline` produces 10 email drafts in the review queue.

### Phase 3: Email Engine + Outreach

1. **SMTP sending** — aiosmtplib, rate limiter with per-day/per-hour counters persisted in SQLite, business hours enforcement.
2. **DNS validation** — Check SPF/DKIM/DMARC via dnspython before first send. Block campaign if missing.
3. **IMAP polling** — aioimaplib, reply classification (positive, negative, auto-reply, OOO, unsubscribe). Unsubscribe suppression.
4. **Follow-up scheduling** — AsyncIOScheduler, Day 3 and Day 7 follow-ups for non-replies.
5. **Outreach agent** — Compose all of the above. Watch for approved emails, send on schedule, poll replies, manage follow-up queue.

**Testable artifact:** Send 1 approved email to a test address. Receive reply. Classify reply correctly.

### Phase 4: Analyst + CLI/TUI Polish

1. **Analyst agent** — Query DB for campaign metrics. Reply rate as primary signal (open rate documented as unreliable). Pattern detection. Insights persisted for Writer context.
2. **Rich CLI completion** — All command groups (agents, data, mail, run, config) with rich output.
3. **TUI (if time permits)** — Textual dashboard, leads table, email review panel.

**Testable artifact:** `python -m ingot run analyze` produces a campaign report. Full CLI workflow from `ingot run scout` through `ingot mail approve` to `ingot run send`.

### v1 Done Condition

10 personalized email drafts the user would actually send. Generated from real YC leads, grounded in real research and real resume qualifications. Each draft is based on two-phase research and user-approved matching.

---

## 6. Patterns to Follow

### Dependency Injection via Function Arguments

Every agent function receives its dependencies as arguments. No agent imports `db`, `llm`, or `config` at module level.

```python
# Good
async def run_phase1(
    queue: asyncio.Queue[LeadSummary],
    llm: LLMClient,
    db: AsyncSession,
    http: httpx.AsyncClient,
) -> None:
    ...

# Bad
from ingot.core.db import get_session  # module-level import of runtime dependency
async def run_phase1(queue: asyncio.Queue) -> None:
    db = get_session()  # hidden dependency
```

**Why:** Testability. Pass a mock LLMClient and in-memory SQLite in tests. Swap Ollama for Claude by passing a different LLMClient instance. No monkey-patching.

### Repository Pattern for Database Access

Agents do not write raw SQL or SQLAlchemy queries. All DB access goes through `core/repositories.py`.

```python
# core/repositories.py
async def save_lead(session: AsyncSession, lead: Lead) -> Lead: ...
async def get_leads_by_status(session: AsyncSession, status: str) -> list[Lead]: ...
async def update_lead_status(session: AsyncSession, lead_id: int, status: str) -> None: ...
async def get_intel_brief(session: AsyncSession, lead_id: int) -> IntelBrief | None: ...
async def save_intel_brief(session: AsyncSession, brief: IntelBrief) -> IntelBrief: ...
```

**Why:** Single place for logging, validation, and status transition enforcement. Agents focus on domain logic.

### Pydantic Models as Agent Contracts

Every agent input and output is a Pydantic model in `core/schemas.py`. These are the contracts between agents.

```python
class LeadSummary(BaseModel):
    """Scout output -> Research Phase 1 input"""
    company_name: str
    venue_url: str
    raw_description: str
    discovered_at: datetime

class IntelBrief(BaseModel):
    """Research output -> Matcher/Writer input"""
    # Phase 1 fields (filled by lightweight research)
    company_name: str
    company_description: str
    company_stage: str | None
    recent_signals: list[str]
    roles_hiring: list[str]
    talking_points: list[str]
    sources: list[str]
    phase1_complete: bool = False

    # Phase 2 fields (filled by deep research, only for approved leads)
    contact_name: str | None = None
    contact_role: str | None = None
    contact_email: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    twitter_url: str | None = None
    person_intel: str | None = None
    refined_talking_points: list[str] = []
    phase2_complete: bool = False
```

**Why:** Type safety across the pipeline. LLM tool responses validate against these schemas — malformed output is caught immediately, not three phases downstream.

### Explicit Error Types

Define typed exceptions in `core/exceptions.py`.

```python
class IngotError(Exception): ...
class LLMToolValidationError(IngotError): ...
class LLMContextOverflowError(IngotError): ...
class VenueScrapeError(IngotError): ...
class MatchBelowThresholdError(IngotError): ...
class EmailRateLimitError(IngotError): ...
class ContactNotFoundError(IngotError): ...
class ResearchBudgetExhaustedError(IngotError): ...
```

**Why:** Orchestrator handles each type differently — retry LLM errors, skip leads with scrape errors, shelve low matches, pause on rate limits.

### Status-Driven Pipeline Resumption

Every Lead tracks its position via the status state machine (see Section 3). The Orchestrator queries by status to determine what work remains:

```python
# Resume after crash
needs_phase1 = await repos.get_leads_by_status(db, "discovered")
needs_matching = await repos.get_leads_by_status(db, "researched_phase1")
needs_phase2 = await repos.get_leads_by_status(db, "approved")
needs_writing = await repos.get_leads_by_status(db, "researched_phase2")
```

**Why:** SQLite is the single source of truth. No in-memory state to lose on crash. No checkpoint files.

### Queue-Based Fan-Out with Bounded Concurrency

Use `asyncio.Queue` with a sentinel pattern for parallel phases:

```python
SENTINEL = None

async def run_parallel_workers(
    worker_fn: Callable,
    queue: asyncio.Queue,
    concurrency: int,
    **kwargs,
) -> None:
    async with asyncio.TaskGroup() as tg:
        for _ in range(concurrency):
            tg.create_task(worker_fn(queue, **kwargs))
    # After all items processed, workers exit on SENTINEL

async def worker(queue: asyncio.Queue, llm: LLMClient, db: AsyncSession, **kwargs):
    while True:
        item = await queue.get()
        if item is SENTINEL:
            queue.task_done()
            break
        try:
            await process(item, llm, db, **kwargs)
        finally:
            queue.task_done()
```

**Why:** Bounded concurrency prevents overwhelming Ollama (which is typically CPU/GPU-bound on one machine) or triggering rate limits on API backends. Default concurrency of 3 is a safe starting point.

### Structured Logging with AgentLog

Every agent call logs to the `AgentLog` table: agent name, lead ID, phase, action, duration, token count, success/failure, error message.

```python
async def log_agent_action(
    session: AsyncSession,
    agent: str,
    lead_id: int | None,
    phase: str,
    action: str,
    duration_ms: int,
    tokens_used: int = 0,
    success: bool = True,
    error: str | None = None,
) -> None: ...
```

**Why:** `ingot agents logs --agent=research --phase=phase2` shows every deep research call with timing and errors. Essential for debugging a multi-phase parallel pipeline.

---

## 7. Anti-Patterns to Avoid

### Circular Dependencies Between Agents

**Wrong:** Analyst feeds insights to Writer, Writer calls Analyst to check if an insight applies.

**Right:** Analyst writes insights to DB. Writer reads insights from DB at generation time. No import, no call, no coupling. The database is the integration point between non-adjacent pipeline stages.

**Rule:** Draw the import graph. If there is a cycle, refactor. Agents never import other agents. The Orchestrator is the only module that imports agent entry points.

### God Orchestrator

**Wrong:** Orchestrator contains prompt logic, scoring thresholds, email formatting, retry logic, rate limiting, and queue management internals. 800 lines.

**Right:** Orchestrator is a coordinator (~150-200 lines). It manages fan-out, queues, approval gates, and status-driven resumption. All domain logic lives in the agent that owns it. The parallel worker pattern (Section 6) is a shared utility, not Orchestrator code.

**Detection rule:** If the Orchestrator exceeds 250 lines, extract logic into the agent or utility that should own it.

### Premature Abstraction

**Wrong:** Build `VenueBase`, `VenueRegistry`, `VenuePluginLoader`, and `VenueConfig` before the first venue (YC) works.

**Right:** Implement `yc_venue.py` as a plain module with functions. When the second venue is added, extract the common interface into `VenueBase`. The abstraction emerges from concrete code.

**Rule:** No abstract base class until there are 2 concrete implementations that need it. The sole exception is `LLMClient`, which is justified because it has 3 known backends from day one.

### Shared Mutable State Between Agents

**Wrong:** A global `pipeline_state` dict that parallel research workers read and write concurrently.

**Right:** Each agent receives immutable input (Pydantic models) and returns immutable output. State changes go through the DB via repository functions with proper async session management. `asyncio.Queue` is the only shared mutable structure, and it is designed for concurrent access.

### Silent Failures from LLM Calls

**Wrong:** Agent catches `Exception` from LLM call, logs a warning, and returns a default/empty IntelBrief that propagates downstream.

**Right:** Agent catches `LLMToolValidationError`, retries up to 3 times with backoff, falls back to XML extraction, and if all fail, raises to the Orchestrator. The Orchestrator marks the lead with an error status and moves to the next lead. A missing IntelBrief is better than a hallucinated one.

**Rule:** Never silently swallow an LLM error. A bad IntelBrief produces a bad email. A bad email damages the user's reputation.

### Running Phase 2 Research on Unapproved Leads

**Wrong:** Research all leads deeply first, then let the user reject half of them. Waste of tokens, time, and API cost.

**Right:** The architecture enforces the gate: Phase 1 research is cheap. Matching + user approval decides who gets Phase 2. Deep research (contact discovery, email finding, social profiles) only runs for leads the user wants to pursue.

### Over-Configuring for Flexibility

**Wrong:** Every string is configurable — prompt templates, scoring weights, concurrency, retry counts, queue sizes, timeouts, thresholds. Config has 200 keys.

**Right:** Hardcode sensible defaults. Make configurable only: LLM backend per agent, match score threshold, research concurrency, send rate limit, business hours window. Add more config keys when users ask for them, not before.

### Testing Against Production LLMs Only

**Wrong:** All tests require a live Ollama instance with a specific model. CI is impossible. Tests take 30 seconds each.

**Right:** Unit tests use a mock LLMClient that returns predetermined Pydantic models. Integration tests (marked slow) run against Ollama. Both exist. Unit tests gate PRs; integration tests are the safety net.

---

## Summary: v1 Architecture at a Glance

| Aspect | Decision |
|--------|----------|
| Pattern | Parallel-capable pipeline with async queues and direct function calls |
| Parallelism | Fan-out via `asyncio.Queue` + `TaskGroup` in Scout, Research Phase 1, Research Phase 2 |
| Communication | Orchestrator calls agents; `asyncio.Queue` for producer-consumer handoff |
| Research strategy | Two-phase: lightweight (pre-approval) and deep (post-approval) |
| Approval gate | After Phase 1 research + matching; before expensive Phase 2 research |
| State | SQLite is the single source of truth; Lead status drives pipeline resumption |
| Agent coupling | Zero. Agents never import each other. DB is the integration point. |
| Dependencies | Injected as function arguments; never imported at module level |
| LLM abstraction | LLMClient wrapping LiteLLM; Pydantic validation on every response |
| Error handling | Typed exceptions; retry with backoff; never silently swallow |
| Abstractions | Only LLMClient is abstract from day one; everything else starts concrete |
| Build order | Config -> DB -> LLM -> Schemas -> Repos -> HTTP -> Agents (Scout first, Analyst last) |
| Concurrency | Bounded worker pools (default 3); backpressure via bounded queues |

---

*Last updated: 2026-02-25*
