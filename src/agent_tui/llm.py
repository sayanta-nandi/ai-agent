"""LLM adapter boundary for the terminal AI agent."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, AsyncIterator, Protocol

import httpx


@dataclass(slots=True)
class LLMMessage:
    """A chat message passed between the agent and a model provider."""

    role: str
    content: str | None = None


@dataclass(slots=True)
class SystemMessage(LLMMessage):
    """A system message setting context/instructions for the LLM."""

    def __init__(self, content: str | None = None) -> None:
        self.role = "system"
        self.content = content


@dataclass(slots=True)
class UserMessage(LLMMessage):
    """A user message containing prompts or input."""

    def __init__(self, content: str | None = None) -> None:
        self.role = "user"
        self.content = content


@dataclass(slots=True)
class LLMFunctionCall:
    """Represents a function call requested by the model."""

    name: str | None = None
    arguments: str | None = None


@dataclass(slots=True)
class LLMToolCall:
    """Represents a tool call request from the model."""

    id: str | None = None
    type: str | None = "function"
    function: LLMFunctionCall | None = None
    index: int | None = None


@dataclass(slots=True)
class AssistantMessage(LLMMessage):
    """An assistant response, which can optionally include tool calls."""

    tool_calls: list[LLMToolCall] | None = None

    def __init__(self, content: str | None = None, tool_calls: list[LLMToolCall] | None = None) -> None:
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls


@dataclass(slots=True)
class ToolMessage(LLMMessage):
    """A message returning the result of a tool execution back to the model."""

    tool_call_id: str | None = None

    def __init__(self, content: str | None = None, tool_call_id: str | None = None) -> None:
        self.role = "tool"
        self.content = content
        self.tool_call_id = tool_call_id


@dataclass(slots=True)
class ToolSchema:
    """Defined schema for a tool that can be exposed to the model."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert schema to OpenAI compatible function tool representation."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def message_to_dict(message: LLMMessage) -> dict[str, Any]:
    """Serialize an LLMMessage (or its subclasses) to an OpenAI-compatible dict."""
    data: dict[str, Any] = {
        "role": message.role,
        "content": message.content,
    }

    # Extract tool_calls if available
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        data["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type or "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
            if tc.function
        ]

    # Extract tool_call_id if available
    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id:
        data["tool_call_id"] = tool_call_id

    return data


class ProviderAdapter(Protocol):
    """Interface for converting messages and schemas to/from specific provider APIs."""

    def prepare_request(
        self,
        api_key: str,
        model: str,
        messages: list[LLMMessage],
        tools: list[ToolSchema] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Prepare final URL, headers, and json payload for the provider."""
        ...

    def parse_response(self, response_data: dict[str, Any]) -> LLMMessage:
        """Parse raw JSON response into an LLMMessage."""
        ...

    def parse_stream_chunk(self, chunk_data: dict[str, Any]) -> LLMMessage | None:
        """Parse raw JSON chunk from stream delta into an LLMMessage."""
        ...


class OpenAIAdapter:
    """Adapter for OpenAI-compatible completions API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def prepare_request(
        self,
        api_key: str,
        model: str,
        messages: list[LLMMessage],
        tools: list[ToolSchema] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [message_to_dict(msg) for msg in messages],
            "stream": stream,
        }
        if tools:
            payload["tools"] = [tool.to_dict() for tool in tools]
            if tool_choice:
                payload["tool_choice"] = tool_choice
            else:
                payload["tool_choice"] = "auto"
        return url, headers, payload

    def parse_response(self, response_data: dict[str, Any]) -> LLMMessage:
        choices = response_data.get("choices", [])
        if not choices:
            raise ValueError("No choices returned from LLM response.")
        message_data = choices[0].get("message", {})
        role = message_data.get("role", "assistant")
        content = message_data.get("content")

        tool_calls_data = message_data.get("tool_calls")
        tool_calls = None
        if tool_calls_data is not None:
            tool_calls = []
            for tc in tool_calls_data:
                func_data = tc.get("function", {})
                tool_calls.append(
                    LLMToolCall(
                        id=tc.get("id"),
                        type=tc.get("type", "function"),
                        function=LLMFunctionCall(
                            name=func_data.get("name"),
                            arguments=func_data.get("arguments"),
                        ),
                    )
                )

        if role == "assistant":
            return AssistantMessage(content=content, tool_calls=tool_calls)
        elif role == "system":
            return SystemMessage(content=content)
        elif role == "user":
            return UserMessage(content=content)
        elif role == "tool":
            return ToolMessage(
                content=content,
                tool_call_id=message_data.get("tool_call_id"),
            )
        else:
            return LLMMessage(role=role, content=content)

    def parse_stream_chunk(self, chunk_data: dict[str, Any]) -> LLMMessage | None:
        choices = chunk_data.get("choices", [])
        if not choices:
            return None
        delta_data = choices[0].get("delta", {})
        role = delta_data.get("role", "assistant")
        content = delta_data.get("content")

        tool_calls_data = delta_data.get("tool_calls")
        tool_calls = None
        if tool_calls_data is not None:
            tool_calls = []
            for tc in tool_calls_data:
                func_data = tc.get("function", {})
                tool_calls.append(
                    LLMToolCall(
                        id=tc.get("id"),
                        type=tc.get("type", "function"),
                        function=LLMFunctionCall(
                            name=func_data.get("name"),
                            arguments=func_data.get("arguments"),
                        ),
                        index=tc.get("index"),
                    )
                )

        if role == "assistant" or (content is not None or tool_calls is not None):
            return AssistantMessage(content=content, tool_calls=tool_calls)
        elif role == "system":
            return SystemMessage(content=content)
        elif role == "user":
            return UserMessage(content=content)
        elif role == "tool":
            return ToolMessage(
                content=content,
                tool_call_id=delta_data.get("tool_call_id"),
            )
        else:
            return LLMMessage(role=role, content=content)


class LLMClient:
    """Async LLM client interface.

    DECISION:
    The V1 provider choice is explicitly deferred to a default OpenAI-compatible
    adapter. This adapter expects the model provider to conform to OpenAI's
    Chat Completions API.

    ASSUMPTIONS & DESIGN FOR LIVE API CALLS:
    1. Base URL & Path:
       The endpoint is constructed by appending `/chat/completions` to the configured
       `base_url` (e.g. `https://api.openai.com/v1/chat/completions`).
    2. Authentication:
       Requests are sent with an `Authorization: Bearer <api_key>` header.
    3. Payload (JSON format):
       - `model`: (str) matching `AgentSettings.model`.
       - `messages`: List of dicts, each with `role` ("system", "user", "assistant",
         "tool") and `content` (str).
       - `tools`: Optional list of tool schemas (defined in downstream tool registry).
       - `tool_choice`: Optional string/dict controlling tool invocation (e.g., "auto").
       - `stream`: Optional boolean to enable chunked text/event-stream responses.
    4. Response Parsing:
       - Status Code: A successful response yields HTTP 200 OK.
       - Text completion: Parsed from `choices[0].message.content`.
       - Tool calls: Parsed from `choices[0].message.tool_calls`, mapping to
         `id` (str), `type` ("function"), and `function` (dict with `name` and `arguments`).
     5. Streaming:
        - Server-sent events (`data: ` chunks) are processed to support real-time token yielding.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        provider: str = "openai",
        adapter: ProviderAdapter | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.provider = provider

        if adapter is not None:
            self.adapter = adapter
        elif provider == "openai":
            self.adapter = OpenAIAdapter(base_url=self.base_url)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSchema] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMMessage:
        """Return a model completion for the supplied messages."""
        url, headers, payload = self.adapter.prepare_request(
            api_key=self.api_key,
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            stream=False,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            response_data = response.json()
            return self.adapter.parse_response(response_data)

    async def complete_stream(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSchema] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMMessage]:
        """Return an async generator yielding model completion message chunks."""
        url, headers, payload = self.adapter.prepare_request(
            api_key=self.api_key,
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            stream=True,
        )

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_json = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        msg = self.adapter.parse_stream_chunk(chunk_json)
                        if msg is not None:
                            yield msg


