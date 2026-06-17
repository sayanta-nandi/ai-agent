from unittest.mock import AsyncMock, MagicMock
import json
from typing import AsyncIterator
import httpx
import pytest
from agent_tui.llm import (
    LLMClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    LLMToolCall,
    LLMFunctionCall,
    ToolSchema,
    OpenAIAdapter,
    message_to_dict,
)


def test_message_types_and_serialization() -> None:
    sys_msg = SystemMessage("You are an assistant.")
    assert sys_msg.role == "system"
    assert sys_msg.content == "You are an assistant."
    assert message_to_dict(sys_msg) == {"role": "system", "content": "You are an assistant."}

    user_msg = UserMessage("Hello!")
    assert user_msg.role == "user"
    assert user_msg.content == "Hello!"
    assert message_to_dict(user_msg) == {"role": "user", "content": "Hello!"}

    tool_call = LLMToolCall(
        id="call_123",
        type="function",
        function=LLMFunctionCall(name="read_file", arguments='{"path": "foo.txt"}'),
    )
    asst_msg = AssistantMessage("Thinking...", tool_calls=[tool_call])
    assert asst_msg.role == "assistant"
    assert asst_msg.content == "Thinking..."
    assert asst_msg.tool_calls == [tool_call]

    dict_asst = message_to_dict(asst_msg)
    assert dict_asst["role"] == "assistant"
    assert dict_asst["content"] == "Thinking..."
    assert len(dict_asst["tool_calls"]) == 1
    assert dict_asst["tool_calls"][0]["id"] == "call_123"
    assert dict_asst["tool_calls"][0]["type"] == "function"
    assert dict_asst["tool_calls"][0]["function"]["name"] == "read_file"
    assert dict_asst["tool_calls"][0]["function"]["arguments"] == '{"path": "foo.txt"}'

    tool_msg = ToolMessage("File contents here", tool_call_id="call_123")
    assert tool_msg.role == "tool"
    assert tool_msg.content == "File contents here"
    assert tool_msg.tool_call_id == "call_123"
    assert message_to_dict(tool_msg) == {
        "role": "tool",
        "content": "File contents here",
        "tool_call_id": "call_123",
    }


def test_tool_schema_serialization() -> None:
    schema = ToolSchema(
        name="read_file",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )
    assert schema.to_dict() == {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    }


def test_openai_adapter_prepare_request() -> None:
    adapter = OpenAIAdapter(base_url="https://api.openai.com/v1/")
    messages = [SystemMessage("system context"), UserMessage("hello")]
    tools = [
        ToolSchema(
            name="dummy",
            description="dummy tool",
            parameters={"type": "object", "properties": {}},
        )
    ]

    url, headers, payload = adapter.prepare_request(
        api_key="my-key",
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stream=True,
    )

    assert url == "https://api.openai.com/v1/chat/completions"
    assert headers == {
        "Authorization": "Bearer my-key",
        "Content-Type": "application/json",
    }
    assert payload["model"] == "gpt-4o"
    assert payload["stream"] is True
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "dummy"
    assert payload["tool_choice"] == "auto"


@pytest.mark.asyncio
async def test_llm_client_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(api_key="test-key", base_url="http://fake-api", model="gpt-4o")

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello user!",
                }
            }
        ]
    }

    class MockResponse:
        def __init__(self) -> None:
            self.status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return mock_response_data

    async def mock_post(self_client: httpx.AsyncClient, url: str, **kwargs: any) -> MockResponse:
        # Verify kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        assert kwargs["json"]["model"] == "gpt-4o"
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    messages = [UserMessage("Hi")]
    response = await client.complete(messages)
    assert isinstance(response, AssistantMessage)
    assert response.role == "assistant"
    assert response.content == "Hello user!"
    assert response.tool_calls is None


@pytest.mark.asyncio
async def test_llm_client_complete_with_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(api_key="test-key", base_url="http://fake-api", model="gpt-4o")

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Let me read that file for you.",
                    "tool_calls": [
                        {
                            "id": "call_xyz",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "test.txt"}',
                            },
                        }
                    ],
                }
            }
        ]
    }

    class MockResponse:
        def __init__(self) -> None:
            self.status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return mock_response_data

    async def mock_post(self_client: httpx.AsyncClient, url: str, **kwargs: any) -> MockResponse:
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    messages = [UserMessage("Read test.txt")]
    response = await client.complete(messages)

    assert isinstance(response, AssistantMessage)
    assert response.content == "Let me read that file for you."
    assert response.tool_calls is not None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].id == "call_xyz"
    assert response.tool_calls[0].type == "function"
    assert response.tool_calls[0].function.name == "read_file"
    assert response.tool_calls[0].function.arguments == '{"path": "test.txt"}'


@pytest.mark.asyncio
async def test_llm_client_complete_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(api_key="test-key", base_url="http://fake-api", model="gpt-4o")

    class MockResponse:
        def __init__(self) -> None:
            self.status_code = 200

        def raise_for_status(self) -> None:
            pass

        async def aiter_lines(self) -> AsyncIterator[str]:
            yield 'data: {"choices": [{"delta": {"role": "assistant", "content": "Hello"}}]}'
            yield ""  # Empty line should be skipped
            yield 'data: {"choices": [{"delta": {"content": " world"}}]}'
            yield "data: [DONE]"

    class AsyncContextManagerMock:
        async def __aenter__(self) -> MockResponse:
            return MockResponse()

        async def __aexit__(self, exc_type: any, exc_val: any, exc_tb: any) -> None:
            pass

    def mock_stream(self_client: httpx.AsyncClient, method: str, url: str, **kwargs: any) -> AsyncContextManagerMock:
        assert kwargs["json"]["stream"] is True
        return AsyncContextManagerMock()

    monkeypatch.setattr(httpx.AsyncClient, "stream", mock_stream)

    messages = [UserMessage("Hi")]
    chunks = []
    async for chunk in client.complete_stream(messages):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0].content == "Hello"
    assert chunks[1].content == " world"


def test_provider_adapter_injection_and_invalid() -> None:
    class DummyAdapter:

        def prepare_request(self, *args: any, **kwargs: any) -> tuple[str, dict, dict]:
            return "http://dummy", {}, {}

        def parse_response(self, *args: any, **kwargs: any) -> LLMMessage:
            return SystemMessage("dummy")

        def parse_stream_chunk(self, *args: any, **kwargs: any) -> LLMMessage | None:
            return None

    # Test custom adapter injection
    client = LLMClient(api_key="key", adapter=DummyAdapter())
    assert isinstance(client.adapter, DummyAdapter)

    # Test invalid provider name raises ValueError
    with pytest.raises(ValueError) as excinfo:
        LLMClient(api_key="key", provider="invalid-provider")
    assert "Unsupported provider" in str(excinfo.value)
