import asyncio
import os
from pathlib import Path
import pytest

from agent_tui.safety import (
    SafetyLevel,
    SafetyManager,
    WorkspaceSafetyError,
    resolve_within_workspace,
    resolve_workspace,
)


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


# SafetyManager Tests


def test_safety_manager_classifies_safe_tools() -> None:
    manager = SafetyManager()

    assert manager.classify_tool("read_file") == SafetyLevel.SAFE
    assert manager.classify_tool("list_files") == SafetyLevel.SAFE


def test_safety_manager_classifies_risky_tools() -> None:
    manager = SafetyManager()

    assert manager.classify_tool("write_file") == SafetyLevel.RISKY
    assert manager.classify_tool("edit_file") == SafetyLevel.RISKY
    assert manager.classify_tool("delete_file") == SafetyLevel.RISKY
    assert manager.classify_tool("run_command") == SafetyLevel.RISKY


def test_safety_manager_rejects_unknown_tools() -> None:
    manager = SafetyManager()

    with pytest.raises(ValueError, match="Unknown tool"):
        manager.classify_tool("unknown_tool")


def test_safety_manager_is_safe_returns_true_for_safe_tools() -> None:
    manager = SafetyManager()

    assert manager.is_safe("read_file") is True
    assert manager.is_safe("list_files") is True


def test_safety_manager_is_safe_returns_false_for_risky_tools() -> None:
    manager = SafetyManager()

    assert manager.is_safe("write_file") is False
    assert manager.is_safe("delete_file") is False


def test_safety_manager_is_safe_returns_false_for_unknown_tools() -> None:
    manager = SafetyManager()

    assert manager.is_safe("unknown_tool") is False


def test_safety_manager_is_risky_returns_true_for_risky_tools() -> None:
    manager = SafetyManager()

    assert manager.is_risky("write_file") is True
    assert manager.is_risky("edit_file") is True
    assert manager.is_risky("delete_file") is True
    assert manager.is_risky("run_command") is True


def test_safety_manager_is_risky_returns_false_for_safe_tools() -> None:
    manager = SafetyManager()

    assert manager.is_risky("read_file") is False
    assert manager.is_risky("list_files") is False


def test_safety_manager_is_risky_returns_false_for_unknown_tools() -> None:
    manager = SafetyManager()

    assert manager.is_risky("unknown_tool") is False


@pytest.mark.asyncio
async def test_safety_manager_validate_tool_call_allows_safe_tools() -> None:
    manager = SafetyManager()

    result = await manager.validate_tool_call("read_file", {"path": "test.txt"})

    assert result is True


@pytest.mark.asyncio
async def test_safety_manager_validate_tool_call_requires_confirmation_for_risky_tools() -> None:
    async def mock_handler(prompt: str) -> bool:
        return True

    manager = SafetyManager(confirmation_handler=mock_handler)

    result = await manager.validate_tool_call("write_file", {"path": "test.txt", "content": "data"})

    assert result is True


@pytest.mark.asyncio
async def test_safety_manager_validate_tool_call_rejects_unknown_tools() -> None:
    manager = SafetyManager()

    with pytest.raises(ValueError, match="Unknown tool"):
        await manager.validate_tool_call("unknown_tool", {})


@pytest.mark.asyncio
async def test_safety_manager_custom_confirmation_handler() -> None:
    confirmation_calls = []

    async def mock_handler(prompt: str) -> bool:
        confirmation_calls.append(prompt)
        return False

    manager = SafetyManager(confirmation_handler=mock_handler)

    result = await manager.request_confirmation("delete_file", {"path": "important.txt"})

    assert result is False
    assert len(confirmation_calls) == 1
    assert "delete_file" in confirmation_calls[0]


@pytest.mark.asyncio
async def test_safety_manager_sync_confirmation_handler() -> None:
    """Test that sync handlers are also supported."""
    def sync_handler(prompt: str) -> bool:
        return True

    manager = SafetyManager(confirmation_handler=sync_handler)

    result = await manager.request_confirmation("write_file", {"path": "test.txt"})

    assert result is True


def test_safety_manager_format_confirmation_prompt() -> None:
    manager = SafetyManager()

    prompt = manager._format_confirmation_prompt(
        "delete_file",
        {"path": "important.txt", "recursive": True},
    )

    assert "delete_file" in prompt
    assert "important.txt" in prompt
    assert "[y/n]" in prompt
