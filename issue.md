# GitHub Issues Draft for `implementation.md`

Repository: `sayanta-nandi/ai-agent`  
Label to apply: `needs-triage` (create if missing)  
Publishing order below is dependency order. Blocker references have been replaced with the actual GitHub issue numbers after publishing.

---

## Proposed breakdown

1. **Project foundation and CLI scaffold** — AFK — Blocked by: None
2. **Config and environment loading** — AFK — Blocked by: #1
3. **Model provider decision and API credential setup** — HITL — Blocked by: #2
4. **Model API adapter** — AFK — Blocked by: #1, partially #3
5. **Workspace path safety** — AFK — Blocked by: #1
6. **Tool interface and registry** — AFK — Blocked by: #1, partially #4
7. **File tools** — AFK — Blocked by: #5, #6
8. **Command execution tool** — AFK — Blocked by: #5, #6
9. **Safety and confirmation layer** — AFK — Blocked by: #6, #7, #8
10. **Agent loop** — AFK — Blocked by: #4, #6, #9, #7, #8
11. **Textual TUI** — AFK — Blocked by: #1, #10, #9
12. **CLI entry point** — AFK — Blocked by: #2, #11, #10
13. **Packaging and local execution** — AFK — Blocked by: #12, #2
14. **Tests and regression coverage** — AFK — Blocked by: core modules and tool implementations
15. **Documentation** — AFK — Blocked by: basic architecture stabilization

> Note: The source plan has 14 numbered tasks, but “Tests and regression coverage” is separated from the implementation tasks because it is a cross-cutting quality slice that should be accepted independently. If you prefer one issue per original numbered task, merge issue 14 into issue 13 and keep documentation as issue 15.

---

## Issue 1 — Project foundation and CLI scaffold

### Parent

None.

### What to build

Initialize the Python project structure, package layout, dependency tooling, and minimal README/test configuration needed to build the terminal AI coding agent.

### Acceptance criteria

- [ ] `pyproject.toml` exists with Python 3.12+ target, project metadata, dependencies, and pytest configuration.
- [ ] Package layout exists under `src/agent_tui/`, including `cli.py`, `config.py`, `agent.py`, `llm.py`, `tools/`, `tui/`, and `safety.py`.
- [ ] Required dependencies are declared: `textual`, `typer`, `pydantic`, `pydantic-settings`, `httpx`, `pytest`, and `pytest-asyncio`.
- [ ] `.gitignore` exists and excludes local environment, cache, build, and virtualenv artifacts.
- [ ] README skeleton documents project purpose and current V1 scope.
- [ ] A minimal test command runs successfully.

### Blocked by

None - can start immediately.

### User stories covered

- As a developer, I can clone the repository and run the test command.
- As a developer, I can import the package and see the V1 module boundaries.

---

## Issue 2 — Config and environment loading

### Parent

None.

### What to build

Load API key, model name, base URL, provider, and workspace path from environment/`.env` with CLI overrides and clear validation errors.

### Acceptance criteria

- [ ] Pydantic settings model defines `api_key`, `base_url`, `model`, `workspace`, and optional `provider`.
- [ ] `.env` loading is supported.
- [ ] Missing API key fails with a clear actionable error.
- [ ] Workspace path can be overridden from the CLI.
- [ ] Config loading has unit tests.

### Blocked by

GitHub issue #1 — Project foundation and CLI scaffold.

### User stories covered

- As a user, I can configure the agent with environment variables.
- As a user, I can override the workspace path when starting the app.

---

## Issue 3 — Model provider decision and API credential setup

### Parent

None.

### What to build

Resolve the V1 model/provider choice and document the API credential setup needed before the model adapter can make real calls.

### Acceptance criteria

- [ ] V1 provider is selected or explicitly deferred with a default OpenAI-compatible adapter.
- [ ] `.env.example` documents required variables for the selected provider/default adapter.
- [ ] README documents how to set the API key, base URL, and model.
- [ ] Any provider-specific assumptions are recorded before implementing live API calls.

### Blocked by

GitHub issue #2 — Config and environment loading.

### User stories covered

- As a user, I know which model provider to configure.
- As a developer, I know what API shape the V1 adapter must support.

---

## Issue 4 — Model API adapter

### Parent

None.

### What to build

Create a clean async abstraction for calling an LLM API, starting with an OpenAI-compatible `/chat/completions` shape and a provider adapter interface for future Anthropic/Gemini/local providers.

### Acceptance criteria

- [ ] Common message types exist for `system`, `user`, `assistant`, and `tool`.
- [ ] Tool schema format is defined and serializable.
- [ ] Async `LLMClient` posts to an OpenAI-compatible chat completions endpoint.
- [ ] Requests include `messages`, `tools`, `tool_choice`, and streaming support where available.
- [ ] Responses parse both final text and tool calls.
- [ ] Provider adapter interface allows future providers to be added.
- [ ] Adapter behavior has tests using mocked HTTP responses.

### Blocked by

GitHub issue #1 — Project foundation and CLI scaffold.  
Partially blocked by GitHub issue #3 — Model provider decision and API credential setup.

### User stories covered

- As the agent, I can send conversation history and tool schemas to the model.
- As the agent, I can receive either a final answer or tool calls from the model.

---

## Issue 5 — Workspace path safety

### Parent

None.

### What to build

Prevent file and command tools from escaping the selected workspace by resolving and validating paths safely.

### Acceptance criteria

- [ ] Workspace path is resolved to an absolute path.
- [ ] `resolve_within_workspace(path)` rejects path traversal, absolute paths outside the workspace, and symlink escapes.
- [ ] Normal and nested workspace paths resolve successfully.
- [ ] Tests cover normal file path, nested file path, path traversal, absolute path outside workspace, and symlink escape attempt.

### Blocked by

GitHub issue #1 — Project foundation and CLI scaffold.

### User stories covered

- As a user, I can trust the agent will not modify files outside my selected workspace.
- As a developer, I have a reusable safety primitive for all workspace tools.

---

## Issue 6 — Tool interface and registry

### Parent

None.

### What to build

Define a consistent internal tool-calling interface, result/error types, and registry for V1 tools.

### Acceptance criteria

- [ ] `Tool` base class or protocol is defined.
- [ ] `ToolResult` and `ToolError` types are defined.
- [ ] Registry includes `read_file`, `write_file`, `edit_file`, `delete_file`, `list_files`, and `run_command`.
- [ ] Model tool calls can be converted into internal tool executions.
- [ ] Tool results can be serialized back into model messages.
- [ ] Registry behavior has unit tests.

### Blocked by

GitHub issue #1 — Project foundation and CLI scaffold.  
Partially blocked by GitHub issue #4 — Model API adapter.

### User stories covered

- As the agent, I can discover and invoke the tools exposed to the model.
- As the model, I receive tool results in a consistent message format.

---

## Issue 7 — File tools

### Parent

None.

### What to build

Implement explicit file operations scoped to the selected workspace.

### Acceptance criteria

- [ ] `list_files(path)` lists directory contents and respects max depth.
- [ ] `read_file(path)` reads text files and rejects huge or binary files with a clear error.
- [ ] `write_file(path, content)` creates parent directories and overwrites only after safety validation.
- [ ] `edit_file(path, changes)` uses a V1 strategy for whole-file or simple block replacement.
- [ ] `delete_file(path)` deletes files only in V1.
- [ ] File tools are registered in the tool registry.
- [ ] File tools have unit tests.

### Blocked by

GitHub issue #5 — Workspace path safety.  
GitHub issue #6 — Tool interface and registry.

### User stories covered

- As the agent, I can inspect and modify files inside the workspace.
- As a user, I can review explicit file operations before they happen.

---

## Issue 8 — Command execution tool

### Parent

None.

### What to build

Run commands inside the selected workspace with timeout handling and captured output.

### Acceptance criteria

- [ ] `run_command(command, timeout)` executes inside `cwd=workspace`.
- [ ] `asyncio.create_subprocess_exec` is used or an equivalent non-shell execution path is documented.
- [ ] stdout, stderr, and exit code are captured.
- [ ] Timeout handling terminates or reports the timed-out command safely.
- [ ] Shell injection risk is avoided by preferring argument-based execution or a clearly documented V1 command format.
- [ ] Tests use safe mock commands.

### Blocked by

GitHub issue #5 — Workspace path safety.  
GitHub issue #6 — Tool interface and registry.

### User stories covered

- As the agent, I can run tests or build commands inside the workspace.
- As a user, command execution is constrained to the selected workspace.

---

## Issue 9 — Safety and confirmation layer

### Parent

None.

### What to build

Classify tool calls and require confirmation before destructive or high-risk actions, with hooks for both TUI and CLI confirmation flows.

### Acceptance criteria

- [ ] Safe tools are classified: `read_file`, `list_files`.
- [ ] Risky tools are classified: `write_file`, `edit_file`, `delete_file`, `run_command`.
- [ ] Existing file writes, deletes, edits, and command execution require confirmation.
- [ ] `SafetyManager` exposes an async confirmation hook.
- [ ] CLI fallback confirmation is available.
- [ ] Safety classification has unit tests.

### Blocked by

GitHub issue #6 — Tool interface and registry.  
GitHub issue #7 — File tools.  
GitHub issue #8 — Command execution tool.

### User stories covered

- As a user, I can approve or reject risky actions before they execute.
- As the agent, I can ask for confirmation without knowing UI details.

---

## Issue 10 — Agent loop

### Parent

None.

### What to build

Implement the core reasoning/tool loop that sends user messages to the model, executes approved tool calls, returns tool results, and stops with a final response.

### Acceptance criteria

- [ ] `AgentSession` maintains conversation history.
- [ ] User messages are sent to the model through the LLM client.
- [ ] Final text responses are yielded to the UI/CLI.
- [ ] Tool calls are executed through approved tools.
- [ ] Tool results are returned to the model.
- [ ] Loop continues until the model returns a final response or reaches a max iteration limit.
- [ ] Streaming support is included if supported by the API.
- [ ] Agent loop is tested with a fake LLM client.

### Blocked by

GitHub issue #4 — Model API adapter.  
GitHub issue #6 — Tool interface and registry.  
GitHub issue #7 — File tools.  
GitHub issue #8 — Command execution tool.  
GitHub issue #9 — Safety and confirmation layer.

### User stories covered

- As a user, I can ask the agent to perform a workspace task.
- As the agent, I can reason, call tools, and return an answer without infinite loops.

---

## Issue 11 — Textual TUI

### Parent

None.

### What to build

Build the terminal UI shell with message, tool log, output, input, confirmation, and error surfaces.

### Acceptance criteria

- [ ] `AgentTuiApp` exists using Textual.
- [ ] UI includes panels for chat/messages, tool call log, command/file output, and user input.
- [ ] Prompt submission works.
- [ ] Pending tool calls are visible.
- [ ] Confirmation dialog is visible.
- [ ] Tool results and errors are displayed.
- [ ] Basic keyboard shortcuts exist: Enter to send, Ctrl+C to cancel/interrupt, and optional `/help`.
- [ ] Smoke test or documented manual run path exists.

### Blocked by

GitHub issue #1 — Project foundation and CLI scaffold.  
GitHub issue #9 — Safety and confirmation layer.  
GitHub issue #10 — Agent loop.

### User stories covered

- As a user, I can interact with the agent through a terminal UI.
- As a user, I can see what the agent is doing and approve risky actions.

---

## Issue 12 — CLI entry point

### Parent

None.

### What to build

Add the terminal command to start the agent app and inject runtime dependencies.

### Acceptance criteria

- [ ] Typer CLI command exists: `agent-tui run [workspace]`.
- [ ] Config is loaded before starting the app.
- [ ] Workspace existence/validation behavior is implemented or documented.
- [ ] Textual app starts with injected config, LLM client, tool registry, safety manager, and agent session.
- [ ] CLI overrides exist for `--model`, `--api-key`, and `--workspace`.
- [ ] CLI tests cover successful startup configuration and validation errors.

### Blocked by

GitHub issue #2 — Config and environment loading.  
GitHub issue #10 — Agent loop.  
GitHub issue #11 — Textual TUI.

### User stories covered

- As a user, I can start the app from the terminal with a workspace path.
- As a user, I can override key settings from the command line.

---

## Issue 13 — Packaging and local execution

### Parent

None.

### What to build

Make the app easy to install and run locally.

### Acceptance criteria

- [ ] Console script is configured: `agent-tui = agent_tui.cli:app`.
- [ ] README documents `uv sync`.
- [ ] README documents `uv run agent-tui run ./workspace`.
- [ ] `.env.example` exists and matches the selected provider/default adapter.
- [ ] Optional `pipx install .` guidance is documented if appropriate.
- [ ] Local execution path is verified.

### Blocked by

GitHub issue #2 — Config and environment loading.  
GitHub issue #12 — CLI entry point.

### User stories covered

- As a user, I can install and run the app with documented commands.
- As a developer, I can reproduce local execution from a clean checkout.

---

## Issue 14 — Tests and regression coverage

### Parent

None.

### What to build

Add automated coverage for core behavior across config, safety, tools, agent loop, serialization, and local docs.

### Acceptance criteria

- [ ] Config loading is tested.
- [ ] Workspace safety is tested.
- [ ] File tools are tested.
- [ ] Command tool is tested with safe mock commands.
- [ ] Safety classification is tested.
- [ ] Agent loop is tested with fake LLM client.
- [ ] Tool result serialization is tested.
- [ ] README or local docs include the pytest command.
- [ ] Regression test suite runs successfully.

### Blocked by

Core modules and tool implementations: Issues #2, #4, #5, #6, #7, #8, #9, and #10.

### User stories covered

- As a developer, I can change core behavior with confidence that regressions are caught.
- As a maintainer, I can run a local test command before merging.

---

## Issue 15 — Documentation

### Parent

None.

### What to build

Document how to use and extend the V1 app.

### Acceptance criteria

- [ ] README explains purpose, stack, setup, usage, safety model, tool list, and future RAG/MCP plan.
- [ ] `.env.example` exists and is referenced by README.
- [ ] Architecture notes cover agent loop, tool registry, model adapter, and TUI.
- [ ] Contributing notes explain setup, tests, and issue workflow.

### Blocked by

Basic architecture stabilization: Issues #10, #11, #12, #13, and #14.

### User stories covered

- As a new user, I can set up and use the app.
- As a new contributor, I can understand the architecture and extend the app safely.
