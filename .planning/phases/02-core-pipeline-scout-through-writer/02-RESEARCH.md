# Phase 2: Core Pipeline (Scout through Writer) - Research

**Researched:** 2026-02-26
**Domain:** Resume parsing, YC lead discovery, multi-agent pipeline, Rich CLI review queue
**Confidence:** HIGH (stack verified against installed venv + Context7 + official sources)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Review Queue UX**
- Entry point: Show a list view table first (lead name, company, status: pending/approved/rejected). User picks which lead to deep-dive.
- Navigation: One lead at a time when deep-diving — present the full draft set (subject line variants, body, Day 3 + Day 7 follow-ups) for that lead, then prompt for action.
- Inline editing: Use Rich text input (no external editor dependency). User re-types or pastes revised draft in the terminal.
- Regeneration: Silent re-run — writer re-generates with same MCQ answers + different seed. No additional prompts before regenerating.

**MCQ Writer Flow**
- MCQ is optional: If the user skips the MCQ step, the writer generates using IntelBrief + match data alone (AI defaults). No forced interaction.
- When MCQ is used, question types: Personalization hooks (what genuinely interests you about this company, referencing IntelBrief specifics) and tone/intent (informational interview vs. direct job ask vs. connection request).
- Question generation: Dynamically generated per lead from the IntelBrief — questions reference specific company context (e.g., recent funding, product pivot, tech stack noted). Not a fixed template.
- Email length/tone adapts by recipient type:
  - HR: slightly longer, highlights credentials, relevant experience prominently
  - CTO/CEO: shorter and more direct, strong hook, minimal credentials, clear ask
  - Default to shorter and direct if recipient type is unknown

**Lead Sourcing and Filtering**
- Targeting priority: Companies whose tech stack or domain overlaps with the user's resume skills. Stack/domain match is the primary relevance signal.
- Leads per run: 10-20 leads surfaced by default.
- Initial scoring formula: Build a documented, weighted multi-factor formula. Factors and example weights (planner to finalize and document in code):
  - Stack/domain match vs. resume skills: ~40%
  - Company stage (seed/Series A preferred for impact): ~25%
  - Job listing keyword match (if available): ~20%
  - Company description semantic similarity to resume: ~15%
  - Formula weights must be documented in code and in a planning note so they can be tuned.
- Deduplication: By contact email, case-insensitive. If a lead's email already exists in SQLite (any status), skip it on subsequent runs.

### Claude's Discretion
- Exact Rich component choices (Panel, Table, Prompt styles) within the list view and deep-dive UX
- Exact scoring formula weights (guided by the ~% ranges above, but planner can adjust based on research)
- Checkpoint/resume implementation details for the Orchestrator
- CAN-SPAM footer exact content
- Subject line generation strategy (both variants)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROFILE-01 | Setup wizard prompts for resume upload (PDF or DOCX) | questionary 2.1.1 installed; file path prompt type available |
| PROFILE-02 | PDF parsing via PyMuPDF (fitz) with multi-column awareness | PyMuPDF `column_boxes` utility + `get_text(clip=rect, sort=True)` per column |
| PROFILE-03 | DOCX parsing via python-docx | `Document.paragraphs`, `Document.tables`, `iter_inner_content()` |
| PROFILE-04 | Plain-text fallback if parsing fails (user copy-pastes text) | questionary `text()` prompt; captured as string |
| PROFILE-05 | LLM-powered structured extraction to UserProfile schema | PydanticAI `output_type=UserProfile` on extraction agent |
| PROFILE-06 | UserProfile contains: name, headline, skills[], experience[], education[], projects[], github_url, linkedin_url, resume_raw_text | SQLModel table with JSON fields for arrays |
| PROFILE-07 | UserProfile persisted to SQLite (one active profile per user, versioning later) | SQLModel `AsyncSession` + `upsert` pattern |
| PROFILE-08 | Matcher and Writer agents load UserProfile on every run | Injected via PydanticAI `deps_type` dataclass |
| PROFILE-09 | Resume validation: reject if <10% fields extracted (user retries with raw text) | Post-extraction Pydantic validator counts populated fields |
| SCOUT-01 | Scout agent discovers leads from venues in parallel | `asyncio.gather` across venues (YC only in v1) |
| SCOUT-02 | YC venue as primary discovery source (direct implementation) | yc-oss GitHub API is the correct approach — see YC Scout section |
| SCOUT-03 | YC scraping strategy: check api.ycombinator.com first, fallback to httpx + BS4 | `api.ycombinator.com` is not a stable official endpoint; use yc-oss JSON API as primary |
| SCOUT-04 | YC scraping output validation: reject if >20% fields None | Pydantic validator on `Lead` schema with `None` field count |
| SCOUT-05 | User-agent rotation and request delays for YC scraping | httpx `headers={'User-Agent': ...}` + `asyncio.sleep()` between requests |
| SCOUT-06 | Lead deduplication by email address (case-insensitive) | SQLite `LOWER(email)` unique constraint + pre-insert query |
| SCOUT-07 | Initial lead scoring (confidence in contact info, company fit signals) | Weighted formula in `scorer.py` with documented weights |
| SCOUT-08 | Lead model persisted with status (discovered/researching/matched/drafted/sent/replied) | SQLModel `Lead` table with `status` enum |
| RESEARCH-01 | Phase 1 Research: company name lookup, role parsing, public LinkedIn/web presence | LLM extraction from yc-oss company data + httpx fetch of company website |
| RESEARCH-02 | Phase 1 Research: lightweight company signals (funding status, size, growth signals) | yc-oss fields: `batch`, `stage`, `team_size`, `tags`, `one_liner` |
| RESEARCH-03 | Phase 1 Research output: IntelBrief schema with company_name, company_signals, person_name, person_role, company_website | PydanticAI `output_type=IntelBriefPhase1` Pydantic model |
| RESEARCH-04 | User approval gate after Phase 1 (accept/reject/defer lead) | questionary `select()` prompt with three choices |
| RESEARCH-05 | Phase 2 Research: contact discovery, personal background research, talking points synthesis | httpx fetch of LinkedIn public profile URL; LLM synthesis |
| RESEARCH-06 | Phase 2 Research: LinkedIn public profile analysis, GitHub profile analysis | httpx GET on public profile URLs; no auth required for public pages |
| RESEARCH-07 | Phase 2 Research: three talking points per lead | PydanticAI agent with `output_type=IntelBriefFull` including `talking_points: list[str]` (len 3) |
| RESEARCH-08 | IntelBrief output: full schema with person_background, talking_points[], company_product_description | Pydantic model with field validators |
| RESEARCH-09 | Token budget tracking within Research agent | PydanticAI `usage_limits=UsageLimits(...)` parameter on `agent.run()` |
| RESEARCH-10 | IntelBrief persisted to SQLite, linked to Lead | SQLModel FK `lead_id` on `IntelBrief` table |
| MATCH-01 | Matcher agent cross-references UserProfile against IntelBrief | PydanticAI agent; deps inject UserProfile + IntelBrief |
| MATCH-02 | Match score calculation (0-100) based on skills overlap, experience relevance, seniority fit, company size fit | Weighted formula; skills overlap via set intersection + TF-IDF cosine for semantic |
| MATCH-03 | Explicit value proposition generation | PydanticAI `output_type=MatchResult` with `value_proposition: str` field |
| MATCH-04 | Match output: match_score, value_proposition, confidence_level | SQLModel `Match` table |
| MATCH-05 | Match stored in Lead record, linked to IntelBrief and UserProfile | SQLModel FK relationships |
| WRITER-01 | Interactive MCQ flow: 2-3 personalized questions per lead | questionary `text()` + `select()` prompts; skippable via Prompt.ask with empty default |
| WRITER-02 | MCQ questions reference IntelBrief and talking points (not generic) | LLM-generated questions using IntelBrief as context; not hardcoded |
| WRITER-03 | Email generation receives: Lead + IntelBrief + UserProfile + ValueProp + MCQ answers | PydanticAI deps dataclass contains all inputs |
| WRITER-04 | Tone adaptation by recipient type: HR / CTO/Engineering / CEO/Founder | System prompt branching on `recipient_type` field from Lead |
| WRITER-05 | Email body is personalized per recipient (not template-based) | LLM generation with strict system prompt; no f-string templates |
| WRITER-06 | Flexible email length per recipient type | System prompt instructions only; no hard word count enforcement |
| WRITER-07 | Email includes: specific company/role reference + relevant experience + one talking point + clear CTA | PydanticAI output validator checks for company name mention |
| WRITER-08 | Two subject line variants for A/B testing | `output_type=EmailDraft` with `subject_a: str`, `subject_b: str` fields |
| WRITER-09 | Follow-up sequence: Day 3 and Day 7 drafts | Same Writer agent called twice with `day=3` / `day=7` context |
| WRITER-10 | CAN-SPAM compliant footer injection | Post-generation footer append; footer string from setup wizard config (physical address + unsubscribe link) |
| WRITER-11 | Email draft persisted with all variants | SQLModel `Email` + `FollowUp` tables |
| WRITER-12 | Review-before-send queue: approve, edit inline, reject, regenerate | Rich `Prompt.ask()` + `console.input()` loop; Table for list view, Panel for deep-dive |
| WRITER-13 | Reject/regenerate flow triggers new MCQ if user requests different angle | Boolean flag `retrigger_mcq` in regenerate path |
| AGENT-04 | Orchestrator routes tasks, maintains campaign state, handles approval gates, checkpoint/resume | Lead status field as checkpoint; re-query on resume |
| TEST-P2-01 through TEST-P2-16 | Full Phase 2 test suite | PydanticAI `TestModel` + `Agent.override`; pytest-asyncio; fixture leads |
</phase_requirements>

---

## Summary

Phase 2 builds the entire pipeline from resume ingestion through email drafts in a review queue. The architecture is a sequence of five PydanticAI agents (Profile, Scout, Research, Matcher, Writer) coordinated by the Orchestrator, each with dependency-injected services and Pydantic-validated outputs persisted to SQLite. The "approval gate" pattern recurs multiple times: after Phase 1 Research (accept/reject/defer per lead), and in the Review Queue (approve/edit/reject/regenerate per draft).

The largest architectural risk is YC data access. `api.ycombinator.com` is not a stable official endpoint. The correct primary source is the community-maintained `yc-oss` GitHub Pages API at `https://yc-oss.github.io/api/` which serves daily-refreshed JSON from YC's Algolia index — no scraping required and no JavaScript rendering. BeautifulSoup4 is still needed as a fallback for fetching individual company pages. This completely eliminates the Playwright risk called out in STATE.md.

The second large topic is PydanticAI API stability. The library has reached version 1.63.0 (released 2026-02-23) with PyPI status "Production/Stable" — the concern documented in STATE.md (`verify 0.0.x API stability`) is resolved. The API is stable. The `Agent`, `RunContext`, `deps_type`, `output_type`, `TestModel`, and `Agent.override` patterns are all confirmed in official docs.

**Primary recommendation:** Use yc-oss JSON API as Scout's primary data source (eliminates scraping), PydanticAI 1.63.0 for all agents (stable), questionary 2.1.1 for MCQ + approval gates (already installed), and Rich 14.3.3 Table/Panel/Prompt for the review queue (already installed).

---

## Standard Stack

### Core (all Phase 2 specific — not in Phase 1)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | >=1.24 (latest) | PDF text extraction with multi-column support | Official `column_boxes` utility handles resume layouts; no external deps |
| python-docx | >=1.1 | DOCX paragraph/table extraction | Standard for Word doc reading; `iter_inner_content()` preserves order |
| beautifulsoup4 | >=4.12 | HTML parsing for company website fallback scraping | Locked in SCOUT-03; simple, no JS rendering needed for static pages |
| scikit-learn | >=1.5 | TF-IDF vectorization + cosine similarity for semantic lead scoring | Standard NLP toolkit; `TfidfVectorizer` + `cosine_similarity` for MATCH-02 |

### Already Installed (verified in venv)

| Library | Installed Version | Purpose |
|---------|------------------|---------|
| pydantic-ai | 1.63.0 | Agent framework for all 5 agents |
| questionary | 2.1.1 | MCQ prompts, approval gates, inline text input |
| rich | 14.3.3 | Table list view, Panel deep-dive, Prompt.ask review |
| httpx | 0.28.1 | Async HTTP for yc-oss API fetch + company website scraping |
| sqlmodel | 0.0.37 | ORM for all Lead/IntelBrief/Match/Email/FollowUp persistence |
| aiosqlite | 0.22.1 | Async SQLite driver |
| litellm | 1.81.15 | LLMClient multi-backend routing (Phase 1) |
| tenacity | 9.1.4 | Retry logic (Phase 1) |
| pytest | 9.0.2 | Test runner |
| pytest-asyncio | 1.3.0 | Async test support |
| pytest-cov | 7.0.0 | Coverage reporting |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lxml | latest | Fast HTML/XML parser backend for BS4 | When html.parser is too slow; install alongside bs4 |
| scikit-learn | >=1.5 | TF-IDF + cosine similarity for semantic scoring (MATCH-02, SCOUT-07) | Semantic similarity component of scoring formula |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| yc-oss JSON API | YC Algolia API directly | yc-oss is simpler (static JSON, no API key) and refreshed daily |
| yc-oss JSON API | httpx + BS4 scraping ycombinator.com | YC site uses infinite scroll + dynamic JS; requires Playwright if scraping directly |
| PyMuPDF | pypdf | PyMuPDF has native multi-column support via `column_boxes`; pypdf does not |
| python-docx | mammoth | python-docx gives structured access to paragraphs/tables/runs; mammoth converts to HTML (unnecessary for text extraction) |
| scikit-learn TF-IDF | sentence-transformers | sentence-transformers gives better semantic similarity but requires 400MB+ model download; TF-IDF is zero-dependency and sufficient for keyword/tech-stack overlap |
| questionary | Rich Prompt only | questionary has richer select/checkbox UIs; Rich Prompt is sufficient for simple text/choice prompts but questionary is already installed |

**Installation (missing packages only):**
```bash
pip install PyMuPDF python-docx beautifulsoup4 lxml scikit-learn
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/ingot/
├── agents/
│   ├── __init__.py
│   ├── profile.py          # Resume parsing + UserProfile extraction
│   ├── scout.py            # YC lead discovery + scoring + dedup
│   ├── research.py         # Two-phase IntelBrief generation
│   ├── matcher.py          # Match score + value proposition
│   ├── writer.py           # MCQ flow + email generation
│   └── orchestrator.py     # Pipeline coordinator (AGENT-04)
├── venues/
│   └── yc.py               # YC-specific fetch logic (not a plugin yet)
├── models/
│   └── schemas.py          # Pydantic output schemas (UserProfile, IntelBrief, etc.)
├── scoring/
│   └── scorer.py           # Documented weighted scoring formula
├── review/
│   └── queue.py            # Rich CLI review queue (Table + Panel + Prompt)
└── cli/
    └── pipeline.py         # Typer commands that invoke Orchestrator
```

### Pattern 1: PydanticAI Agent with Dependency Injection

Every Phase 2 agent follows this pattern — no agent imports another agent, all external services injected via deps.

```python
# Source: https://ai.pydantic.dev/dependencies
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
import httpx

@dataclass
class ResearchDeps:
    http_client: httpx.AsyncClient
    db_session: AsyncSession
    llm_client: LLMClient  # from Phase 1

class IntelBriefPhase1(BaseModel):
    company_name: str
    company_signals: list[str]
    person_name: str
    person_role: str
    company_website: str

research_agent = Agent(
    'anthropic:claude-3-5-haiku-latest',  # or from config
    deps_type=ResearchDeps,
    output_type=IntelBriefPhase1,
    system_prompt="You are a research agent..."
)

@research_agent.tool
async def fetch_company_page(ctx: RunContext[ResearchDeps], url: str) -> str:
    response = await ctx.deps.http_client.get(url)
    return response.text[:5000]  # token budget guard
```

### Pattern 2: YC Scout via yc-oss JSON API

**Key finding:** `api.ycombinator.com` is not a stable public endpoint. The correct source is `https://yc-oss.github.io/api/` — a community-maintained, daily-refreshed JSON API built from YC's Algolia index.

```python
# Source: https://github.com/yc-oss/api (verified 2026-02-26)
# Available endpoints:
# - https://yc-oss.github.io/api/companies/all.json  (all ~5,690 launched companies)
# - https://yc-oss.github.io/api/batches/winter-2025.json  (by batch)
# - https://yc-oss.github.io/api/industries/b2b.json  (by industry)

# Company record fields (verified by fetching all.json):
# id, name, slug, former_names[], small_logo_thumb_url, website, all_locations,
# long_description, one_liner, team_size, industry, subindustry, launched_at,
# tags[], tags_highlighted[], top_company, isHiring, nonprofit, batch, status,
# industries[], regions[], stage, app_video_public, demo_day_video_public,
# app_answers, question_answers, url, api

async def fetch_yc_companies(
    http_client: httpx.AsyncClient,
    batch: str | None = None
) -> list[dict]:
    if batch:
        url = f"https://yc-oss.github.io/api/batches/{batch}.json"
    else:
        url = "https://yc-oss.github.io/api/companies/all.json"
    response = await http_client.get(url)
    response.raise_for_status()
    return response.json()
```

**Fields directly useful for Scout scoring:**
- `tags` — technology/domain tags (stack match signal)
- `batch` — determines company age/stage context
- `stage` — funding stage (seed/series A/etc.)
- `team_size` — company size signal
- `one_liner` + `long_description` — semantic similarity vs. resume
- `isHiring` — job listing keyword match signal proxy
- `industries` — domain match signal

### Pattern 3: Weighted Scoring Formula (Documented in Code)

The formula must be documented both in code and in a planning note. Use a `ScoringWeights` dataclass or named constants:

```python
# src/ingot/scoring/scorer.py
# WEIGHTS ARE INTENTIONALLY VISIBLE — tune via config or planning note
from dataclasses import dataclass

@dataclass
class ScoringWeights:
    """
    Weighted lead scoring formula.
    Sum must equal 1.0.
    Tune by editing this dataclass or via config override.

    Decision rationale (from 02-CONTEXT.md):
    - Stack/domain match: ~40% — primary signal for relevance
    - Company stage: ~25% — seed/Series A preferred for outsized impact
    - Job keyword match: ~20% — strong intent signal when available
    - Semantic similarity: ~15% — catches description overlap missed by keyword match
    """
    stack_domain_match: float = 0.40
    company_stage: float = 0.25
    job_keyword_match: float = 0.20
    semantic_similarity: float = 0.15

def score_lead(company: dict, user_profile: UserProfile, weights: ScoringWeights) -> float:
    stack_score = _stack_overlap(company["tags"], user_profile.skills)
    stage_score = _stage_preference(company.get("stage", ""))
    keyword_score = _keyword_match(company.get("one_liner", ""), user_profile.skills)
    semantic_score = _cosine_similarity(
        company.get("long_description", ""),
        user_profile.resume_raw_text
    )
    return (
        weights.stack_domain_match * stack_score +
        weights.company_stage * stage_score +
        weights.job_keyword_match * keyword_score +
        weights.semantic_similarity * semantic_score
    )
```

### Pattern 4: Multi-Phase Research with Approval Gate

```python
# Phase 1: lightweight, runs for all leads
phase1_brief = await research_agent_phase1.run(
    f"Research {lead.company_name}",
    deps=deps,
    usage_limits=UsageLimits(total_tokens=2000)  # RESEARCH-09
)

# Approval gate (RESEARCH-04)
action = questionary.select(
    f"Lead: {lead.person_name} @ {lead.company_name}",
    choices=["accept", "reject", "defer"]
).ask()

if action == "accept":
    # Phase 2: expensive, only for approved leads
    phase2_brief = await research_agent_phase2.run(...)
```

### Pattern 5: Rich Review Queue — List View Then Deep Dive

```python
# Source: https://rich.readthedocs.io/en/stable/table.html
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

def show_lead_list(leads: list[Lead]) -> str:
    table = Table(title="Email Review Queue", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="white")
    table.add_column("Company", style="magenta")
    table.add_column("Score", justify="right", style="yellow")
    table.add_column("Status", style="green")
    for i, lead in enumerate(leads, 1):
        status_color = {"pending": "yellow", "approved": "green", "rejected": "red"}.get(lead.status, "white")
        table.add_row(str(i), lead.person_name, lead.company_name,
                      str(lead.match_score), f"[{status_color}]{lead.status}[/]")
    console.print(table)
    return Prompt.ask("Enter lead number to review (or 'q' to quit)")

def show_draft_deepdive(lead: Lead, email: Email) -> str:
    console.print(Panel(
        f"[bold]Subject A:[/] {email.subject_a}\n"
        f"[bold]Subject B:[/] {email.subject_b}\n\n"
        f"{email.body}\n\n"
        f"[dim]--- Day 3 Follow-up ---[/dim]\n{email.followup_day3}\n\n"
        f"[dim]--- Day 7 Follow-up ---[/dim]\n{email.followup_day7}",
        title=f"{lead.person_name} @ {lead.company_name}",
        border_style="blue"
    ))
    return Prompt.ask("Action", choices=["approve", "edit", "reject", "regenerate"])
```

### Pattern 6: Checkpoint/Resume via Lead Status Field

The Orchestrator checkpoints by persisting `Lead.status` after every stage transition. On resume, it re-queries for leads at each status and skips already-completed ones:

```python
# Orchestrator checkpoint/resume pattern
async def run_pipeline(campaign_id: int, db: AsyncSession):
    # Resume-safe: each stage filters by status
    pending_leads = await db.exec(select(Lead).where(Lead.status == "discovered"))
    for lead in pending_leads:
        await research_phase1(lead, db)  # transitions to "researching"

    approved_leads = await db.exec(select(Lead).where(Lead.status == "approved"))
    for lead in approved_leads:
        await match(lead, db)  # transitions to "matched"

    matched_leads = await db.exec(select(Lead).where(Lead.status == "matched"))
    for lead in matched_leads:
        await write(lead, db)  # transitions to "drafted"
```

### Pattern 7: MCQ Flow (Optional, Skippable)

```python
# questionary 2.1.1 — text() and select() prompts
import questionary

def run_mcq(intel_brief: IntelBrief) -> dict[str, str] | None:
    skip = questionary.confirm(
        "Run personalization questions for this lead? (recommended)",
        default=True
    ).ask()
    if not skip:
        return None  # Writer uses AI defaults from IntelBrief alone

    # LLM generates 2-3 questions from IntelBrief (not hardcoded)
    questions = generate_mcq_questions(intel_brief)  # returns list[str]
    answers = {}
    for q in questions:
        answers[q] = questionary.text(q).ask()
    return answers
```

### Anti-Patterns to Avoid

- **Scraping ycombinator.com directly:** The site uses infinite scroll + Algolia/JS rendering. Use `yc-oss.github.io/api/` JSON instead.
- **Hardcoded MCQ questions:** Questions must be LLM-generated from IntelBrief. A fixed template defeats the personalization goal.
- **Multi-column PDF as plain `get_text()`:** `page.get_text()` without column detection produces interleaved text on multi-column resumes. Always use `column_boxes()` first, then `get_text(clip=col_rect, sort=True)` per column.
- **Importing one agent from another:** The Orchestrator is the only coordinator. Agents must not know about each other.
- **Swallowing LLM validation errors:** All PydanticAI `output_type` responses are validated at call time. Catch `ValidationError` and surface it with context.
- **Long Orchestrator:** Orchestrator must stay under 250 lines (AGENT-07). All domain logic belongs in agent modules.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-column PDF layout detection | Custom column-detection algorithm | `pymupdf.column_boxes()` from PyMuPDF-Utilities | PyMuPDF already solves this; custom implementation will misfire on headers/footers |
| Text similarity for lead scoring | Bag-of-words string overlap | `sklearn.metrics.pairwise.cosine_similarity` + `TfidfVectorizer` | Handles term weighting, stopwords, and sparse matrix efficiency automatically |
| Structured LLM output parsing | Regex/JSON.loads on raw model output | PydanticAI `output_type=PydanticModel` | Automatic retry on schema violation; validated response guaranteed |
| Terminal interactive prompts | Custom `input()` loop with validation | `questionary.select()` / `questionary.text()` | Handles arrow keys, validation loop, styling; questionary 2.1.1 already installed |
| Token budget enforcement | Manual `len(text.split())` counting | PydanticAI `UsageLimits(total_tokens=N)` | Exact token counts from model response; not word counts |
| Lead deduplication logic | Hash map in memory | SQLite `LOWER(email)` constraint + pre-insert SELECT | Persisted across runs; handles case-insensitivity natively |

**Key insight:** Every "clever" custom solution in this domain has a known edge case that the standard library already handles. The PDF multi-column problem alone has a [documented utility](https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/text-extraction/multi_column.py) in the official PyMuPDF repo.

---

## Common Pitfalls

### Pitfall 1: YC Site Scraping via httpx + BS4 Fails Silently

**What goes wrong:** `httpx.get("https://www.ycombinator.com/companies")` returns HTML with no company data — the companies are loaded by Algolia/JavaScript after initial render.
**Why it happens:** YC's company directory uses client-side rendering via infinite scroll + Algolia search.
**How to avoid:** Use `yc-oss.github.io/api/companies/all.json` as the primary source. It contains 5,690+ launched companies with all needed fields. Only fall back to httpx + BS4 for fetching individual *company websites* (not YC's directory).
**Warning signs:** BS4 parse of YC returns a `<div id="__next">` with no company content.

### Pitfall 2: PyMuPDF Extracts Interleaved Multi-Column Text

**What goes wrong:** A two-column resume produces text where column A line 1, column B line 1, column A line 2, column B line 2 are mixed together.
**Why it happens:** `page.get_text(sort=True)` sorts by Y coordinate only — it doesn't understand column boundaries.
**How to avoid:** Import `column_boxes` from PyMuPDF-Utilities; call `column_boxes(page)` to get column `Rect` objects, then call `page.get_text(clip=rect, sort=True)` for each column separately and concatenate.
**Warning signs:** Skills section appears mid-sentence inside an Experience entry.

### Pitfall 3: PydanticAI Agent Hangs on Ollama Tool-Use

**What goes wrong:** Writer agent calls a tool, Ollama model returns malformed JSON for tool parameters, agent enters infinite retry loop.
**Why it happens:** Not all Ollama models support JSON tool-use reliably. The XML fallback from Phase 1 (INFRA-16) must be active.
**How to avoid:** Set `ALLOW_MODEL_REQUESTS=False` in tests (use `TestModel`). In production, ensure LLMClient from Phase 1 is the only model interface — never instantiate models directly in agent files.
**Warning signs:** Agent takes >30s without returning; Ollama logs show repeated malformed JSON.

### Pitfall 4: Lead Scoring Returns All-Zeros for Tech-Stack Match

**What goes wrong:** `tags` field in yc-oss JSON uses values like `"B2B"`, `"SaaS"`, `"Developer Tools"` — not specific technologies. Stack overlap against resume skills (Python, TypeScript, etc.) returns 0 for nearly all companies.
**Why it happens:** yc-oss `tags` are domain/category tags, not technology tags. Tech stack is described in `one_liner` and `long_description` free text.
**How to avoid:** Stack match must extract tech terms from `one_liner` + `long_description` via keyword search (not just `tags` comparison). `tags` are useful for domain match (e.g. "Developer Tools" → dev-focused company). The semantic similarity component (TF-IDF on `long_description`) covers the gap.
**Warning signs:** All leads score 0.0 on the `stack_domain_match` component.

### Pitfall 5: Rich `console.input()` Cannot Be Used Inside `Live` or `Progress` Contexts

**What goes wrong:** Inline edit prompt renders garbled output when called while a `Rich.Live` display is active.
**Why it happens:** Rich's Live display captures stdout; `console.input()` conflicts with the Live rendering loop.
**How to avoid:** Stop any Live display before showing prompts. The review queue should use sequential `console.print()` + `Prompt.ask()` — not a Live display. This is a known Rich limitation (GitHub Discussion #1791).
**Warning signs:** Input cursor appears in wrong position or prompt text overlaps with table output.

### Pitfall 6: CAN-SPAM Violation from Missing Physical Address

**What goes wrong:** Email footer omits physical address; fine up to $51,744 per violating email (2025 FTC rates).
**Why it happens:** Developers add unsubscribe link but forget physical address requirement.
**How to avoid:** Footer template must include all three CAN-SPAM mandatory elements: (1) sender identity, (2) physical postal address or registered PO box, (3) clear unsubscribe mechanism. Collect physical address in setup wizard (WRITER-10). Add a test that checks footer is present in every generated email (TEST-P2-06).
**Warning signs:** Footer string does not contain any of: street, avenue, ave, P.O., suite, city.

### Pitfall 7: Orchestrator Checkpoint Loses State on Exception

**What goes wrong:** Pipeline crashes mid-run; on restart it re-processes leads that were already matched/drafted, generating duplicate emails.
**Why it happens:** Status update happens after the expensive operation, not before.
**How to avoid:** Update Lead status to the *in-progress* state BEFORE beginning the expensive operation, then update to the completed state after. This way, a crash during the operation leaves the lead in "researching" (not "discovered"), and resume logic can detect and retry only incomplete leads.

---

## Code Examples

Verified patterns from official sources:

### PyMuPDF Multi-Column Text Extraction

```python
# Source: https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/text-extraction/multi_column.py
# Source: https://artifex.com/blog/extracting-text-from-multi-column-pages-a-practical-pymupdf-guide
import pymupdf
from pymupdf_utilities_text_extraction import column_boxes  # install separately or copy utility

def extract_pdf_text(path: str) -> str:
    doc = pymupdf.open(path)
    full_text = []
    for page in doc:
        # column_boxes returns list of Rect for each detected column
        # footer_margin=50 excludes page footer noise
        cols = column_boxes(page, footer_margin=50, no_image_text=True)
        if cols:
            for col_rect in cols:
                col_text = page.get_text(clip=col_rect, sort=True)
                full_text.append(col_text)
        else:
            # Single column fallback
            full_text.append(page.get_text(sort=True))
    return "\n".join(full_text)
```

### python-docx Full Text Extraction

```python
# Source: https://context7.com/skelmis/python-docx/llms.txt
from docx import Document

def extract_docx_text(path: str) -> str:
    doc = Document(path)
    parts = []
    # iter_inner_content preserves paragraph/table interleave order
    for item in doc.element.body.iter_inner_content():
        if hasattr(item, 'text'):
            parts.append(item.text)
        else:  # table
            for row in item.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)
```

### PydanticAI Agent with Structured Output

```python
# Source: https://ai.pydantic.dev/output
# Source: https://ai.pydantic.dev/dependencies
from pydantic import BaseModel
from pydantic_ai import Agent
from dataclasses import dataclass

class UserProfile(BaseModel):
    name: str
    headline: str
    skills: list[str]
    experience: list[str]
    education: list[str]
    projects: list[str]
    github_url: str | None
    linkedin_url: str | None
    resume_raw_text: str

@dataclass
class ProfileDeps:
    resume_text: str

profile_agent = Agent(
    'anthropic:claude-3-5-haiku-latest',
    deps_type=ProfileDeps,
    output_type=UserProfile,
    system_prompt=(
        "Extract a structured UserProfile from the resume text provided. "
        "If a field cannot be determined, return null for optional fields. "
        "skills must be specific technologies and tools, not soft skills."
    )
)

async def extract_profile(resume_text: str) -> UserProfile:
    result = await profile_agent.run(
        "Extract profile from this resume",
        deps=ProfileDeps(resume_text=resume_text)
    )
    return result.output  # Guaranteed to be UserProfile by Pydantic
```

### PydanticAI TestModel for Agent Tests

```python
# Source: https://ai.pydantic.dev/testing/
import pytest
from pydantic_ai.models.test import TestModel
from ingot.agents.profile import profile_agent, ProfileDeps

@pytest.fixture
def mock_profile_agent():
    with profile_agent.override(model=TestModel()):
        yield

async def test_profile_extraction(mock_profile_agent):
    result = await profile_agent.run(
        "Extract profile",
        deps=ProfileDeps(resume_text="John Doe\nPython, TypeScript\n...")
    )
    assert result.output.name is not None  # TestModel generates valid schema data
```

### Lead Deduplication via SQLite

```python
# Pattern: check before insert, case-insensitive
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from ingot.db.models import Lead

async def dedup_and_insert(lead_data: dict, session: AsyncSession) -> Lead | None:
    # Case-insensitive email check (SCOUT-06)
    existing = await session.exec(
        select(Lead).where(Lead.person_email.ilike(lead_data["person_email"]))
    )
    if existing.first():
        return None  # Skip duplicate
    lead = Lead(**lead_data)
    session.add(lead)
    await session.commit()
    return lead
```

### YC Companies Fetch with Filtering

```python
# Source: https://github.com/yc-oss/api (verified 2026-02-26)
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_yc_batch(http_client: httpx.AsyncClient, batch: str) -> list[dict]:
    """
    Fetch YC companies for a specific batch from yc-oss GitHub Pages API.
    Batch format: 'winter-2025', 'summer-2024', etc.
    Falls back to all companies if batch not found.
    """
    url = f"https://yc-oss.github.io/api/batches/{batch}.json"
    try:
        resp = await http_client.get(url, headers={"User-Agent": "INGOT/0.1"})
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError:
        # Batch not found — fall back to all companies
        resp = await http_client.get("https://yc-oss.github.io/api/companies/all.json")
        resp.raise_for_status()
        return resp.json()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PydanticAI 0.0.x (unstable) | PydanticAI 1.63.0 (Production/Stable) | Released 2026-02-23 | API is stable; the STATE.md concern about `0.0.x` instability is resolved |
| scrape ycombinator.com with BS4 | yc-oss JSON API (`yc-oss.github.io/api/`) | Established; community-maintained | No JS rendering needed; 5,690+ companies in clean JSON; refreshed daily |
| raw `get_text()` for all PDFs | `column_boxes()` + per-column extraction | PyMuPDF 1.18+ | Correct multi-column reading order; critical for resume layout fidelity |
| agent.run_sync() | agent.run() (async) | PydanticAI redesign | All Phase 2 agents are async; use `await agent.run()` not `run_sync()` |

**Deprecated/outdated:**
- `api.ycombinator.com/v1/companies`: Not a stable official endpoint. Do not use. The `yc-oss` GitHub Pages API is the correct approach.
- `pydantic_ai` 0.0.x `result.data` pattern: In 1.x the output is accessed via `result.output` not `result.data`.

---

## Open Questions

1. **Column boxes utility import path**
   - What we know: PyMuPDF has `column_boxes` documented in PyMuPDF-Utilities GitHub repo
   - What's unclear: Whether `column_boxes` is bundled in the main `pymupdf` package or must be copied from PyMuPDF-Utilities
   - Recommendation: Check `import pymupdf; dir(pymupdf)` after install; if not present, copy `multi_column.py` from PyMuPDF-Utilities into `src/ingot/utils/`

2. **yc-oss API freshness and coverage**
   - What we know: Refreshed daily via GitHub Actions; covers ~5,690 publicly launched companies
   - What's unclear: Whether very recent batches (last 30 days) are present; whether `stage` field is populated for all companies
   - Recommendation: In Plan 02-02, add a validation step that checks `len(companies) > 100` and logs field coverage percentages before scoring

3. **Recipient type detection (HR vs. CTO vs. CEO)**
   - What we know: Writer tone adapts by recipient type; yc-oss data does not include contact person details
   - What's unclear: How Phase 2 Research identifies the specific contact person and their role; yc-oss does not have `person_email` or `person_role` fields
   - Recommendation: Research Phase 2 must include a contact discovery step (httpx fetch of company website + LLM extraction of team/contact page) to identify the best contact person. The `person_role` field in the `Lead` schema is populated during Research Phase 2, not Scout.

4. **scikit-learn binary size**
   - What we know: scikit-learn is ~35MB installed; TF-IDF is lightweight at runtime
   - What's unclear: Whether the project wants to avoid this dependency for the semantic similarity component
   - Recommendation: Include scikit-learn; the 15% semantic similarity weight requires it; the alternative (sentence-transformers) is 400MB+

5. **`questionary` vs. `Rich.Prompt` for MCQ**
   - What we know: Both are installed; questionary has richer `select()` UX with arrow keys; Rich Prompt is simpler
   - What's unclear: Which the user prefers for the MCQ flow
   - Recommendation: Use questionary for the MCQ step (better UX for multi-choice persona/tone selection) and Rich Prompt for the review queue (text input + action choice). Both are already installed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `pytest tests/test_phase2/ -x --no-cov -q` |
| Full suite command | `pytest tests/ --cov=ingot --cov-fail-under=70` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROFILE-02 | PyMuPDF extracts text from single-column PDF | unit | `pytest tests/test_profile.py::test_pdf_single_column -x` | ❌ Wave 0 |
| PROFILE-02 | PyMuPDF extracts text from multi-column PDF in correct order | unit | `pytest tests/test_profile.py::test_pdf_multi_column -x` | ❌ Wave 0 |
| PROFILE-03 | python-docx extracts paragraphs and table text | unit | `pytest tests/test_profile.py::test_docx_extraction -x` | ❌ Wave 0 |
| PROFILE-05 | LLM extraction produces valid UserProfile (TestModel) | unit | `pytest tests/test_profile.py::test_profile_extraction -x` | ❌ Wave 0 |
| PROFILE-09 | Validation rejects profile with <10% fields populated | unit | `pytest tests/test_profile.py::test_profile_validation_rejects_sparse -x` | ❌ Wave 0 |
| SCOUT-03 | YC fetch returns >0 companies from yc-oss API | integration | `pytest tests/test_scout.py::test_yc_fetch -x` | ❌ Wave 0 |
| SCOUT-04 | Lead record rejected if >20% fields None | unit | `pytest tests/test_scout.py::test_lead_validation -x` | ❌ Wave 0 |
| SCOUT-06 | Dedup skips lead with same email (case-insensitive) | unit | `pytest tests/test_scout.py::test_dedup_case_insensitive -x` | ❌ Wave 0 |
| SCOUT-07 | Scoring formula sums to weighted total in [0,1] | unit | `pytest tests/test_scorer.py::test_score_bounds -x` | ❌ Wave 0 |
| SCOUT-07 | Stack-match component returns 0 when no tech overlap | unit | `pytest tests/test_scorer.py::test_stack_match_zero -x` | ❌ Wave 0 |
| RESEARCH-04 | Approval gate accepts accept/reject/defer inputs | unit | `pytest tests/test_research.py::test_approval_gate -x` | ❌ Wave 0 |
| RESEARCH-09 | Token budget exceeded raises error (not silent skip) | unit | `pytest tests/test_research.py::test_token_budget -x` | ❌ Wave 0 |
| MATCH-02 | Match score is in [0, 100] range | unit | `pytest tests/test_matcher.py::test_score_range -x` | ❌ Wave 0 |
| MATCH-03 | Value proposition references company name | unit | `pytest tests/test_matcher.py::test_value_prop_specificity -x` | ❌ Wave 0 |
| WRITER-01 | MCQ returns None when user skips | unit | `pytest tests/test_writer.py::test_mcq_skippable -x` | ❌ Wave 0 |
| WRITER-08 | EmailDraft has non-empty subject_a and subject_b | unit | `pytest tests/test_writer.py::test_subject_variants -x` | ❌ Wave 0 |
| WRITER-10 | CAN-SPAM footer present in all email drafts | unit | `pytest tests/test_writer.py::test_canspam_footer -x` | ❌ Wave 0 |
| AGENT-04 | Orchestrator resume skips leads already at "matched" status | unit | `pytest tests/test_orchestrator.py::test_checkpoint_resume -x` | ❌ Wave 0 |
| TEST-P2-07 | Scout discovers YC leads and dedup works | integration | `pytest tests/integration/test_scout_integration.py -x` | ❌ Wave 0 |
| TEST-P2-08 | Research Phase 1 completes in <5s per lead (mocked HTTP) | integration | `pytest tests/integration/test_research_phase1.py -x` | ❌ Wave 0 |
| TEST-P2-09 | Approval gate transitions lead status correctly | integration | `pytest tests/integration/test_approval_gate.py -x` | ❌ Wave 0 |
| TEST-P2-13 | Full pipeline on 5 fixture leads produces 5 drafts | e2e | `pytest tests/e2e/test_pipeline.py -x` | ❌ Wave 0 |
| TEST-P2-14 | All 10 required draft fields populated | e2e | `pytest tests/e2e/test_pipeline.py::test_all_draft_fields -x` | ❌ Wave 0 |
| TEST-P2-15 | Orchestrator checkpoint/resume preserves state across interruption | regression | `pytest tests/regression/test_checkpoint.py -x` | ❌ Wave 0 |
| TEST-P2-16 | Scout on 100 companies <5s; pipeline on 5 leads <15s | performance | `pytest tests/performance/test_benchmarks.py -x -m benchmark` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_phase2/ -x --no-cov -q`
- **Per wave merge:** `pytest tests/ --cov=ingot --cov-fail-under=70`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All test files are missing — none exist yet. Wave 0 (Plan 02-07) must create:

- [ ] `tests/test_profile.py` — covers PROFILE-02, PROFILE-03, PROFILE-05, PROFILE-09 (TEST-P2-02, TEST-P2-03)
- [ ] `tests/test_scout.py` — covers SCOUT-03, SCOUT-04, SCOUT-06 (TEST-P2-01, TEST-P2-07)
- [ ] `tests/test_scorer.py` — covers SCOUT-07 scoring formula unit tests
- [ ] `tests/test_research.py` — covers RESEARCH-04, RESEARCH-09 (TEST-P2-08, TEST-P2-09, TEST-P2-10)
- [ ] `tests/test_matcher.py` — covers MATCH-02, MATCH-03 (TEST-P2-04, TEST-P2-11)
- [ ] `tests/test_writer.py` — covers WRITER-01, WRITER-08, WRITER-10 (TEST-P2-05, TEST-P2-06, TEST-P2-12)
- [ ] `tests/test_orchestrator.py` — covers AGENT-04 checkpoint/resume (TEST-P2-15)
- [ ] `tests/integration/test_scout_integration.py` — covers TEST-P2-07
- [ ] `tests/integration/test_research_phase1.py` — covers TEST-P2-08
- [ ] `tests/integration/test_approval_gate.py` — covers TEST-P2-09
- [ ] `tests/e2e/test_pipeline.py` — covers TEST-P2-13, TEST-P2-14
- [ ] `tests/regression/test_checkpoint.py` — covers TEST-P2-15
- [ ] `tests/performance/test_benchmarks.py` — covers TEST-P2-16
- [ ] `tests/conftest.py` — fixture leads (10 known YC companies), fixture IntelBriefs, fixture UserProfile, mock LLM client via TestModel
- [ ] `tests/fixtures/` — static JSON fixture data (sample yc-oss companies, sample resumes as text)

**Framework install:** Already installed (`pytest 9.0.2`, `pytest-asyncio 1.3.0`). No framework install needed.

**Missing packages (add to pyproject.toml):**
```bash
pip install PyMuPDF python-docx beautifulsoup4 lxml scikit-learn
```

---

## Sources

### Primary (HIGH confidence)

- `/pymupdf/pymupdf` (Context7) — `get_text()`, `get_text(clip=rect, sort=True)`, block extraction patterns
- `/skelmis/python-docx` (Context7) — `Document.paragraphs`, `iter_inner_content()`, table extraction
- `/wention/beautifulsoup4` (Context7) — `find()`, `find_all()`, CSS selectors, parser setup
- `/textualize/rich` (Context7) — `Table`, `Panel`, `Prompt.ask()`, `Console.input()`, markup styling
- `/websites/ai_pydantic_dev` (Context7) — `Agent`, `RunContext`, `deps_type`, `output_type`, `UsageLimits`, `TestModel`, `Agent.override`
- `/encode/httpx` (Context7) — `AsyncClient`, headers, connection limits, concurrent requests
- https://pypi.org/project/pydantic-ai/ — Version 1.63.0, Production/Stable status (verified 2026-02-26)
- https://pypi.org/project/questionary/ — Version 2.1.1, text/select/checkbox prompt types (verified 2026-02-26)
- https://yc-oss.github.io/api/companies/all.json — 28 fields per company record verified by fetch (2026-02-26)
- https://github.com/yc-oss/api — API structure, refresh mechanism, endpoint list (verified 2026-02-26)
- https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business — CAN-SPAM requirements: physical address, unsubscribe, penalties

### Secondary (MEDIUM confidence)

- https://artifex.com/blog/extracting-text-from-multi-column-pages-a-practical-pymupdf-guide — `column_boxes()` utility pattern (official PyMuPDF blog, verified against Context7 code)
- https://ai.pydantic.dev/testing/ — TestModel, FunctionModel, Agent.override fixture pattern (official docs, fetched 2026-02-26)
- https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/text-extraction/multi_column.py — column_boxes source (official PyMuPDF org)
- scikit-learn cosine_similarity — `TfidfVectorizer` + `cosine_similarity` for semantic scoring (standard; official sklearn docs)

### Tertiary (LOW confidence)

- YC website infinite scroll / Algolia behavior — observed in WebSearch results; not directly verified via fetch (supports the recommendation to use yc-oss API instead)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all core packages verified in installed venv or official PyPI; versions confirmed
- YC data source: HIGH — yc-oss API fetched and field schema verified directly
- PydanticAI stability: HIGH — PyPI status confirmed as Production/Stable, version 1.63.0
- Architecture patterns: HIGH — all patterns verified from Context7 official docs
- Scoring formula: MEDIUM — weights are user-specified ranges; exact formula design is planner discretion
- Contact discovery (Phase 2 Research): MEDIUM — httpx + LLM extraction pattern is standard but exact LinkedIn scraping behavior not verified
- Pitfalls: HIGH for PDF/YC/Rich issues (verified from official sources); MEDIUM for Ollama tool-use (based on Phase 1 research patterns)

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable libraries); re-verify yc-oss API availability before Scout implementation
