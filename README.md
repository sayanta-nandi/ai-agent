# agent-tui

Terminal AI coding agent scaffold.

`agent-tui` is a Python terminal application that lets an LLM operate in one selected workspace through explicit tool calls. The V1 design prioritizes safe, reviewable automation: the agent can propose file and command operations, but risky actions require confirmation before they run.

## Purpose

Use `agent-tui` when you want a lightweight, terminal-first coding agent that:

- runs inside a single workspace directory,
- uses a model adapter boundary for LLM calls,
- exposes a small set of explicit file and command tools,
- asks for confirmation before destructive or high-risk actions,
- provides a minimal Textual TUI for chat, tool logs, and output.

## Stack

The V1 app is built with:

- **Python 3.12+**
- **uv** for dependency management and local runs
- **Typer** for the CLI entry point
- **Textual** for the terminal UI
- **Pydantic / pydantic-settings** for configuration validation
- **httpx** for async model API calls
- **pytest** and **pytest-asyncio** for tests

## Setup

1. Install project dependencies and the package in a local environment:

   ```bash
   uv sync
   ```

2. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

   The template is tracked in [`.env.example`](.env.example). Do not commit `.env`; it is ignored by the project `.gitignore`.

3. Edit `.env` and set at least:

   ```ini
   API_KEY=your-api-key-here
   MODEL=gpt-4o
   ```

   The default provider is OpenAI-compatible (`PROVIDER=openai`) and points at `BASE_URL=https://api.openai.com/v1`. You can change `BASE_URL` for local or alternative OpenAI-compatible providers.

4. Choose or create the workspace directory the agent should operate in.

## Usage

Run the agent against a workspace directory:

```bash
uv run agent-tui run ./workspace
```

You can override configuration from the command line:

```bash
uv run agent-tui run ./workspace \
  --model gpt-4o \
  --api-key "$API_KEY" \
  --base-url https://api.openai.com/v1
```

You can also install the console script globally with `pipx`:

```bash
pipx install .
agent-tui run ./workspace
```

## Configuration

`agent-tui` reads settings from environment variables, a local `.env` file, and CLI overrides.

| Variable | Required | Default | Description |
|---|---:|---|---|
| `API_KEY` | Yes | None | API key for the model provider. Local OpenAI-compatible servers may accept any non-empty value. |
| `MODEL` | Yes | None | Model identifier to request. |
| `BASE_URL` | No | `https://api.openai.com/v1` | Base URL for the OpenAI-compatible chat completions endpoint. |
| `WORKSPACE` | No | Current directory | Workspace root used by file and command tools. |
| `PROVIDER` | No | `openai` | Provider adapter name. V1 currently uses the OpenAI-compatible adapter. |

CLI overrides are available for `--api-key`, `--model`, `--base-url`, `--provider`, and `--workspace`.

## Safety model

The app uses a workspace boundary to keep tool operations inside the selected workspace:

- workspace paths are resolved to absolute paths,
- path traversal such as `../secret` is rejected,
- absolute paths outside the workspace are rejected,
- symlink escape attempts are rejected.

Tool calls are also classified before execution:

| Risk level | Tools | Behavior |
|---|---|---|
| Safe | `list_files`, `read_file` | Can run after workspace path validation. |
| Risky | `write_file`, `edit_file`, `delete_file`, `run_command` | Require confirmation before execution. |

The TUI shows a safety confirmation modal for risky tool calls. The CLI path uses the same `SafetyManager` boundary so future command-line confirmation can reuse the policy.

## Tool list

V1 tools are registered in `src/agent_tui/tools/registry.py` by the CLI before the `AgentSession` starts:

| Tool | Purpose |
|---|---|
| `list_files` | List files and directories inside the workspace. |
| `read_file` | Read text files inside the workspace. |
| `write_file` | Create or overwrite files inside the workspace after confirmation. |
| `edit_file` | Replace file content or simple blocks inside the workspace after confirmation. |
| `delete_file` | Delete files inside the workspace after confirmation. |
| `run_command` | Run a command with `cwd` set to the workspace after confirmation. |

## Architecture notes

The high-level architecture is documented in [Architecture](docs/architecture.md). It covers:

- the agent loop and message history,
- the tool registry and tool execution flow,
- the OpenAI-compatible model adapter,
- the Textual TUI layout and confirmation flow,
- configuration and workspace safety boundaries.

Additional provider details are documented in [Model Provider Decision and API Credential Setup](docs/provider_decision.md).

## Future RAG and MCP plan

V1 intentionally does not implement RAG or MCP. The current architecture leaves extension points for future work:

1. **RAG**: add document ingestion, embedding generation, vector search, and retrieval-augmented prompts.
2. **MCP**: add an MCP client boundary, tool discovery, and permission policy integration.
3. **Provider adapters**: add native Anthropic, Gemini, or other provider adapters behind the existing adapter boundary.

These features should be added as separate issues so the workspace safety model and confirmation flow remain explicit.

## Development

This project targets Python 3.12+.

```bash
python -m pytest
```

Use `uv run python -m pytest` if you want to run tests inside the `uv` environment.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests, branch naming, commit messages, and issue workflow guidance.
