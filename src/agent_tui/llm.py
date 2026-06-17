"""LLM adapter boundary for the terminal AI agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LLMMessage:
    """A chat message passed between the agent and a model provider."""

    role: str
    content: str


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

    async def complete(self, messages: list[LLMMessage]) -> LLMMessage:
        """Return a model completion for the supplied messages."""
        del messages
        raise NotImplementedError("LLMClient.complete is not implemented yet.")

