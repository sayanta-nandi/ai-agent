# Contributing

Thanks for contributing to `agent-tui`. This project uses a small, safety-first workflow so changes to agent behavior, tool execution, and workspace boundaries stay reviewable.

## Setup

1. Use Python 3.12 or newer.
2. Install dependencies with `uv`:

   ```bash
   uv sync
   ```

3. Copy the environment template before running the app locally:

   ```bash
   cp .env.example .env
   ```

4. Configure `.env` for local development. You can point `BASE_URL` at an OpenAI-compatible local server if you do not want to call a cloud provider.

## Running the app

Run the terminal app against a workspace directory:

```bash
uv run agent-tui run ./workspace
```

Override settings from the CLI when needed:

```bash
uv run agent-tui run ./workspace --model gpt-4o --api-key "$API_KEY"
```

## Tests

Run the full test suite:

```bash
python -m pytest
```

Or run it through `uv`:

```bash
uv run python -m pytest
```

When adding agent, tool, safety, config, CLI, or TUI behavior, add focused tests near the feature being changed. Existing regression coverage should continue to pass.

## Branches

Start from `main` and create a focused branch:

```bash
git switch main
git pull origin main
git switch -c <type>/<description>-#<issue-number>
```

Use lowercase, hyphen-separated descriptions and include the GitHub issue number.

Examples:

```text
fix/workspace-path-safety-#5
feature/textual-tui-#11
docs/v1-app-usage-and-architecture-#15
```

## Commits

Use Conventional Commits:

```text
type(scope): short description
```

Examples:

```text
fix(safety): reject symlink escapes outside workspace
test(agent): add coverage for rejected tool calls
docs(readme): document V1 usage and architecture
```

Keep commits focused. A single commit should normally address one logical change.

## Pull requests

Create a PR back to `main` when the change is ready. The PR should:

- reference the issue it resolves,
- explain what changed and why,
- list tests or manual checks run,
- stay focused on the issue,
- avoid unrelated refactors or formatting churn.

Use the GitHub issue template or PR description template when available.

## Issue workflow

1. Read the issue and acceptance criteria before changing code.
2. Check whether the issue is blocked by earlier work.
3. Create a branch from current `main`.
4. Implement the smallest change that satisfies the acceptance criteria.
5. Run the relevant tests locally.
6. Push the branch and open a PR.
7. Address review feedback in focused follow-up commits.

For safety-sensitive changes, call out the new boundary or confirmation behavior in the PR description.
