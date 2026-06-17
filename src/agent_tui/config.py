"""Configuration models and loading helpers for the terminal AI agent."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Runtime settings loaded from environment variables and optional .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: str = Field(..., description="API key for the configured model provider.")
    base_url: str = Field("https://api.openai.com/v1", description="OpenAI-compatible API base URL.")
    model: str = Field(..., description="Model name to use for completions.")
    workspace: Path = Field(default_factory=Path.cwd, description="Workspace directory for agent operations.")
    provider: str = Field("openai", description="Provider name used by the model adapter.")


def load_settings(
    workspace: str | Path | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
) -> AgentSettings:
    """Load and validate agent settings with optional overrides."""
    kwargs = {}
    if workspace is not None:
        kwargs["workspace"] = Path(workspace)
    if api_key is not None:
        kwargs["api_key"] = api_key
    if model is not None:
        kwargs["model"] = model
    if base_url is not None:
        kwargs["base_url"] = base_url
    if provider is not None:
        kwargs["provider"] = provider

    try:
        return AgentSettings(**kwargs)
    except ValidationError as exc:
        # Check specifically if api_key is missing
        missing_api_key = False
        for error in exc.errors():
            loc = error.get("loc", ())
            if "api_key" in loc and error.get("type") in ("missing", "value_error.missing"):
                missing_api_key = True
                break

        if missing_api_key:
            raise ValueError(
                "API key is missing. Please set the API_KEY environment variable or specify it via CLI/env."
            ) from exc
        raise ValueError(f"Configuration validation failed: {exc}") from exc

