# Domain Pitfalls

**Domain:** AI-powered cold outreach tool (multi-agent, local-first, Gmail-backed)
**Project:** INGOT — INtelligent Generation & Outreach Tool
**Researched:** 2026-02-25
**Overall confidence:** MEDIUM (web tools unavailable; analysis draws on training data through Aug 2025 + deep domain knowledge; flagged where verification needed)

---

## Critical Pitfalls

Mistakes that cause rewrites, account bans, or legal liability.

---

### Pitfall 1: Gmail Account Suspension from Bulk SMTP Sending

**What goes wrong:** Using Gmail SMTP to send cold outreach emails triggers Google's spam detection. A personal Gmail account sending 50-100+ emails/day to strangers with similar subjects gets flagged. Google silently rate-limits first, then suspends the account. The account used to send is likely the user's primary email — losing it is catastrophic.

**Why it happens:**
- Gmail SMTP has a hard cap per day for personal and free accounts (numbers subject to Google policy; verify current limits at support.google.com/mail/answer/22839).
- Google's spam classifier scores: high recipient diversity + low prior relationship + similar email structure = spam signal.
- Cold emails have high bounce rates (invalid addresses), and SMTP handles bounces poorly — they increase spam score.
- Sending via SMTP bypasses Gmail's categorization system, increasing chances of inbox spam classification.
- "Business hours only" logic helps slightly but does not prevent suspension — volume per hour and per day are both tracked.

**Consequences:**
- Permanent Google account suspension (loses Gmail, Drive, Docs, everything).
- If using Google Workspace / custom domain, domain reputation tanks.
- No warning — one day it works, next day it does not.

**Prevention:**
- Use a dedicated sending domain (not the user's primary Gmail). e.g., firstname@firstname-outreach.com.
- Implement email warming: start at 5/day, increase 2-3/day over 4-6 weeks before any cold sends.
- Hard cap enforced in code: never exceed 30 cold emails/day from a new account. 50/day max from a warmed account (6+ weeks old).
- Build per-day and per-hour send counters into SQLite — counters must survive process restarts.
- Bounce handling: if bounce rate exceeds 5%, pause sending and alert user immediately.
- Prefer Gmail API with OAuth2 over raw SMTP — the API gives better error codes, rate limit headers, and is harder to abuse accidentally.
- Never reuse the personal primary Gmail address for campaign sends.

**Detection (warning signs):**
- SMTP 550 5.7.1 or 421 4.7.0 responses from smtp.gmail.com.
- Emails land in your own spam folder during self-test.
- Google sends "unusual activity" security alert to the account.
- Reply rate drops suddenly to 0 despite continued sends.

**Phase mapping:** Phase 1 (Email Engine setup) — bake in rate limiting before any real sends. Setup wizard must warn about dedicated domain requirement and block sends without confirmation.

---

### Pitfall 2: Email Deliverability Failure (Missing SPF/DKIM/DMARC)

**What goes wrong:** Emails are sent but never seen. They land in spam or are silently dropped. This is distinct from account suspension — the account still works but emails do not reach inboxes.

**Why it happens:**
- Cold emails from a domain without SPF, DKIM, and DMARC configured are treated as unauthenticated by receiving mail servers.
- Google's bulk sender policy update (2024) requires DKIM and DMARC for senders of 5000+ messages/day. Below that threshold, lack of authentication still significantly hurts deliverability.
- A new domain with no sending history has zero reputation — ISPs reject or quarantine by default.
- Email warming is not optional. It is the only way to build sender reputation on a new domain.

**Consequences:**
- 0% reply rate despite well-crafted emails that are never seen.
- No feedback to the system — Outreach agent sees "sent" but recipient never received it.
- Open pixel tracking shows 0 opens, making Analyst agent data completely meaningless.

**Prevention:**
- Setup wizard must verify that the user's sending domain has SPF, DKIM, and DMARC configured before allowing any sends. Use dns.resolver (dnspython library) to check TXT records.
- Generate and display the exact DNS records the user needs to add for their domain.
- Email warming must be enforced by APScheduler — not left to the user to remember.
- Test deliverability to seed addresses (Gmail, Outlook, Yahoo) before campaign launch.
- Block the campaign from starting if DNS validation fails.

**Detection (warning signs):**
- dns.resolver finds no TXT record starting with "v=spf1" for the sending domain.
- No DKIM TXT record at the selector subdomain.
- No DMARC TXT record at _dmarc subdomain.
- 0 opens after 50+ sends.
- SMTP bounce messages mentioning SPF, DMARC, or authentication.

**Phase mapping:** Phase 1 (Email Engine) — DNS validation in setup wizard. Phase 2 (Outreach agent) — warming schedule enforced by scheduler, not advisory.

---

### Pitfall 3: LLM Tool-Use Unreliability Across Backends

**What goes wrong:** The system requires every agent to run on Ollama at zero API cost. But local models have inconsistent and unreliable tool/function-calling behavior. Code that works perfectly with Claude claude-sonnet-4-6 silently fails with llama3.2:3b or mistral:7b — the agent gets stuck, returns malformed JSON, or hallucinates tool arguments.

**Why it happens:**
- Tool use is a learned capability. Even models with official tool-call support in Ollama (llama3.1, mistral-nemo, qwen2.5) have significantly lower reliability than Claude or GPT-4o.
- "Supports tool use" in Ollama means the model was fine-tuned to output JSON in a specific format — it does not guarantee schema adherence, correct argument types, or single-call behavior.
- Small models (3B, 7B) frequently: return multiple tool calls when one was requested; hallucinate tool names not in the schema; return valid JSON that fails Pydantic validation; truncate JSON mid-generation when context window fills.
- The XML fallback path requires prompt engineering that is model-specific — a prompt that works for one model fails for another.

**Consequences:**
- Agent enters infinite retry loop (tool call fails, retry, fails again).
- Silent data corruption: agent "succeeds" but with hallucinated values (fake company facts in IntelBrief, invented match scores).
- Orchestrator cannot route if the agent does not return expected structured output.
- Ollama pipeline appears to work but produces plausible-looking garbage.

**Prevention:**
- Design the LLMClient abstraction from day one with explicit tool-call validation: validate every tool response against Pydantic schema, raise a typed error on failure — never pass unvalidated output downstream.
- Implement retry with backoff and fallback: 3 attempts with tool-use, then fall back to XML-extraction prompt, then surface error to user.
- Build a model compatibility test suite that runs against any configured backend before a campaign.
- Per-agent model config is essential — recommend Claude for Writer and Research, local models for Scout and Analyst.
- Implement context window management: estimate token count before each tool call, summarize or truncate inputs before hitting model limits.
- Document which Ollama models are tested and known-good for tool use.

**Detection (warning signs):**
- Agent retry counter consistently hitting max retries.
- ValidationError from Pydantic on tool responses.
- AgentLog showing "success" but downstream data is clearly wrong.
- Model returns tool call in unexpected format.

**Phase mapping:** Phase 1 (LLMClient abstraction) — validation layer is non-negotiable. Phase 2 (agent implementations) — test each agent against Ollama before marking phase complete.

---

### Pitfall 4: Web Scraping Brittleness and Anti-Bot Detection

**What goes wrong:** YC's company directory (v1 primary venue) and company websites have anti-bot measures. httpx-based scraping works initially, then breaks — HTML structure changes, Cloudflare blocks the request, or rate limiting kicks in silently.

**Why it happens:**
- YC's site is a React SPA. The initial HTML returned to httpx contains no company data — data is loaded via JavaScript. httpx does not execute JS.
- Cloudflare serves a JS challenge that pure HTTP clients cannot pass.
- Scraping without rotating user-agents and request delays triggers 429s or silent IP bans.
- HTML structure changes break CSS or XPath selectors without warning — data silently becomes None.

**Consequences:**
- Scout agent returns 0 leads despite "successful" HTTP responses.
- Lead data has None values for critical fields — Writer agent produces generic emails.
- Pipeline appears to work but produces garbage output silently.

**Prevention:**
- For YC specifically: check for a YC public API or JSON data endpoint before building an HTML scraper. (Verify at api.ycombinator.com before assuming scraping is required.)
- Implement schema validation on scraped output: if more than 20% of fields are None, flag as scrape failure — do not pass empty data downstream.
- Respect robots.txt — build a robots.txt checker into VenueBase.
- Minimum 1-2 second delay between requests; randomize between 0.5 and 3 seconds.
- Rotate User-Agent strings from a list of real browser UA strings.
- Make Playwright activation easy when httpx fails.
- Per-venue freshness check: 0 results = alert user immediately, do not proceed.

**Detection (warning signs):**
- httpx returns 403, 429, or 503 from venue.
- Parsed HTML contains Cloudflare challenge markup.
- Lead count drops to 0 across multiple runs.
- Fields that previously populated now return None.

**Phase mapping:** Phase 2 (Scout agent / YC venue) — build validation into VenueBase from the start.

---

### Pitfall 5: Cold Email Legal Violations (CAN-SPAM, GDPR, CASL)

**What goes wrong:** The tool generates and sends unsolicited commercial emails. Missing required disclosures create legal exposure for the user — and for you as the pip package developer.

**Why it happens:**
- CAN-SPAM (US): requires physical mailing address in every commercial email, clear opt-out mechanism, non-deceptive subject lines. Penalty: up to $50,120 per email.
- GDPR (EU): mass cold outreach to EU recipients violates legitimate interest requirements.
- CASL (Canada): cold emails are illegal without pre-existing business relationship.

**Consequences:**
- Legal liability for the user.
- If distributed as a pip package, liability exposure for the developer if the tool enables non-compliant sends at scale.

**Prevention:**
- Writer agent must inject CAN-SPAM required footer in every email: opt-out instruction and user's physical address.
- Setup wizard must collect user's physical mailing address.
- Display compliance warning during setup.
- Add an UnsubscribedEmail table in SQLite. Any reply containing "unsubscribe", "remove me", or "stop" triggers immediate suppression.
- Reply classifier must treat unsubscribe intent as a first-class category.

**Detection (warning signs):**
- Emails missing footer with physical address.
- No unsubscribe mechanism in email or reply classifier.
- Sending to EU contacts without per-recipient basis tracking.

**Phase mapping:** Phase 1 (setup wizard) — collect physical address. Phase 2 (Writer agent) — inject compliant footer. Phase 2 (Outreach agent / reply classifier) — unsubscribe detection and suppression.

---

## Moderate Pitfalls

---

### Pitfall 6: SQLite Concurrency with Async Workers

**What goes wrong:** Multiple async workers hitting SQLite concurrently. Without proper async setup, writes fail with OperationalError: database is locked.

**Why it happens:**
- asyncio and SQLite are a known mismatch. SQLite is synchronous I/O; blocking calls from async code block the event loop.
- SQLModel/SQLAlchemy async support requires aiosqlite as the backend driver.
- SQLite's default connection pool of 1 means every concurrent write blocks.

**Prevention:**
- Use aiosqlite as the SQLAlchemy driver from day one: create_async_engine("sqlite+aiosqlite:///...").
- Enable WAL mode: PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;
- Never hold a session open across an await boundary.

**Detection (warning signs):**
- sqlalchemy.exc.OperationalError: database is locked in logs.
- Deadlocks between APScheduler thread and async workers.

**Phase mapping:** Phase 1 (Data Layer setup) — choose aiosqlite from the start.

---

### Pitfall 7: Agent Orchestration Complexity and Circular Dependencies

**What goes wrong:** 7 agents talking to each other create circular call chains that deadlock or produce unbounded recursion.

**Prevention:**
- Enforce a strict DAG: Scout > Research > Matcher > Writer > Outreach > Analyst. No backward edges.
- Event bus events must be strictly one-directional.
- Orchestrator should be a router only. If it grows beyond 200 lines, that is a warning sign.
- For v1: skip the event bus entirely. Use direct async function calls.

**Detection (warning signs):**
- Orchestrator module grows to 500+ lines.
- Adding a new feature requires modifying more than 2 agent files.
- Same agent appears more than once in a call stack trace.

**Phase mapping:** Phase 1 (Architecture) — draw and commit to the DAG before writing any agent code.

---

### Pitfall 8: Over-Engineering Extensibility Before Core Works

**What goes wrong:** Building event bus, agent registry, module registry, hook system, and venue plugin system before the core pipeline works produces a framework with no product — 3000 lines of infrastructure, 0 sent emails.

**Prevention:**
- Rule: nothing is infrastructure until it has 2 real consumers.
- For v1: implement YC venue directly, not as a plugin. Extract VenueBase after the first implementation works.
- Venue plugin system, hook system, module registry: all v2.
- Exception: LLMClient abstraction must be built correctly from day one.

**Detection (warning signs):**
- Writing interfaces before any concrete implementations exist.
- base.py is larger than any concrete implementation file.
- Week 2 and no emails have been generated yet.

**Phase mapping:** Phase 1 — LLMClient abstraction only. Phase 2 — one working venue (direct, no plugin system). Phase 3+ — extract plugin system from working code only.

---

### Pitfall 9: Resume Parsing Edge Cases Producing Corrupt UserProfile

**What goes wrong:** Multi-column PDF resumes and DOCX with text boxes produce garbled text from parsers. LLM extracts a corrupt UserProfile — wrong skills, misattributed dates, or empty profile.

**Prevention:**
- Sanity check after extraction: minimum 200 words, at least one date pattern. Offer plain-text paste fallback if check fails.
- Use page.get_text("blocks") for multi-column PDF and sort blocks by x-coordinate.
- Validate UserProfile after LLM extraction: at least 1 experience entry, 3 skills, non-empty name.
- Store resume_raw_text as escape hatch — Writer and Matcher can always fall back.
- Never silently proceed with a corrupt UserProfile.

**Detection (warning signs):**
- experience list is empty after extraction.
- skills contains full sentences instead of skill names.
- name contains a job title or company name.

**Phase mapping:** Phase 1 (Profile System) — build validation into UserProfile model. Fail loudly.

---

### Pitfall 10: Ollama Context Window Overflow Killing Research Agent

**What goes wrong:** Research agent accumulates context across tool calls. By tool call 4-5, context exceeds the Ollama model's window. Model silently truncates early context, dropping system prompt, producing incoherent IntelBriefs.

**Prevention:**
- Token budget system in Research agent: estimate context token count before each tool call. Stop tool calls when remaining budget drops below 1000 tokens.
- Use heuristic: 1 token ~= 4 characters.
- Hard cap: max 5 tool calls per lead before forcing IntelBrief generation.
- Always set num_ctx explicitly in Ollama API request. Ollama defaults to 2048 for many models if not specified.
- Summarize intermediate tool results to bullet points before appending to context.

**Detection (warning signs):**
- IntelBrief quality degrades after 3+ tool calls.
- Research agent instructions not followed in later tool calls.
- Ollama API response shows prompt_eval_count near num_ctx limit.

**Phase mapping:** Phase 2 (Research agent) — token budget from day one.

---

## Minor Pitfalls

---

### Pitfall 11: Open Pixel Tracking Reliability

**What goes wrong:** Gmail's image proxy and Apple Mail Privacy Protection fire the open pixel on delivery, not on open. Open rate data is 30-40% accurate at best.

**Prevention:** Track pixel fires as "potential open" not confirmed open. Reply rate is the only reliable signal. Document this prominently in Analyst output.

**Phase mapping:** Phase 3 (Analyst agent) — document the limitation. Do not build optimization logic on noisy open data.

---

### Pitfall 12: APScheduler Threading Conflicts with asyncio

**What goes wrong:** APScheduler's default BackgroundScheduler is thread-based. Scheduling async functions from a thread-based scheduler causes RuntimeError or silent failures.

**Prevention:** Use AsyncIOScheduler running inside the same event loop. Alternatively, have the scheduler push tasks onto an asyncio.Queue that async workers consume.

**Phase mapping:** Phase 2 (Outreach agent / follow-up queue) — choose AsyncIOScheduler from the start.

---

### Pitfall 13: Fernet Key Derivation Breaking Config on Machine Migration

**What goes wrong:** Deriving the Fernet key from hardware identifiers alone makes the config permanently unreadable when the user migrates machines or reinstalls macOS.

**Prevention:** Derive the key from a user-supplied passphrase plus a stored salt. Salt is stored unencrypted; passphrase is entered by user. On new machine: re-enter passphrase, config is readable.

**Phase mapping:** Phase 1 (Setup wizard / config system) — design key derivation before storing any real credentials.

---

### Pitfall 14: SQLModel + Alembic Field Addition Silently Missing in Database

**What goes wrong:** Adding a field to a SQLModel class does not automatically add the column to SQLite. Without a corresponding Alembic migration, OperationalError at runtime.

**Prevention:** Run alembic upgrade head as first operation in CLI startup. Add a startup check that verifies database schema version matches current migration head. Treat Alembic migrations as mandatory for any model change.

**Phase mapping:** Phase 1 (Data Layer) — establish Alembic discipline from the first table.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| LLMClient abstraction | Tool-use validation missing, silent data corruption | Validate every tool response against Pydantic schema before returning |
| Setup wizard | No dedicated domain warning, primary Gmail ban | Hard-block sends without confirmed dedicated domain setup |
| Setup wizard | Machine-change breaks Fernet key, unreadable config | Passphrase plus salt design from the start |
| UserProfile extraction | Multi-column PDF produces garbled text | Validate extraction output; offer plain-text paste fallback |
| YC venue scraping | YC is React SPA, httpx returns no data | Check for YC public API first; flag 0-result scrapes immediately |
| Research agent | Context window overflow with Ollama models | Token budget plus max 5 tool calls per lead |
| Outreach agent | Gmail SMTP sends get account suspended | Rate limiter, per-day cap, bounce tracking, dedicated domain only |
| Outreach agent | SPF/DKIM/DMARC missing, 0 deliverability | DNS validation in setup wizard before first send |
| Outreach agent | CAN-SPAM footer missing, legal exposure | Writer injects footer; setup wizard collects physical address |
| Outreach agent | APScheduler thread/async mismatch | Use AsyncIOScheduler exclusively |
| Analyst agent | Open pixel data misleading due to Gmail proxy and Apple MPP | Document limitation; rely on reply rate as primary signal |
| Data Layer | SQLite plus async workers, database locked errors | Use aiosqlite engine plus WAL mode from day one |
| Architecture | Event bus plus 7 agents creates circular dependencies | Enforce strict DAG; skip event bus for v1 |
| Architecture | Plugin system before core pipeline works, wrong abstraction | No abstraction until 2 concrete implementations exist |

---

## Sources

Web access was unavailable during this research session. All findings are based on training data through August 2025.

| Domain | Confidence | Notes |
|--------|-----------|-------|
| Gmail SMTP limits and suspension behavior | MEDIUM | Verify current numbers at support.google.com/mail/answer/22839 |
| Email deliverability (SPF/DKIM/DMARC) | HIGH | Stable technical standards; 2024 Google policy is documented |
| Ollama tool-use reliability by model | MEDIUM | Rapidly evolving; verify at ollama.com/search?c=tools |
| SQLite + asyncio patterns | HIGH | Stable Python ecosystem behavior |
| CAN-SPAM requirements | HIGH | US federal law; not recently changed |
| GDPR cold email rules | MEDIUM | Enforcement guidance evolves; consult a lawyer for distribution |
| APScheduler asyncio integration | HIGH | Documented library behavior |
| PyMuPDF multi-column extraction limitation | HIGH | Documented known limitation |
| Web scraping anti-bot detection patterns | HIGH | Well-documented |

**Recommended verification before Phase 1:**
- Gmail SMTP limits: https://support.google.com/mail/answer/22839
- Google bulk sender requirements: https://support.google.com/mail/answer/81126
- Ollama tool-support models: https://ollama.com/search?c=tools
- YC public API availability: https://api.ycombinator.com
