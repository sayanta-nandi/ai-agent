"""Safety helpers for workspace-constrained agent operations."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable


class WorkspaceSafetyError(ValueError):
    """Raised when a path is outside the configured workspace."""


def resolve_workspace(workspace: str | Path) -> Path:
    """Resolve a workspace path to an absolute directory path."""
    resolved = Path(workspace).expanduser().resolve()
    if not resolved.exists():
        raise WorkspaceSafetyError(f"Workspace does not exist: {resolved}")
    if not resolved.is_dir():
        raise WorkspaceSafetyError(f"Workspace is not a directory: {resolved}")
    return resolved


def resolve_within_workspace(workspace: str | Path, path: str | Path) -> Path:
    """Resolve a path and ensure it remains inside the workspace."""
    workspace_path = resolve_workspace(workspace)
    resolved_path = (workspace_path / Path(path)).expanduser().resolve()

    try:
        resolved_path.relative_to(workspace_path)
    except ValueError as exc:
        raise WorkspaceSafetyError(f"Path escapes workspace: {path}") from exc

    return resolved_path


class SafetyLevel:
    """Classification of tool safety levels."""

    SAFE = "safe"
    """Tool that only reads information, no side effects."""

    RISKY = "risky"
    """Tool that modifies state or executes code."""


class SafetyManager:
    """Manages safety classification and confirmation for tool calls."""

    # Tools that only read information
    SAFE_TOOLS = {"read_file", "list_files"}

    # Tools that require confirmation before execution
    RISKY_TOOLS = {"write_file", "edit_file", "delete_file", "run_command"}

    def __init__(
        self,
        confirmation_handler: Callable[[str], Any] | None = None,
    ) -> None:
        """Initialize the SafetyManager.

        Args:
            confirmation_handler: Optional async function that handles confirmation prompts.
                If not provided, uses CLI fallback.
                Function signature: async def handler(prompt: str) -> bool
        """
        self._confirmation_handler = confirmation_handler

    def classify_tool(self, tool_name: str) -> str:
        """Classify a tool as safe or risky.

        Args:
            tool_name: The name of the tool to classify.

        Returns:
            Either SafetyLevel.SAFE or SafetyLevel.RISKY.

        Raises:
            ValueError: If the tool is not recognized.
        """
        if tool_name in self.SAFE_TOOLS:
            return SafetyLevel.SAFE
        if tool_name in self.RISKY_TOOLS:
            return SafetyLevel.RISKY
        raise ValueError(f"Unknown tool: {tool_name}")

    def is_safe(self, tool_name: str) -> bool:
        """Check if a tool is safe (does not require confirmation).

        Args:
            tool_name: The name of the tool to check.

        Returns:
            True if the tool is safe, False otherwise.
        """
        try:
            return self.classify_tool(tool_name) == SafetyLevel.SAFE
        except ValueError:
            return False

    def is_risky(self, tool_name: str) -> bool:
        """Check if a tool is risky (requires confirmation).

        Args:
            tool_name: The name of the tool to check.

        Returns:
            True if the tool is risky, False otherwise.
        """
        try:
            return self.classify_tool(tool_name) == SafetyLevel.RISKY
        except ValueError:
            return False

    async def request_confirmation(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> bool:
        """Request user confirmation for a tool call.

        Args:
            tool_name: The name of the tool being called.
            tool_args: The arguments being passed to the tool.

        Returns:
            True if the user confirms, False otherwise.
        """
        prompt = self._format_confirmation_prompt(tool_name, tool_args)

        if self._confirmation_handler:
            result = self._confirmation_handler(prompt)
            # Handle both sync and async handlers
            if asyncio.iscoroutine(result):
                return await result
            return result

        return await self._cli_confirmation(prompt)

    async def validate_tool_call(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> bool:
        """Validate a tool call and request confirmation if needed.

        Args:
            tool_name: The name of the tool being called.
            tool_args: The arguments being passed to the tool.

        Returns:
            True if the call should proceed, False if blocked by user.

        Raises:
            ValueError: If the tool is unknown.
        """
        self.classify_tool(tool_name)  # Validate the tool exists

        if self.is_safe(tool_name):
            return True

        return await self.request_confirmation(tool_name, tool_args)

    def _format_confirmation_prompt(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """Format a confirmation prompt for a tool call.

        Args:
            tool_name: The name of the tool being called.
            tool_args: The arguments being passed to the tool.

        Returns:
            A formatted prompt string for user confirmation.
        """
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"Execute {tool_name}({args_str})? [y/n]: "

    async def _cli_confirmation(self, prompt: str) -> bool:
        """CLI fallback for requesting user confirmation.

        Args:
            prompt: The confirmation prompt to display.

        Returns:
            True if the user enters 'y' or 'yes', False otherwise.
        """
        # Run in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: input(prompt).strip().lower(),
        )
        return response in ("y", "yes")
