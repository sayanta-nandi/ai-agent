import os
from pathlib import Path
import pytest

from agent_tui.safety import WorkspaceSafetyError, resolve_within_workspace, resolve_workspace


def test_resolve_workspace_returns_absolute_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    resolved = resolve_workspace(workspace)

    assert resolved.is_absolute()
    assert resolved == workspace.resolve()


def test_resolve_within_workspace_allows_nested_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    nested_file = workspace / "subdir" / "file.txt"
    nested_file.parent.mkdir()
    nested_file.write_text("content", encoding="utf-8")

    resolved = resolve_within_workspace(workspace, nested_file.relative_to(workspace))

    assert resolved == nested_file.resolve()
    assert resolved.is_relative_to(workspace.resolve())


def test_resolve_within_workspace_rejects_path_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(WorkspaceSafetyError, match="Path escapes workspace"):
        resolve_within_workspace(workspace, Path("..") / outside.name)


def test_resolve_within_workspace_rejects_absolute_path_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(WorkspaceSafetyError, match="Path escapes workspace"):
        resolve_within_workspace(workspace, outside)


@pytest.mark.skipif(
    hasattr(os, "symlink") is False,
    reason="symlink is not supported on this platform",
)
def test_resolve_within_workspace_rejects_symlink_escape_attempt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    safe_link = workspace / "outside-link"

    try:
        safe_link.symlink_to(outside_dir, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"Cannot create symlink on this platform: {exc}")

    with pytest.raises(WorkspaceSafetyError, match="Path escapes workspace"):
        resolve_within_workspace(workspace, safe_link / "secret.txt")
