# Project Research Summary

**Project:** INGOT -- INtelligent Generation & Outreach Tool
**Domain:** AI-powered cold outreach (job hunting focus), multi-agent pipeline, local-first CLI/TUI
**Researched:** 2026-02-25
**Confidence:** MEDIUM

## Executive Summary

INGOT is a 7-agent pipeline that scouts job leads, deeply researches each company and contact, matches the user's resume qualifications against each opportunity, and writes highly personalized cold emails. The research confirms this is a tractable single-developer project when built as a parallel-capable async pipeline with SQLite persistence, using PydanticAI for agent orchestration and LiteLLM for multi-backend LLM access. The recommended architecture splits Research into two phases -- lightweight company intel before user approval, expensive contact discovery after -- which avoids the most common waste pattern in AI outreach tools (deep-researching leads the user rejects).

The stack is Python-native and dependency-light: PydanticAI + LiteLLM for agents, SQLModel + aiosqlite for persistence, Typer + Rich for CLI, Textual for TUI, httpx + BeautifulSoup4 for scraping, aiosmtplib + aioimaplib for email. Every component was chosen to be async-native because the pipeline is fundamentally I/O-bound (LLM calls, HTTP scraping, SMTP/IMAP). The "free-first" constraint (every agent runnable on Ollama at zero API cost) is achievable but introduces the single highest technical risk: local model tool-use unreliability. Mitigation requires strict Pydantic validation on every LLM response, retry-with-fallback chains, and per-agent model configuration so users can assign premium models to high-stakes agents (Writer, Research) while keeping cheap models on low-stakes ones (Scout, Analyst).

The top risks are: (1) Gmail account suspension from bulk SMTP sending without a dedicated domain, (2) email deliverability failure from missing SPF/DKIM/DMARC, (3) LLM tool-use unreliability on local models, (4) web scraping brittleness (YC is a React SPA), and (5) CAN-SPAM legal violations from missing required disclosures. All five are preventable with upfront design decisions in Phase 1 (rate limiters, DNS validation, Pydantic validation layer, scrape output validation, and mandatory CAN-SPAM footer injection). None require deferred solutions.

## Key Findings

### Recommended Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Agent Framework | PydanticAI | ~0.0.x (verify PyPI) | Type-safe agent orchestration with native multi-model support |
| LLM Abstraction | LiteLLM | ~1.x (verify PyPI) | Unified client for Claude, OpenAI, Ollama, any OpenAI-compatible API |
| CLI | Typer + Rich + rich-click | ~0.12.x / ~13.x / ~1.x | Command groups, rich terminal output, styled help |
| TUI | Textual | ~0.x (verify PyPI) | Dashboard, leads table, email review panel |
| Email Send | aiosmtplib | ~3.x | Async SMTP (Gmail port 587 STARTTLS) |
| Email Receive | aioimaplib | ~1.x | Async IMAP polling for replies |
| HTTP | httpx | ~0.27.x | Async scraping with HTTP/2, connection pooling |
| HTML Parsing | BeautifulSoup4 + lxml | ~4.12.x / ~5.x | Static page parsing with fast backend |
| Browser (opt-in) | Playwright | ~1.4x | JS-heavy pages via `pip install ingot[browser]` |
| ORM | SQLModel | ~0.0.x (verify PyPI) | Single class = DB table + Pydantic validation |
| DB Driver | aiosqlite | ~0.20.x | Async SQLite for async SQLAlchemy engine |
| Migrations | Alembic | ~1.13.x | Schema version management |
| PDF Parsing | PyMuPDF | ~1.24.x | Resume text extraction (multi-column aware) |
| DOCX Parsing | python-docx | ~1.1.x | Word document parsing |
| Encryption | cryptography (Fernet) | ~42.x | AES-128-CBC + HMAC-SHA256 for config secrets |
| DNS Validation | dnspython | latest | SPF/DKIM/DMARC record verification |
| Scheduling | APScheduler (AsyncIOScheduler) | latest | Follow-up email scheduling |

**Key stack tension:** PydanticAI version is early (~0.0.x as of Aug 2025). If the API has changed significantly by now, LiteLLM alone with manual Pydantic validation is the fallback. Verify PydanticAI's current state on PyPI before committing.

### Expected Features

**Must have (table stakes) -- without these, the product is incomplete:**
- Personalized email body per recipient (not templates)
- Follow-up sequence generation (Day 3, Day 7)
- Review-before-send queue (approve / edit / reject / regenerate)
- Subject line A/B variants (2 per email)
- Resume ingestion and structured UserProfile extraction
- Lead deduplication in Scout
- Reply detection and classification (positive, negative, auto-reply, OOO)
- Rate limiting and send throttling (business hours only)
- Per-recipient tone adaptation (HR vs CEO vs CTO)
- Campaign persistence in SQLite (resume interrupted campaigns)
- First-run setup wizard (SMTP/IMAP, API keys, resume upload)
- Basic open/reply analytics

**Should have (differentiators) -- these are INGOT's competitive edge:**
- Match score (0-100) per lead with explicit value proposition
- Interactive MCQ flow per lead before email generation
- IntelBrief synthesis (company + person intel with signals and talking points)
- Ollama / local LLM as first-class citizen (zero API cost operation)
- Agent pipeline transparency (step-by-step narration)
- Per-agent LLM backend selection (cost optimization)
- pip-installable with zero SaaS dependency

**Nice to have (build if time permits in v1):**
- Pluggable venue discovery system
- Lifecycle hooks for power users
- Batch mode with learned patterns
- Positive reply handling with suggested response
- TUI dashboard (Rich CLI is the primary interface)

### Architecture Approach

The architecture is a **fan-out / gate / fan-out / sequential** pipeline with 7 phases. The critical design insight is splitting Research into two phases separated by a user approval gate. Phase 1 Research is cheap (company/role lookup). Matching + user approval happens next. Phase 2 Research (expensive contact discovery) only runs for approved leads. This saves significant computation and API cost. All state is persisted to SQLite before phase transitions, enabling crash recovery via Lead status queries. Agents communicate through the Orchestrator only -- no agent imports another agent. Dependencies are injected as function arguments.

**Major components:**
1. **Core Infrastructure** (config, db, llm, schemas, repositories, http) -- shared services consumed by all agents
2. **Scout Agent** -- venue scraping, lead discovery, deduplication
3. **Research Agent** -- two-phase intel gathering (lightweight then deep)
4. **Matcher Agent** -- qualification matching, scoring, value proposition generation
5. **Writer Agent** -- email generation with tone adaptation, MCQ flow, follow-up sequences
6. **Outreach Agent** -- send scheduling, rate limiting, IMAP polling, reply classification
7. **Analyst Agent** -- post-campaign metrics, pattern detection, insight persistence
8. **Orchestrator** -- pipeline coordination, fan-out/gather, approval gates, checkpoint/resume

**Key architectural rules:**
- No agent imports another agent; Orchestrator is the only coordinator
- DB is the integration point between non-adjacent pipeline stages
- No abstract base class until 2 concrete implementations need it (exception: LLMClient)
- Orchestrator stays under 250 lines; domain logic lives in agents
- Validate every LLM response against Pydantic schema before passing downstream

### Critical Pitfalls

1. **Gmail account suspension from bulk SMTP** -- Use a dedicated sending domain (never primary Gmail). Hard-cap sends at 30/day for new accounts. Persist per-day/per-hour counters in SQLite. Track bounce rate and pause at 5%.

2. **Email deliverability failure (missing SPF/DKIM/DMARC)** -- DNS validation in setup wizard using dnspython. Block campaign launch if records are missing. Generate the exact DNS records the user needs.

3. **LLM tool-use unreliability on local models** -- Validate every tool response against Pydantic schema. Retry 3x with backoff, fall back to XML extraction, then surface error. Per-agent model config so premium models handle high-stakes agents.

4. **Web scraping brittleness (YC is a React SPA)** -- Check for YC public API first. Validate scraped output (reject if >20% fields None). Make Playwright opt-in easy. Rotate user-agents and add request delays.

5. **CAN-SPAM legal violations** -- Writer agent injects compliant footer on every email. Setup wizard collects physical mailing address. Reply classifier treats unsubscribe intent as first-class. Maintain UnsubscribedEmail suppression table.

## Implications for Roadmap

### Phase 1: Foundation and Core Infrastructure
**Rationale:** Everything depends on config, database, LLM client, and schemas. These must exist and be tested before any agent code.
**Delivers:** Working config system with Fernet encryption, SQLite with WAL mode and migrations, LLMClient with Pydantic validation and retry/fallback, all inter-agent schemas, repository layer, shared HTTP client, minimal setup wizard.
**Features addressed:** Campaign persistence, first-run setup wizard, encrypted config, per-agent LLM backend selection (config layer only).
**Pitfalls avoided:** Fernet key derivation (passphrase+salt from day one), SQLite async locking (aiosqlite+WAL from day one), LLM tool-use unreliability (validation layer from day one), Alembic discipline (established with first migration).
**Stack:** SQLModel, aiosqlite, Alembic, LiteLLM, PydanticAI, cryptography, httpx, dnspython.

### Phase 2: Core Pipeline (Scout through Writer)
**Rationale:** The pipeline from lead discovery to email draft is the product's core value loop. Build it end-to-end before adding the email engine. The v1 done condition is "10 email drafts the user would actually send" -- this phase delivers that.
**Delivers:** Resume parsing and UserProfile extraction, Scout agent with YC venue (direct implementation, no plugin system), Research agent (both phases), Matcher agent with scoring and value prop, Writer agent with tone adaptation and MCQ flow, Orchestrator wiring all phases with approval gate and checkpoint/resume.
**Features addressed:** Resume ingestion, lead deduplication, IntelBrief synthesis, match scoring, value proposition, personalized email generation, subject line variants, follow-up sequences, interactive MCQ flow, review-before-send queue, pipeline transparency, per-recipient tone adaptation.
**Pitfalls avoided:** Over-engineering extensibility (YC venue is direct code, not a plugin), context window overflow (token budget in Research agent), resume parsing edge cases (validation + plain-text fallback), silent LLM failures (typed exceptions, never swallow errors).
**Stack:** PyMuPDF, python-docx, httpx, BeautifulSoup4, lxml, PydanticAI, Typer, Rich.

### Phase 3: Email Engine and Outreach
**Rationale:** Sending requires the pipeline to produce drafts first (Phase 2). Email infrastructure has the highest-risk pitfalls (account suspension, deliverability failure, legal compliance) and must be built carefully with all safeguards from day one.
**Delivers:** SMTP sending with rate limiting and business-hours enforcement, DNS validation (SPF/DKIM/DMARC check before first send), IMAP reply polling and classification, follow-up scheduling (Day 3, Day 7), bounce tracking, unsubscribe suppression, CAN-SPAM footer enforcement.
**Features addressed:** Rate limiting, business-hours send windows, reply detection and classification, follow-up sequences (sending, not just drafting), open pixel tracking.
**Pitfalls avoided:** Gmail account suspension (rate limits, dedicated domain enforcement, bounce tracking), deliverability failure (DNS validation blocks campaign without records), CAN-SPAM violations (footer injection, unsubscribe handling), APScheduler threading (AsyncIOScheduler from start).
**Stack:** aiosmtplib, aioimaplib, dnspython, APScheduler (AsyncIOScheduler).

### Phase 4: Analyst, CLI Polish, and TUI
**Rationale:** Analytics require sent email data (Phase 3). CLI polish and TUI are presentation layer -- they add usability but not core functionality. Build last so the underlying pipeline is stable.
**Delivers:** Analyst agent (reply rate as primary signal, open rate documented as unreliable), complete Rich CLI with all command groups, Textual TUI (if time permits) with dashboard, leads table, email review panel.
**Features addressed:** Basic open/reply analytics, pattern detection, complete CLI command taxonomy, TUI dashboard and keyboard shortcuts.
**Pitfalls avoided:** Open pixel unreliability (documented caveat, reply rate is primary signal), God Orchestrator (by this point Orchestrator should be stable and under 250 lines).
**Stack:** Textual, Rich (polish pass).

### Phase Ordering Rationale

- **Config/DB/LLM before agents:** Every agent depends on these three. Building them first means agents are testable from the moment they exist.
- **Pipeline before email engine:** The v1 done condition is email drafts, not sent emails. Getting to drafts fast validates the entire value proposition (research-grounded, qualification-matched personalization).
- **Email engine as a separate phase:** It carries the highest-risk pitfalls (account suspension, legal liability). Isolating it forces careful implementation with all safeguards.
- **Analyst and TUI last:** Both are read-only consumers of data produced by earlier phases. Neither blocks the core workflow.
- **YC venue as direct code, not a plugin:** Prevents the #1 time-wasting pattern (building plugin infrastructure before the first concrete implementation works). Extract VenueBase when adding the second venue in v2.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Scout/YC venue):** YC's site structure needs live verification. It may be a React SPA requiring Playwright, or there may be a public API. Check api.ycombinator.com and the current site structure before implementing.
- **Phase 3 (Email Engine):** Gmail SMTP limits change frequently. Verify current daily send limits at support.google.com/mail/answer/22839 before setting hard caps.
- **Phase 2 (PydanticAI integration):** PydanticAI was ~0.0.x as of Aug 2025. Verify current API stability and version on PyPI. If it has changed substantially, fall back to LiteLLM with manual Pydantic validation.

Phases with standard patterns (skip deeper research):
- **Phase 1 (Config/DB/LLM):** SQLModel + Alembic + aiosqlite is well-documented. Fernet encryption is straightforward. LiteLLM has stable API.
- **Phase 4 (Analyst/CLI/TUI):** Typer, Rich, and Textual are mature with extensive documentation and examples.

## Deferred to v2

Explicitly deferred features and capabilities across all research files. This is the v2 backlog.

**From FEATURES.md (Anti-Features):**
- Email warmup / dedicated warmup network
- Multi-account inbox rotation
- Contact database / enrichment API
- CRM sync (HubSpot, Salesforce, Pipedrive)
- LinkedIn automation (ToS violation risk)
- A/B test statistical engine
- Multi-user / team mode
- Browser extension
- Continuous monitoring / news alerts
- AI-generated profile photos / image personalization

**From PROJECT.md (Out of Scope):**
- Budget / token cost tracking
- Funding signal monitoring
- LinkedIn warm-up automation
- Warm intro finder
- ATS keyword optimizer module
- Interview prep module
- Application tracker module
- Multi-account Gmail support
- Company news monitoring (RSS/alerts)
- Network graph visualization
- Tech stack detection from job postings
- Smart send timing optimization
- Subject line evolution (auto-feedback to Writer)
- Meeting detection + Calendly auto-injection
- More than 2 venues (remaining venues added incrementally post-v1)

**From ARCHITECTURE.md (v2 infrastructure):**
- Event bus (LeadDiscovered, IntelBriefReady, etc.)
- Agent registry (agents register by name)
- Module registry (ATS, interview prep, application tracker as new agents + TUI screens)
- Integration layer (named adapters for third-party services)
- Hook system (user-defined lifecycle hooks in ~/.outreach-agent/hooks/)
- Venue plugin system with VenueBase abstraction and auto-discovery
- Redis queue for multi-process parallelism
- Guided venue creation wizard

**From PITFALLS.md (v2 mitigations):**
- Gmail API with OAuth2 (preferred over raw SMTP but requires GCP project setup)
- Multi-process parallelism via Redis (for large campaigns beyond v1's 10-lead target)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | All libraries are well-established except PydanticAI (early version, verify on PyPI). LiteLLM, SQLModel, Typer, Rich, Textual, httpx are all mature. |
| Features | MEDIUM | Competitor analysis based on Aug 2025 training data. Feature landscape is stable but specific competitor capabilities may have changed. PROJECT.md requirements are HIGH confidence. |
| Architecture | HIGH | The fan-out/gate/fan-out pattern, two-phase research split, and repository pattern are well-understood. Build order is dependency-driven and sound. |
| Pitfalls | MEDIUM | Gmail SMTP limits and Ollama tool-use reliability are the two areas most likely to have changed since Aug 2025. Legal requirements (CAN-SPAM) and technical patterns (SQLite+async, scraping) are stable. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **PydanticAI version and API stability:** Verify current version on PyPI. If API has changed significantly from the 0.0.x era, adjust agent implementation approach.
- **YC site structure:** Live verification needed. Check for public API at api.ycombinator.com. Determine if httpx is sufficient or if Playwright is required.
- **Gmail SMTP daily limits:** Verify current numbers at support.google.com/mail/answer/22839. The 30/day conservative cap may be too low or too high.
- **Ollama tool-use model compatibility:** Check ollama.com/search?c=tools for current models with reliable tool support. The model landscape has likely changed since Aug 2025.
- **aioimaplib maintenance status:** Less prominent library. Verify it is still maintained on PyPI. Alternative: imapclient with run_in_executor wrapper if aioimaplib is abandoned.

## Sources

### Primary (HIGH confidence)
- PROJECT.md -- product requirements, constraints, and context (direct source of truth)
- Python ecosystem knowledge (SQLModel, Alembic, Typer, Rich, Textual, httpx, aiosmtplib) -- stable, well-documented libraries

### Secondary (MEDIUM confidence)
- PydanticAI capabilities and API -- based on Aug 2025 training data; rapid evolution expected
- LiteLLM multi-backend routing -- stable but version-specific behavior
- Competitor landscape (Apollo, Hunter, Lemlist, Instantly, Smartlead, Woodpecker) -- Aug 2025 snapshot
- Gmail SMTP limits and suspension behavior -- subject to Google policy changes
- Ollama tool-use reliability by model -- rapidly evolving

### Tertiary (LOW confidence)
- aioimaplib library status -- less prominent, needs PyPI verification
- YC site structure and API availability -- needs live verification

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
