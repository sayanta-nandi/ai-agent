"""Configuration models and loading helpers for the terminal AI agent."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Runtime settings loaded from environment variables and optional .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: str = Field(..., description="API key for the configured model provider.")
    base_url: str = Field("https://api.openai.com/v1", description="OpenAI-compatible API base URL.")
    model: str = Field(..., description="Model name to use for completions.")
    workspace: Path = Field(default_factory=Path.cwd, description="Workspace directory for agent operations.")
    provider: str = Field("openai", description="Provider name used by the model adapter.")


def load_settings(workspace: str | Path | None = None) -> AgentSettings:
    """Load and validate agent settings with an optional workspace override."""
    settings = AgentSettings()
    if workspace is not None:
        settings.workspace = Path(workspace)
    return settings
