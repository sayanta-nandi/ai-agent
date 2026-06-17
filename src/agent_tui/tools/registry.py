"""Tool registry for discovering and invoking tools."""

from __future__ import annotations

import json
from typing import Any

from agent_tui.tools.base import Tool, ToolError, ToolResult


class ToolRegistry:
    """Registry and manager for all available tools.

    Handles:
    - Discovering registered tools
    - Converting model tool calls to internal tool executions
    - Serializing tool results back to model messages
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry.

        Args:
            tool: A Tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Retrieve a tool by name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            The Tool instance, or None if not found.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools.

        Returns:
            A list of all Tool instances in the registry.
        """
        return list(self._tools.values())

    def tool_schemas_for_model(self) -> list[dict[str, Any]]:
        """Generate OpenAI-compatible tool schemas for model requests.

        Returns:
            A list of tool schemas suitable for OpenAI's tools parameter.
        """
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
            })
        return schemas

    async def execute_tool_call(
        self,
        tool_name: str,
        tool_arguments: dict[str, Any],
    ) -> ToolResult | ToolError:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: The name of the tool to execute.
            tool_arguments: The arguments to pass to the tool.

        Returns:
            A ToolResult on success, or a ToolError on failure.
        """
        tool = self.get(tool_name)
        if tool is None:
            return ToolError(
                tool_name=tool_name,
                error_message=f"Tool '{tool_name}' not found in registry.",
                error_type="not_found",
            )

        try:
            return await tool.execute(**tool_arguments)
        except Exception as e:
            return ToolError(
                tool_name=tool_name,
                error_message=f"Tool execution failed: {e}",
                error_type="execution",
                metadata={"exception_type": type(e).__name__},
            )

    @staticmethod
    def result_to_model_message(result: ToolResult | ToolError) -> dict[str, Any]:
        """Convert a tool result to a model message format.

        Serializes the result for inclusion in LLM message history.

        Args:
            result: A ToolResult or ToolError to serialize.

        Returns:
            A dict suitable for adding to LLM message history.
        """
        if isinstance(result, ToolResult):
            return {
                "role": "tool",
                "content": result.content,
                "metadata": {
                    "tool_name": result.tool_name,
                    **(result.metadata or {}),
                }
            }
        else:  # ToolError
            return {
                "role": "tool",
                "content": result.error_message,
                "metadata": {
                    "tool_name": result.tool_name,
                    "error_type": result.error_type,
                    **(result.metadata or {}),
                }
            }

    @staticmethod
    def model_tool_call_to_execution_args(
        tool_call_arguments_json: str,
    ) -> dict[str, Any]:
        """Parse a model tool call's arguments from JSON.

        Args:
            tool_call_arguments_json: JSON string of tool call arguments.

        Returns:
            A dict of keyword arguments to pass to tool.execute().

        Raises:
            json.JSONDecodeError: If JSON parsing fails.
        """
        return json.loads(tool_call_arguments_json)
