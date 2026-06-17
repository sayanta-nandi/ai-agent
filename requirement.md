# AI Automation Platform Requirements

## Name

TBD

## Description

A cross-platform desktop AI automation platform for developers and non-technical builders. Users discuss project ideas with AI agents in terminal-first workspaces, let agents create/run/update projects, review outputs, and continue iterating until the project is ready to deploy.

## Decisions Made

- **Platform:** Electron + TypeScript.
- **Target users:** Developers and non-technical users building any kind of project with AI, not only AI agents.
- **Core workflow:** Terminal/agent-first loop:
  1. User opens an agent workspace.
  2. User discusses an idea with an agent.
  3. Agent creates or modifies a project.
  4. Agent runs the project.
  5. User reviews the output.
  6. User continues the conversation.
  7. Agent updates the project.
  8. Loop repeats.
- **Workspace model:** Each agent has an isolated app-managed workspace by default.
- **Collaboration model:** Agents are isolated by default; workspaces can be merged into a shared project when the user chooses.
- **UI model:** Each agent workspace includes:
  - A chat panel for conversation with the agent.
  - A real terminal panel for commands, logs, server output, errors, and interactive CLI sessions.
- **Safety model:** Review mode is the default.
  - User can override safety mode per agent or project.
  - Possible modes: sandboxed, review, strict, developer.
- **File access:** Agents work inside the app-managed workspace by default.
  - Explicit user approval is required before accessing sensitive locations such as Desktop, Documents, source-control repositories, cloud credentials, or system paths.
- **Deployment:** Deployment targets should be plugin-based.
  - Future targets may include Vercel, Netlify, Render, Railway, AWS, Docker, SSH, GitHub Pages, etc.
- **MCP/plugins:** MCP should be treated as a capability system, not only a tool system.
  - Plugins should declare capabilities such as tools, resources, prompts, memory, browser access, file access, deployment, credentials, and permissions.

## Requirements

- Build a desktop application using Electron and TypeScript.
- Support multiple agent workspaces running at the same time.
- Allow users to switch between agent workspaces easily.
- Provide a chat interface for each agent.
- Provide a real terminal interface for each agent.
- Show command execution, logs, runtime output, errors, and interactive terminal sessions.
- Let agents create projects inside isolated workspaces.
- Let agents run projects and show results to the user.
- Support iterative development through continued user-agent conversation.
- Support merging isolated agent workspaces into a shared project when needed.
- Include per-agent and per-project safety controls.
- Require user approval for sensitive file/location access.
- Support plugin-based deployment targets.
- Support MCP-based plugins for tools, resources, prompts, memory, permissions, and capabilities.
- Keep the platform extensible so future plugins can add new tools, deploy targets, and agent capabilities.
