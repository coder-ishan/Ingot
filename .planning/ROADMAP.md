# Roadmap: INGOT — INtelligent Generation & Outreach Tool

## Overview

INGOT is built in four phases that follow a strict dependency order: shared services before
agents, agents before sending, sending before analytics. Phase 2 is the v1 done condition —
ten personalized email drafts the user would actually send, end-to-end from YC lead discovery
through the interactive MCQ review queue. Phases 3 and 4 extend the product into a complete
outreach system with real sending, reply handling, analytics, and a polished CLI and TUI.
Every pitfall identified in research (Gmail suspension, deliverability, CAN-SPAM, LLM
tool-use unreliability, scraping brittleness) is addressed in the phase where it is first
introduced, not deferred.

## Milestone

**v1 — First 10 Emails**
Done condition: User has 10 personalized email drafts in the review queue, each grounded
in real company and person research, matched against the user's resume qualifications,
and ready to approve, edit, or regenerate. No emails need to be sent for v1 to be complete.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation and Core Infrastructure** - All shared services exist and are tested; any agent can be built without re-solving config, DB, or LLM
- [ ] **Phase 2: Core Pipeline (Scout through Writer)** - Pipeline produces 10 email drafts the user would actually send (v1 done condition)
- [ ] **Phase 3: Email Engine and Outreach** - Emails get sent safely with rate limiting, DNS validation, bounce tracking, reply polling, and CAN-SPAM compliance
- [ ] **Phase 4: Analyst, CLI Polish, and TUI** - Analytics, complete CLI command groups, optional TUI dashboard, pip packaging

## Phase Details

### Phase 1: Foundation and Core Infrastructure
**Goal**: All shared services exist and are tested. Any agent can be built without re-solving
config, DB, or LLM. Every pitfall that can be wired in from day one is wired in here:
Fernet key derivation, aiosqlite WAL mode, Pydantic validation layer, retry/fallback chain.
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07,
INFRA-08, INFRA-09, INFRA-10, INFRA-11, INFRA-12, INFRA-13, INFRA-14, INFRA-15, INFRA-16,
INFRA-17, INFRA-18, INFRA-19, INFRA-20, DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07,
DB-08, DB-09, DB-10, DB-11, AGENT-01, AGENT-02, AGENT-03, AGENT-05, AGENT-06, AGENT-07,
AGENT-08, AGENT-09, TEST-P1-01, TEST-P1-02, TEST-P1-03, TEST-P1-04, TEST-P1-05,
TEST-P1-06, TEST-P1-07, TEST-P1-08, TEST-P1-09, TEST-INFRA-01, TEST-INFRA-02,
TEST-INFRA-03, TEST-INFRA-04, TEST-INFRA-05, TEST-INFRA-06, TEST-INFRA-07, TEST-INFRA-08
**Success Criteria** (what must be TRUE):
  1. User can run the setup wizard and complete it in under 5 minutes: credentials are
     encrypted and persisted, config reloads correctly on next run, per-agent LLM backend
     selection is reflected in config.json
  2. LLMClient connects to at least one configured backend (Claude, OpenAI, or Ollama),
     returns a validated Pydantic response, retries on transient failure with exponential
     backoff, and falls back to XML extraction when JSON tool calls fail
  3. All 11 database models (UserProfile, Lead, IntelBrief, Match, Email, FollowUp,
     Campaign, AgentLog, Venue, OutreachMetric, UnsubscribedEmail) exist in SQLite, are
     readable and writable via async ORM calls, and the Alembic migration applies cleanly
     from a fresh database
  4. Running the test suite passes all Phase 1 unit and integration tests with minimum 70%
     coverage on config, encryption, DB, and LLMClient modules; no test requires real API
     keys or real SMTP credentials
**Plans**: TBD

Plans:
- [ ] 01-01: Config system, Fernet encryption, setup wizard, directory structure
- [ ] 01-02: SQLite models, aiosqlite async engine, WAL mode, Alembic migration
- [ ] 01-03: LLMClient (LiteLLM), Pydantic validation, retry/fallback, tool-use compatibility
- [ ] 01-04: Agent framework (PydanticAI or LiteLLM fallback), shared httpx client, async task dispatcher
- [ ] 01-05: Test infrastructure (pytest-asyncio, fixtures, mocks) and Phase 1 test suite

### Phase 2: Core Pipeline (Scout through Writer)
**Goal**: The pipeline produces 10 email drafts the user would actually send. This is the
v1 done condition. Every step from lead discovery to draft-in-review-queue works
end-to-end: YC scraping, two-phase research with approval gate, qualification matching,
interactive MCQ email generation, and the review queue (approve / edit / reject /
regenerate). No sending required for this phase to be complete.
**Depends on**: Phase 1
**Requirements**: PROFILE-01, PROFILE-02, PROFILE-03, PROFILE-04, PROFILE-05, PROFILE-06,
PROFILE-07, PROFILE-08, PROFILE-09, SCOUT-01, SCOUT-02, SCOUT-03, SCOUT-04, SCOUT-05,
SCOUT-06, SCOUT-07, SCOUT-08, RESEARCH-01, RESEARCH-02, RESEARCH-03, RESEARCH-04,
RESEARCH-05, RESEARCH-06, RESEARCH-07, RESEARCH-08, RESEARCH-09, RESEARCH-10, MATCH-01,
MATCH-02, MATCH-03, MATCH-04, MATCH-05, WRITER-01, WRITER-02, WRITER-03, WRITER-04,
WRITER-05, WRITER-06, WRITER-07, WRITER-08, WRITER-09, WRITER-10, WRITER-11, WRITER-12,
WRITER-13, AGENT-04, TEST-P2-01, TEST-P2-02, TEST-P2-03, TEST-P2-04, TEST-P2-05,
TEST-P2-06, TEST-P2-07, TEST-P2-08, TEST-P2-09, TEST-P2-10, TEST-P2-11, TEST-P2-12,
TEST-P2-13, TEST-P2-14, TEST-P2-15, TEST-P2-16
**Success Criteria** (what must be TRUE):
  1. User uploads a PDF or DOCX resume through the setup wizard and UserProfile is
     extracted with all required fields (name, headline, skills, experience, education,
     projects, github_url, linkedin_url, resume_raw_text); extraction is rejected and
     user is prompted to retry if fewer than 10% of fields are populated
  2. Scout agent discovers leads from YC and presents them in the CLI; leads are
     deduplicated by email (case-insensitive), each has an initial score, and all lead
     data is persisted to SQLite with status "discovered"
  3. Research agent completes Phase 1 (lightweight company intel) for each lead, presents
     results to the user at the approval gate, and transitions approved leads to Phase 2
     research (expensive contact discovery with talking points); rejected or deferred leads
     do not consume Phase 2 tokens
  4. Matcher agent produces a match score (0-100) and explicit value proposition for each
     approved lead; both are specific to the company and role, not generic statements
  5. Writer agent runs the interactive MCQ flow (2-3 personalized questions per lead
     referencing the IntelBrief), generates a personalized email draft with tone adapted
     to recipient type (HR / CTO / CEO), includes 2 subject line variants, Day 3 and Day 7
     follow-up drafts, a CAN-SPAM compliant footer, and places the full draft set in the
     review queue; user can approve, edit inline, reject, or regenerate each draft
  6. Running the full pipeline end-to-end on 5 fixture leads completes without unhandled
     errors; the Orchestrator checkpoint/resume mechanism preserves all state across a
     simulated interruption; all Phase 2 tests pass with minimum 70% coverage and
     performance benchmarks met (Scout under 5s on 100 YC companies, full pipeline under
     15s on 5 leads)
**Plans**: TBD

Plans:
- [ ] 02-01: Resume parsing (PyMuPDF, python-docx, plain-text fallback) and UserProfile extraction
- [ ] 02-02: Scout agent — YC venue (direct httpx + BeautifulSoup4, API check first), deduplication, initial scoring
- [ ] 02-03: Research agent — Phase 1 (lightweight) and Phase 2 (deep), approval gate, IntelBrief schema
- [ ] 02-04: Matcher agent — match score, value proposition, confidence level
- [ ] 02-05: Writer agent — MCQ flow, email generation, tone adaptation, subject variants, follow-up sequences, CAN-SPAM footer
- [ ] 02-06: Orchestrator wiring, approval gate, checkpoint/resume, Rich CLI review queue (approve/edit/reject/regenerate)
- [ ] 02-07: Phase 2 test suite — unit, integration, end-to-end, regression, performance

### Phase 3: Email Engine and Outreach
**Goal**: Emails actually get sent safely. Dedicated domain enforcement, DNS validation,
rate limiting, bounce tracking, reply polling, follow-up scheduling, unsubscribe
suppression, and CAN-SPAM compliance are all in place before the first real send.
Gmail account suspension and legal liability are the two highest-risk pitfalls; this
phase addresses both completely.
**Depends on**: Phase 2
**Requirements**: OUTREACH-01, OUTREACH-02, OUTREACH-03, OUTREACH-04, OUTREACH-05,
OUTREACH-06, OUTREACH-07, OUTREACH-08, OUTREACH-09, OUTREACH-10, OUTREACH-11,
OUTREACH-12, OUTREACH-13, OUTREACH-14, OUTREACH-15, OUTREACH-16, OUTREACH-17,
TEST-P3-01, TEST-P3-02, TEST-P3-03, TEST-P3-04, TEST-P3-05, TEST-P3-06,
TEST-P3-07, TEST-P3-08, TEST-P3-09, TEST-P3-10, TEST-P3-11, TEST-P3-12, TEST-P3-13
**Success Criteria** (what must be TRUE):
  1. Setup wizard runs DNS validation (SPF, DKIM, DMARC) via dnspython and blocks campaign
     launch if required records are missing; when records are missing, the exact DNS record
     values the user needs to add are displayed
  2. SMTP sending via Gmail (port 587 STARTTLS) works with credentials loaded from
     encrypted config; the per-day counter (hard cap 30) and per-hour counter (hard cap 5)
     are enforced and persisted to SQLite; sends outside the 9 AM - 5 PM recipient
     timezone window and on weekends are held until the next valid window
  3. Bounce rate is tracked continuously; if the bounce rate exceeds 5%, all sends are
     paused and the user is notified with the current bounce rate and the threshold
  4. IMAP polling detects replies and classifies them (positive, negative, auto-reply,
     OOO, unsubscribe intent); unsubscribe intent adds the address to the
     UnsubscribedEmail suppression table and no further emails are sent to that address
  5. Day 3 and Day 7 follow-up emails are scheduled via APScheduler (AsyncIOScheduler)
     and are only sent if no positive reply has been received; on positive reply, the user
     is notified and a Calendly link option is surfaced
  6. All Phase 3 email engine tests pass; the regression suite validates that Phase 2
     draft data flows into Phase 3 sending without data loss or schema errors
**Plans**: TBD

Plans:
- [ ] 03-01: SMTP sending (aiosmtplib), rate limiting (per-day/per-hour counters), business-hours enforcement, DNS validation
- [ ] 03-02: IMAP reply polling (aioimaplib), reply classification, unsubscribe detection, suppression table
- [ ] 03-03: Follow-up scheduling (APScheduler AsyncIOScheduler), bounce tracking, open pixel tracking, send logging
- [ ] 03-04: Phase 3 test suite — unit, integration, regression

### Phase 4: Analyst, CLI Polish, and TUI
**Goal**: Full product polish. Analytics identify which outreach patterns are working,
the Rich CLI has all command groups complete, and the optional Textual TUI provides
a dashboard view and keyboard-driven email review panel. pip packaging makes the tool
installable by others.
**Depends on**: Phase 3
**Requirements**: ANALYST-01, ANALYST-02, ANALYST-03, ANALYST-04, ANALYST-05,
CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08, CLI-09,
TUI-01, TUI-02, TUI-03, TUI-04, TUI-05, TUI-06,
TEST-P4-01, TEST-P4-02, TEST-P4-03, TEST-P4-04, TEST-P4-05, TEST-P4-06,
TEST-P4-07, TEST-P4-08, TEST-P4-09
**Success Criteria** (what must be TRUE):
  1. Analyst agent calculates reply rate (positive replies / sent emails) as the primary
     signal and presents it in the campaign metrics dashboard; open rate is tracked but
     displayed with a documented caveat about pixel unreliability; pattern findings
     (which talking points, company sizes, and roles convert most) are persisted for
     Writer context in future runs
  2. All CLI command groups are complete and functional: agents (list/logs/inspect),
     data (leads/emails/stats/export), mail (pending/review/approve/reject/track),
     run (scout/research/match/write/followup/analyze), config (show/set/setup); all
     commands produce styled Rich terminal output (tables, panels, color-coded badges);
     --help works for every command; invalid args are rejected with clear error messages
  3. The Textual TUI loads without errors, tab navigation works (Overview / Leads / Email
     Review / Settings), the leads table sorts by match score and status, and keyboard
     shortcuts (e=edit, a=approve, r=reject, g=regenerate) are all functional in the
     email review panel
  4. All Phase 4 tests pass; manual QA checklist is complete (CLI output readable and
     colorized, TUI responsive, keyboard shortcuts confirmed, setup wizard completes in
     under 5 minutes end-to-end)
**Plans**: TBD

Plans:
- [ ] 04-01: Analyst agent — reply rate, open rate caveat, pattern detection, insight persistence, campaign metrics dashboard
- [ ] 04-02: Complete Rich CLI — all command groups, styled output, --help, config commands, test send command
- [ ] 04-03: Textual TUI — dashboard tabs, leads table, email review panel with keyboard shortcuts, settings screen
- [ ] 04-04: pip packaging, install docs, Phase 4 test suite and manual QA

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Core Infrastructure | 0/5 | Not started | - |
| 2. Core Pipeline (Scout through Writer) | 0/7 | Not started | - |
| 3. Email Engine and Outreach | 0/4 | Not started | - |
| 4. Analyst, CLI Polish, and TUI | 0/4 | Not started | - |

## Coverage

All v1 requirements are mapped to exactly one phase. Counts by category:

| Category | Count | Phase |
|----------|-------|-------|
| INFRA-01 to INFRA-20 | 20 | Phase 1 |
| DB-01 to DB-11 | 11 | Phase 1 |
| AGENT-01 to AGENT-09 (framework + arch) | 8 (AGENT-01,02,03,05,06,07,08,09) | Phase 1 |
| AGENT-04 (Orchestrator runtime) | 1 | Phase 2 |
| PROFILE-01 to PROFILE-09 | 9 | Phase 2 |
| SCOUT-01 to SCOUT-08 | 8 | Phase 2 |
| RESEARCH-01 to RESEARCH-10 | 10 | Phase 2 |
| MATCH-01 to MATCH-05 | 5 | Phase 2 |
| WRITER-01 to WRITER-13 | 13 | Phase 2 |
| OUTREACH-01 to OUTREACH-17 | 17 | Phase 3 |
| ANALYST-01 to ANALYST-05 | 5 | Phase 4 |
| CLI-01 to CLI-09 | 9 | Phase 4 |
| TUI-01 to TUI-06 | 6 | Phase 4 |
| TEST-P1-01 to TEST-P1-09 | 9 | Phase 1 |
| TEST-P2-01 to TEST-P2-16 | 16 | Phase 2 |
| TEST-P3-01 to TEST-P3-13 | 13 | Phase 3 |
| TEST-P4-01 to TEST-P4-09 | 9 | Phase 4 |
| TEST-INFRA-01 to TEST-INFRA-08 | 8 | Phase 1 |

**Total v1 requirements mapped: 177 / 177**

## Future Additions / v2 Backlog

Everything below was identified as valuable during planning and explicitly deferred
so v1 stays focused on the done condition (10 email drafts). These are the first
candidates for Phase 5+ after v1 ships.

### Infrastructure and Architecture

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| Event bus (LeadDiscovered, IntelBriefReady, EmailDrafted, etc.) | No observers in v1; architect when integrations are added | INFRA-V2-01 |
| Agent registry (agents register by name, Orchestrator routes via lookup) | Single hardcoded agent set in v1 | INFRA-V2-02 |
| Module registry (ATS, interview prep, application tracker as agents + TUI screens) | Out of scope for cold outreach core | INFRA-V2-03 |
| Integration adapters (Calendly, Notion, Slack) | Gmail-only in v1; extensible later | INFRA-V2-04 |
| User-defined hook system (~/.outreach-agent/hooks/) | Power user feature; v1 focuses on happy path | INFRA-V2-05 |
| Redis queue for multi-process parallelism | asyncio.Queue sufficient for v1's 10-lead target | INFRA-V2-06 |
| Budget and token cost tracking per agent and campaign | Cost awareness secondary to email quality in v1 | INFRA-V2-07 |
| Venue plugin system (VenueBase abstract class, auto-discovery) | Extract VenueBase when adding second venue; no premature abstraction | INFRA-V2-08, INFRA-V2-09 |
| Guided venue creation wizard (--venue-setup) | Requires pluggable venue system first | INFRA-V2-10 |

### Scout and Lead Discovery

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| Additional venues: Apollo, Hunter, ProductHunt, Crunchbase, AngelList, LinkedIn | Prove pipeline end-to-end with YC; scale venues incrementally | SCOUT-V2-01 |
| Cross-venue deduplication (same person found via multiple venues consolidated) | Only one venue in v1 | SCOUT-V2-02 |
| Warm intro finder (common connections via LinkedIn network graph) | Requires network graph; advanced for v1 scope | SCOUT-V2-03 |

### Research and Intelligence

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| Funding signal monitoring (Series rounds, funding announcements) | Deep one-shot research is sufficient for v1; continuous monitoring is v2 | RESEARCH-V2-01 |
| Company news monitoring (RSS feeds, hiring signals, tech stack changes) | Not core to cold outreach pipeline | RESEARCH-V2-02 |
| Tech stack detection from job postings | Optional signal; v1 focuses on company and person intel | RESEARCH-V2-03 |
| LinkedIn warm-up automation | ToS violation risk; careful legal review needed before v2 | RESEARCH-V2-04 |

### Writer and Email Generation

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| Batch mode with learned patterns (auto-generate once 3+ emails approved with similar patterns) | Requires approved email history to learn from; post-v1 | WRITER-V2-01 |
| Subject line evolution (auto-feedback from open and reply metrics to Writer) | Manual insight feedback in v1; automation in v2 | WRITER-V2-02 |
| Meeting detection and Calendly auto-injection | Depends on Calendly integration; deferred to v2 | WRITER-V2-03 |
| Positive reply suggested response templates | Simplify reply handling in v1; add templates in v2 | WRITER-V2-04 |

### Outreach and Email Engine

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| Gmail API with OAuth2 (replaces raw SMTP) | Requires GCP project setup; SMTP is simpler for v1 | OUTREACH-V2-01 |
| Multi-account Gmail support (rotate sending domains for large campaigns) | Single-user tool in v1; multi-account is a team feature | OUTREACH-V2-02 |
| Smart send timing optimization (learn best times per recipient type) | Learning curve; fixed business-hours window sufficient for v1 | OUTREACH-V2-03 |
| Email warmup and dedicated warmup network integration | Infrastructure investment; not needed for 30/day v1 volume | OUTREACH-V2-04 |

### Analytics

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| A/B test statistical engine (confidence intervals for subject variant performance) | Manual interpretation in v1; statistical analysis in v2 | ANALYST-V2-01 |
| Network graph visualization (relationship mapping, warm intro paths) | Advanced UI; not core to pipeline | ANALYST-V2-02 |
| CRM sync (HubSpot, Salesforce, Pipedrive) | Enterprise feature; out of scope for personal tool | ANALYST-V2-03 |

### Profile and Resume

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| Contact database and enrichment API integration (Apollo, Hunter for email validation) | Enrichment in v2; v1 uses scraping and Research agent | PROFILE-V2-01 |

### TUI and Interface

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| Network graph visualization screen in TUI | Requires network graph data from v2 Scout | TUI-V2-01 |
| A/B test performance dashboard in TUI | Requires statistical engine from v2 Analyst | TUI-V2-02 |

### Modules (v2+)

| Item | Why Deferred | v2 Requirement |
|------|-------------|----------------|
| ATS keyword optimizer module | Specialty module; not core to cold outreach | MODULES-V2-01 |
| Interview prep module | Outside cold outreach scope | MODULES-V2-02 |
| Application tracker module | Outside cold outreach scope | MODULES-V2-03 |
| Browser extension | Client distribution; defer to v2 | MODULES-V2-04 |
| Multi-user / team mode | Single-user tool in v1 | MODULES-V2-05 |

### Technical Decisions That May Change

| Decision | v1 Stance | Revisit Trigger |
|----------|-----------|-----------------|
| PydanticAI as agent framework | Use if API is stable on PyPI; fall back to LiteLLM + manual Pydantic if not | Verify on PyPI before Phase 1 planning |
| aioimaplib for async IMAP | Use if actively maintained; fall back to imapclient + run_in_executor | Verify maintenance status on PyPI |
| 30/day Gmail hard cap | Conservative cap for new sending domain | Verify current Google limits at support.google.com/mail/answer/22839 |
| httpx-only for YC scraping | API check first; Playwright fallback if YC is a gated React SPA | Live verification of api.ycombinator.com needed in Phase 2 |
| Ollama tool-use model compatibility | XML prompt-engineered fallback covers all models | Check ollama.com/search?c=tools for current tool-capable models |

---
*ROADMAP.md — INGOT v1 specification*
*Created: 2026-02-25*
*Milestone: v1 — First 10 Emails*
