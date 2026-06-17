"""Agent orchestration boundary for the terminal AI agent."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator

from agent_tui.llm import (
    AssistantMessage,
    LLMClient,
    LLMFunctionCall,
    LLMMessage,
    LLMToolCall,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from agent_tui.safety import SafetyManager
from agent_tui.tools.base import ToolError, ToolResult
from agent_tui.tools.registry import ToolRegistry


class AgentSession:
    """Manages an agent session, maintaining history and running the reasoning loop."""

    def __init__(
        self,
        client: LLMClient,
        registry: ToolRegistry,
        safety_manager: SafetyManager,
        system_prompt: str | None = None,
        max_iterations: int = 10,
    ) -> None:
        """Initialize the AgentSession.

        Args:
            client: The LLM client to use for completions.
            registry: The tool registry to execute tool calls.
            safety_manager: The safety manager to classify and confirm tool calls.
            system_prompt: Optional initial system prompt to start the conversation.
            max_iterations: Maximum iterations in the tool execution loop to avoid infinite runs.
        """
        self.client = client
        self.registry = registry
        self.safety_manager = safety_manager
        self.max_iterations = max_iterations
        self.conversation_history: list[LLMMessage] = []

        if system_prompt:
            self.conversation_history.append(SystemMessage(system_prompt))

    async def run(
        self,
        user_message: str,
        stream: bool = True,
    ) -> AsyncIterator[LLMMessage]:
        """Run the agent loop for a user message.

        Args:
            user_message: The user prompt to send to the agent.
            stream: Whether to stream completions from the LLM.

        Yields:
            LLMMessage: Message chunks (when streaming text/tool calls) or complete messages.
        """
        user_msg = UserMessage(user_message)
        self.conversation_history.append(user_msg)
        yield user_msg

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # Get schemas for registered tools
            tools = self.registry.tool_schemas_for_model()
            llm_tools = tools if tools else None

            assistant_msg: AssistantMessage | None = None

            if stream:
                accumulated_content = ""
                accumulated_tool_calls: dict[int, LLMToolCall] = {}

                async for chunk in self.client.complete_stream(
                    messages=self.conversation_history,
                    tools=llm_tools,
                ):
                    if chunk.content:
                        accumulated_content += chunk.content
                        yield chunk

                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            idx = tc.index if tc.index is not None else 0
                            if idx not in accumulated_tool_calls:
                                accumulated_tool_calls[idx] = LLMToolCall(
                                    id=tc.id,
                                    type=tc.type,
                                    function=LLMFunctionCall(
                                        name=tc.function.name if tc.function else None,
                                        arguments=tc.function.arguments if tc.function else ""
                                    ),
                                    index=idx
                                )
                            else:
                                existing = accumulated_tool_calls[idx]
                                if tc.id:
                                    existing.id = tc.id
                                if tc.type:
                                    existing.type = tc.type
                                if tc.function:
                                    if tc.function.name:
                                        existing.function.name = tc.function.name
                                    if tc.function.arguments:
                                        if existing.function.arguments is None:
                                            existing.function.arguments = ""
                                        existing.function.arguments += tc.function.arguments

                # Construct the final AssistantMessage representing this step's output
                final_tool_calls = list(accumulated_tool_calls.values()) if accumulated_tool_calls else None
                assistant_msg = AssistantMessage(
                    content=accumulated_content if accumulated_content else None,
                    tool_calls=final_tool_calls,
                )
            else:
                assistant_msg = await self.client.complete(
                    messages=self.conversation_history,
                    tools=llm_tools,
                )
                yield assistant_msg

            # Save the final message to history
            self.conversation_history.append(assistant_msg)

            # If the assistant didn't call any tools, we are done
            if not assistant_msg.tool_calls:
                break

            # Execute tool calls sequentially
            for tool_call in assistant_msg.tool_calls:
                tool_name = tool_call.function.name if tool_call.function else None
                tool_args_str = tool_call.function.arguments if tool_call.function else "{}"

                if not tool_name:
                    err_result = ToolError(
                        tool_name="unknown",
                        error_message="Model requested a tool call without a function name.",
                        error_type="validation",
                    )
                    tool_msg = ToolMessage(
                        content=err_result.error_message,
                        tool_call_id=tool_call.id,
                    )
                    self.conversation_history.append(tool_msg)
                    yield tool_msg
                    continue

                try:
                    tool_args = self.registry.model_tool_call_to_execution_args(tool_args_str)
                except Exception as e:
                    err_result = ToolError(
                        tool_name=tool_name,
                        error_message=f"Failed to parse tool arguments: {e}",
                        error_type="validation",
                    )
                    tool_msg = ToolMessage(
                        content=err_result.error_message,
                        tool_call_id=tool_call.id,
                    )
                    self.conversation_history.append(tool_msg)
                    yield tool_msg
                    continue

                # Safety validation
                try:
                    allowed = await self.safety_manager.validate_tool_call(tool_name, tool_args)
                except Exception as e:
                    err_result = ToolError(
                        tool_name=tool_name,
                        error_message=f"Safety validation error: {e}",
                        error_type="validation",
                    )
                    tool_msg = ToolMessage(
                        content=err_result.error_message,
                        tool_call_id=tool_call.id,
                    )
                    self.conversation_history.append(tool_msg)
                    yield tool_msg
                    continue

                if not allowed:
                    err_result = ToolError(
                        tool_name=tool_name,
                        error_message=f"Tool execution for '{tool_name}' was rejected by the user.",
                        error_type="permission",
                    )
                    tool_msg = ToolMessage(
                        content=err_result.error_message,
                        tool_call_id=tool_call.id,
                    )
                    self.conversation_history.append(tool_msg)
                    yield tool_msg
                    continue

                # Execute
                result = await self.registry.execute_tool_call(tool_name, tool_args)

                tool_msg_content = result.content if isinstance(result, ToolResult) else result.error_message
                tool_msg = ToolMessage(
                    content=tool_msg_content,
                    tool_call_id=tool_call.id,
                )
                self.conversation_history.append(tool_msg)
                yield tool_msg


@dataclass(slots=True)
class AgentRun:
    """Represents a single agent run in a workspace."""

    workspace: str

    def start(self) -> None:
        """Start the agent loop.

        This is a scaffold method. The full agent loop will be implemented in a later issue.
        """

