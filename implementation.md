# Implementation Plan

## Target V1 Scope

```text
Terminal-only AI coding agent
One workspace directory at a time
Model API integration
Agent loop with tool calling
Explicit file tools
Command execution inside workspace
Safety confirmation for destructive/high-risk actions
Minimal Textual TUI
Future-ready hooks for RAG/MCP, but not implemented yet
```

## Recommended Stack

```text
Python 3.12+
uv
Textual for TUI
Typer for CLI entrypoint
Pydantic for config/tool schemas
httpx for async model API calls
pytest for tests
```

---

# Task Breakdown with Dependencies

## 1. Project Setup

**Task:** Initialize Python project structure and tooling.

**Subtasks:**
- Create `pyproject.toml`
- Add dependencies:
  - `textual`
  - `typer`
  - `pydantic`
  - `pydantic-settings`
  - `httpx`
  - `pytest`
  - `pytest-asyncio`
- Add basic package layout:
  - `src/agent_tui/`
  - `src/agent_tui/cli.py`
  - `src/agent_tui/config.py`
  - `src/agent_tui/agent.py`
  - `src/agent_tui/llm.py`
  - `src/agent_tui/tools/`
  - `src/agent_tui/tui/`
  - `src/agent_tui/safety.py`
- Add `.gitignore`
- Add README skeleton
- Add basic pytest config

**Blocks:** None.

**Can run in parallel with:** Architecture decisions, model provider decision, TUI wireframe.

---

## 2. Config and Environment Loading

**Task:** Load API key, model name, and workspace path.

**Subtasks:**
- Define Pydantic settings model:
  - `api_key`
  - `base_url`
  - `model`
  - `workspace`
  - optional `provider`
- Support `.env`
- Validate missing API key with clear error
- Support CLI override for workspace path
- Add config tests

**Blocks:**
- Blocked by: Project setup.

**Can run in parallel with:** TUI wireframe and model API adapter design.

---

## 3. Model API Adapter

**Task:** Create a clean abstraction for calling an LLM API.

**Subtasks:**
- Define common message types:
  - `system`
  - `user`
  - `assistant`
  - `tool`
- Define tool schema format
- Implement async `LLMClient`
- Start with OpenAI-compatible API shape:
  - `POST /chat/completions`
  - `messages`
  - `tools`
  - `tool_choice`
  - `stream`
- Parse:
  - text response
  - tool calls
- Add provider adapter interface so Anthropic/Gemini/local can be added later

**Blocks:**
- Blocked by: Project setup.
- Partially blocked by: Choosing model/provider.

**Can run in parallel with:** Tool implementations and TUI shell.

---

## 4. Tool Interface and Registry

**Task:** Define a consistent tool-calling interface.

**Subtasks:**
- Create `Tool` base class or protocol
- Define `ToolResult`
- Define `ToolError`
- Create tool registry:
  - `read_file`
  - `write_file`
  - `edit_file`
  - `delete_file`
  - `list_files`
  - `run_command`
- Convert tool calls from model into internal tool executions
- Serialize tool results back into model messages

**Blocks:**
- Blocked by: Project setup.
- Partially blocked by: Tool schema format from model adapter.

**Can run in parallel with:** File tools, command tool, safety module.

---

## 5. Workspace Path Safety

**Task:** Prevent tools from escaping the selected workspace.

**Subtasks:**
- Resolve workspace path to absolute path
- Implement `resolve_within_workspace(path)`
- Prevent `..`, symlinks, absolute paths outside workspace
- Add tests for:
  - normal file path
  - nested file path
  - path traversal
  - absolute path outside workspace
  - symlink escape attempt

**Blocks:**
- Blocked by: Project setup.

**Can run in parallel with:** File tools, command tool, config.

---

## 6. File Tools

**Task:** Implement explicit file operations.

**Subtasks:**
- `list_files(path)`
  - list directory contents
  - respect max depth
- `read_file(path)`
  - read text files
  - reject huge files or binary files with clear error
- `write_file(path, content)`
  - create parent directories
  - overwrite only after safety check
- `edit_file(path, changes)`
  - choose minimal V1 strategy:
    - replace whole file content, or
    - simple line/block replacement
- `delete_file(path)`
  - file only in V1, or file + empty directory later
- Add unit tests

**Blocks:**
- Blocked by:
  - Project setup
  - Workspace path safety
  - Tool interface

**Can run in parallel with:** Command tool and safety module.

---

## 7. Command Execution Tool

**Task:** Run commands inside the selected workspace.

**Subtasks:**
- Implement `run_command(command, timeout)`
- Use `asyncio.create_subprocess_exec`
- Set `cwd=workspace`
- Capture:
  - stdout
  - stderr
  - exit code
- Add timeout handling
- Avoid shell injection by preferring argument-based execution
- Decide V1 command format:
  - safer: `command` + `args`
  - simpler: shell string
- Add tests using safe mock commands

**Blocks:**
- Blocked by:
  - Project setup
  - Tool interface
  - Workspace path safety

**Can run in parallel with:** File tools and safety module.

---

## 8. Safety and Confirmation Layer

**Task:** Ask confirmation before destructive/high-risk actions.

**Subtasks:**
- Classify tool calls:
  - safe:
    - `read_file`
    - `list_files`
  - risky:
    - `write_file`
    - `edit_file`
    - `delete_file`
    - `run_command`
- Define confirmation policy:
  - `write_file` existing file → confirm
  - `delete_file` → confirm
  - `edit_file` → confirm
  - `run_command` → confirm
- Implement `SafetyManager`
- Add async confirmation hook for TUI
- Add CLI fallback confirmation
- Add tests for classification

**Blocks:**
- Blocked by:
  - Tool interface
  - File/command tool list

**Can run in parallel with:** Agent loop and TUI confirmation UI.

---

## 9. Agent Loop

**Task:** Implement the core reasoning/tool loop.

**Subtasks:**
- Define `AgentSession`
- Maintain conversation history
- Send user message to model
- Handle response:
  - final text → yield to UI
  - tool calls → execute tools
- Execute approved tools
- Return tool results to model
- Continue until model final response
- Add max iteration limit to avoid infinite loops
- Add streaming support if API supports it
- Add tests with fake LLM client

**Blocks:**
- Blocked by:
  - Model API adapter
  - Tool interface
  - Safety manager
  - File/command tools

**Can run in parallel with:** TUI integration after interfaces stabilize.

---

## 10. Textual TUI

**Task:** Build terminal UI.

**Subtasks:**
- Create `AgentTuiApp`
- Add screens/panels:
  - chat/messages
  - tool call log
  - command/file output
  - user input
- Implement prompt submission
- Stream assistant responses
- Show pending tool calls
- Show confirmation dialog
- Show tool results
- Show errors
- Add basic keyboard shortcuts:
  - Enter: send
  - Ctrl+C: cancel/interrupt
  - maybe `/help`
- Add smoke test or manual run path

**Blocks:**
- Blocked by:
  - Project setup
  - Agent loop interface
  - Safety confirmation interface

**Can run in parallel with:** CLI plumbing and model adapter.

---

## 11. CLI Entry Point

**Task:** Add terminal command to start the app.

**Subtasks:**
- Add Typer CLI command:
  - `agent-tui run [workspace]`
- Load config
- Validate workspace exists or create it if intended
- Start Textual app
- Inject dependencies:
  - config
  - LLM client
  - tool registry
  - safety manager
  - agent session
- Add `--model`, `--api-key`, `--workspace` overrides
- Add `--dry-run` optional later
- Add CLI tests

**Blocks:**
- Blocked by:
  - Config
  - TUI app
  - Agent session

**Can run in parallel with:** Packaging and README.

---

## 12. Packaging and Local Execution

**Task:** Make the app easy to run.

**Subtasks:**
- Add console script:
  - `agent-tui = agent_tui.cli:app`
- Document:
  - `uv sync`
  - `uv run agent-tui run ./workspace`
- Optional:
  - `pipx install .`
  - PyInstaller only if needed later
- Add `.env.example`

**Blocks:**
- Blocked by:
  - CLI entrypoint
  - Config

**Can run in parallel with:** README and example usage.

---

## 13. Tests and Regression Coverage

**Task:** Add automated tests for core behavior.

**Subtasks:**
- Test config loading
- Test workspace safety
- Test file tools
- Test command tool with mocked subprocess
- Test safety classification
- Test agent loop with fake LLM
- Test tool result serialization
- Add pytest command to CI/local docs

**Blocks:**
- Blocked by:
  - Core modules
  - Tool implementations

**Can run in parallel with:** TUI and CLI work.

---

## 14. Documentation

**Task:** Document how to use and extend the app.

**Subtasks:**
- Write README:
  - purpose
  - stack
  - setup
  - usage
  - safety model
  - tool list
  - future RAG/MCP plan
- Add `.env.example`
- Add architecture notes:
  - agent loop
  - tool registry
  - model adapter
  - TUI
- Add contributing notes

**Blocks:**
- Blocked by:
  - Basic architecture stabilization

**Can run in parallel with:** Packaging and tests.

---

# Suggested Parallel Workstreams

## Workstream A — Core Agent

1. Project setup
2. Model API adapter
3. Tool interface
4. Agent loop
5. Tests with fake LLM

## Workstream B — Workspace Tools

1. Project setup
2. Workspace safety
3. File tools
4. Command tool
5. Safety layer

## Workstream C — Terminal UI

1. Project setup
2. TUI wireframe
3. Textual app shell
4. Confirmation dialog
5. Agent integration

## Workstream D — CLI/Config/Packaging

1. Project setup
2. Config loading
3. Typer CLI
4. Packaging
5. README

---

# Recommended First Milestone

## Milestone 1: CLI Agent Without Full TUI

Goal:

```text
Run from terminal, ask one question, execute one tool, return answer.
```

Tasks:
- Project setup
- Config
- Model adapter
- Tool registry
- Workspace safety
- File tools
- Command tool
- Safety confirmation in plain CLI
- Basic agent loop

## Milestone 2: Textual TUI

Goal:

```text
Interactive terminal app with chat, tool logs, streaming output, confirmations.
```

Tasks:
- Textual app shell
- Message panel
- Input panel
- Tool log panel
- Confirmation dialog
- Agent session integration

## Milestone 3: Polish

Goal:

```text
Safe, usable, documented V1.
```

Tasks:
- Error handling
- Tests
- README
- Packaging
- Example commands
- Timeout/max iteration safeguards

---

# Recommended Build Order

```text
1. Project setup
2. Config
3. Workspace safety
4. Tool interface
5. File tools
6. Command tool
7. Safety manager
8. Model adapter
9. Agent loop
10. CLI entrypoint
11. Textual TUI shell
12. TUI integration
13. Tests
14. README/package
```
