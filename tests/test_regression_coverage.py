"""Regression coverage for core agent-tui behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agent_tui.agent import AgentSession
from agent_tui.config import load_settings
from agent_tui.llm import AssistantMessage, LLMFunctionCall, LLMToolCall, ToolMessage, UserMessage
from agent_tui.safety import SafetyLevel, SafetyManager, resolve_within_workspace
from agent_tui.tools import ListFilesTool, ReadFileTool, RunCommandTool, Tool, ToolError, ToolRegistry, ToolResult, WriteFileTool


class FakeLLMClient:
    def __init__(self, response: AssistantMessage) -> None:
        self.response = response
        self.calls: list[tuple[list[Any], list[dict[str, Any]] | None]] = []

    async def complete(self, messages: list[Any], tools: list[dict[str, Any]] | None = None) -> AssistantMessage:
        self.calls.append((messages, tools))
        return self.response

    async def complete_stream(self, messages: list[Any], tools: list[dict[str, Any]] | None = None):
        self.calls.append((messages, tools))
        yield self.response


class FakeTool(Tool):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Fake read-only tool."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        self.calls.append(kwargs)
        return ToolResult(tool_name=self.name, content=f"read {kwargs['path']}")


def test_config_loading_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "env-key")
    monkeypatch.setenv("MODEL", "env-model")

    settings = load_settings()

    assert settings.api_key == "env-key"
    assert settings.model == "env-model"


def test_workspace_safety_rejects_escape_attempt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(ValueError, match="Path escapes workspace"):
        resolve_within_workspace(workspace, outside)


@pytest.mark.asyncio
async def test_file_tools_round_trip_within_workspace(tmp_path: Path) -> None:
    write_tool = WriteFileTool(tmp_path)
    read_tool = ReadFileTool(tmp_path)
    list_tool = ListFilesTool(tmp_path)

    write_result = await write_tool.execute(path="notes.txt", content="hello")
    read_result = await read_tool.execute(path="notes.txt")
    list_result = await list_tool.execute(path=".", max_depth=1)

    assert isinstance(write_result, ToolResult)
    assert isinstance(read_result, ToolResult)
    assert read_result.content == "hello"
    assert isinstance(list_result, ToolResult)
    assert "notes.txt" in list_result.content


@pytest.mark.asyncio
async def test_command_tool_uses_safe_mock_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = RunCommandTool(tmp_path)

    async def fake_run(args: list[str], timeout: float) -> ToolResult:
        assert args == ["echo", "ok"]
        assert timeout == 1.5
        return ToolResult(
            tool_name="run_command",
            content="STDOUT:\nok",
            metadata={"exit_code": 0, "command": " ".join(args)},
        )

    monkeypatch.setattr(tool, "_run_with_timeout", fake_run)

    result = await tool.execute(command="echo ok", timeout=1.5)

    assert isinstance(result, ToolResult)
    assert result.metadata["exit_code"] == 0


def test_safety_classification_and_confirmation_prompt() -> None:
    manager = SafetyManager()

    assert manager.classify_tool("read_file") == SafetyLevel.SAFE
    assert manager.classify_tool("run_command") == SafetyLevel.RISKY
    assert manager.is_safe("list_files") is True
    assert "run_command" in manager._format_confirmation_prompt("run_command", {"command": "echo ok"})


@pytest.mark.asyncio
async def test_agent_loop_uses_fake_llm_and_safe_tool() -> None:
    tool = FakeTool()
    registry = ToolRegistry()
    registry.register(tool)
    client = FakeLLMClient(
        AssistantMessage(
            content="done",
            tool_calls=[
                LLMToolCall(
                    id="call-1",
                    type="function",
                    function=LLMFunctionCall(name="read_file", arguments='{"path": "notes.txt"}'),
                )
            ],
        )
    )

    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=SafetyManager(),
        max_iterations=1,
    )

    messages = [message async for message in session.run("Read notes.txt", stream=False)]

    assert isinstance(messages[0], UserMessage)
    assert any(isinstance(message, ToolMessage) for message in messages)
    assert tool.calls == [{"path": "notes.txt"}]
    assert client.calls


def test_tool_result_serialization_for_model_message() -> None:
    result = ToolResult(
        tool_name="read_file",
        content="file contents",
        metadata={"path": "notes.txt", "file_size": 13},
    )

    message = ToolRegistry.result_to_model_message(result)

    assert message == {
        "role": "tool",
        "content": "file contents",
        "metadata": {
            "tool_name": "read_file",
            "path": "notes.txt",
            "file_size": 13,
        },
    }


def test_local_docs_include_pytest_command() -> None:
    readme = Path(__file__).resolve().parents[1] / "README.md"

    assert "pytest" in readme.read_text(encoding="utf-8")
