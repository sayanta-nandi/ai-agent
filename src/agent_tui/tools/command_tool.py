"""Command execution tool for workspace-constrained command running."""

from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Any

from agent_tui.safety import resolve_workspace, WorkspaceSafetyError
from agent_tui.tools.base import Tool, ToolResult, ToolError


class RunCommandTool(Tool):
    """Execute commands inside a workspace with timeout and output capture."""

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the run command tool.

        Args:
            workspace: The root workspace path for all command execution.
        """
        self.workspace = resolve_workspace(workspace)

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return "Run a shell command inside the workspace with timeout and captured output."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute (will be split into args to avoid shell injection).",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds. Default is 30.",
                    "default": 30,
                },
            },
            "required": ["command"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        """Execute a command inside the workspace.

        Args:
            command: Command string to execute (will be parsed into args).
            timeout: Timeout in seconds (default 30).

        Returns:
            ToolResult with stdout, stderr, and exit code, or ToolError on failure.
        """
        command = kwargs.get("command")
        timeout = kwargs.get("timeout", 30)

        if command is None:
            return ToolError(
                tool_name=self.name,
                error_message="command parameter is required.",
                error_type="validation",
            )

        if not command or not isinstance(command, str) or not command.strip():
            return ToolError(
                tool_name=self.name,
                error_message="command cannot be empty.",
                error_type="validation",
            )

        if not isinstance(timeout, (int, float)) or timeout <= 0:
            return ToolError(
                tool_name=self.name,
                error_message="timeout must be a positive number.",
                error_type="validation",
            )

        # Parse command into args to avoid shell injection
        try:
            args = shlex.split(command)
        except ValueError as e:
            return ToolError(
                tool_name=self.name,
                error_message=f"Failed to parse command: {e}",
                error_type="validation",
                metadata={"command": command},
            )

        if not args:
            return ToolError(
                tool_name=self.name,
                error_message="command cannot be empty.",
                error_type="validation",
            )

        # Execute command with timeout
        result = await self._run_with_timeout(args, timeout)
        return result

    async def _run_with_timeout(
        self, args: list[str], timeout: float
    ) -> ToolResult | ToolError:
        """Execute command with timeout handling.

        Args:
            args: Command arguments (already parsed into list).
            timeout: Timeout in seconds.

        Returns:
            ToolResult with output and exit code, or ToolError on execution failure.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                try:
                    await process.wait()
                except Exception:
                    pass
                return ToolError(
                    tool_name=self.name,
                    error_message=f"Command timed out after {timeout} seconds.",
                    error_type="execution",
                    metadata={"command": " ".join(args), "timeout": timeout},
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            exit_code = process.returncode

            # Build output content
            output_lines = []
            if stdout_str:
                output_lines.append(f"STDOUT:\n{stdout_str}")
            if stderr_str:
                output_lines.append(f"STDERR:\n{stderr_str}")

            content = "\n".join(output_lines) if output_lines else "(no output)"

            return ToolResult(
                tool_name=self.name,
                content=content,
                metadata={
                    "exit_code": exit_code,
                    "command": " ".join(args),
                    "has_stdout": bool(stdout_str),
                    "has_stderr": bool(stderr_str),
                },
            )

        except OSError as e:
            return ToolError(
                tool_name=self.name,
                error_message=f"Failed to execute command: {e}",
                error_type="execution",
                metadata={"command": " ".join(args), "error_type": type(e).__name__},
            )
