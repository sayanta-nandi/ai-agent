"""Safety helpers for workspace-constrained agent operations."""

from __future__ import annotations

from pathlib import Path


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
