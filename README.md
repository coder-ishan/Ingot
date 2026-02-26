# INGOT — INtelligent Generation & Outreach Tool

> Autonomous job-hunting via a team of AI agents: scout leads, research companies, match your skills, write personalised cold emails, and track replies — all from the command line.

Most great jobs are never posted. Founders and hiring managers hire people they've *already talked to*. INGOT makes your search proactive by running a personal recruiting agency 24/7 — at a scale no human could maintain alone.

---

## How it works

INGOT orchestrates seven specialised agents in a pipeline:

```
                    ┌──────────────────────────┐
                    │    ORCHESTRATOR AGENT    │
                    │  Routes tasks · TUI chat │
                    └────────────┬─────────────┘
          ┌──────────┬───────────┼────────────┬──────────┐
          ▼          ▼           ▼            ▼          ▼
       SCOUT     RESEARCH    MATCHER       WRITER    OUTREACH
       discovers  builds      cross-refs   drafts    sends +
       leads      intel       your resume  emails    tracks
                                      └──────────────► ANALYST
                                                       reports
```

| Agent | Responsibility |
|---|---|
| **Scout** | Discovers leads from configured venues (YC, Apollo, LinkedIn, etc.) |
| **Research** | Scrapes company pages, press releases, and public profiles for talking points |
| **Matcher** | Scores each lead against your resume and generates a personalised value proposition |
| **Writer** | Drafts a 150–200 word cold email grounded in the research and your qualifications |
| **Outreach** | Manages sending (rate limiting, business-hours windows) and tracks opens/replies |
| **Analyst** | Surfaces campaign insights and weekly digests |
| **Orchestrator** | User-facing chat interface that routes requests across the team |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python ≥ 3.11 | `python --version` to verify |
| [uv](https://docs.astral.sh/uv/) or pip | Package manager |
| Gmail account + [App Password](https://support.google.com/accounts/answer/185833) | For sending/receiving emails |
| **One of:** Ollama (free) · Anthropic API key · OpenAI API key | LLM backend |

### Optional: Ollama (fully free, local)

```bash
# macOS
brew install ollama
ollama serve          # start the server (keep running)
ollama pull llama3.1  # download the default model (~4 GB)
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/ingot.git
cd ingot

# Install with uv (recommended)
uv sync

# — or — install with pip in a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

After installation the `ingot` command is available in your environment:

```bash
ingot --help
```

---

## Setup

Run the interactive setup wizard to configure credentials and choose your LLM backend:

```bash
ingot setup
```

The wizard walks through:

1. **Gmail address** — used to send outreach emails
2. **Gmail App Password** — [generate one here](https://support.google.com/accounts/answer/185833) (not your regular password)
3. **Mailing address** — required for CAN-SPAM compliance footer
4. **LLM backend** — choose a preset or configure each agent individually:
   - `fully_free` — all agents use local Ollama (zero API cost)
   - `best_quality` — Writer & Research use Claude Sonnet; others use Claude Haiku
   - `custom` — pick a LiteLLM model string for each of the 7 agents

Credentials are saved to `~/.ingot/config.json` with secrets Fernet-encrypted at rest.

### Non-interactive setup (CI / scripting)

```bash
export GMAIL_USERNAME="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export ANTHROPIC_API_KEY="sk-ant-..."   # only needed for best_quality preset

ingot setup --non-interactive --preset best_quality
```

### Re-run setup

Running `ingot setup` again only prompts for fields that are not yet configured. Existing values are preserved.

---

## Usage

> **Note:** The full agent pipeline and TUI chat are under active development. Today the `setup` command is the stable entry point.

```bash
# Show all available commands
ingot --help

# Configure credentials and LLM models
ingot setup

# Re-run with a different preset (leaves other fields intact)
ingot setup --preset fully_free

# Verbose output (use -vv for debug level)
ingot setup -v
```

---

## Configuration reference

Config file location: `~/.ingot/config.json`

| Field | Description | Default |
|---|---|---|
| `smtp.host` | SMTP server host | `smtp.gmail.com` |
| `smtp.port` | SMTP port | `587` |
| `smtp.username` | Sending Gmail address | — |
| `smtp.password` | Gmail App Password (encrypted) | — |
| `imap.host` | IMAP server for reply polling | `imap.gmail.com` |
| `anthropic_api_key` | Anthropic API key (encrypted) | — |
| `openai_api_key` | OpenAI API key (encrypted) | — |
| `mailing_address` | Physical address for CAN-SPAM footer | — |
| `agents.<name>.model` | LiteLLM model string per agent | `ollama/llama3.1` |
| `max_retries` | LLM call retry limit | `3` |
| `llm_fallback_chain` | Ordered fallback backends | `["claude","openai","ollama"]` |

### LiteLLM model strings

INGOT uses [LiteLLM](https://docs.litellm.ai/) so any supported provider works:

```
ollama/llama3.1                          # local Ollama
anthropic/claude-3-5-sonnet-20241022     # Anthropic
anthropic/claude-haiku-4-5-20251001      # Anthropic (cheaper)
openai/gpt-4o                            # OpenAI
openai/gpt-4o-mini                       # OpenAI (cheaper)
```

---

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run the test suite (requires ≥ 80 % coverage)
pytest

# Run with coverage report
pytest --cov=ingot --cov-report=html
open htmlcov/index.html

# Database migrations (Alembic)
alembic upgrade head
```

### Project layout

```
src/ingot/
├── agents/          # Seven specialist agents + base class
├── cli/             # Typer CLI (setup wizard)
├── config/          # Config schema, manager, and crypto helpers
├── db/              # SQLModel models + Alembic migrations
├── llm/             # LiteLLM client with fallback logic
├── dispatcher.py    # Agent task dispatcher
└── http_client.py   # Shared async HTTP client
```

---

## Security notes

- Secrets (passwords, API keys) are **Fernet-encrypted** before being written to `config.json`. The encryption key is derived from a machine-local secret stored in `~/.ingot/`.
- Gmail App Passwords are used instead of your account password — you can revoke them independently at any time.
- INGOT never stores or transmits your credentials to any third party.

---

## License

MIT
