"""Agent orchestration boundary for the terminal AI agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentRun:
    """Represents a single agent run in a workspace."""

    workspace: str

    def start(self) -> None:
        """Start the agent loop.

        This is a scaffold method. The full agent loop will be implemented in a later issue.
        """
