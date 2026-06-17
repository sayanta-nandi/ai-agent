"""Unit tests for the Textual TUI interface."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from textual.widgets import Input

from agent_tui.agent import AgentSession
from agent_tui.config import AgentSettings
from agent_tui.llm import AssistantMessage, LLMFunctionCall, LLMToolCall
from agent_tui.safety import SafetyManager
from agent_tui.tools.registry import ToolRegistry
from agent_tui.tui.app import AgentTuiApp, ConfirmationModal, MessageWidget
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from test_agent import DummyTool, FakeLLMClient


@pytest.mark.asyncio
async def test_tui_app_rendering_and_submission() -> None:
    settings = AgentSettings(api_key="test_key", model="test_model", workspace=".")
    client = FakeLLMClient([AssistantMessage("Hello from agent!")])
    registry = ToolRegistry()
    safety_manager = SafetyManager()
    session = AgentSession(client=client, registry=registry, safety_manager=safety_manager)

    app = AgentTuiApp(session=session, settings=settings)

    async with app.run_test() as pilot:
        # Check that widgets are mounted correctly
        assert app.chat_scroll is not None
        assert app.input_widget is not None
        assert app.tool_log_widget is not None
        assert app.output_viewer_widget is not None

        # Focus input and enter text
        app.input_widget.focus()
        app.input_widget.value = "Hello"
        await pilot.press("enter")

        # Let the async agent run process
        await pilot.pause()

        # Check message widgets
        messages = list(app.chat_scroll.query(MessageWidget))
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].raw_content == "Hello"
        assert messages[1].role == "assistant"
        assert messages[1].raw_content == "Hello from agent!"


@pytest.mark.asyncio
async def test_tui_help_command() -> None:
    settings = AgentSettings(api_key="test_key", model="test_model", workspace=".")
    client = FakeLLMClient([])
    registry = ToolRegistry()
    safety_manager = SafetyManager()
    session = AgentSession(client=client, registry=registry, safety_manager=safety_manager)

    app = AgentTuiApp(session=session, settings=settings)

    async with app.run_test() as pilot:
        # Type '/help' in input and submit
        app.input_widget.value = "/help"
        await pilot.press("enter")
        await pilot.pause()

        # Check that we did not run the agent (no user message widget mounted)
        messages = list(app.chat_scroll.query(MessageWidget))
        assert len(messages) == 0


@pytest.mark.asyncio
async def test_tui_safety_confirmation_allow() -> None:
    settings = AgentSettings(api_key="test_key", model="test_model", workspace=".")

    # Register risky tool
    tool = DummyTool("write_file")
    registry = ToolRegistry()
    registry.register(tool)

    safety_manager = SafetyManager()

    tool_call = LLMToolCall(
        id="call_111",
        type="function",
        function=LLMFunctionCall(name="write_file", arguments='{"path": "test.txt"}'),
    )
    first_response = AssistantMessage("I will write it.", tool_calls=[tool_call])
    second_response = AssistantMessage("Successfully wrote file.")

    client = FakeLLMClient([first_response, second_response])
    session = AgentSession(client=client, registry=registry, safety_manager=safety_manager)

    app = AgentTuiApp(session=session, settings=settings)

    async with app.run_test() as pilot:
        app.input_widget.value = "Create test file"
        await pilot.press("enter")

        # Wait for safety confirmation modal to be pushed
        for _ in range(50):
            if isinstance(app.screen, ConfirmationModal):
                break
            await asyncio.sleep(0.02)
        assert isinstance(app.screen, ConfirmationModal)

        # Press 'y' to confirm the action
        await pilot.press("y")
        
        # Wait for safety confirmation modal to be dismissed
        for _ in range(50):
            if not isinstance(app.screen, ConfirmationModal):
                break
            await asyncio.sleep(0.02)
        assert not isinstance(app.screen, ConfirmationModal)

        # Verify tool was executed
        assert tool.called_with == {"path": "test.txt"}


@pytest.mark.asyncio
async def test_tui_safety_confirmation_deny() -> None:
    settings = AgentSettings(api_key="test_key", model="test_model", workspace=".")

    # Register risky tool
    tool = DummyTool("write_file")
    registry = ToolRegistry()
    registry.register(tool)

    safety_manager = SafetyManager()

    tool_call = LLMToolCall(
        id="call_222",
        type="function",
        function=LLMFunctionCall(name="write_file", arguments='{"path": "test.txt"}'),
    )
    first_response = AssistantMessage("I will write it.", tool_calls=[tool_call])
    second_response = AssistantMessage("Blocked.")

    client = FakeLLMClient([first_response, second_response])
    session = AgentSession(client=client, registry=registry, safety_manager=safety_manager)

    app = AgentTuiApp(session=session, settings=settings)

    async with app.run_test() as pilot:
        app.input_widget.value = "Create test file"
        await pilot.press("enter")

        # Wait for safety confirmation modal to be pushed
        for _ in range(50):
            if isinstance(app.screen, ConfirmationModal):
                break
            await asyncio.sleep(0.02)
        assert isinstance(app.screen, ConfirmationModal)

        # Press 'n' to deny the action
        await pilot.press("n")
        
        # Wait for safety confirmation modal to be dismissed
        for _ in range(50):
            if not isinstance(app.screen, ConfirmationModal):
                break
            await asyncio.sleep(0.02)
        assert not isinstance(app.screen, ConfirmationModal)

        # Verify tool was NOT executed
        assert tool.called_with is None
