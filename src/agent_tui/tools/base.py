"""Base tool interface and result types for the terminal AI agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(slots=True)
class ToolResult:
    """Result of a successful tool execution."""

    tool_name: str
    """The name of the tool that was executed."""

    content: str
    """The result content, typically serializable as a string."""

    metadata: dict[str, Any] | None = None
    """Optional metadata (e.g., file size, command exit code)."""


@dataclass(slots=True)
class ToolError:
    """Result of a failed tool execution."""

    tool_name: str
    """The name of the tool that failed."""

    error_message: str
    """The error message describing what went wrong."""

    error_type: Literal["validation", "execution", "permission", "not_found", "other"] = "other"
    """Classification of the error for better UX."""

    metadata: dict[str, Any] | None = None
    """Optional metadata (e.g., file path, line number)."""


class Tool(ABC):
    """Base class for all tools exposed to the agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique identifier for this tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON schema describing the tool's input parameters.

        This is used for OpenAI-compatible tool calling.
        """
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        """Execute the tool with the given parameters.

        Returns either a ToolResult on success or a ToolError on failure.
        """
        ...
