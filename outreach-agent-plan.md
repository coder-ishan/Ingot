# OutreachAgent — Autonomous Job Outreach with Agent Teams

## Core Philosophy

Most great jobs are never posted. Founders and hiring managers hire people they've *already talked to* — people who reached out, showed genuine interest, and demonstrated they understood the company's problems. Traditional job search is reactive (apply → get ghosted). This tool makes it proactive.

**The thesis:** Replace the job board with a personal recruiting agency that runs 24/7, researches every target company deeply, writes emails that sound genuinely human, cross-references the user's real qualifications against each opportunity, and learns from every reply — at a scale no human could maintain alone.

**Principles:**
1. **Relevance over volume** — a targeted, researched email beats 100 generic ones
2. **Qualifications-aware** — every email is grounded in the user's actual skills and experience
3. **Relationships, not transactions** — track full lifecycle, nurture over weeks
4. **Continuous learning** — every open, click, and reply teaches the system what works
5. **Pluggable everything** — new venues, email providers, LLMs, and future modules are first-class
6. **Free-first** — every agent can run on a local OSS model (Ollama) with zero API cost
7. **Future-ready** — architecture is a job hunting *platform*, not just an email sender

---

## Agent Team Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                      │
│  User-facing. Routes tasks, synthesizes results,           │
│  maintains context across agent team. Lives in TUI chat.   │
└──────────┬─────────────────────────────────────────────────┘
           │ delegates to
  ┌─────────┼──────────────────────────────────────┐
  ▼         ▼          ▼          ▼        ▼        ▼
SCOUT   RESEARCH   MATCHER    WRITER  OUTREACH  ANALYST
AGENT   AGENT      AGENT      AGENT   AGENT     AGENT
```

### Agent Team Details

**1. Orchestrator Agent** (`agent/orchestrator.py`)
- User-facing: handles natural language in TUI chat
- Routes tasks to specialists, synthesizes output
- Maintains campaign memory and user context across sessions
- Example: "Find CTOs at YC fintech startups" → Scout → Research → Matcher → Writer → Outreach pipeline

**2. Scout Agent** (`agent/scout.py`)
- Discovers leads from all configured venues in parallel
- Deduplicates across venues (same person found on Apollo + LinkedIn)
- Initial lead scoring (company size, funding stage, role relevance)
- Tools: `scrape_venue()`, `deduplicate_leads()`, `score_lead()`

**3. Research Agent** (`agent/research.py`)
- Builds deep intelligence brief per lead
- Scrapes company homepage, About page, blog posts, press releases
- Checks person's LinkedIn, GitHub (public), Twitter activity
- Detects signals: recent funding, new product launch, open job postings
- Outputs: `IntelBrief` with company context and talking points
- Tools: `fetch_company_intel()`, `fetch_person_intel()`, `detect_signals()`

**4. Matcher Agent** (`agent/matcher.py`)
- Cross-references the user's **UserProfile** (extracted from resume) against each lead
- Identifies skill/experience overlap: "Your Rust + trading systems experience matches their backend stack"
- Scores leads by qualification match (0–100)
- Generates a **personalized value proposition** for each lead:
  - What skills make the user relevant to this specific company
  - Which of their problems the user can solve
  - Experience highlights to lead with
- Feeds value props directly to Writer Agent
- Tools: `match_skills()`, `score_qualifications()`, `generate_value_prop()`

**5. Writer Agent** (`agent/writer.py`)
- Receives `Lead` + `IntelBrief` + `ValueProp` from Matcher
- Writes personalized cold email that references:
  - Company's specific product/mission (from Intel)
  - User's relevant experience (from ValueProp)
- Tone adapts by role: HR (professional), CEO (peer), CTO (technical)
- Generates 2 subject line variants for A/B testing
- Drafts follow-up sequence (Day 3, Day 7) for non-replies
- Enforces: 150–200 words, one clear ask, no buzzwords
- Tools: `compose_email()`, `generate_subject_variants()`, `compose_followup()`

**6. Outreach Agent** (`agent/outreach.py`)
- Manages sending: rate limiting, business-hours-only send windows
- Polls Gmail IMAP for replies, classifies (positive / negative / auto-reply / OOO)
- On positive reply: notifies user, suggests response, optionally sends Calendly link
- Manages follow-up queue based on engagement signals
- Tools: `send_email()`, `poll_replies()`, `classify_reply()`, `schedule_followup()`

**7. Analyst Agent** (`agent/analyst.py`)
- Daily or on-demand: reports on open rate, reply rate, best subject lines, best venues
- Identifies patterns: "Emails mentioning their product get 3x more replies"
- Feeds insights back to Writer Agent's system prompt context
- Tools: `query_metrics()`, `run_cohort_analysis()`, `generate_report()`

---

## Pluggable LLM Backend

### LLMClient Abstraction (`agent/llm_client.py`)
All agents use a single `LLMClient` interface — no agent directly imports `anthropic` or `openai`. The client handles tool-use, streaming, and retries regardless of backend.

**Supported backends (out of the box):**
| Backend | How | Cost |
|---|---|---|
| Claude (Anthropic) | `anthropic` SDK | Pay-per-token |
| OpenAI / GPT | `openai` SDK (OpenAI-compatible API) | Pay-per-token |
| Ollama (local) | HTTP to `localhost:11434` | Free |
| LM Studio | OpenAI-compatible HTTP | Free |
| Any OpenAI-compatible API | Base URL override | Varies |

### Per-Agent Model Config
Each agent has its own model setting in `~/.outreach-agent/config.json`. This lets you run cheap/free models where accuracy matters less, and reserve strong models for email writing:

```json
{
  "agents": {
    "orchestrator": { "backend": "ollama", "model": "llama3.2" },
    "scout":        { "backend": "ollama", "model": "qwen2.5" },
    "research":     { "backend": "claude", "model": "claude-haiku-4-5-20251001" },
    "matcher":      { "backend": "ollama", "model": "llama3.2" },
    "writer":       { "backend": "claude", "model": "claude-sonnet-4-6" },
    "outreach":     { "backend": "ollama", "model": "qwen2.5" },
    "analyst":      { "backend": "claude", "model": "claude-haiku-4-5-20251001" }
  }
}
```

The setup wizard prompts for each agent's preferred backend and shows cost estimates. A **"fully free" preset** runs all agents on Ollama with `llama3.2` (requires Ollama installed locally). A **"best quality" preset** uses Claude Sonnet for Writer + Research and Haiku for the rest.

### Tool-Use Compatibility
OSS models via Ollama that support tool-use natively (llama3.1+, qwen2.5, mistral-nemo) use structured JSON tool calls. For models without native tool-use support, the `LLMClient` falls back to a prompt-engineered tool-calling format (XML tags) with a local parser.

---

## Resume Profile System

### Setup Flow
During the setup wizard (`setup/wizard.py`), the user is prompted:
> "Upload your resume (PDF or DOCX) to personalize your outreach"

The resume is parsed and stored as a structured `UserProfile` in the local DB:

```python
UserProfile:
  name, email, phone
  headline            # e.g., "Backend Engineer with 3 years in fintech"
  skills[]            # ["Rust", "Python", "distributed systems", "trading systems"]
  experience[]        # [{company, role, years, description}, ...]
  education[]         # [{school, degree, year}, ...]
  projects[]          # [{name, description, tech_stack[]}, ...]
  github_url
  linkedin_url
  resume_raw_text     # full text for LLM context
```

The Matcher Agent loads `UserProfile` on every matching run. The Writer Agent also has read access to construct accurate "here's why I'm relevant" paragraphs.

### Resume Parsing
- `PyMuPDF` (fitz) for PDF parsing
- `python-docx` for DOCX
- Claude extracts structured fields from raw text (one-shot extraction call)

---

## Future Module Architecture

The platform is designed as a modular job hunting suite. Future modules slot in as new agents + TUI screens:

```
outreach-agent/
└── modules/                   # Future pluggable modules
    ├── ats_checker/           # ATS score against job descriptions
    │   └── agent.py           # Analyzes JD keywords, scores resume fit, suggests edits
    ├── interview_prep/        # Interview preparation agent
    │   └── agent.py           # Generates likely questions, mock answers from user profile
    ├── job_board_scraper/     # Scrape actual job listings (LinkedIn Jobs, Indeed, Lever, Greenhouse)
    │   └── agent.py
    └── application_tracker/  # Track applied roles, status, deadlines
        └── agent.py
```

Each module registers itself with the Orchestrator via a `ModuleRegistry`. The TUI adds a tab per active module. This means the core platform never needs to change to add ATS checking or interview prep — they're just new agents.

---

## Installation & Local Setup

### Directory Structure (post-install)
```
~/.outreach-agent/
├── config.json                # Encrypted API keys, Gmail credentials, preferences
├── outreach.db                # Primary SQLite database
├── logs/
│   ├── agent.log              # All agent activity
│   └── email.log              # Email send/receive log
├── resume/
│   └── resume.pdf             # User's uploaded resume
└── venues/
    └── custom_venue.py        # User-defined venue plugins
```

### Installation Steps
```bash
# Option A: pip install (future PyPI package)
pip install outreach-agent

# Option B: clone + install (development)
git clone <repo>
cd outreach-agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium    # headless browser for scraping
python main.py                 # launches setup wizard on first run
```

### Database: SQLite (primary, zero-dependency)
SQLite is the right choice for a single-user local tool:
- No server to run
- File-based, easily backed up
- Sufficient for tens of thousands of leads
- SQLModel provides async-compatible ORM

**Migration tool:** Alembic handles schema migrations as the product evolves.

**Optional Redis:** If the user enables multi-process workers in settings, Redis is used as the task queue backend instead of asyncio.Queue. Falls back gracefully if Redis is not available.

### Environment & Secrets
All secrets stored encrypted in `~/.outreach-agent/config.json` using `cryptography` (Fernet symmetric encryption). Key derived from a local machine key (not stored in the repo or env file).

`.env` is used only during development for overrides.

---

## Project Structure

```
outreach-agent/
├── main.py                    # Entry point: wizard or TUI
├── pyproject.toml             # Dependencies + build config
├── agent/
│   ├── base.py                # BaseAgent: LLMClient + tool-use loop
│   ├── llm_client.py          # LLMClient abstraction (Claude/OpenAI/Ollama/LMStudio)
│   ├── backends/
│   │   ├── anthropic.py       # Claude backend
│   │   ├── openai_compat.py   # OpenAI + any OpenAI-compatible API
│   │   └── ollama.py          # Ollama local backend
│   ├── orchestrator.py
│   ├── scout.py
│   ├── research.py
│   ├── matcher.py             # Skills/qualifications matching
│   ├── writer.py
│   ├── outreach.py
│   ├── analyst.py
│   └── prompts/               # System prompt .md files per agent
├── discovery/
│   ├── base.py                # VenueBase abstract class
│   ├── ycombinator.py
│   ├── producthunt.py
│   ├── crunchbase.py
│   ├── angellist.py
│   ├── apollo.py
│   ├── hunter.py
│   ├── linkedin.py
│   └── registry.py            # Auto-loads venues, plugin system
├── email_engine/
│   ├── smtp.py                # Gmail SMTP + rate limiter
│   ├── imap.py                # Gmail IMAP reply poller
│   ├── tracker.py             # Open pixel tracking
│   └── scheduler.py           # APScheduler follow-up queue
├── profile/
│   ├── parser.py              # PDF/DOCX resume parser
│   └── extractor.py           # Claude-powered structured extraction
├── setup/
│   ├── wizard.py              # First-run: Gmail, API keys, resume upload
│   └── venue_setup.py         # Guided new venue creation wizard
├── tui/
│   ├── app.py                 # Textual App
│   ├── screens/
│   │   ├── dashboard.py       # Stats + Orchestrator chat
│   │   ├── leads.py           # Leads table with pipeline status + match scores
│   │   ├── emails.py          # Email list + preview
│   │   └── settings.py        # Config, venues, resume, API keys
│   └── widgets/
│       ├── stats_panel.py
│       ├── chat_panel.py
│       └── activity_feed.py   # Live event stream from all agents
├── queue/
│   ├── dispatcher.py          # Async task dispatcher
│   └── workers.py             # Worker pool for agent jobs
├── modules/                   # Future pluggable modules (empty stubs)
│   ├── __init__.py
│   ├── registry.py            # ModuleRegistry for future modules
│   ├── ats_checker/
│   ├── interview_prep/
│   └── application_tracker/
├── db/
│   ├── models.py              # All SQLModel tables
│   ├── queries.py             # Helper query functions
│   └── migrations/            # Alembic migration files
└── config.py                  # ~/.outreach-agent/ config management
```

---

## Data Models

```python
UserProfile:  id, name, headline, skills[], experience[], education[], projects[], resume_path, updated_at
Lead:         id, name, email, company, role, source_venue, score, match_score, value_prop, status, scraped_at
IntelBrief:   id, lead_id, company_summary, person_summary, signals[], talking_points[], created_at
Email:        id, lead_id, subject, body, subject_variant, sent_at, opened_at, replied_at, reply_type, reply_body
Campaign:     id, name, query, venues[], status, lead_count, sent_count, reply_count, created_at
AgentLog:     id, agent_name, task, input_summary, output_summary, tokens_used, duration_ms, created_at
Venue:        id, name, enabled, config_json, last_scraped_at
```

---

## Extensibility Architecture

The system is built around four extension points. Adding any future feature means implementing one or more of these interfaces — the core never changes.

### 1. Event Bus (`queue/events.py`)
All significant state changes emit events. Any agent or module can subscribe. This is how new features plug in without touching existing code.

```python
# Events emitted by core:
LeadDiscovered(lead_id, venue, score)
IntelBriefReady(lead_id)
ValuePropGenerated(lead_id)
EmailDrafted(lead_id, email_id)
EmailSent(email_id)
EmailOpened(email_id, timestamp)
ReplyReceived(email_id, reply_type, body)
FollowUpQueued(email_id, scheduled_at)
AgentCompleted(agent_name, task_id, output)

# Future modules subscribe to events they care about:
# FundingMonitor subscribes to: nothing (polls externally)
# FundingMonitor emits: FundingSignalDetected(company)
# Scout subscribes to: FundingSignalDetected → triggers new scout run
```

This pub-sub pattern means the Funding Monitor, LinkedIn warm-up, or any future module just subscribes to the right events and emits new ones — no changes to Scout, Research, or Writer.

### 2. Agent Registry (`agent/registry.py`)
Agents are registered by name. The Orchestrator routes tasks by consulting the registry, not a hardcoded if-else chain.

```python
@agent_registry.register("scout")
class ScoutAgent(BaseAgent): ...

@agent_registry.register("interview_prep")  # future module, drops in
class InterviewPrepAgent(BaseAgent): ...
```

New agents register themselves on import. The Orchestrator picks them up automatically.

### 3. Venue Plugin System (`discovery/registry.py`)
Already described above — `VenueBase` + auto-discovery. Any `.py` file in `discovery/` or `~/.outreach-agent/venues/` is loaded automatically.

### 4. TUI Module System (`tui/module_registry.py`)
Modules can register new TUI screens and sidebar items. The Textual App queries the registry at startup and mounts registered screens.

```python
@tui_registry.register_screen(tab_label="ATS", shortcut="F5")
class ATSCheckerScreen(Screen): ...  # drops in when ats_checker module is enabled
```

### 5. Integration Layer (`integrations/`)
All third-party service calls go through named integration adapters. New services (Calendly, Notion, Slack) are added here without touching agent logic.

```
integrations/
├── base.py              # IntegrationBase
├── gmail.py             # Gmail SMTP + IMAP
├── calendly.py          # (future) Calendar link generation
├── notion.py            # (future) Sync leads to Notion DB
├── slack.py             # (future) Daily digest to Slack
└── registry.py          # Auto-loads enabled integrations from config
```

### 6. Hook System (`hooks/`)
Lifecycle hooks let users add custom logic at key points (similar to git hooks) without modifying source:

```
~/.outreach-agent/hooks/
├── on_lead_discovered.py    # Custom scoring logic
├── on_email_drafted.py      # Custom email post-processing
└── on_reply_received.py     # Custom reply handling
```

---

## Future Features Backlog

All features below are designed to slot into the extensibility architecture above. None require changes to the core pipeline.

### Intelligence & Targeting
- **Tech stack detection** — scrape job postings + company GitHub org to infer stack; Matcher scores your skills against it (new Research Agent tool + Matcher skill)
- **Funding signal triggers** — monitor Crunchbase/PH for funding rounds; auto-queue Scout run when a company raises (new `FundingMonitor` module, subscribes/emits events)
- **Company news monitoring** — RSS/Google Alerts per target company; Writer Agent references recent press in opener (new Research tool + event)
- **Competitor mapping** — Research Agent builds competitive landscape for each target company's industry
- **GitHub contribution detection** — identify OSS repos at target companies relevant to user's skills; suggest contributing before emailing CTO

### Relationship & Network
- **Warm intro finder** — scan LinkedIn connections for second-degree paths into target companies; Orchestrator prioritizes warm paths (new Research tool)
- **LinkedIn warm-up** — auto-engage with target's LinkedIn posts (like/comment via Playwright) before cold email (new `LinkedInWarmup` module + event hook)
- **Auto-LinkedIn connect** — connection request + personalized note before/after email (new Outreach tool)
- **Network graph view** — TUI screen: visual graph of you → connections → companies → targets (new TUI screen via module registry)

### Email Intelligence
- **Smart send timing** — learn optimal send windows per industry/role from historical open data (Analyst Agent enhancement)
- **Subject line evolution** — winning subject lines fed back to Writer Agent system prompt automatically (Analyst → Writer feedback loop via event)
- **Reply draft assist** — on positive reply, Orchestrator drafts your response for review (new Outreach event handler)
- **Meeting detection** — detect "let's talk" intent in replies, inject Calendly link (new Outreach + Calendly integration)
- **Auto unsubscribe handler** — detect opt-out replies, mark do-not-contact permanently (new reply classifier label + Outreach handler)

### Job Board & Career Module
- **Job posting scraper** — scrape LinkedIn Jobs, Greenhouse, Lever, Workable; combine with outreach ("saw you're hiring a backend engineer") (new Venue type: `job_board`)
- **ATS keyword optimizer** — given a JD, show which keywords your resume is missing (new `ATSChecker` module)
- **Interview prep** — generate likely questions + answers given company + role + UserProfile (new `InterviewPrep` module)
- **Application tracker** — log all applications, interview stages, decisions; pipeline view in TUI (new `ApplicationTracker` module + TUI screen)

### Workflow & Control
- **Multi-account support** — manage multiple Gmail accounts per role/niche; route campaigns to specific accounts
- **Company blacklist/whitelist** — config-driven, checked by Scout before adding leads
- **Campaign templates** — save reusable campaign configs as named presets
- **`outreach add-lead <url>`** — CLI quick-add from LinkedIn URL → fires Research + Matcher + Writer
- **Daily briefing** — morning digest: new replies, pending reviews, suggested actions (new Analyst event + Orchestrator hook)
- **Outreach health score** — daily score (0–100) in stats panel; tracks leads, send rate, reply rate, pipeline progress
- **Browser quick-add** — future browser extension to push profiles directly into Scout queue

---

## Implementation Steps

1. **Scaffold** — project structure, `pyproject.toml`, Alembic setup
2. **DB layer** — SQLModel models + migrations + `queries.py`
3. **Config system** — `~/.outreach-agent/` encrypted config
4. **Resume profile** — PDF/DOCX parser + Claude extraction → `UserProfile`
5. **Setup wizard** — Gmail SMTP/IMAP, API keys, resume upload, test send
6. **BaseAgent** — LLM client wrapper with tool-use loop (shared by all agents)
7. **VenueBase + YC scraper** — first working venue end-to-end
8. **Remaining venues** — Apollo, Hunter, ProductHunt, Crunchbase, AngelList, LinkedIn
9. **Venue plugin system** — registry + `--venue-setup` wizard
10. **Scout Agent** — parallel venue scraping, dedup, scoring
11. **Research Agent** — company + person intel, signal detection
12. **Matcher Agent** — UserProfile × IntelBrief → match score + value prop
13. **Writer Agent** — personalized email with value prop, A/B subjects, follow-ups
14. **Outreach Agent** — SMTP send + IMAP poll + reply classifier + follow-up scheduler
15. **Analyst Agent** — metrics, cohort analysis, insight feedback loop
16. **Orchestrator Agent** — pipeline coordination + user chat
17. **Async task queue** — dispatcher + worker pool wiring all agents
18. **TUI** — Textual app, all screens + match score in leads view + activity feed
19. **Module stubs** — empty `ats_checker`, `interview_prep`, `application_tracker` + `ModuleRegistry`
20. **Main entry point + installation script** — wizard → TUI → agent team startup

---

## Dependencies

```toml
[project.dependencies]
anthropic = ">=0.40.0"         # Claude API backend
openai = ">=1.40.0"            # OpenAI + OpenAI-compatible backends (Ollama, LMStudio)
textual = ">=0.70.0"           # Terminal UI
playwright = ">=1.45.0"        # Headless browser scraping
sqlmodel = ">=0.0.21"          # SQLite ORM
alembic = ">=1.13.0"           # DB migrations
httpx = ">=0.27.0"             # Async HTTP client
beautifulsoup4 = ">=4.12.0"    # HTML parsing
apscheduler = ">=3.10.0"       # Follow-up scheduling
rich = ">=13.0.0"              # Text formatting
click = ">=8.1.0"              # CLI entry points
python-dotenv = ">=1.0.0"
cryptography = ">=42.0.0"      # Encrypt stored secrets
pymupdf = ">=1.24.0"           # PDF parsing
python-docx = ">=1.1.0"        # DOCX parsing
redis = {version = ">=5.0.0", optional = true}  # Optional task queue backend

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "mypy", "ruff"]
```

**Note on Ollama:** Ollama uses an OpenAI-compatible REST API, so `openai` SDK handles it with a `base_url` override (`http://localhost:11434/v1`). No separate Ollama SDK needed.

---

## CLI Command Interface

The tool exposes a full `outreach` CLI for every operation — no need to open the TUI for quick checks. Commands are grouped by domain:

### Agent Inspection
```bash
outreach agents list                  # List all agents + status (idle/running/error)
outreach agents logs                  # Tail recent agent activity across all agents
outreach agents logs --agent writer   # Filter to specific agent
outreach agents inspect <agent-name>  # Full run history + last input/output + token usage
```

### Data & Analytics
```bash
outreach data leads                   # Table of all leads (name, company, role, match score, status)
outreach data leads --venue yc --status new   # Filter by venue and status
outreach data emails                  # All emails: sent, pending review, opened, replied
outreach data stats                   # Dashboard summary: sent, open rate, reply rate, interviews
outreach data export --format csv     # Export leads or emails to CSV
outreach data lead <id>               # Full detail view of one lead + intel brief + email history
```

### Email Tracking & Review
```bash
outreach mail pending                 # Show emails in review queue awaiting approval
outreach mail review <id>             # Open email draft for inline editing before send
outreach mail approve <id>            # Approve and send immediately
outreach mail approve-all             # Approve all pending (with confirmation prompt)
outreach mail reject <id>             # Reject draft, optionally regenerate
outreach mail track                   # Live view of opens, clicks, replies
outreach mail thread <lead-id>        # Full email thread with a lead (sent + received)
```

### Manual Agent Triggers
```bash
outreach run scout --venue yc --query "fintech startups" --count 20
outreach run research <lead-id>       # Re-research a specific lead
outreach run match                    # Re-run Matcher on all unmatched leads
outreach run write <lead-id>          # Regenerate email draft for a lead
outreach run followup                 # Queue follow-ups for all eligible leads
outreach run analyze                  # Run Analyst Agent and print report
```

### Config & Setup
```bash
outreach config show                  # Print current config (redacted secrets)
outreach config set --agent writer --backend claude --model claude-sonnet-4-6
outreach config set --agent scout --backend ollama --model llama3.2
outreach setup                        # Re-run setup wizard
outreach --venue-setup                # Add a new discovery venue
```

---

## Human-in-the-Loop Mode

The system defaults to **review-before-send**: every email draft goes into a **Review Queue** before sending. This keeps you in control of every word sent in your name.

### Review Queue Flow
```
Writer Agent drafts email
        │
        ▼
Review Queue (status: "pending_review")
        │
        ├─ outreach mail review <id>   → open in editor, edit subject/body
        ├─ outreach mail approve <id>  → send immediately
        ├─ outreach mail reject <id>   → discard or regenerate
        └─ In TUI: F3 Emails → Review tab → inline edit panel
```

### Step-by-Step Assist Mode
Enable in config (`"assist_mode": true`) to have the Orchestrator narrate every step and pause at configurable checkpoints:

```
[Scout] Found 8 leads from YC W25 fintech batch.
[Scout] Highest match: Sarah Chen (CTO, Fintex) — match score 87/100
        → Continue to research all 8? [Y/n/select]

[Research] Compiled intel brief for Sarah Chen.
        Key signal: Fintex raised $4M seed 3 weeks ago, actively hiring backend
        → View full brief? [Y/n]

[Matcher] Value prop generated:
        "Your Rust + distributed systems experience directly matches Fintex's
         backend challenges — they're building a real-time clearing engine."
        → Edit value prop? [Y/n]

[Writer] Draft email ready for review.
        Subject A: "Rust dev excited about Fintex's clearing engine"
        Subject B: "Quick note from a backend engineer"
        → Open in review queue: `outreach mail review 42`
```

### Inline Edit in TUI
In the TUI Emails tab → Review subtab:
- Full email preview pane with editable subject, body
- Side panel shows the `IntelBrief` and `ValueProp` for reference while editing
- Keyboard shortcut: `e` to edit, `a` to approve, `r` to reject, `g` to regenerate

---

## Verification

- `python main.py` → setup wizard prompts for resume + Gmail + API keys
- `python main.py --venue-setup` → guided new venue creation
- TUI launches with stats panel, activity feed, agent chat
- Chat: "find 5 YC fintech startups and email their CTOs" → Scout → Research → Matcher → Writer → Outreach fires in sequence, visible in activity feed
- Leads tab shows match scores next to each lead
- Emails tab shows sent emails with open/reply status
- F4 Settings shows resume profile with extracted skills
- Analyst daily digest appears in chat after 24h
