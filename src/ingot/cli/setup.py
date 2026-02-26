"""Setup wizard CLI command for INGOT."""
from __future__ import annotations

import typer


def setup_app(
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Read credentials from env vars"),
    preset: str | None = typer.Option(None, "--preset", help="'fully_free' or 'best_quality'"),
    verbose: int = typer.Option(0, "-v", count=True, max=2),
) -> None:
    """Run the INGOT setup wizard to configure credentials and LLM backends."""
    raise NotImplementedError("Setup wizard not yet implemented — see Task 3")
