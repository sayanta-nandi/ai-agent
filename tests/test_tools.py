"""Tests for tool interface and registry."""

from __future__ import annotations

import json
import pytest
from typing import Any

from agent_tui.tools import Tool, ToolResult, ToolError, ToolRegistry


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name: str = "mock_tool", should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A mock tool for testing."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"},
            },
            "required": ["param1"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult | ToolError:
        if self._should_fail:
            return ToolError(
                tool_name=self._name,
                error_message="Mock tool failed intentionally.",
                error_type="execution",
            )
        return ToolResult(
            tool_name=self._name,
            content=f"Executed with {kwargs}",
            metadata={"param_count": len(kwargs)},
        )


class TestToolResult:
    """Tests for ToolResult."""

    def test_tool_result_creation(self) -> None:
        """Test creating a ToolResult."""
        result = ToolResult(
            tool_name="test_tool",
            content="Success!",
            metadata={"key": "value"},
        )
        assert result.tool_name == "test_tool"
        assert result.content == "Success!"
        assert result.metadata == {"key": "value"}

    def test_tool_result_without_metadata(self) -> None:
        """Test creating a ToolResult without metadata."""
        result = ToolResult(tool_name="test_tool", content="Result")
        assert result.metadata is None


class TestToolError:
    """Tests for ToolError."""

    def test_tool_error_creation(self) -> None:
        """Test creating a ToolError."""
        error = ToolError(
            tool_name="test_tool",
            error_message="Something went wrong",
            error_type="execution",
            metadata={"line": 42},
        )
        assert error.tool_name == "test_tool"
        assert error.error_message == "Something went wrong"
        assert error.error_type == "execution"

    def test_tool_error_default_type(self) -> None:
        """Test ToolError defaults to 'other' type."""
        error = ToolError(
            tool_name="test_tool",
            error_message="Error",
        )
        assert error.error_type == "other"


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        assert registry.get("test_tool") == tool

    def test_register_duplicate_raises_error(self) -> None:
        """Test that registering a duplicate tool raises ValueError."""
        registry = ToolRegistry()
        tool1 = MockTool("duplicate")
        tool2 = MockTool("duplicate")
        registry.register(tool1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)

    def test_get_nonexistent_tool(self) -> None:
        """Test getting a tool that doesn't exist."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self) -> None:
        """Test listing all registered tools."""
        registry = ToolRegistry()
        tool1 = MockTool("tool1")
        tool2 = MockTool("tool2")
        registry.register(tool1)
        registry.register(tool2)
        tools = registry.list_tools()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools

    def test_tool_schemas_for_model(self) -> None:
        """Test generating OpenAI-compatible tool schemas."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        schemas = registry.tool_schemas_for_model()
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "A mock tool for testing."
        assert "parameters" in schema["function"]

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self) -> None:
        """Test executing a successful tool call."""
        registry = ToolRegistry()
        tool = MockTool("test_tool", should_fail=False)
        registry.register(tool)
        result = await registry.execute_tool_call("test_tool", {"param1": "value"})
        assert isinstance(result, ToolResult)
        assert result.tool_name == "test_tool"
        assert "param1" in result.content

    @pytest.mark.asyncio
    async def test_execute_tool_call_failure(self) -> None:
        """Test executing a tool that fails."""
        registry = ToolRegistry()
        tool = MockTool("test_tool", should_fail=True)
        registry.register(tool)
        result = await registry.execute_tool_call("test_tool", {})
        assert isinstance(result, ToolError)
        assert result.tool_name == "test_tool"
        assert "Mock tool failed" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self) -> None:
        """Test executing a tool that doesn't exist."""
        registry = ToolRegistry()
        result = await registry.execute_tool_call("nonexistent", {})
        assert isinstance(result, ToolError)
        assert result.error_type == "not_found"
        assert "not found" in result.error_message

    def test_result_to_model_message_success(self) -> None:
        """Test converting a ToolResult to a model message."""
        result = ToolResult(
            tool_name="test_tool",
            content="Success!",
            metadata={"key": "value"},
        )
        message = ToolRegistry.result_to_model_message(result)
        assert message["role"] == "tool"
        assert message["content"] == "Success!"
        assert message["metadata"]["tool_name"] == "test_tool"
        assert message["metadata"]["key"] == "value"

    def test_result_to_model_message_error(self) -> None:
        """Test converting a ToolError to a model message."""
        error = ToolError(
            tool_name="test_tool",
            error_message="Execution failed",
            error_type="execution",
        )
        message = ToolRegistry.result_to_model_message(error)
        assert message["role"] == "tool"
        assert message["content"] == "Execution failed"
        assert message["metadata"]["tool_name"] == "test_tool"
        assert message["metadata"]["error_type"] == "execution"

    def test_model_tool_call_to_execution_args_valid_json(self) -> None:
        """Test parsing valid JSON tool call arguments."""
        json_args = json.dumps({"param1": "value", "param2": 42})
        args = ToolRegistry.model_tool_call_to_execution_args(json_args)
        assert args == {"param1": "value", "param2": 42}

    def test_model_tool_call_to_execution_args_invalid_json(self) -> None:
        """Test parsing invalid JSON tool call arguments."""
        invalid_json = "{invalid json}"
        with pytest.raises(json.JSONDecodeError):
            ToolRegistry.model_tool_call_to_execution_args(invalid_json)

    @pytest.mark.asyncio
    async def test_full_workflow(self) -> None:
        """Test a complete workflow: register, schema, execute, convert result."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)

        # Get schemas for model
        schemas = registry.tool_schemas_for_model()
        assert len(schemas) == 1

        # Execute tool call
        result = await registry.execute_tool_call("test_tool", {"param1": "test"})
        assert isinstance(result, ToolResult)

        # Convert result to model message
        message = ToolRegistry.result_to_model_message(result)
        assert message["role"] == "tool"
