# agent-tui

Terminal AI coding agent scaffold.

## Purpose

`agent-tui` is a Python-based terminal AI coding agent. It is being built around a safe workspace model, explicit tool calls, an async LLM adapter, and a minimal Textual interface.

## Install and run locally

`agent-tui` is packaged as a Python project and exposes the `agent-tui` console script.

```bash
# Install project dependencies and the package in the local environment
uv sync

# Create your local configuration from the template
cp .env.example .env
```

Edit `.env` and set at least `API_KEY` and `MODEL`. The template uses the default OpenAI-compatible provider (`PROVIDER=openai`) and `BASE_URL=https://api.openai.com/v1`). Create or choose an existing workspace directory for the agent to operate in.

Run the agent against a workspace directory:

```bash
uv run agent-tui run ./workspace
```

You can also install the console script globally with `pipx` if you want to run `agent-tui` outside this checkout:

```bash
pipx install .
agent-tui run ./workspace
```

## Current V1 scope

The V1 target is:

- Terminal-only interaction
- One workspace directory at a time
- Model API integration through an adapter boundary
- Agent loop with tool calling
- Explicit file and command tools
- Safety confirmation for destructive or high-risk actions
- Minimal Textual TUI
- Future hooks for RAG and MCP, without implementing them yet


## Configuration

`agent-tui` is configured using environment variables, a local `.env` file, or CLI argument overrides.

### Required Settings

To run the agent, you must configure:
- **API Key**: The credential used to authenticate requests to the model provider.
- **Model**: The model name to run (e.g. `gpt-4o`).

By default, the agent expects an OpenAI-compatible provider.

### Setup using `.env`

Create a `.env` file in the project root (using [.env.example](file:///D:/projects/ai-automation/.env.example) as a template):

```ini
# API key for authentication (Required)
API_KEY=your-api-key-here

# Model name to request (Required)
MODEL=gpt-4o

# OpenAI-compatible API base URL (Optional, defaults to OpenAI's public API)
BASE_URL=https://api.openai.com/v1

# Workspace directory for agent operations (Optional, defaults to the current working directory)
WORKSPACE=./workspace

# Provider name used by the model adapter (Optional, defaults to "openai")
PROVIDER=openai
```

### CLI Overrides

When launching the agent command-line tool, you can override these parameters:
- `--api-key <key>`: Override the API key.
- `--model <name>`: Override the model.
- `--workspace <path>`: Override the target workspace directory.

For more details on provider decisions and assumptions, see the [Model Provider Decision document](file:///D:/projects/ai-automation/docs/provider_decision.md).

## Development

This project targets Python 3.12+.

```bash
python -m pytest
```

The implementation is currently scaffolded. Core modules exist at their V1 boundaries, and later issues will fill in configuration loading, provider setup, LLM calls, tools, safety, the agent loop, and the TUI.

