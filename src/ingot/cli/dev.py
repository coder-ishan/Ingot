"""Dev / UAT commands for testing pipeline components."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

_out = Console()
_err = Console(stderr=True)


def parse_resume_cmd(
    path: Path = typer.Argument(..., help="Path to PDF or DOCX resume"),
    full: bool = typer.Option(False, "--full", help="Print full text instead of preview"),
) -> None:
    """Parse a resume file and print the extracted text."""
    from ingot.agents.profile import parse_resume, ResumeParseError

    if not path.exists():
        _err.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(code=1)

    try:
        text = parse_resume(path)
    except ResumeParseError as exc:
        _err.print(f"[red]Parse error: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    _out.print(f"[green]Parsed {path.name}[/green] — {len(text):,} chars\n")

    if full:
        _out.print(text)
    else:
        preview = text[:1000]
        _out.print(Panel(preview, title="Preview (first 1000 chars)", expand=False))
        if len(text) > 1000:
            _out.print(f"[dim]... {len(text) - 1000:,} more chars. Use --full to see everything.[/dim]")
