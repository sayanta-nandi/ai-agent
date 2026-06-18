# Architecture

This document describes the V1 architecture for `agent-tui`, the terminal AI coding agent.

## High-level components

```text
CLI (Typer)
  -> loads settings and validates workspace
  -> creates model client, tool registry, safety manager, agent session
  -> starts Textual TUI app

AgentSession
  -> owns conversation history
  -> asks LLMClient for completions with tool schemas
  -> validates tool calls through SafetyManager
  -> executes accepted tools through ToolRegistry
  -> converts tool results back into LLM messages

Textual TUI
  -> displays chat history
  -> displays tool logs and output
  -> provides safety confirmation modals
```

## Agent loop

`AgentSession` owns the V1 reasoning loop.

1. The user prompt is converted to a `UserMessage` and appended to conversation history.
2. The session asks the `LLMClient` for a completion, passing registered tool schemas.
3. If the assistant response contains tool calls, the session iterates through them.
4. Each tool call is parsed from JSON arguments into execution arguments.
5. `SafetyManager.validate_tool_call` decides whether the tool can run.
6. Accepted tool calls are executed by `ToolRegistry`.
7. Tool results are converted into `ToolMessage` values and appended to conversation history.
8. The loop repeats until the model stops requesting tools or `max_iterations` is reached.

The loop is async and yields messages as they are produced so the TUI can stream chat, tool, and output events.

## Tool registry

The tool registry lives in `src/agent_tui/tools/registry.py`.

Responsibilities:

- register `Tool` instances by name,
- expose registered tools as OpenAI-compatible function schemas,
- parse JSON tool-call arguments into Python keyword arguments,
- execute tools by name,
- convert `ToolResult` and `ToolError` objects into model message data.

V1 tools are defined in `src/agent_tui/tools/`:

- `file_tools.py`: `list_files`, `read_file`, `write_file`, `edit_file`, `delete_file`
- `command_tool.py`: `run_command`
- `base.py`: shared `Tool`, `ToolResult`, and `ToolError` types

Each tool receives the workspace boundary it should operate in, and the safety layer validates paths before execution.

## Model adapter

The model adapter boundary lives in `src/agent_tui/llm.py`.

V1 uses an OpenAI-compatible adapter:

- `POST /chat/completions`
- `messages`
- `tools`
- `tool_choice`
- `stream`

`OpenAIAdapter.prepare_request` converts `LLMMessage` and `ToolSchema` values into request data. `OpenAIAdapter.parse_response` and `OpenAIAdapter.parse_stream_chunk` convert provider responses back into `LLMMessage` values.

The adapter interface is designed so future providers can be added without changing the agent loop.

## Textual TUI

The TUI app lives in `src/agent_tui/tui/app.py`.

Responsibilities:

- render a two-panel layout with chat on the left and tool/output logs on the right,
- send user prompts into `AgentSession`,
- display assistant text and tool messages,
- write tool executions and command output to dedicated logs,
- show a modal confirmation for risky tool calls.

The TUI wires the agent session's safety manager confirmation handler into `ConfirmationModal`, so the same safety decision point can be reused by future CLI confirmation flows.

## Configuration and workspace safety

`src/agent_tui/config.py` loads settings from environment variables, `.env`, and CLI overrides. Required V1 settings are `API_KEY` and `MODEL`.

`src/agent_tui/safety.py` enforces the workspace boundary:

- resolves paths relative to the workspace,
- rejects traversal outside the workspace,
- rejects absolute paths outside the workspace,
- rejects symlink escape attempts,
- classifies risky tools for confirmation.

## Extension points

- Add a new model provider by implementing the adapter protocol in `src/agent_tui/llm.py`.
- Add a new tool by implementing `Tool` and registering it in the CLI before creating `AgentSession`.
- Add RAG by introducing ingestion, embedding, retrieval, and prompt-context modules without bypassing `SafetyManager`.
- Add MCP by introducing an MCP client boundary and registering discovered tools through the same registry and safety policy.
