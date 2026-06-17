"""Unit tests for the CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from agent_tui.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    """Verify the CLI version command prints the expected info."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "agent-tui" in result.output


def test_cli_run_missing_api_key(tmp_path: Path) -> None:
    """Verify that a missing API key yields a clear configuration error."""
    # Ensure env is empty of API_KEY
    with patch.dict("os.environ", {}, clear=True):
        result = runner.invoke(app, ["run", str(tmp_path)])
        assert result.exit_code == 1
        assert "Configuration error" in result.output
        assert "API key is missing" in result.output


def test_cli_run_non_existent_workspace() -> None:
    """Verify that a non-existent workspace directory yields a workspace error."""
    with patch.dict("os.environ", {"API_KEY": "test_key", "MODEL": "test_model"}):
        result = runner.invoke(app, ["run", "this-directory-does-not-exist-xyz"])
        assert result.exit_code == 1
        assert "Workspace error" in result.output


@patch("agent_tui.tui.AgentTuiApp.run")
def test_cli_run_success(mock_run: Any, tmp_path: Path) -> None:
    """Verify a successful run starts the TUI application."""
    with patch.dict("os.environ", {"API_KEY": "test_key", "MODEL": "test_model"}):
        result = runner.invoke(app, ["run", str(tmp_path)])
        assert result.exit_code == 0
        mock_run.assert_called_once()


@patch("agent_tui.tui.AgentTuiApp.run")
def test_cli_run_overrides(mock_run: Any, tmp_path: Path) -> None:
    """Verify CLI options override default configuration settings."""
    with patch.dict("os.environ", {"API_KEY": "env_key", "MODEL": "env_model"}):
        result = runner.invoke(
            app,
            [
                "run",
                str(tmp_path),
                "--model",
                "custom-model",
                "--api-key",
                "custom-key",
                "--base-url",
                "https://custom-url.com",
                "--provider",
                "openai",
            ],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
