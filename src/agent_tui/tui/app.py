"""Textual TUI application for the terminal AI agent."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static

from agent_tui.agent import AgentSession
from agent_tui.config import AgentSettings
from agent_tui.llm import AssistantMessage, ToolMessage, UserMessage


class ConfirmationModal(ModalScreen[bool]):
    """Modal screen for safety confirmation of risky tool executions."""

    def __init__(self, prompt_text: str) -> None:
        super().__init__()
        self.prompt_text = prompt_text

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("[bold yellow]⚠️ Safety Confirmation Required[/bold yellow]", id="confirm-title"),
            Label(self.prompt_text, id="confirm-prompt"),
            Horizontal(
                Button("Allow (y)", variant="success", id="confirm-yes"),
                Button("Deny (n)", variant="error", id="confirm-no"),
                id="confirm-buttons",
            ),
            id="confirm-dialog",
        )

    def on_mount(self) -> None:
        # Highlight yes by default
        self.query_one("#confirm-yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        elif event.button.id == "confirm-no":
            self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key in ("y", "Y"):
            self.dismiss(True)
        elif event.key in ("n", "N"):
            self.dismiss(False)


class MessageWidget(Static):
    """Widget to display a chat message with custom styles per role."""

    def __init__(self, role: str, content: str = "") -> None:
        super().__init__(classes=f"message message-{role}")
        self.role = role
        self.raw_content = content

    def on_mount(self) -> None:
        self.update_content(self.raw_content)

    def update_content(self, content: str) -> None:
        self.raw_content = content
        # Set border title to role
        if self.role == "user":
            self.border_title = "🧑 User"
        else:
            self.border_title = "🤖 Agent"
        
        if content.strip():
            self.update(Markdown(content))
        else:
            self.update("[italic gray]Thinking...[/italic gray]")


class AgentTuiApp(App):
    """Textual application orchestrating the terminal AI coding agent."""

    CSS = """
    Screen {
        background: #0f172a;
    }

    #main-layout {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 6fr 4fr;
        height: 1fr;
    }

    #left-panel {
        layout: vertical;
        height: 1fr;
    }

    #chat-scroll {
        height: 1fr;
        border: solid #3b82f6;
        border-title-align: left;
        background: #1e293b;
        padding: 1;
    }

    #input-area {
        height: auto;
        dock: bottom;
        margin: 1;
    }

    #input-widget {
        background: #0f172a;
        border: tall #3b82f6;
    }

    #right-panel {
        layout: vertical;
        height: 1fr;
    }

    #tool-log {
        height: 4fr;
        border: solid #10b981;
        border-title-align: left;
        background: #1e293b;
        padding: 1;
    }

    #output-viewer {
        height: 6fr;
        border: solid #f59e0b;
        border-title-align: left;
        background: #1e293b;
        padding: 1;
    }

    /* Message Styles */
    .message {
        margin: 0 0 1 0;
        padding: 0 1;
    }

    .message-user {
        background: #1e3a8a;
        border: round #3b82f6;
    }

    .message-assistant {
        background: #064e3b;
        border: round #10b981;
    }

    .error-msg {
        background: #7f1d1d;
        color: #fca5a5;
        border: round #ef4444;
        margin: 0 0 1 0;
        padding: 0 1;
    }

    /* Modal Screen Styling */
    ConfirmationModal {
        align: center middle;
        background: rgba(15, 23, 42, 0.7);
    }

    #confirm-dialog {
        width: 60;
        height: auto;
        background: #1e293b;
        border: double #f59e0b;
        padding: 1 2;
        align: center middle;
    }

    #confirm-title {
        text-align: center;
        margin-bottom: 1;
        color: #f59e0b;
    }

    #confirm-prompt {
        margin-bottom: 2;
        text-align: center;
    }

    #confirm-buttons {
        align: center middle;
        height: auto;
    }

    #confirm-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "cancel_or_exit", "Cancel/Exit", show=True),
        Binding("f1", "show_help", "Help", show=True),
    ]

    def __init__(self, session: AgentSession, settings: AgentSettings) -> None:
        super().__init__()
        self.session = session
        self.settings = settings
        self.agent_run_task: asyncio.Task | None = None

        # Wire up safety manager's confirmation handler to TUI app
        self.session.safety_manager._confirmation_handler = self.request_confirmation

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Horizontal(
                Vertical(
                    VerticalScroll(id="chat-scroll"),
                    Container(
                        Input(placeholder="Type your prompt here... (Press Enter to send)", id="input-widget"),
                        id="input-area",
                    ),
                    id="left-panel",
                ),
                Vertical(
                    RichLog(id="tool-log", max_lines=1000, wrap=True),
                    RichLog(id="output-viewer", max_lines=5000, wrap=True),
                    id="right-panel",
                ),
                id="main-layout",
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self.chat_scroll = self.query_one("#chat-scroll", VerticalScroll)
        self.input_widget = self.query_one("#input-widget", Input)
        self.tool_log_widget = self.query_one("#tool-log", RichLog)
        self.output_viewer_widget = self.query_one("#output-viewer", RichLog)

        # Set panel titles
        self.chat_scroll.border_title = "💬 Chat History"
        self.chat_scroll.border_subtitle = f"Workspace: {self.settings.workspace}"
        self.tool_log_widget.border_title = "🛠️ Tool Call Log"
        self.output_viewer_widget.border_title = "📄 Output / File / Command Details"

        # Focus input field
        self.input_widget.focus()

        # Write welcome message
        self.tool_log_widget.write("[bold green]Welcome to Agent TUI![/bold green]")
        self.tool_log_widget.write(f"Connected to model: [cyan]{self.settings.model}[/cyan]")
        self.tool_log_widget.write("Type a prompt and press Enter to start.")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return

        # Clear input field
        self.input_widget.value = ""

        if prompt == "/help":
            self.show_help_info()
            return

        # Check if already running
        if self.agent_run_task is not None:
            self.tool_log_widget.write(
                "[warning]⚠️ An agent task is already running. Press Ctrl+C to cancel it first.[/warning]"
            )
            return

        # Disable input while running
        self.input_widget.disabled = True

        # Start running agent loop
        self.agent_run_task = asyncio.create_task(self._run_agent(prompt))

    def action_cancel_or_exit(self) -> None:
        """Cancel current agent run if active, otherwise exit app."""
        if self.agent_run_task is not None:
            self.agent_run_task.cancel()
            self.tool_log_widget.write("[red]🚫 Cancellation requested by user...[/red]")
        else:
            self.exit()

    def action_show_help(self) -> None:
        self.show_help_info()

    def show_help_info(self) -> None:
        self.tool_log_widget.write("[bold cyan]💡 Available Commands & Shortcuts:[/bold cyan]")
        self.tool_log_widget.write("  - [green]Enter[/green] / [green]Submit[/green] in input: Send message to agent")
        self.tool_log_widget.write("  - [green]Ctrl+C[/green]: Cancel running agent task, or exit if idle")
        self.tool_log_widget.write("  - [green]/help[/green] (in input) or [green]F1[/green]: Show this help message")
        self.tool_log_widget.write("  - [green]y / n[/green] or click buttons: Approve or deny safety confirmations")

    async def request_confirmation(self, prompt: str) -> bool:
        """Called by the SafetyManager when a tool call requires confirmation."""
        future: asyncio.Future[bool] = asyncio.Future()
        modal = ConfirmationModal(prompt)
        self.push_screen(
            modal,
            callback=lambda val: future.set_result(val if val is not None else False)
            if not future.done()
            else None,
        )
        return await future

    async def _run_agent(self, prompt: str) -> None:
        """Executes the agent run session loop and updates UI elements."""
        self.tool_log_widget.write(f"\n--- [bold blue]Starting Task[/bold blue]: {prompt} ---")

        # Mount User Message widget
        user_widget = MessageWidget(role="user", content=prompt)
        await self.chat_scroll.mount(user_widget)
        self.chat_scroll.scroll_end()

        current_assistant_widget = None

        try:
            async for message in self.session.run(prompt, stream=True):
                if isinstance(message, UserMessage):
                    # Already handled manually before the loop
                    continue

                if isinstance(message, AssistantMessage):
                    if current_assistant_widget is None:
                        current_assistant_widget = MessageWidget(role="assistant", content="")
                        await self.chat_scroll.mount(current_assistant_widget)

                    if message.content:
                        # Append content to the current assistant message
                        current_assistant_widget.update_content(
                            current_assistant_widget.raw_content + message.content
                        )

                    if message.tool_calls:
                        for tc in message.tool_calls:
                            tool_name = tc.function.name if tc.function else "unknown"
                            tool_args = tc.function.arguments if tc.function else "{}"
                            self.tool_log_widget.write(
                                f"[yellow]🔧 Pending: {tool_name}({tool_args})[/yellow]"
                            )

                elif isinstance(message, ToolMessage):
                    self.tool_log_widget.write(
                        f"[green]✓ Completed tool call (ID: {message.tool_call_id or 'unknown'})[/green]"
                    )
                    
                    # Output details
                    self.output_viewer_widget.write(
                        f"\n--- [bold green]Tool Result[/bold green] (ID: {message.tool_call_id or 'unknown'}) ---"
                    )
                    self.output_viewer_widget.write(message.content)
                    
                    # Clear current assistant widget so next LLM generation starts fresh
                    current_assistant_widget = None

                # Keep chat scrolled to end
                self.chat_scroll.scroll_end()

        except asyncio.CancelledError:
            self.tool_log_widget.write("[red]🚫 Interrupted execution.[/red]")
            err_widget = Static("[bold red]Execution cancelled by user.[/bold red]", classes="error-msg")
            await self.chat_scroll.mount(err_widget)
            self.chat_scroll.scroll_end()
        except Exception as e:
            self.tool_log_widget.write(f"[red]❌ Error: {e}[/red]")
            err_widget = Static(f"[bold red]System Error:[/] {e}", classes="error-msg")
            await self.chat_scroll.mount(err_widget)
            self.chat_scroll.scroll_end()
        finally:
            self.agent_run_task = None
            self.input_widget.disabled = False
            self.input_widget.focus()
