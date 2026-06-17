import os
from pathlib import Path
import pytest
from pydantic import ValidationError
from agent_tui.config import AgentSettings, load_settings


def test_load_settings_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test load_settings succeeds when required env vars are set."""
    monkeypatch.setenv("API_KEY", "test-key-123")
    monkeypatch.setenv("MODEL", "gpt-4")
    monkeypatch.setenv("BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("PROVIDER", "openai")

    settings = load_settings()
    assert settings.api_key == "test-key-123"
    assert settings.model == "gpt-4"
    assert settings.base_url == "https://api.openai.com/v1"
    assert settings.provider == "openai"
    assert settings.workspace == Path.cwd()


def test_load_settings_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test load_settings raises a clear ValueError when API key is missing."""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("MODEL", "gpt-4")

    with pytest.raises(ValueError) as exc_info:
        load_settings()
    assert "API key is missing" in str(exc_info.value)


def test_load_settings_cli_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that arguments to load_settings override environment variables."""
    monkeypatch.setenv("API_KEY", "env-key")
    monkeypatch.setenv("MODEL", "env-model")

    settings = load_settings(
        api_key="cli-key",
        model="cli-model",
        base_url="https://cli.url",
        provider="cli-provider",
        workspace="/tmp/cli-workspace",
    )
    assert settings.api_key == "cli-key"
    assert settings.model == "cli-model"
    assert settings.base_url == "https://cli.url"
    assert settings.provider == "cli-provider"
    assert settings.workspace == Path("/tmp/cli-workspace")


def test_load_settings_from_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings can be loaded from a .env file."""
    # Write a temporary .env file
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        "API_KEY=dotenv-key-abc\nMODEL=dotenv-model\n",
        encoding="utf-8"
    )

    # Change working directory to tmp_path to let Pydantic find the .env
    monkeypatch.chdir(tmp_path)
    # Clear environment variables to force loading from .env
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("MODEL", raising=False)

    settings = load_settings()
    assert settings.api_key == "dotenv-key-abc"
    assert settings.model == "dotenv-model"
