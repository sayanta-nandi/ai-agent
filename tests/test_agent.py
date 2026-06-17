from unittest.mock import AsyncMock, MagicMock
from typing import Any, AsyncIterator
import pytest

from agent_tui.agent import AgentSession
from agent_tui.llm import (
    LLMClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    LLMToolCall,
    LLMFunctionCall,
)
from agent_tui.safety import SafetyManager
from agent_tui.tools.base import Tool, ToolResult, ToolError
from agent_tui.tools.registry import ToolRegistry


class FakeLLMClient:
    def __init__(self, responses: list[LLMMessage | list[LLMMessage]]) -> None:
        self.responses = responses
        self.calls = []

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[Any] | None = None,
        tool_choice: Any | None = None,
    ) -> LLMMessage:
        self.calls.append((list(messages), tools))
        if not self.responses:
            return AssistantMessage("No more responses queued in FakeLLMClient.")
        res = self.responses.pop(0)
        if isinstance(res, list):
            return res[-1]
        return res

    async def complete_stream(
        self,
        messages: list[LLMMessage],
        tools: list[Any] | None = None,
        tool_choice: Any | None = None,
    ) -> AsyncIterator[LLMMessage]:
        self.calls.append((list(messages), tools))
        if not self.responses:
            yield AssistantMessage("No more responses queued in FakeLLMClient.")
            return
        res = self.responses.pop(0)
        if isinstance(res, list):
            for chunk in res:
                yield chunk
        else:
            yield res


class DummyTool(Tool):
    def __init__(self, name: str) -> None:
        self._name = name
        self.called_with = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Dummy tool {self._name}"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        self.called_with = kwargs
        return ToolResult(tool_name=self._name, content=f"dummy result for {kwargs.get('path')}")


@pytest.mark.asyncio
async def test_agent_session_basic_chat() -> None:
    fake_response = AssistantMessage("Hello! How can I help you today?")
    client = FakeLLMClient([fake_response])
    registry = ToolRegistry()
    safety_manager = SafetyManager()

    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=safety_manager,
        system_prompt="You are a helpful assistant.",
    )

    results = []
    async for event in session.run("Hi", stream=False):
        results.append(event)

    assert len(results) == 2
    assert isinstance(results[0], UserMessage)
    assert results[0].content == "Hi"
    assert isinstance(results[1], AssistantMessage)
    assert results[1].content == "Hello! How can I help you today?"

    assert len(session.conversation_history) == 3
    assert isinstance(session.conversation_history[0], SystemMessage)
    assert session.conversation_history[0].content == "You are a helpful assistant."
    assert isinstance(session.conversation_history[1], UserMessage)
    assert isinstance(session.conversation_history[2], AssistantMessage)


@pytest.mark.asyncio
async def test_agent_session_tool_call_success() -> None:
    tool = DummyTool("read_file")
    registry = ToolRegistry()
    registry.register(tool)

    tool_call = LLMToolCall(
        id="call_123",
        type="function",
        function=LLMFunctionCall(name="read_file", arguments='{"path": "hello.txt"}'),
    )
    first_response = AssistantMessage("Let me read hello.txt", tool_calls=[tool_call])
    second_response = AssistantMessage("I have read it. It is done.")

    client = FakeLLMClient([first_response, second_response])
    safety_manager = SafetyManager()

    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=safety_manager,
    )

    results = []
    async for event in session.run("Read hello.txt", stream=False):
        results.append(event)

    assert len(results) == 4
    assert isinstance(results[0], UserMessage)
    assert isinstance(results[1], AssistantMessage)
    assert results[1].tool_calls == [tool_call]
    assert isinstance(results[2], ToolMessage)
    assert results[2].content == "dummy result for hello.txt"
    assert results[2].tool_call_id == "call_123"
    assert isinstance(results[3], AssistantMessage)

    assert tool.called_with == {"path": "hello.txt"}

    assert len(session.conversation_history) == 4
    assert session.conversation_history[0].role == "user"
    assert session.conversation_history[1].role == "assistant"
    assert session.conversation_history[2].role == "tool"
    assert session.conversation_history[3].role == "assistant"


@pytest.mark.asyncio
async def test_agent_session_tool_call_rejected_by_safety() -> None:
    tool = DummyTool("write_file")
    registry = ToolRegistry()
    registry.register(tool)

    tool_call = LLMToolCall(
        id="call_999",
        type="function",
        function=LLMFunctionCall(name="write_file", arguments='{"path": "hello.txt"}'),
    )
    first_response = AssistantMessage("Let me write hello.txt", tool_calls=[tool_call])
    second_response = AssistantMessage("I could not proceed because it was rejected.")

    client = FakeLLMClient([first_response, second_response])

    async def reject_handler(prompt: str) -> bool:
        return False

    safety_manager = SafetyManager(confirmation_handler=reject_handler)

    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=safety_manager,
    )

    results = []
    async for event in session.run("Write hello.txt", stream=False):
        results.append(event)

    assert len(results) == 4
    assert isinstance(results[2], ToolMessage)
    assert "rejected" in results[2].content
    assert results[2].tool_call_id == "call_999"

    assert tool.called_with is None


@pytest.mark.asyncio
async def test_agent_session_streaming() -> None:
    chunks = [
        AssistantMessage(content="Hello"),
        AssistantMessage(content=" world"),
        AssistantMessage(content="!"),
    ]
    client = FakeLLMClient([chunks])
    registry = ToolRegistry()
    safety_manager = SafetyManager()

    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=safety_manager,
    )

    results = []
    async for event in session.run("Hi", stream=True):
        results.append(event)

    assert len(results) == 4
    assert isinstance(results[0], UserMessage)
    assert results[1].content == "Hello"
    assert results[2].content == " world"
    assert results[3].content == "!"

    assert len(session.conversation_history) == 2
    assert session.conversation_history[0].role == "user"
    assert session.conversation_history[1].role == "assistant"
    assert session.conversation_history[1].content == "Hello world!"


@pytest.mark.asyncio
async def test_agent_session_streaming_with_tool_calls() -> None:
    chunks = [
        AssistantMessage(content="Thinking...", tool_calls=[
            LLMToolCall(
                id="call_abc",
                type="function",
                function=LLMFunctionCall(name="read_file", arguments=''),
                index=0
            )
        ]),
        AssistantMessage(tool_calls=[
            LLMToolCall(
                function=LLMFunctionCall(arguments='{"path": '),
                index=0
            )
        ]),
        AssistantMessage(tool_calls=[
            LLMToolCall(
                function=LLMFunctionCall(arguments='"foo.txt"}'),
                index=0
            )
        ]),
    ]

    tool = DummyTool("read_file")
    registry = ToolRegistry()
    registry.register(tool)

    second_response = AssistantMessage("Done reading.")

    client = FakeLLMClient([chunks, second_response])
    safety_manager = SafetyManager()

    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=safety_manager,
    )

    results = []
    async for event in session.run("Read foo.txt", stream=True):
        results.append(event)

    assert tool.called_with == {"path": "foo.txt"}


@pytest.mark.asyncio
async def test_agent_session_max_iterations() -> None:
    tool = DummyTool("read_file")
    registry = ToolRegistry()
    registry.register(tool)

    tool_call = LLMToolCall(
        id="call_loop",
        type="function",
        function=LLMFunctionCall(name="read_file", arguments='{"path": "a.txt"}'),
    )
    endless_response = AssistantMessage("Calling again", tool_calls=[tool_call])

    client = FakeLLMClient([endless_response] * 15)
    safety_manager = SafetyManager()

    session = AgentSession(
        client=client,
        registry=registry,
        safety_manager=safety_manager,
        max_iterations=3,
    )

    results = []
    async for event in session.run("Start", stream=False):
        results.append(event)

    assert len(results) == 7
    assert len(session.conversation_history) == 7
