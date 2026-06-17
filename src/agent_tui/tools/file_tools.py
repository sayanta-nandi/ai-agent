"""File tools for workspace-constrained file operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agent_tui.safety import resolve_within_workspace, WorkspaceSafetyError
from agent_tui.tools.base import Tool, ToolResult, ToolError


class ListFilesTool(Tool):
    """List directory contents within a workspace."""

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the list files tool.

        Args:
            workspace: The root workspace path for all file operations.
        """
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files and directories in a given path, respecting workspace boundaries."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to workspace to list.",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum directory depth to traverse. 1 for immediate children only.",
                    "default": 1,
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        """Execute the list files tool.

        Args:
            path: Path relative to workspace.
            max_depth: Maximum depth to traverse (default 1).

        Returns:
            ToolResult with file listing or ToolError on failure.
        """
        try:
            path_arg = kwargs.get("path", ".")
            max_depth = kwargs.get("max_depth", 1)

            if max_depth < 1:
                return ToolError(
                    tool_name=self.name,
                    error_message="max_depth must be at least 1.",
                    error_type="validation",
                )

            resolved_path = resolve_within_workspace(self.workspace, path_arg)

            if not resolved_path.exists():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"Path does not exist: {path_arg}",
                    error_type="not_found",
                    metadata={"requested_path": path_arg},
                )

            if not resolved_path.is_dir():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"Path is not a directory: {path_arg}",
                    error_type="validation",
                    metadata={"requested_path": path_arg},
                )

            # Build file listing with depth limiting
            items = []
            self._collect_items(resolved_path, Path(path_arg), max_depth, 0, items)

            content = "\n".join(sorted(items))
            return ToolResult(
                tool_name=self.name,
                content=content if content else "(empty directory)",
                metadata={
                    "path": str(path_arg),
                    "item_count": len(items),
                    "max_depth": max_depth,
                },
            )

        except WorkspaceSafetyError as e:
            return ToolError(
                tool_name=self.name,
                error_message=str(e),
                error_type="validation",
            )
        except Exception as e:
            return ToolError(
                tool_name=self.name,
                error_message=f"Failed to list files: {e}",
                error_type="execution",
            )

    def _collect_items(
        self,
        current_path: Path,
        display_path: Path,
        max_depth: int,
        current_depth: int,
        items: list[str],
    ) -> None:
        """Recursively collect items up to max_depth."""
        if current_depth >= max_depth:
            return

        try:
            entries = sorted(current_path.iterdir())
            for entry in entries:
                relative_display = display_path / entry.name
                if entry.is_dir():
                    items.append(f"{relative_display}/")
                    if current_depth + 1 < max_depth:
                        self._collect_items(
                            entry,
                            relative_display,
                            max_depth,
                            current_depth + 1,
                            items,
                        )
                else:
                    items.append(str(relative_display))
        except (PermissionError, OSError):
            pass


class ReadFileTool(Tool):
    """Read text file contents within a workspace."""

    # Constants for safety
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    BINARY_THRESHOLD = 512  # bytes to check for binary content

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the read file tool.

        Args:
            workspace: The root workspace path for all file operations.
        """
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read a text file from the workspace."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to workspace to read.",
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        """Execute the read file tool.

        Args:
            path: Path relative to workspace.

        Returns:
            ToolResult with file content or ToolError on failure.
        """
        try:
            path_arg = kwargs.get("path")
            if not path_arg:
                return ToolError(
                    tool_name=self.name,
                    error_message="path is required.",
                    error_type="validation",
                )

            resolved_path = resolve_within_workspace(self.workspace, path_arg)

            if not resolved_path.exists():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"File not found: {path_arg}",
                    error_type="not_found",
                    metadata={"requested_path": path_arg},
                )

            if not resolved_path.is_file():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"Path is not a file: {path_arg}",
                    error_type="validation",
                    metadata={"requested_path": path_arg},
                )

            # Check file size
            file_size = resolved_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return ToolError(
                    tool_name=self.name,
                    error_message=f"File too large ({file_size} bytes). Maximum: {self.MAX_FILE_SIZE} bytes.",
                    error_type="execution",
                    metadata={"file_size": file_size, "max_size": self.MAX_FILE_SIZE},
                )

            # Check for binary content
            try:
                with open(resolved_path, "rb") as f:
                    chunk = f.read(self.BINARY_THRESHOLD)
                    if self._is_binary(chunk):
                        return ToolError(
                            tool_name=self.name,
                            error_message=f"File appears to be binary: {path_arg}",
                            error_type="validation",
                            metadata={"requested_path": path_arg},
                        )
            except UnicodeDecodeError:
                return ToolError(
                    tool_name=self.name,
                    error_message=f"File is not valid text: {path_arg}",
                    error_type="validation",
                    metadata={"requested_path": path_arg},
                )

            # Read file content
            content = resolved_path.read_text(encoding="utf-8")
            return ToolResult(
                tool_name=self.name,
                content=content,
                metadata={
                    "path": str(path_arg),
                    "file_size": file_size,
                    "line_count": len(content.splitlines()),
                },
            )

        except WorkspaceSafetyError as e:
            return ToolError(
                tool_name=self.name,
                error_message=str(e),
                error_type="validation",
            )
        except Exception as e:
            return ToolError(
                tool_name=self.name,
                error_message=f"Failed to read file: {e}",
                error_type="execution",
            )

    @staticmethod
    def _is_binary(chunk: bytes) -> bool:
        """Check if a byte chunk appears to be binary."""
        if not chunk:
            return False
        # If it contains null bytes, likely binary
        return b"\x00" in chunk


class WriteFileTool(Tool):
    """Write content to a text file within a workspace."""

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the write file tool.

        Args:
            workspace: The root workspace path for all file operations.
        """
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a text file in the workspace. Creates parent directories and overwrites existing files."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to workspace to write to.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file.",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        """Execute the write file tool.

        Args:
            path: Path relative to workspace.
            content: Content to write.

        Returns:
            ToolResult on success or ToolError on failure.
        """
        try:
            path_arg = kwargs.get("path")
            content = kwargs.get("content")

            if not path_arg:
                return ToolError(
                    tool_name=self.name,
                    error_message="path is required.",
                    error_type="validation",
                )

            if content is None:
                return ToolError(
                    tool_name=self.name,
                    error_message="content is required.",
                    error_type="validation",
                )

            resolved_path = resolve_within_workspace(self.workspace, path_arg)

            # Create parent directories if needed
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            resolved_path.write_text(str(content), encoding="utf-8")

            return ToolResult(
                tool_name=self.name,
                content=f"File written successfully: {path_arg}",
                metadata={
                    "path": str(path_arg),
                    "bytes_written": len(content.encode("utf-8")),
                    "is_new_file": True,
                },
            )

        except WorkspaceSafetyError as e:
            return ToolError(
                tool_name=self.name,
                error_message=str(e),
                error_type="validation",
            )
        except Exception as e:
            return ToolError(
                tool_name=self.name,
                error_message=f"Failed to write file: {e}",
                error_type="execution",
            )


class EditFileTool(Tool):
    """Edit a file by replacing a block of content."""

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the edit file tool.

        Args:
            workspace: The root workspace path for all file operations.
        """
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit a file by replacing a specific block of content. Useful for targeted modifications."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to workspace to edit.",
                },
                "old_content": {
                    "type": "string",
                    "description": "The exact content block to find and replace.",
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content to replace with.",
                },
            },
            "required": ["path", "old_content", "new_content"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        """Execute the edit file tool.

        Args:
            path: Path relative to workspace.
            old_content: Content block to find and replace.
            new_content: New content to write.

        Returns:
            ToolResult on success or ToolError on failure.
        """
        try:
            path_arg = kwargs.get("path")
            old_content = kwargs.get("old_content")
            new_content = kwargs.get("new_content")

            if not path_arg:
                return ToolError(
                    tool_name=self.name,
                    error_message="path is required.",
                    error_type="validation",
                )

            if old_content is None or new_content is None:
                return ToolError(
                    tool_name=self.name,
                    error_message="old_content and new_content are required.",
                    error_type="validation",
                )

            resolved_path = resolve_within_workspace(self.workspace, path_arg)

            if not resolved_path.exists():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"File not found: {path_arg}",
                    error_type="not_found",
                    metadata={"requested_path": path_arg},
                )

            if not resolved_path.is_file():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"Path is not a file: {path_arg}",
                    error_type="validation",
                    metadata={"requested_path": path_arg},
                )

            # Read current content
            current_content = resolved_path.read_text(encoding="utf-8")

            # Check if old_content exists
            if old_content not in current_content:
                return ToolError(
                    tool_name=self.name,
                    error_message=f"Content block not found in file: {path_arg}",
                    error_type="validation",
                    metadata={
                        "requested_path": path_arg,
                        "content_length": len(old_content),
                    },
                )

            # Replace content (only first occurrence to be safe)
            updated_content = current_content.replace(old_content, new_content, 1)

            # Write updated content
            resolved_path.write_text(updated_content, encoding="utf-8")

            return ToolResult(
                tool_name=self.name,
                content=f"File edited successfully: {path_arg}",
                metadata={
                    "path": str(path_arg),
                    "old_content_length": len(old_content),
                    "new_content_length": len(new_content),
                    "bytes_changed": len(new_content) - len(old_content),
                },
            )

        except WorkspaceSafetyError as e:
            return ToolError(
                tool_name=self.name,
                error_message=str(e),
                error_type="validation",
            )
        except Exception as e:
            return ToolError(
                tool_name=self.name,
                error_message=f"Failed to edit file: {e}",
                error_type="execution",
            )


class DeleteFileTool(Tool):
    """Delete a file within a workspace."""

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the delete file tool.

        Args:
            workspace: The root workspace path for all file operations.
        """
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def description(self) -> str:
        return "Delete a file in the workspace. This is a destructive operation."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to workspace to delete.",
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        """Execute the delete file tool.

        Args:
            path: Path relative to workspace.

        Returns:
            ToolResult on success or ToolError on failure.
        """
        try:
            path_arg = kwargs.get("path")

            if not path_arg:
                return ToolError(
                    tool_name=self.name,
                    error_message="path is required.",
                    error_type="validation",
                )

            resolved_path = resolve_within_workspace(self.workspace, path_arg)

            if not resolved_path.exists():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"File not found: {path_arg}",
                    error_type="not_found",
                    metadata={"requested_path": path_arg},
                )

            if not resolved_path.is_file():
                return ToolError(
                    tool_name=self.name,
                    error_message=f"Path is not a file: {path_arg}",
                    error_type="validation",
                    metadata={"requested_path": path_arg},
                )

            # Delete the file
            file_size = resolved_path.stat().st_size
            resolved_path.unlink()

            return ToolResult(
                tool_name=self.name,
                content=f"File deleted successfully: {path_arg}",
                metadata={
                    "path": str(path_arg),
                    "deleted_size": file_size,
                },
            )

        except WorkspaceSafetyError as e:
            return ToolError(
                tool_name=self.name,
                error_message=str(e),
                error_type="validation",
            )
        except Exception as e:
            return ToolError(
                tool_name=self.name,
                error_message=f"Failed to delete file: {e}",
                error_type="execution",
            )
