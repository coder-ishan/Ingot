"""Setup wizard CLI command for INGOT.

Supports both interactive (questionary prompts) and non-interactive
(env vars + --preset flag) modes. Existing values in config.json are
skipped — only missing or blank fields are prompted.

Usage:
    ingot setup                                    # interactive
    ingot setup --preset fully_free                # interactive, apply preset
    ingot setup --non-interactive --preset best_quality  # CI/env-var mode
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.table import Table

from ingot.config.manager import ConfigManager
from ingot.config.schema import AgentConfig, AppConfig
from ingot.logging_config import configure_logging

# ----- constants ----

_AGENT_NAMES: list[str] = [
    "orchestrator",
    "scout",
    "research",
    "matcher",
    "writer",
    "outreach",
    "analyst",
]

_PRESET_FULLY_FREE = "fully_free"
_PRESET_BEST_QUALITY = "best_quality"

_OLLAMA_MODEL = "ollama/llama3.1"
_CLAUDE_SONNET = "anthropic/claude-3-5-sonnet-20241022"
_CLAUDE_HAIKU = "anthropic/claude-3-haiku-20240307"

_PRESET_MODELS: dict[str, dict[str, str]] = {
    _PRESET_FULLY_FREE: {name: _OLLAMA_MODEL for name in _AGENT_NAMES},
    _PRESET_BEST_QUALITY: {
        **{name: _CLAUDE_HAIKU for name in _AGENT_NAMES},
        "writer": _CLAUDE_SONNET,
        "research": _CLAUDE_SONNET,
    },
}

_out = Console()
_err = Console(stderr=True)


# ----- helpers ------

def _mask(value: str, show_chars: int = 4) -> str:
    """Return a masked version of a secret for display."""
    if not value:
        return "(not set)"
    if len(value) <= show_chars:
        return "*" * len(value)
    return value[:show_chars] + "*" * (len(value) - show_chars)


def _apply_preset(cfg: AppConfig, preset_name: str) -> None:
    """Apply a named preset to the agent model map."""
    models = _PRESET_MODELS.get(preset_name)
    if models is None:
        _err.print(f"[red]Unknown preset '{preset_name}'. Choose 'fully_free' or 'best_quality'.[/red]")
        raise typer.Exit(code=1)
    for agent_name, model in models.items():
        if agent_name not in cfg.agents:
            cfg.agents[agent_name] = AgentConfig(model=model)
        else:
            cfg.agents[agent_name].model = model


def _print_summary(cfg: AppConfig, cm: ConfigManager) -> None:
    """Print a Rich summary table of configured services."""
    log_dir = cm.base_dir / "logs"

    table = Table(title="INGOT Configuration Summary", show_lines=True)
    table.add_column("Service", style="bold cyan")
    table.add_column("Status")
    table.add_column("Value")

    def status(val: str) -> str:
        return "[green]configured[/green]" if val else "[yellow]not set[/yellow]"

    table.add_row("Gmail Username", status(cfg.smtp.username), cfg.smtp.username or "(not set)")
    table.add_row("Gmail App Password", status(cfg.smtp.password), _mask(cfg.smtp.password))
    table.add_row("Anthropic API Key", status(cfg.anthropic_api_key), _mask(cfg.anthropic_api_key))
    table.add_row("OpenAI API Key", status(cfg.openai_api_key), _mask(cfg.openai_api_key))
    table.add_row("Mailing Address", status(cfg.mailing_address), cfg.mailing_address or "(not set)")

    for agent in _AGENT_NAMES:
        model = cfg.agents.get(agent, AgentConfig()).model
        table.add_row(f"Agent: {agent}", "[green]configured[/green]", model)

    _out.print(table)
    _out.print(f"\n[dim]Log directory: {log_dir}[/dim]")


# ----- main command ------

def setup_app(
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Read credentials from env vars"
    ),
    preset: str | None = typer.Option(
        None, "--preset", help="'fully_free' or 'best_quality'"
    ),
    verbose: int = typer.Option(0, "-v", count=True, max=2),
) -> None:
    """Run the INGOT setup wizard to configure credentials and LLM backends."""
    try:
        _run_setup(non_interactive=non_interactive, preset=preset, verbose=verbose)
    except KeyboardInterrupt as exc:
        _err.print("\n[yellow]Setup cancelled.[/yellow]")
        raise typer.Exit(code=1) from exc
    except typer.Exit:
        raise
    except Exception as exc:
        log_path = Path.home() / ".ingot" / "logs"
        _err.print(f"[red][Setup] Something went wrong. Full error logged to {log_path}[/red]")
        logging.getLogger("ingot.cli.setup").error(
            "Setup wizard failed", exc_info=True
        )
        raise typer.Exit(code=1) from exc


def _run_setup(
    *,
    non_interactive: bool,
    preset: str | None,
    verbose: int,
) -> None:
    """Internal setup logic separated from the Typer decorator."""
    cm = ConfigManager()
    cm.ensure_dirs()
    configure_logging(cm.base_dir, verbosity=verbose)
    cfg = cm.load()

    if non_interactive:
        _run_non_interactive(cfg, preset=preset)
    else:
        _run_interactive(cfg, preset=preset)

    cm.save(cfg)
    _out.print("\n[green]Setup complete![/green]")
    _print_summary(cfg, cm)


# ----- non-interactive mode ------

def _run_non_interactive(cfg: AppConfig, preset: str | None) -> None:
    """Populate config from environment variables."""
    gmail_username = os.environ.get("GMAIL_USERNAME", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if gmail_username:
        cfg.smtp.username = gmail_username
        cfg.imap.username = gmail_username
    if gmail_password:
        cfg.smtp.password = gmail_password
        cfg.imap.password = gmail_password
    if anthropic_key:
        cfg.anthropic_api_key = anthropic_key
    if openai_key:
        cfg.openai_api_key = openai_key

    # Apply preset or default to fully_free
    effective_preset = preset or _PRESET_FULLY_FREE
    _apply_preset(cfg, effective_preset)

    # Ensure all 7 agents exist
    for agent_name in _AGENT_NAMES:
        if agent_name not in cfg.agents:
            cfg.agents[agent_name] = AgentConfig()

    # Validate required API keys based on configured models
    errors: list[str] = []
    needs_anthropic = any("anthropic" in a.model for a in cfg.agents.values())
    needs_openai = any("openai" in a.model or "gpt" in a.model for a in cfg.agents.values())
    if needs_anthropic and not cfg.anthropic_api_key:
        errors.append(
            "ANTHROPIC_API_KEY is required for the selected preset/models but was not set."
        )
    if needs_openai and not cfg.openai_api_key:
        errors.append(
            "OPENAI_API_KEY is required for the selected preset/models but was not set."
        )
    if gmail_username and not cfg.smtp.password:
        errors.append(
            "GMAIL_APP_PASSWORD must be set when GMAIL_USERNAME is provided."
        )

    if errors:
        for error in errors:
            _err.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1)


# ----- interactive mode ------

def _run_interactive(cfg: AppConfig, preset: str | None) -> None:
    """Prompt user for each unconfigured value."""
    _out.print("[bold]INGOT Setup Wizard[/bold]\n")

    # Step 1: Gmail username
    if not cfg.smtp.username:
        username = questionary.text("Gmail address for sending:").ask()
        if username:
            cfg.smtp.username = username.strip()
            cfg.imap.username = username.strip()
    else:
        _out.print(f"Gmail address: [dim][already configured: {cfg.smtp.username}][/dim]")

    # Step 2: Gmail App Password
    if not cfg.smtp.password:
        password = questionary.password("Gmail App Password:").ask()
        if not password:
            _err.print("[red]Gmail App Password cannot be empty.[/red]")
            raise typer.Exit(code=1)
        cfg.smtp.password = password
        cfg.imap.password = password
    else:
        _out.print("Gmail App Password: [dim][already configured][/dim]")

    # Step 3: Mailing address (CAN-SPAM)
    if not cfg.mailing_address:
        address = questionary.text(
            "Physical mailing address (required for CAN-SPAM):"
        ).ask()
        if address:
            cfg.mailing_address = address.strip()
    else:
        _out.print("Mailing address: [dim][already configured][/dim]")

    # Step 4: Determine LLM preset or ask
    effective_preset = preset
    if effective_preset is None:
        choice = questionary.select(
            "LLM setup:",
            choices=[
                "fully_free (all Ollama)",
                "best_quality (Claude Sonnet for Writer+Research, Haiku for rest)",
                "custom",
            ],
        ).ask()

        if choice and choice.startswith("fully_free"):
            effective_preset = _PRESET_FULLY_FREE
        elif choice and choice.startswith("best_quality"):
            effective_preset = _PRESET_BEST_QUALITY
        else:
            effective_preset = "custom"

    # Step 5: Apply preset or prompt per-agent
    if effective_preset in (_PRESET_FULLY_FREE, _PRESET_BEST_QUALITY):
        _apply_preset(cfg, effective_preset)
    else:
        _prompt_custom_agents(cfg)

    # Step 6: API keys based on which models are in use
    needs_anthropic = any(
        "anthropic" in a.model for a in cfg.agents.values()
    )
    needs_openai = any(
        "openai" in a.model or "gpt" in a.model for a in cfg.agents.values()
    )
    needs_ollama = any(
        "ollama" in a.model for a in cfg.agents.values()
    )

    if needs_anthropic and not cfg.anthropic_api_key:
        while True:
            key = questionary.password("Anthropic API Key (sk-ant-...):").ask()
            if not key:
                _err.print("[red]Anthropic API key is required. Press Ctrl+C to abort.[/red]")
                continue
            if not key.startswith("sk-ant-"):
                _err.print("[yellow]Warning: key does not start with 'sk-ant-'[/yellow]")
            cfg.anthropic_api_key = key
            break

    if needs_openai and not cfg.openai_api_key:
        while True:
            key = questionary.password("OpenAI API Key (sk-...):").ask()
            if not key:
                _err.print("[red]OpenAI API key is required. Press Ctrl+C to abort.[/red]")
                continue
            if not key.startswith("sk-"):
                _err.print("[yellow]Warning: key does not start with 'sk-'[/yellow]")
            cfg.openai_api_key = key
            break

    if needs_ollama:
        _out.print(
            "[dim]Note: Ensure Ollama is running at localhost:11434[/dim]"
        )

    # Ensure all 7 agents exist
    for agent_name in _AGENT_NAMES:
        if agent_name not in cfg.agents:
            cfg.agents[agent_name] = AgentConfig()


def _prompt_custom_agents(cfg: AppConfig) -> None:
    """Prompt for a model string for each of the 7 agents."""
    _out.print("\n[bold]Custom agent model configuration:[/bold]")
    for agent_name in _AGENT_NAMES:
        current = cfg.agents.get(agent_name, AgentConfig()).model
        model = questionary.text(
            f"Model for {agent_name}:",
            default=current,
        ).ask()
        if model:
            if agent_name not in cfg.agents:
                cfg.agents[agent_name] = AgentConfig(model=model.strip())
            else:
                cfg.agents[agent_name].model = model.strip()
