# INGOT — INtelligent Generation & Outreach Tool

## What This Is

An autonomous cold outreach tool that replaces manual job hunting with an AI-powered pipeline. It scouts leads from discovery venues, deeply researches each company and person, matches the user's actual qualifications against each opportunity, and writes highly personalized cold emails. Interaction happens through a rich CLI (Claude Code style) with an interactive TUI for dashboard views and email review flows. Built for personal use and as a product others can install via pip.

## Core Value

Every email sent is grounded in real research about the company AND real qualifications from the user's resume — no generic templates, no spray-and-pray.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Agent Pipeline**
- [ ] 7 agents: Orchestrator, Scout, Research, Matcher, Writer, Outreach, Analyst
- [ ] Orchestrator: routes tasks, maintains campaign memory, handles natural language chat
- [ ] Scout: discovers leads from venues in parallel, deduplicates, initial scoring
- [ ] Research: builds deep IntelBrief per lead (company intel, person intel, signals, talking points)
- [ ] Matcher: cross-references UserProfile against IntelBrief, generates match score (0-100) + value proposition
- [ ] Writer: receives Lead + IntelBrief + ValueProp, writes personalized email, tone adapts by role (HR/CEO/CTO), generates subject variants + follow-up sequences
- [ ] Outreach: manages sending (rate limiting, business hours), polls replies via IMAP, classifies replies, manages follow-up queue
- [ ] Analyst: tracks open/reply rates, identifies patterns, feeds insights back to Writer's context

**LLM & Agent Framework**
- [ ] Pluggable LLM backends: Claude (anthropic SDK), OpenAI (openai SDK), Ollama (OpenAI-compatible HTTP to localhost:11434), LM Studio, any OpenAI-compatible API
- [ ] Single LLMClient abstraction — no agent directly imports anthropic or openai
- [ ] Per-agent model config in ~/.outreach-agent/config.json
- [ ] Free-first: every agent must run on Ollama with zero API cost
- [ ] Tool-use compatibility: native JSON tool calls for models that support it, prompt-engineered XML fallback for models without
- [ ] Agent framework: research best option (PydanticAI, LangGraph, custom BaseAgent), pick one for v1, design for swappability

**Resume Profile System**
- [ ] Setup wizard prompts for resume upload (PDF or DOCX)
- [ ] PyMuPDF (fitz) for PDF parsing, python-docx for DOCX
- [ ] LLM-powered structured extraction to UserProfile (name, headline, skills[], experience[], education[], projects[], github_url, linkedin_url, resume_raw_text)
- [ ] Matcher and Writer agents load UserProfile on every run

**Email Generation & Review**
- [ ] Interactive mode: per-lead MCQ questions (2-3 personalized to their company/person), then generate draft
- [ ] Batch mode: once patterns learned, generate autonomously with optional review
- [ ] Review-before-send queue: approve, edit inline, reject, regenerate
- [ ] Flexible email length per recipient type (not fixed word count)
- [ ] 2 subject line variants for A/B testing
- [ ] Follow-up sequence: Day 3, Day 7 drafts for non-replies

**Gmail Integration (Email Engine)**
- [ ] SMTP for sending via Gmail
- [ ] IMAP for polling replies
- [ ] Reply classification: positive, negative, auto-reply, OOO
- [ ] Open pixel tracking
- [ ] Rate limiting and business-hours-only send windows
- [ ] APScheduler for follow-up queue scheduling
- [ ] On positive reply: notify user, suggest response, optionally send Calendly link

**Interface**
- [ ] Rich CLI (primary): conversational with rich terminal output (tables, panels), similar to Claude Code
- [ ] CLI commands grouped by domain: agents (list/logs/inspect), data (leads/emails/stats/export), mail (pending/review/approve/reject/track), run (scout/research/match/write/followup/analyze), config (show/set/setup)
- [ ] Interactive TUI (nice-to-have): Textual-based dashboard, leads table with match scores, email review panel with inline editing, activity feed, settings screen
- [ ] TUI keyboard shortcuts: e (edit), a (approve), r (reject), g (regenerate)
- [ ] Step-by-step assist mode: Orchestrator narrates every step and pauses at configurable checkpoints

**Setup & Configuration**
- [ ] First-run setup wizard: Gmail SMTP/IMAP credentials, API keys per LLM backend, resume upload, per-agent LLM backend selection, browser automation opt-in, test send
- [ ] ~/.outreach-agent/ directory: config.json (encrypted), outreach.db, logs/, resume/, venues/ (custom plugins)
- [ ] Fernet symmetric encryption for all stored secrets (key derived from local machine key)
- [ ] Setup presets: "fully free" (all Ollama), "best quality" (Claude Sonnet for Writer+Research, Haiku for rest)

**Data Layer**
- [ ] SQLite via SQLModel ORM
- [ ] Alembic for schema migrations
- [ ] Models: UserProfile, Lead, IntelBrief, Email, Campaign, AgentLog, Venue
- [ ] Optional Redis for multi-process task queue (falls back to asyncio.Queue)

**Discovery Venues**
- [ ] 1-2 venues for v1: YC as primary
- [ ] VenueBase abstract class for all venues
- [ ] Venue plugin system: auto-discovery of .py files in discovery/ and ~/.outreach-agent/venues/
- [ ] Guided venue creation wizard (--venue-setup)
- [ ] Scraping: httpx as default, Playwright browser automation opt-in (configured during setup)

**Extensibility Architecture**
- [ ] Event bus: LeadDiscovered, IntelBriefReady, ValuePropGenerated, EmailDrafted, EmailSent, EmailOpened, ReplyReceived, FollowUpQueued, AgentCompleted
- [ ] Agent registry: agents register by name, Orchestrator routes by consulting registry
- [ ] Module registry: future modules (ATS, interview prep, application tracker) register as new agents + TUI screens
- [ ] Integration layer: named adapters for third-party services (Gmail, future: Calendly, Notion, Slack)
- [ ] Hook system: ~/.outreach-agent/hooks/ for user-defined lifecycle hooks (on_lead_discovered, on_email_drafted, on_reply_received)

**Async & Task Queue**
- [ ] Async task dispatcher + worker pool wiring all agents
- [ ] Parallel venue scraping within Scout agent

### Out of Scope

- Budget/token tracking — v2 feature
- Funding signal monitoring — v2 (surveillance is deep one-shot, not continuous)
- LinkedIn warm-up automation — v2
- Warm intro finder — v2
- ATS keyword optimizer module — v2
- Interview prep module — v2
- Application tracker module — v2
- Browser extension — v2
- Multi-account Gmail support — v2
- Company news monitoring (RSS/alerts) — v2
- Network graph visualization — v2
- Tech stack detection from job postings — v2
- Smart send timing optimization — v2
- Subject line evolution (auto-feedback to Writer) — v2 (manual insight feedback in v1)
- Meeting detection + Calendly auto-injection — v2
- More than 2 venues in v1 — remaining venues (Apollo, Hunter, ProductHunt, Crunchbase, AngelList, LinkedIn) added incrementally
- Multiple agent backends simultaneously — pick one for v1, swappable architecture for later
- .env for secrets — encrypted config only (dev overrides acceptable)

## Context

- User is actively job hunting (backend, full-stack, ML/AI roles) while building this as a product
- Currently doing manual outreach (LinkedIn, Google, hand-written emails) — this replaces that entirely
- "Done" for v1 = 10 personalized email drafts the user would actually send
- The tool should feel like a personal recruiting agency that runs in the terminal
- Email quality is the highest-value differentiator — the interactive MCQ flow per lead ensures every email is steered by the user's judgment, not just AI guessing
- Two interaction modes: interactive (per-lead MCQ → draft → review) for learning, then batch (autonomous drafting with review queue) once patterns are established
- The plan document (outreach-agent-plan.md) contains extensive future feature backlog for v2+
- Ollama/free-first is critical — every agent must be runnable on local models at zero API cost
- Project structure follows the architecture in outreach-agent-plan.md: agent/, discovery/, email_engine/, profile/, setup/, tui/, queue/, modules/, db/, config.py

## Constraints

- **LLM Backend**: Must support Claude, OpenAI, AND Ollama equally — no vendor lock-in
- **Browser Automation**: Playwright is opt-in only, httpx is the default scraping method
- **Agent Framework**: Research will determine the best option; must support multi-LLM, tool-use, and be swappable
- **Data Storage**: SQLite only — no external database servers (single-user local tool)
- **Secrets**: Fernet-encrypted config — no plaintext API keys on disk
- **Email Length**: Flexible per recipient type (CEO vs recruiter), not a fixed word count
- **Installation**: pip installable, Playwright optional (`pip install outreach-agent[browser]`)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Rich CLI primary + TUI for interactive flows | CLI for quick actions, TUI for dashboard/email review | — Pending |
| Interactive MCQ per lead before email generation | User steers personalization, system learns preferences over time | — Pending |
| Ollama as first-class, not afterthought | Free-first principle; removes barrier to adoption | — Pending |
| 1-2 venues for v1 (YC primary) | Prove pipeline end-to-end before scaling venue count | — Pending |
| Agent framework deferred to research | Too many viable options; research will compare with real data | — Pending |
| Playwright opt-in, httpx default | Reduces install friction; most scraping doesn't need a browser | — Pending |
| Single agent backend for v1 | Avoid premature abstraction; design interface for swappability | — Pending |
| Fernet encryption for secrets | No plaintext keys on disk; machine-local key derivation | — Pending |
| SQLite + SQLModel | Zero-dependency DB for single-user tool; Alembic for migrations | — Pending |

---
*Last updated: 2025-02-25 after initialization*
