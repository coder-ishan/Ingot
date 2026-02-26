"""CLI entry point for INGOT."""
import typer

from ingot.cli.setup import setup_app

# Use invoke_without_command=True so that the app always shows the Commands
# section even with a single sub-command registered.
app = typer.Typer(
    name="ingot",
    help="INGOT — INtelligent Generation & Outreach Tool",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """INGOT — INtelligent Generation & Outreach Tool."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


app.command(name="setup", help="Run the INGOT setup wizard")(setup_app)
