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


@patch("agent_tui.tui.AgentTuiApp.run")
def test_cli_run_workspace_option(mock_run: Any, tmp_path: Path) -> None:
    """Verify that --workspace option can be used instead of a positional argument."""
    with patch.dict("os.environ", {"API_KEY": "test_key", "MODEL": "test_model"}):
        result = runner.invoke(app, ["run", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_cli_run_workspace_option_non_existent() -> None:
    """Verify that --workspace with a non-existent path yields a workspace error."""
    with patch.dict("os.environ", {"API_KEY": "test_key", "MODEL": "test_model"}):
        result = runner.invoke(
            app, ["run", "--workspace", "this-directory-does-not-exist-xyz"]
        )
        assert result.exit_code == 1
        assert "Workspace error" in result.output


@patch("agent_tui.tui.AgentTuiApp.run")
def test_cli_run_workspace_option_overrides_positional(
    mock_run: Any, tmp_path: Path
) -> None:
    """Verify that --workspace option takes precedence over the positional argument."""
    # Create two directories to differentiate
    dir_a = tmp_path / "dir_a"
    dir_a.mkdir()
    dir_b = tmp_path / "dir_b"
    dir_b.mkdir()

    captured_settings: list[Any] = []
    original_init = None

    # Capture the AgentTuiApp constructor call to verify which workspace was used
    import agent_tui.tui as tui_mod

    original_init = tui_mod.AgentTuiApp.__init__

    def mock_init(self: Any, session: Any, settings: Any) -> None:
        captured_settings.append(settings)
        original_init(self, session=session, settings=settings)

    with (
        patch.dict("os.environ", {"API_KEY": "test_key", "MODEL": "test_model"}),
        patch.object(tui_mod.AgentTuiApp, "__init__", mock_init),
    ):
        result = runner.invoke(
            app,
            [
                "run",
                str(dir_a),
                "--workspace",
                str(dir_b),
            ],
        )
        assert result.exit_code == 0
        assert len(captured_settings) == 1
        # --workspace option (dir_b) should take precedence over positional (dir_a)
        assert captured_settings[0].workspace == dir_b.resolve()


@patch("agent_tui.tui.AgentTuiApp.run")
def test_cli_run_overrides_propagate_to_settings(
    mock_run: Any, tmp_path: Path
) -> None:
    """Verify that CLI override values actually propagate to the settings object."""
    captured_settings: list[Any] = []

    import agent_tui.tui as tui_mod

    original_init = tui_mod.AgentTuiApp.__init__

    def mock_init(self: Any, session: Any, settings: Any) -> None:
        captured_settings.append(settings)
        original_init(self, session=session, settings=settings)

    with (
        patch.dict("os.environ", {"API_KEY": "env_key", "MODEL": "env_model"}),
        patch.object(tui_mod.AgentTuiApp, "__init__", mock_init),
    ):
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
        assert len(captured_settings) == 1
        settings = captured_settings[0]
        assert settings.model == "custom-model"
        assert settings.api_key == "custom-key"
        assert settings.base_url == "https://custom-url.com"
        assert settings.provider == "openai"
        assert settings.workspace == tmp_path.resolve()

