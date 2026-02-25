# Requirements: INGOT — INtelligent Generation & Outreach Tool

**Defined:** 2026-02-25
**Core Value:** Every email sent is grounded in real research about the company AND real qualifications from the user's resume — no generic templates, no spray-and-pray.

**v1 Done Condition:** 10 personalized email drafts the user would actually send, end-to-end from lead discovery through review queue.

---

## v1 Requirements

### INFRA — Core Infrastructure

- [ ] **INFRA-01**: Config system with ~/.outreach-agent/ directory structure (config.json, outreach.db, logs/, resume/, venues/)
- [ ] **INFRA-02**: Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) for all stored secrets
- [ ] **INFRA-03**: Encryption key derivation from local machine key (deterministic, stored securely)
- [ ] **INFRA-04**: First-run setup wizard: Gmail SMTP/IMAP credentials, API keys per LLM backend, resume upload
- [ ] **INFRA-05**: Setup presets: "fully free" (all Ollama) and "best quality" (Claude Sonnet for Writer+Research, Haiku for rest)
- [ ] **INFRA-06**: Per-agent LLM backend selection via config.json (not global single model)
- [ ] **INFRA-07**: SQLite database via SQLModel ORM with aiosqlite async driver
- [ ] **INFRA-08**: SQLite WAL mode enabled for concurrent async access
- [ ] **INFRA-09**: Alembic schema migration system (initial migration + deployment tested)
- [ ] **INFRA-10**: LLMClient abstraction with support for Claude (anthropic SDK), OpenAI (openai SDK), Ollama (OpenAI-compatible to localhost:11434), LM Studio, any OpenAI-compatible API
- [ ] **INFRA-11**: Single LLMClient entry point — no agent directly imports anthropic or openai
- [ ] **INFRA-12**: LLMClient uses LiteLLM internally for multi-backend routing
- [ ] **INFRA-13**: Tool-use compatibility: native JSON tool calls for models that support it, prompt-engineered XML fallback for models without
- [ ] **INFRA-14**: Strict Pydantic validation on every LLM response before passing downstream
- [ ] **INFRA-15**: Retry logic with exponential backoff (3 retries) on transient LLM failures
- [ ] **INFRA-16**: Fallback to XML extraction when JSON tool calls fail
- [ ] **INFRA-17**: Async task dispatcher with worker pool (asyncio.Queue base, Redis optional for v2)
- [ ] **INFRA-18**: Shared async HTTP client (httpx) with connection pooling and request delays for scraping
- [ ] **INFRA-19**: Async SMTP client (aiosmtplib) for email sending
- [ ] **INFRA-20**: Async IMAP client (aioimaplib) for reply polling

### PROFILE — Resume Ingestion and UserProfile Extraction

- [ ] **PROFILE-01**: Setup wizard prompts for resume upload (PDF or DOCX)
- [ ] **PROFILE-02**: PDF parsing via PyMuPDF (fitz) with multi-column awareness
- [ ] **PROFILE-03**: DOCX parsing via python-docx
- [ ] **PROFILE-04**: Plain-text fallback if parsing fails (user copy-pastes text)
- [ ] **PROFILE-05**: LLM-powered structured extraction to UserProfile schema
- [ ] **PROFILE-06**: UserProfile contains: name, headline, skills[], experience[], education[], projects[], github_url, linkedin_url, resume_raw_text
- [ ] **PROFILE-07**: UserProfile persisted to SQLite (one active profile per user, versioning for later)
- [ ] **PROFILE-08**: Matcher and Writer agents load UserProfile on every run
- [ ] **PROFILE-09**: Resume validation: reject if <10% fields extracted (user retries with raw text)

### SCOUT — Lead Discovery and Deduplication

- [ ] **SCOUT-01**: Scout agent discovers leads from venues in parallel
- [ ] **SCOUT-02**: YC venue as primary discovery source for v1 (direct implementation, not plugin system yet)
- [ ] **SCOUT-03**: YC scraping strategy: check api.ycombinator.com for public API first, fallback to httpx + BeautifulSoup4
- [ ] **SCOUT-04**: YC scraping output validation: reject if >20% fields None
- [ ] **SCOUT-05**: User-agent rotation and request delays for YC scraping
- [ ] **SCOUT-06**: Lead deduplication by email address (case-insensitive)
- [ ] **SCOUT-07**: Initial lead scoring (confidence in contact info, company fit signals)
- [ ] **SCOUT-08**: Lead model persisted with status (discovered, researching, matched, drafted, sent, replied)

### RESEARCH — IntelBrief Generation (Two-Phase)

- [ ] **RESEARCH-01**: Phase 1 Research (lightweight, pre-approval): company name lookup, role parsing, public LinkedIn/web presence
- [ ] **RESEARCH-02**: Phase 1 Research: lightweight company signals (funding status, size, growth signals from public data)
- [ ] **RESEARCH-03**: Phase 1 Research output: IntelBrief schema with company_name, company_signals, person_name, person_role, company_website
- [ ] **RESEARCH-04**: User approval gate after Phase 1 (accept/reject/defer lead)
- [ ] **RESEARCH-05**: Phase 2 Research (expensive, post-approval): contact discovery, personal background research, talking points synthesis
- [ ] **RESEARCH-06**: Phase 2 Research: LinkedIn profile analysis (public data), GitHub profile analysis (if available), recent work signals
- [ ] **RESEARCH-07**: Phase 2 Research: three talking points per lead (company achievement + person background connection + value prop preview)
- [ ] **RESEARCH-08**: IntelBrief output: company_name, company_signals[], person_name, person_role, company_website, person_background, talking_points[], company_product_description
- [ ] **RESEARCH-09**: Token budget tracking within Research agent (pause if budget exceeded, surface error)
- [ ] **RESEARCH-10**: IntelBrief persisted to SQLite, linked to Lead

### MATCH — Qualification Matching and Scoring

- [ ] **MATCH-01**: Matcher agent cross-references UserProfile against IntelBrief
- [ ] **MATCH-02**: Match score calculation (0-100) based on: skills overlap, experience relevance, seniority fit, company size fit
- [ ] **MATCH-03**: Explicit value proposition generation (why the user is valuable to this specific company/role)
- [ ] **MATCH-04**: Match output: match_score, value_proposition, confidence_level
- [ ] **MATCH-05**: Match stored in Lead record, linked to IntelBrief and UserProfile

### WRITER — Email Generation (Personalization, MCQ Flow, Tone, Subjects, Follow-ups)

- [ ] **WRITER-01**: Interactive MCQ flow: 2-3 personalized questions per lead (steered by company/role)
- [ ] **WRITER-02**: MCQ questions reference IntelBrief and talking points (not generic)
- [ ] **WRITER-03**: Email generation receives: Lead + IntelBrief + UserProfile + ValueProp + MCQ answers
- [ ] **WRITER-04**: Tone adaptation by recipient type: HR (formal, process-focused), CTO/Engineering (technical, specific skills), CEO/Founder (visionary, fit + culture)
- [ ] **WRITER-05**: Email body is personalized per recipient (not template-based)
- [ ] **WRITER-06**: Flexible email length per recipient type (CEO emails may be shorter, technical emails may be longer) — no fixed word count
- [ ] **WRITER-07**: Email includes: specific reference to company/role + relevant experience + one talking point + clear CTA
- [ ] **WRITER-08**: Two subject line variants for A/B testing (both reference company/role, not generic)
- [ ] **WRITER-09**: Follow-up sequence generation: Day 3 and Day 7 drafts (tone escalates slightly, adds new talking point or urgency signal)
- [ ] **WRITER-10**: CAN-SPAM compliant footer injection: "Not interested?" unsubscribe link + physical mailing address (from setup wizard) + sender identity
- [ ] **WRITER-11**: Email draft persisted with all variants (subject A/B, follow-up sequences)
- [ ] **WRITER-12**: Review-before-send queue: approve, edit inline, reject, regenerate options
- [ ] **WRITER-13**: Reject/regenerate flow triggers new MCQ if user requests different angle

### OUTREACH — Email Sending, Rate Limiting, Reply Handling, Scheduling

- [ ] **OUTREACH-01**: SMTP sending via Gmail (port 587 STARTTLS)
- [ ] **OUTREACH-02**: Rate limiting: hard-cap at 30 sends/day for new accounts (configurable per setup)
- [ ] **OUTREACH-03**: Per-hour rate limiting (no more than 5 sends/hour to avoid rate limit triggers)
- [ ] **OUTREACH-04**: Business-hours-only send window (9 AM - 5 PM recipient timezone, Mon-Fri)
- [ ] **OUTREACH-05**: Per-day and per-hour send counters persisted in SQLite
- [ ] **OUTREACH-06**: Bounce rate tracking: pause all sends if bounce rate exceeds 5% (stored in Outreach tables)
- [ ] **OUTREACH-07**: DNS validation in setup wizard (SPF/DKIM/DMARC records check via dnspython)
- [ ] **OUTREACH-08**: Campaign launch blocked if required DNS records missing (exact records provided to user)
- [ ] **OUTREACH-09**: IMAP polling for replies (async aioimaplib)
- [ ] **OUTREACH-10**: Reply classification: positive (interested, meeting request), negative (not interested, bad fit), auto-reply (OOO, auto-responder), CAN-SPAM compliance
- [ ] **OUTREACH-11**: Unsubscribe intent detection in replies (honor unsubscribe, add to suppression table)
- [ ] **OUTREACH-12**: UnsubscribedEmail suppression table (no future sends to suppressed addresses)
- [ ] **OUTREACH-13**: Follow-up scheduling via APScheduler (AsyncIOScheduler)
- [ ] **OUTREACH-14**: Day 3 and Day 7 follow-ups queued and scheduled (only sent if no positive reply received)
- [ ] **OUTREACH-15**: On positive reply: notify user, suggest response, optionally surface Calendly link option
- [ ] **OUTREACH-16**: Open pixel tracking (1x1 GIF via unique tracking URL, fallback graceful if unsupported)
- [ ] **OUTREACH-17**: Email send logging: timestamp, recipient, subject, status, bounce/delivery notifications

### ANALYST — Analytics and Pattern Detection

- [ ] **ANALYST-01**: Reply rate calculation (primary signal: % of sent emails receiving positive replies)
- [ ] **ANALYST-02**: Open rate tracking (documented caveat: pixel-based, unreliable, secondary signal only)
- [ ] **ANALYST-03**: Pattern detection: which talking points convert most, which company sizes convert most, which roles convert most
- [ ] **ANALYST-04**: Insight persistence: pattern findings stored for Writer context in future runs
- [ ] **ANALYST-05**: Basic campaign metrics dashboard (sent count, reply count, pending count)

### CLI — Rich CLI Interface and Commands

- [ ] **CLI-01**: Rich CLI as primary interface (Typer + Rich + rich-click for styled output)
- [ ] **CLI-02**: Command grouping by domain: agents (list/logs/inspect), data (leads/emails/stats/export), mail (pending/review/approve/reject/track), run (scout/research/match/write/followup/analyze), config (show/set/setup)
- [ ] **CLI-03**: Rich terminal output: tables for leads, panels for email previews, color-coded status badges
- [ ] **CLI-04**: Step-by-step assist mode: Orchestrator narrates every step and pauses at configurable checkpoints
- [ ] **CLI-05**: Email review panel: inline edit, approve/reject/regenerate buttons
- [ ] **CLI-06**: Leads table with match scores, company names, contact info, status flags
- [ ] **CLI-07**: Campaign stats: leads discovered, leads researched, leads matched, emails drafted, emails sent, replies received
- [ ] **CLI-08**: Config view/set commands (non-secret values only)
- [ ] **CLI-09**: Test send command (sends test email to user's own address to validate SMTP setup)

### TUI — Textual TUI (Nice-to-Have but In Scope)

- [ ] **TUI-01**: Textual-based dashboard interface (tab-based: Overview, Leads, Email Review, Settings)
- [ ] **TUI-02**: Leads table with sorting (match score desc, status, company name)
- [ ] **TUI-03**: Email review panel with inline editing (e = edit, a = approve, r = reject, g = regenerate)
- [ ] **TUI-04**: Activity feed (last 20 events: lead discovered, email drafted, email sent, reply received)
- [ ] **TUI-05**: Settings screen (LLM backend per-agent, rate limits, timezone, mailing address)
- [ ] **TUI-06**: Toggle between CLI and TUI modes (seamless handoff, same underlying data)

### AGENT FRAMEWORK & ORCHESTRATOR

- [ ] **AGENT-01**: 7 agents: Orchestrator, Scout, Research, Matcher, Writer, Outreach, Analyst
- [ ] **AGENT-02**: Agent framework: PydanticAI (verify v0.0.x → current API stability on PyPI before committing)
- [ ] **AGENT-03**: Fallback to LiteLLM + manual Pydantic validation if PydanticAI API has changed significantly
- [ ] **AGENT-04**: Orchestrator routes tasks, maintains campaign state, handles natural language chat, coordinates approval gates
- [ ] **AGENT-05**: No agent imports another agent; Orchestrator is the only coordinator
- [ ] **AGENT-06**: Agent dependencies injected as function arguments (LLMClient, db, http_client, repositories)
- [ ] **AGENT-07**: Orchestrator stays under 250 lines (domain logic lives in agents)
- [ ] **AGENT-08**: Agent registry (for future module expansion in v2)
- [ ] **AGENT-09**: Typed exception handling (never swallow errors, surface them clearly)

### DATABASE SCHEMAS

- [ ] **DB-01**: UserProfile: name, headline, skills[], experience[], education[], projects[], github_url, linkedin_url, resume_raw_text, created_at, updated_at
- [ ] **DB-02**: Lead: company_name, person_name, person_email, person_role, company_website, source_venue, status (discovered/researching/matched/drafted/sent/replied), created_at
- [ ] **DB-03**: IntelBrief: company_signals[], person_background, talking_points[], company_product_description, linked_to_lead_id, created_at
- [ ] **DB-04**: Match: match_score (0-100), value_proposition, confidence_level, linked_to_lead_id, created_at
- [ ] **DB-05**: Email: subject_a, subject_b, body, tone_adapted_for, mcq_answers_json, status (drafted/approved/sent/rejected), created_at
- [ ] **DB-06**: FollowUp: parent_email_id, scheduled_for_day (3 or 7), body, status (queued/sent/skipped), created_at, sent_at
- [ ] **DB-07**: Campaign: campaign_name, created_at, started_at, ended_at, total_leads, total_sent, total_replied, status (active/paused/completed)
- [ ] **DB-08**: AgentLog: agent_name, step_description, status, duration_ms, error_message, input_tokens, output_tokens, cost_estimate, created_at
- [ ] **DB-09**: Venue: venue_name, venue_type, config_json, last_run_at, lead_count_discovered, last_error
- [ ] **DB-10**: OutreachMetric: sent_today, sent_this_hour, bounce_count, bounce_rate, last_sent_at, created_at
- [ ] **DB-11**: UnsubscribedEmail: email_address, unsubscribe_reason, unsubscribed_at

---

## v2 Requirements

### INFRA — Infrastructure Expansion

- [ ] **INFRA-V2-01**: Event bus architecture (LeadDiscovered, IntelBriefReady, ValuePropGenerated, EmailDrafted, EmailSent, EmailOpened, ReplyReceived, FollowUpQueued, AgentCompleted)
- [ ] **INFRA-V2-02**: Agent registry (agents register by name, Orchestrator routes via registry lookup)
- [ ] **INFRA-V2-03**: Module registry (ATS, interview prep, application tracker register as new agents + TUI screens)
- [ ] **INFRA-V2-04**: Integration layer (named adapters for third-party services: Gmail, future Calendly, Notion, Slack)
- [ ] **INFRA-V2-05**: Hook system (~/.outreach-agent/hooks/ for user-defined lifecycle hooks: on_lead_discovered, on_email_drafted, on_reply_received)
- [ ] **INFRA-V2-06**: Redis queue for multi-process task parallelism (replaces asyncio.Queue for large campaigns)
- [ ] **INFRA-V2-07**: Budget/token cost tracking per agent and per campaign
- [ ] **INFRA-V2-08**: Pluggable venue discovery system with VenueBase abstract class
- [ ] **INFRA-V2-09**: Venue plugin auto-discovery (.py files in discovery/ and ~/.outreach-agent/venues/)
- [ ] **INFRA-V2-10**: Guided venue creation wizard (--venue-setup interactive flow)

### SCOUT — Multi-Venue and Advanced Deduplication

- [ ] **SCOUT-V2-01**: Additional venues beyond YC: Apollo, Hunter, ProductHunt, Crunchbase, AngelList, LinkedIn (added incrementally)
- [ ] **SCOUT-V2-02**: Cross-venue deduplication (same person found via multiple venues consolidated)
- [ ] **SCOUT-V2-03**: Warm intro finder (locate common connections on LinkedIn via network graph)

### RESEARCH — Advanced Intelligence

- [ ] **RESEARCH-V2-01**: Funding signal monitoring (Series rounds, funding announcements, investor signals)
- [ ] **RESEARCH-V2-02**: Company news monitoring (RSS feeds, alert subscriptions for tech stack changes, hiring signals)
- [ ] **RESEARCH-V2-03**: Tech stack detection from job postings (parse roles for required/desired tech)
- [ ] **RESEARCH-V2-04**: LinkedIn warm-up automation (profile visits, message intent signals)

### WRITER — Advanced Personalization

- [ ] **WRITER-V2-01**: Batch mode with learned patterns (once user approves 3+ emails with similar patterns, auto-generate similar leads)
- [ ] **WRITER-V2-02**: Subject line evolution (auto-feedback to Writer from open/reply metrics)
- [ ] **WRITER-V2-03**: Meeting detection + Calendly auto-injection (detect availability in replies, inject meeting links)
- [ ] **WRITER-V2-04**: Positive reply handling with suggested response templates

### OUTREACH — Advanced Email Management

- [ ] **OUTREACH-V2-01**: Gmail API with OAuth2 (preferred over raw SMTP, requires GCP project setup)
- [ ] **OUTREACH-V2-02**: Multi-account Gmail support (rotate sending domains/accounts for large campaigns)
- [ ] **OUTREACH-V2-03**: Smart send timing optimization (learn best times to send for each recipient type)
- [ ] **OUTREACH-V2-04**: Email warmup / dedicated warmup network integration

### ANALYST — Advanced Analytics

- [ ] **ANALYST-V2-01**: A/B test statistical engine (track subject variant performance, confidence intervals)
- [ ] **ANALYST-V2-02**: Network graph visualization (relationship mapping, warm intro paths)
- [ ] **ANALYST-V2-03**: CRM sync (HubSpot, Salesforce, Pipedrive integration)

### PROFILE — Advanced Resume Processing

- [ ] **PROFILE-V2-01**: Contact database / enrichment API integration (Apollo, Hunter for email validation)

### TUI — Extended Dashboard

- [ ] **TUI-V2-01**: Network graph visualization (relationship mapping UI)
- [ ] **TUI-V2-02**: A/B test performance dashboard (visual comparison of subject variants)

### ADDITIONAL MODULES (v2+)

- [ ] **MODULES-V2-01**: ATS keyword optimizer module (optimize resume/cover letter for ATS parsing)
- [ ] **MODULES-V2-02**: Interview prep module (mock interviews, question suggestions)
- [ ] **MODULES-V2-03**: Application tracker module (track submitted applications, follow-up reminders)
- [ ] **MODULES-V2-04**: Browser extension (one-click add to outreach from job boards)
- [ ] **MODULES-V2-05**: Multi-user / team mode (shared campaigns, permission model)

---

## Out of Scope (Explicitly Deferred)

| Feature | Category | Rationale | v2+ Candidate |
|---------|----------|-----------|---|
| Budget/token tracking | INFRA | Cost awareness is secondary; focus on email quality first | v2 |
| Funding signal monitoring | RESEARCH | Deep one-shot research > continuous monitoring for v1 | v2 |
| LinkedIn warm-up automation | OUTREACH | ToS violation risk; defer to v2 with careful legal review | v2 |
| Warm intro finder | SCOUT | Requires network graph; advanced for v1 scope | v2 |
| ATS keyword optimizer | MODULES | Specialty module; not core to cold outreach pipeline | v2+ |
| Interview prep module | MODULES | Outside cold outreach scope | v2+ |
| Application tracker module | MODULES | Outside cold outreach scope | v2+ |
| Browser extension | MODULES | Client distribution; defer to v2 | v2+ |
| Multi-account Gmail support | OUTREACH | Single-user tool; multi-account is team feature | v2 |
| Company news monitoring (RSS/alerts) | RESEARCH | Continuous monitoring not core to v1; manual research sufficient | v2 |
| Network graph visualization | ANALYST | Advanced UI; not core to pipeline | v2 |
| Tech stack detection from job postings | RESEARCH | Optional signal; v1 focuses on company/person intel | v2 |
| Smart send timing optimization | OUTREACH | Learning curve; batch send at fixed times in v1 | v2 |
| Subject line evolution (auto-feedback) | WRITER | Manual insight feedback in v1; automation in v2 | v2 |
| Meeting detection + Calendly auto-injection | OUTREACH | Depends on Calendly integration; defer to v2 | v2 |
| More than 2 venues in v1 | SCOUT | Prove pipeline end-to-end with YC first; scale venues in v2 | v2 |
| Multiple agent backends simultaneously | AGENT | Pick one framework for v1; swappable architecture in v2 | v2 |
| .env for secrets | INFRA | Encrypted config only (dev overrides acceptable) | — |
| Contact database / enrichment API | PROFILE | Enrichment in v2; v1 uses scraping + Research agent | v2 |
| CRM sync (HubSpot, Salesforce, Pipedrive) | ANALYST | Enterprise features; defer to v2 | v2+ |
| LinkedIn automation (general) | OUTREACH | ToS violation risk; careful planning needed | v2 |
| A/B test statistical engine | ANALYST | Manual interpretation in v1; statistical analysis in v2 | v2 |

---

## Testing Strategy and Requirements by Phase

### Testing Principles

1. **Unit tests for all business logic:** Config encryption/decryption, Pydantic schema validation, LLM response parsing, Lead deduplication, Match scoring, Email generation templates
2. **Integration tests for all data flow:** Setup wizard → config persisted → LLM loaded, Resume upload → UserProfile extracted → stored, Scout discovers lead → Research Phase 1 → approval gate
3. **End-to-end tests for critical paths:** Full pipeline (discover → research → match → write → review) with mock LLMs and fixture data
4. **Regression suite before Phase 3 shipping:** Email sending, rate limiting, reply classification must not break in future iterations
5. **Manual QA checklist:** Setup wizard UX, CLI output readability, TUI keyboard shortcuts (Phase 4)
6. **Performance benchmarks (Phase 2-3):** Scout on 100 YC companies (<5s), Research on 5 leads (<30s total with token limits), email generation end-to-end (<10s per draft)

### Phase 1: Infrastructure Testing

- [ ] **TEST-P1-01**: Unit tests for config encryption/decryption (Fernet key derivation, secret storage, retrieval)
- [ ] **TEST-P1-02**: Unit tests for SQLModel schemas (all database tables serialize/deserialize correctly)
- [ ] **TEST-P1-03**: Unit tests for LLMClient initialization (all backends: Claude, OpenAI, Ollama API, OpenAI-compatible)
- [ ] **TEST-P1-04**: Unit tests for Pydantic validation (invalid LLM responses rejected with clear errors)
- [ ] **TEST-P1-05**: Unit tests for retry/fallback logic (3 retries with exponential backoff, XML fallback on JSON failure)
- [ ] **TEST-P1-06**: Integration test: Setup wizard creates config, encrypts secrets, persists to disk, can reload
- [ ] **TEST-P1-07**: Integration test: SQLite connection with WAL mode, concurrent async writes don't lock
- [ ] **TEST-P1-08**: Integration test: Alembic migration applied, schema matches all models
- [ ] **TEST-P1-09**: Performance: LLMClient initialization <500ms, config load <100ms, DB transaction <50ms

### Phase 2: Pipeline Testing (Scout, Research, Match, Writer)

- [ ] **TEST-P2-01**: Unit tests for Lead deduplication (email case-insensitive, duplicates merged correctly)
- [ ] **TEST-P2-02**: Unit tests for Resume parsing (PDF, DOCX, plain text; edge cases: multi-column, corrupted, empty)
- [ ] **TEST-P2-03**: Unit tests for UserProfile extraction (Pydantic validation, required fields enforced, fallback on low extraction rate)
- [ ] **TEST-P2-04**: Unit tests for Match scoring (0-100 range, skills overlap weighted, experience relevance scored)
- [ ] **TEST-P2-05**: Unit tests for Email generation (personalization with company/person references, tone variants, subject A/B)
- [ ] **TEST-P2-06**: Unit tests for CAN-SPAM footer injection (required fields present, unsubscribe link valid format)
- [ ] **TEST-P2-07**: Integration test: Scout discovers YC leads (validate output against known YC companies, dedup works)
- [ ] **TEST-P2-08**: Integration test: Research Phase 1 generates company signals (lightweight, completes in <5s per lead)
- [ ] **TEST-P2-09**: Integration test: User approval gate works (accept/reject/defer transitions correct)
- [ ] **TEST-P2-10**: Integration test: Research Phase 2 generates talking points (3 per lead, references company/person)
- [ ] **TEST-P2-11**: Integration test: Matcher generates value proposition (personalized, not generic)
- [ ] **TEST-P2-12**: Integration test: Writer MCQ flow generates personalized questions (2-3 per lead, references IntelBrief)
- [ ] **TEST-P2-13**: Integration test: Full pipeline end-to-end (5 fixture leads from discover to draft in review queue)
- [ ] **TEST-P2-14**: End-to-end test: All 10 v1 drafts generate successfully with all required fields (no missing subjects, bodies, follow-ups)
- [ ] **TEST-P2-15**: Regression: Orchestrator checkpoint/resume works (pause after Phase 1, resume from checkpoint, all state preserved)
- [ ] **TEST-P2-16**: Performance: Scout on 100 YC companies <5s, Research Phase 1 on 5 leads <10s, Match+Write on 5 leads <15s

### Phase 3: Email Engine Testing

- [ ] **TEST-P3-01**: Unit tests for rate limiting (per-day counter increments, per-hour counter increments, hard caps enforced)
- [ ] **TEST-P3-02**: Unit tests for business-hours send window (scheduler respects 9 AM - 5 PM time window, skips weekends)
- [ ] **TEST-P3-03**: Unit tests for bounce rate tracking (bounce count increments, rate calculated correctly, pause at 5%)
- [ ] **TEST-P3-04**: Unit tests for reply classification (positive/negative/auto-reply detection, confidence scores)
- [ ] **TEST-P3-05**: Unit tests for unsubscribe handling (unsubscribe intent detected, address added to suppression table)
- [ ] **TEST-P3-06**: Unit tests for open pixel tracking (unique pixel URL generated, gracefully handles missing image)
- [ ] **TEST-P3-07**: Integration test: SMTP connection to Gmail test account (credentials loaded from encrypted config, test send succeeds)
- [ ] **TEST-P3-08**: Integration test: Rate limiting enforced (schedule 50 sends, verify only 30 sent on day 1, rest queued)
- [ ] **TEST-P3-09**: Integration test: DNS validation blocks launch without SPF/DKIM/DMARC (setup wizard refuses campaign start)
- [ ] **TEST-P3-10**: Integration test: IMAP polling retrieves test replies, classifies them correctly
- [ ] **TEST-P3-11**: Integration test: Follow-up scheduling queues Day 3 and Day 7 emails correctly (APScheduler state persisted)
- [ ] **TEST-P3-12**: Integration test: Bounce tracking pauses campaign at 5% bounce rate
- [ ] **TEST-P3-13**: Regression: Email send/receive pipeline doesn't break with Phase 2 data (10 fixture emails sent, replies polled)

### Phase 4: Analytics and CLI Testing

- [ ] **TEST-P4-01**: Unit tests for reply rate calculation (correct denominator: sent emails, correct numerator: positive replies)
- [ ] **TEST-P4-02**: Unit tests for pattern detection (talking point frequency, company size frequency, role frequency)
- [ ] **TEST-P4-03**: Unit tests for CLI command parsing (all commands recognized, --help works, invalid args rejected)
- [ ] **TEST-P4-04**: Integration test: Analyst generates campaign summary (reply rate, patterns, insights persisted)
- [ ] **TEST-P4-05**: Integration test: CLI lists leads, shows match scores, displays campaign stats
- [ ] **TEST-P4-06**: Integration test: CLI email review flow (approve/reject/regenerate transitions work, MCQ retriggers on regenerate)
- [ ] **TEST-P4-07**: Manual QA: CLI output readable and colorized (no malformed tables, status badges visible)
- [ ] **TEST-P4-08**: Manual QA: TUI dashboard loads, tabs navigate, keyboard shortcuts work (e/a/r/g)
- [ ] **TEST-P4-09**: Manual QA: Setup wizard completes in <5 minutes (credentials prompt, resume upload, backend selection, test send)

### Testing Infrastructure

- [ ] **TEST-INFRA-01**: Pytest configuration with async support (pytest-asyncio)
- [ ] **TEST-INFRA-02**: Fixture database (test SQLite, auto-cleaned between tests)
- [ ] **TEST-INFRA-03**: Fixture LLM client (mock responses for all test cases, deterministic)
- [ ] **TEST-INFRA-04**: Fixture config (encrypted, temporary directory cleaned up)
- [ ] **TEST-INFRA-05**: Test coverage reporting (minimum 70% for Phase 1-2, 60% for Phase 3-4)
- [ ] **TEST-INFRA-06**: Mock Gmail SMTP/IMAP (in-memory, no real email sending in tests)
- [ ] **TEST-INFRA-07**: Fixture YC data (100 known companies, stable responses)
- [ ] **TEST-INFRA-08**: Fixture UserProfile and IntelBrief (standard test data for all pipeline tests)

---

## Future Additions (v1 Deferred Items)

These are features identified as valuable during PROJECT.md and research but explicitly marked as "skip for v1" or deferred. They are revisitable after v1 ships and should inform the post-launch product roadmap.

| Item | Category | v1 Status | Reason Deferred | v2 Plan |
|------|----------|-----------|-----------------|---------|
| Venue plugin system with VenueBase abstraction | SCOUT | Skip (YC as direct code) | Premature abstraction; extract VenueBase when adding second venue | INFRA-V2-08, INFRA-V2-09 |
| Guided venue creation wizard | SCOUT | Deferred | Requires pluggable venue system first | INFRA-V2-10 |
| Event bus and LeadDiscovered pattern | INFRA | Deferred | No observers yet in v1; architect when integrations added | INFRA-V2-01 |
| Agent registry pattern | AGENT | Deferred | Single hardcoded agent set in v1; registry for v2 modules | INFRA-V2-02 |
| Module registry (ATS, interview prep, application tracker) | MODULES | Deferred | Out of scope; future product expansion | INFRA-V2-03, MODULES-V2-01+ |
| Integration adapters (Notion, Slack, Calendly) | INFRA | Deferred | Focus on Gmail only in v1; extensible later | INFRA-V2-04 |
| User-defined hook system | INFRA | Deferred | Power user feature; v1 focuses on happy path | INFRA-V2-05 |
| Redis multi-process queue | INFRA | Deferred | asyncio.Queue sufficient for v1's 10-lead target | INFRA-V2-06 |
| Positive reply suggested responses | OUTREACH | Nice-to-have in v1 | Simplify reply handling; add templates in v2 | OUTREACH-V2-04 |
| Batch mode with learned patterns | WRITER | Deferred | Requires 3+ approved emails to learn from; post-v1 iteration | WRITER-V2-01 |
| Insight feedback loop (Writer learns from Analyst patterns) | ANALYST | Deferred | Build analytics first (v1), then feedback loop (v2) | ANALYST-V2-01, WRITER-V2-02 |
| Advanced TUI (network graph, A/B test dashboard) | TUI | Deferred | Rich CLI sufficient for v1; TUI is "nice-to-have" | TUI-V2-01, TUI-V2-02 |
| Open pixel reliability mitigation | OUTREACH | Documented caveat | Pixel unreliable; reply rate is primary signal in v1 | — |

---

## v1 Traceability: Requirements to Phase

This table maps each v1 requirement to the phase in which it is implemented (per SUMMARY.md phase structure).

| Requirement ID | Brief | Phase | Notes |
|---|---|---|---|
| INFRA-01 to INFRA-20 | Core infrastructure, config, DB, LLM client | Phase 1 | Foundation for all downstream agents |
| PROFILE-01 to PROFILE-09 | Resume parsing, UserProfile extraction | Phase 2 | Blocks Writer and Matcher |
| SCOUT-01 to SCOUT-08 | Lead discovery (YC), deduplication, initial scoring | Phase 2 | Core pipeline entry point |
| RESEARCH-01 to RESEARCH-10 | IntelBrief generation (two-phase), approval gate | Phase 2 | Core pipeline, high-token-cost agent |
| MATCH-01 to MATCH-05 | Qualification matching, scoring, value prop | Phase 2 | Consumes UserProfile + IntelBrief |
| WRITER-01 to WRITER-13 | Email generation, MCQ, tone, subjects, follow-ups | Phase 2 | Core value delivery (drafts) |
| AGENT-01 to AGENT-09 | Agent framework, orchestration, exception handling | Phase 1-2 | Spans all phases, foundational architecture |
| DB-01 to DB-11 | Database schemas and models | Phase 1 | Foundation, referenced by all phases |
| CLI-01 to CLI-09 | Rich CLI interface and commands | Phase 4 | Presentation layer, consumed last |
| OUTREACH-01 to OUTREACH-17 | Email sending, rate limiting, reply handling, scheduling | Phase 3 | Depends on Phase 2 draft production |
| ANALYST-01 to ANALYST-05 | Analytics, pattern detection, metrics | Phase 4 | Reads data produced by Phase 3 |
| TUI-01 to TUI-06 | Textual TUI dashboard (nice-to-have) | Phase 4 | Polish/usability, no blocking value |
| TEST-P1-01 to TEST-P1-09 | Phase 1 unit and integration tests | Phase 1 | Foundation tests; run continuously |
| TEST-P2-01 to TEST-P2-16 | Phase 2 unit, integration, e2e, regression, performance tests | Phase 2 | Pipeline tests; validate 10 drafts generated |
| TEST-P3-01 to TEST-P3-13 | Phase 3 email engine tests | Phase 3 | Safeguard against suspension/deliverability issues |
| TEST-P4-01 to TEST-P4-09 | Phase 4 analytics, CLI, TUI, manual QA | Phase 4 | Polish testing; smoke tests before v1 release |
| TEST-INFRA-01 to TEST-INFRA-08 | Test infrastructure (pytest, fixtures, mocking, coverage) | Phase 1 | Set up once, used by all phases |

**Phase 1 Delivers:** Config system, encrypted secrets, SQLite with migrations, LLMClient with Pydantic validation, all database schemas, Agent framework setup, comprehensive unit/integration tests
**Phase 2 Delivers:** Resume parsing, Scout/Research/Matcher/Writer agents, end-to-end pipeline, 10 email drafts in review queue (v1 done condition), regression and performance tests
**Phase 3 Delivers:** SMTP/IMAP integration, rate limiting, reply classification, follow-up scheduling, campaign tracking, email engine regression suite
**Phase 4 Delivers:** Analytics and insights, complete CLI polish, TUI dashboard (if time permits), end-to-end QA and performance validation

---

## Key Assumptions and Validations

Before v1 shipping, the following assumptions must be validated:

1. **PydanticAI API stability** — Verify current version on PyPI. If API has changed significantly from 0.0.x, use LiteLLM + manual Pydantic validation instead.
2. **YC site structure** — Live verification: check api.ycombinator.com for public API. Determine if httpx is sufficient or if Playwright is required.
3. **Gmail SMTP daily limits** — Verify current send limits at support.google.com/mail/answer/22839 (30/day conservative cap may need adjustment).
4. **Ollama tool-use model compatibility** — Check ollama.com/search?c=tools for current models with reliable tool support.
5. **aioimaplib maintenance** — Verify active maintenance on PyPI. If abandoned, use imapclient with run_in_executor wrapper.

---

## Definition of Done (v1)

**Pipeline completion:** User can start with a resume, discover leads from YC, research each lead, match qualifications, and generate 10 personalized email drafts via the interactive MCQ flow.

**Quality gates:**
- All 10 drafts are in the review queue (not sent)
- Each draft is personalized with company/person research, not generic
- Each draft passes CAN-SPAM compliance check (footer present)
- User can approve, edit, or regenerate each draft
- No LLM tool-use failures go unhandled (Pydantic validation catches all invalid responses)
- All Phase 1, 2, and 3 test suites pass (minimum 70% coverage)
- Performance benchmarks met (Scout <5s/100 leads, Research <30s/5 leads, full pipeline <15s/5 leads)

**Usability:**
- Setup wizard completes in <5 minutes (credentials + resume upload)
- Pipeline runs end-to-end without manual intervention
- All errors surface with clear recovery instructions
- CLI provides progress narration and status visibility
- Manual QA checklist completed (CLI readable, TUI responsive, keyboard shortcuts work)

---

## Implementation Notes

### Design Principles Applied

1. **Atomic requirements:** Every requirement is a single, testable feature. No "aggregate" items like "build the Writer agent" — instead, each writing feature is separate (MCQ, tone adaptation, subjects, follow-ups, etc.).

2. **No premature abstraction:** YC venue is direct code (SCOUT-02), not a plugin system, until a second venue is added in v2. Plugin system deferred (INFRA-V2-08).

3. **Phase ordering enforces dependency injection:** Config/DB/LLM before agents. Pipeline before email engine. Email engine before analytics. Analyst and TUI last. Tests integrated throughout.

4. **Pitfalls baked into v1 requirements:** Gmail account suspension (OUTREACH-02 to OUTREACH-06), deliverability (OUTREACH-07 to OUTREACH-08), LLM tool-use (INFRA-14 to INFRA-16), scraping brittleness (SCOUT-04 to SCOUT-05), CAN-SPAM (WRITER-10, OUTREACH-10 to OUTREACH-12).

5. **Free-first architecture:** Every agent can run on Ollama (INFRA-10, INFRA-13 with XML fallback). Cost optimization via per-agent model config (INFRA-06).

6. **Testing as first-class requirement:** Every phase has parallel test requirements (Phase 1 foundation tests, Phase 2 pipeline tests, Phase 3 email engine tests, Phase 4 QA). Minimum 70% coverage for critical paths, performance benchmarks for all phases.

### Traceability to Research

All items in SUMMARY.md "Deferred to v2" section are captured in the v2 Requirements section above. All items in SUMMARY.md "Pitfalls" section have corresponding v1 requirements mapped to Phase 1-3. All items in SUMMARY.md "Expected Features" section are mapped:
- **Must have:** Captured in WRITER, OUTREACH, PROFILE, MATCH sections
- **Should have:** RESEARCH (two-phase split), MATCH (match score), WRITER (MCQ, tone), INFRA (Ollama, per-agent config), AGENT (transparency)
- **Nice to have:** TUI (v1 scope but Phase 4), Venue extensibility (v2), Batch mode (v2)

---

*REQUIREMENTS.md — INGOT v1 specification*
*Last updated: 2026-02-25*
*Ready for Phase 1 planning*
