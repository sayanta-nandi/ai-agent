# agent-tui

Terminal AI coding agent scaffold.

## Purpose

`agent-tui` is a Python-based terminal AI coding agent. It is being built around a safe workspace model, explicit tool calls, an async LLM adapter, and a minimal Textual interface.

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

## Development

This project targets Python 3.12+.

```bash
python -m pytest
```

The implementation is currently scaffolded. Core modules exist at their V1 boundaries, and later issues will fill in configuration loading, provider setup, LLM calls, tools, safety, the agent loop, and the TUI.
