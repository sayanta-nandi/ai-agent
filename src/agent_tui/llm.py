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

    A concrete OpenAI-compatible implementation will be added after the provider decision.
    """

    async def complete(self, messages: list[LLMMessage]) -> LLMMessage:
        """Return a model completion for the supplied messages."""
        del messages
        raise NotImplementedError("LLMClient.complete is not implemented yet.")
