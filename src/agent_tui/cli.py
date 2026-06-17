"""CLI command definitions for the terminal AI agent."""

import typer

app = typer.Typer(help="Terminal AI coding agent.")


@app.command()
def version() -> None:
    """Print the agent-tui version."""
    from importlib.metadata import version

    typer.echo(f"agent-tui {version('agent-tui')}")


@app.command()
def run() -> None:
    """Run the terminal AI agent."""
    typer.echo("agent-tui run is not implemented yet.")
