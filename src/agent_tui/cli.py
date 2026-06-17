"""CLI command definitions for the terminal AI agent."""

import typer

app = typer.Typer(help="Terminal AI coding agent.")


@app.command()
def version() -> None:
    """Print the agent-tui version."""
    from importlib.metadata import version

    typer.echo(f"agent-tui {version('agent-tui')}")


@app.command()
def run(
    workspace: str = typer.Argument(None, help="Workspace directory for agent operations."),
    model: str = typer.Option(None, "--model", help="Model name override."),
    api_key: str = typer.Option(None, "--api-key", help="API key override."),
    base_url: str = typer.Option(None, "--base-url", help="API base URL override."),
    provider: str = typer.Option(None, "--provider", help="Model provider override."),
) -> None:
    """Run the terminal AI agent."""
    from agent_tui.agent import AgentSession
    from agent_tui.config import load_settings
    from agent_tui.llm import LLMClient
    from agent_tui.safety import SafetyManager, resolve_workspace
    from agent_tui.tools import (
        DeleteFileTool,
        EditFileTool,
        ListFilesTool,
        ReadFileTool,
        RunCommandTool,
        ToolRegistry,
        WriteFileTool,
    )
    from agent_tui.tui import AgentTuiApp

    try:
        settings = load_settings(
            workspace=workspace,
            api_key=api_key,
            model=model,
            base_url=base_url,
            provider=provider,
        )
    except ValueError as e:
        typer.echo(f"Configuration error: {e}", err=True)
        raise typer.Exit(code=1)

    try:
        # Validate workspace path safety/existence
        resolve_workspace(settings.workspace)
    except Exception as e:
        typer.echo(f"Workspace error: {e}", err=True)
        raise typer.Exit(code=1)

    # Initialize client, registry, tools, safety, session
    client = LLMClient(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
        provider=settings.provider,
    )

    registry = ToolRegistry()
    registry.register(ListFilesTool(workspace=settings.workspace))
    registry.register(ReadFileTool(workspace=settings.workspace))
    registry.register(WriteFileTool(workspace=settings.workspace))
    registry.register(EditFileTool(workspace=settings.workspace))
    registry.register(DeleteFileTool(workspace=settings.workspace))
    registry.register(RunCommandTool(workspace=settings.workspace))

    safety_manager = SafetyManager()
    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=safety_manager,
    )

    # Start TUI App
    tui_app = AgentTuiApp(session=session, settings=settings)
    tui_app.run()
