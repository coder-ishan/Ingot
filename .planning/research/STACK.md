# Technology Stack

**Project:** INGOT — INtelligent Generation & Outreach Tool
**Researched:** 2026-02-25
**Note:** Web access and Context7 were unavailable during this research session. All findings are based on training data (cutoff August 2025). Version numbers should be verified against PyPI before pinning.

---

## Recommended Stack

### Agent Framework

**Recommendation: PydanticAI**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pydantic-ai | ~0.0.x (verify on PyPI) | Agent orchestration framework | Type-safe agents, native multi-model support (Anthropic, OpenAI, Ollama via OpenAI-compatible), structured output via Pydantic models, dependency injection pattern fits per-agent model config |

**Rationale:** PydanticAI (by the Pydantic team) was purpose-built for production agent development. It natively supports Claude, OpenAI, and any OpenAI-compatible API (Ollama at localhost:11434) through a unified model abstraction. Its dependency injection system maps cleanly to INGOT's per-agent LLM config requirement. Structured output via Pydantic models means IntelBrief, UserProfile, and ValueProp are typed all the way through the agent chain without manual parsing.

LangGraph suits complex graph-based state machines; INGOT's pipeline is a directed DAG (Orchestrator -> Scout -> Research -> Matcher -> Writer -> Outreach -> Analyst), not an arbitrary graph. PydanticAI is lighter and more Pythonic for this shape. Custom BaseAgent means implementing tool-use, streaming, retry, and structured output from scratch — weeks of work PydanticAI gives for free.

**Confidence: MEDIUM** — Released late 2024, rapid adoption by August 2025. Version number needs PyPI verification.

**What NOT to use:**
- LangChain: abstraction leakage, poor async, actively avoided by production teams in 2025
- LangGraph: graph model overkill for a linear 7-agent pipeline
- AutoGen: heavier dependency footprint, suited to multi-agent debate patterns

---

### LLM Client Abstraction

**Recommendation: LiteLLM**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| litellm | ~1.x (verify on PyPI) | Unified LLM client | Single `litellm.completion()` routes to Claude, OpenAI, Ollama, LM Studio, any OpenAI-compatible API; handles auth, retry, rate limits |

**Rationale:** `model="ollama/llama3"` for Ollama, `model="claude-3-5-sonnet-20241022"` for Claude, `model="gpt-4o"` for OpenAI — same call, same interface. This is exactly the single LLMClient abstraction INGOT requires. Eliminates three separate SDK codepaths.

**Confidence: HIGH** — De facto multi-LLM abstraction in the Python ecosystem since 2023.

---

### CLI Framework

**Recommendation: Typer + Rich**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| typer | ~0.12.x | CLI argument parsing, command groups | Built on Click, type-annotated, command groups map to INGOT's domains (agents, data, mail, run, config) |
| rich | ~13.x | Terminal output (tables, panels, progress) | Standard for "Claude Code style" terminal output; Live, Console, Panel, Table, Progress primitives |
| rich-click | ~1.x | Rich-styled --help pages | Makes help output readable and styled |

**Rationale:** INGOT's command taxonomy (agents list/logs/inspect, run scout/research, mail pending/approve) maps directly to Typer command groups. Rich's `Live` context manager handles streaming agent output. The Typer+Rich pairing is the industry standard for production Python CLIs in 2025.

**Confidence: HIGH** — Both are mature and stable.

**What NOT to use:** argparse (no command groups), Click alone (more boilerplate than Typer).

---

### TUI Framework

**Recommendation: Textual**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| textual | ~0.x (verify on PyPI) | Interactive TUI — dashboard, lead review, email editing | Dominant Python TUI framework; CSS-based layout, reactive widgets, async-native, same author as Rich |

**Rationale:** PROJECT.md requirements map 1:1 to Textual widgets: leads table (DataTable), email review panel (Markdown + TextArea), activity feed (Log widget), settings screen (Input + Select). Keyboard shortcuts (e/a/r/g) are native to Textual's key binding system. No other Python TUI framework in 2025 is production-ready at this level.

**Confidence: HIGH** — Mature and actively maintained.

**What NOT to use:** curses (extremely low-level), urwid (not async-native), blessed (same limitations as urwid).

---

### Email Libraries

**Recommendation: aiosmtplib + aioimaplib**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| aiosmtplib | ~3.x | Async SMTP sending | Native asyncio — non-blocking sends in async agent loop; Gmail port 587 STARTTLS |
| aioimaplib | ~1.x | Async IMAP polling | Native asyncio — Outreach agent polls replies without blocking; Gmail port 993 SSL |
| email (stdlib) | N/A | Message construction | MIMEText/MIMEMultipart — stdlib sufficient |

**Rationale:** INGOT is async throughout. Synchronous smtplib/imaplib inside asyncio requires `run_in_executor` workarounds. aiosmtplib and aioimaplib are async-native drop-ins. Gmail auth via App Passwords (no OAuth2 GCP project required for a personal tool).

**Confidence: MEDIUM** — aiosmtplib well-known; aioimaplib less prominent. Verify maintenance status on PyPI.

**What NOT to use:** smtplib (synchronous, blocks event loop), Gmail API (requires OAuth2 + GCP project, too much friction).

---

### Web Scraping

**Recommendation: httpx + BeautifulSoup4 + optional Playwright**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | ~0.27.x | Async HTTP client | Async-native, HTTP/2, connection pooling; PROJECT.md default |
| beautifulsoup4 | ~4.12.x | HTML parsing | Simple, sufficient for YC/static pages |
| lxml | ~5.x | Fast BS4 parser backend | 3-10x faster than html.parser for large pages |
| playwright | ~1.4x | Browser automation (opt-in) | JS-heavy pages; `pip install outreach-agent[browser]` |

**Rationale:** httpx + asyncio.gather handles parallel venue scraping in Scout agent efficiently. lxml is a drop-in performance upgrade for BS4 with no API change. Playwright is opt-in via extras to minimize base install footprint — most scraping (YC is static) doesn't need a browser.

**Confidence: HIGH** — All well-established and stable.

**What NOT to use:** requests (synchronous), Selenium (heavier than Playwright), scrapy (full-framework overkill for 1-2 venues).

---

### Database

**Recommendation: SQLModel + SQLite + Alembic**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sqlmodel | ~0.0.x (verify on PyPI) | ORM (SQLAlchemy + Pydantic in one class) | Single class = DB table + Pydantic validation schema; no duplicate model definitions |
| aiosqlite | ~0.20.x | Async SQLite driver | Required for async SQLAlchemy engine with SQLite |
| alembic | ~1.13.x | Schema migrations | Industry standard for SQLAlchemy-based projects |

**Rationale:** SQLModel (by the FastAPI/Pydantic author) is the cleanest ORM when Pydantic is already in the stack. INGOT's models (Lead, IntelBrief, Email, Campaign, AgentLog, Venue) only need to be defined once. SQLite is correct for a single-user local tool — no server, no connection strings. Alembic handles schema changes across versions.

**Confidence: HIGH** — All three mature and well-documented.

**What NOT to use:** PostgreSQL (requires server for a local tool), Tortoise ORM (less ecosystem), raw sqlite3 (no migration tooling).

---

### Resume Parsing

**Recommendation: PyMuPDF + python-docx**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pymupdf | ~1.24.x | PDF text extraction | Fastest, most accurate Python PDF parser; imported as `fitz`; handles multi-column resumes |
| python-docx | ~1.1.x | DOCX parsing | Standard library for Word documents |

**Rationale:** PROJECT.md specifies both. PyMuPDF is significantly better than pdfminer or pypdf for resume text extraction accuracy. After extraction, raw text goes to an LLM with a structured extraction prompt to produce a typed UserProfile (Pydantic model). No NLP library needed — LLM handles semantic extraction.

**Confidence: HIGH** — Both well-established.

**What NOT to use:** pdfplumber (slower for general text), pypdf/PyPDF2 (less accurate), pdfminer (more code, worse results).

---

### Encryption

**Recommendation: cryptography (Fernet)**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| cryptography | ~42.x | Fernet symmetric encryption for config.json secrets | AES-128-CBC + HMAC-SHA256; authenticated encryption; PROJECT.md requirement |

**Key derivation pattern:**
