"""Interactive REPL implementation using prompt_toolkit.

Provides:
- Natural language interaction by default
- Slash commands for utility functions (/help, /model, etc.)
- Shell commands (ls, cd, etc.)
- Arrow key history navigation
- Ctrl+R reverse search
- Context-aware tab completion
"""

from typing import Any, Iterator

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console

from grok_cli import config
from grok_cli.ui.prompt import create_prompt, PROMPT_STYLE
from grok_cli.agent import Agent, display_response
from grok_cli.slash_commands import (
    is_slash_command,
    parse_slash_command,
    execute_slash_command,
    SLASH_COMMANDS,
)
from grok_cli.commands.shell import is_shell_command, execute_shell_command

console = Console()


class GrokCompleter(Completer):
    """Tab completer for Grok CLI."""

    def __init__(self) -> None:
        """Initialize completer."""
        # Slash commands
        self.slash_commands = [f"/{cmd}" for cmd in SLASH_COMMANDS.keys()]
        self.slash_commands.extend(["/exit", "/quit", "/q"])

        # Shell commands
        self.shell_commands = [
            "ls",
            "ll",
            "cd",
            "pwd",
            "cat",
            "head",
            "tail",
            "mkdir",
            "tree",
            "cp",
            "mv",
            "rm",
        ]

    def get_completions(self, document: Document, complete_event: Any) -> Iterator[Completion]:
        """Get completions for current input.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor.strip()

        # Slash command completion
        if text.startswith("/"):
            for cmd in self.slash_commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
            return

        # Shell command completion (only at start of line)
        words = text.split()
        if not words or (len(words) == 1 and not document.text_before_cursor.endswith(" ")):
            word = words[0] if words else ""
            for cmd in self.shell_commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))


def start_repl(cfg: dict[str, Any]) -> None:
    """Start the interactive REPL.

    Args:
        cfg: Configuration dictionary
    """
    # Set up history file
    history_file = config.get_grok_dir() / "history"
    history = FileHistory(str(history_file))

    # Create prompt session with history and completion
    session: PromptSession[str] = PromptSession(
        history=history,
        completer=GrokCompleter(),
        complete_while_typing=True,
        style=Style.from_dict(PROMPT_STYLE),
    )

    # Initialize agent
    agent = Agent(cfg)

    # Get current model from config
    current_model = cfg.get("default_model", "grok41_fast")

    console.print("[dim]Type naturally to chat, /help for commands, /exit to quit[/dim]\n")

    # Main REPL loop
    while True:
        try:
            # Create dynamic prompt
            prompt = create_prompt(model=current_model)

            # Get user input
            line = session.prompt(prompt)
            line = line.strip()

            # Skip empty input
            if not line:
                continue

            # Check for exit commands (without slash for convenience)
            if line.lower() in ("exit", "quit"):
                break

            # Handle slash commands
            if is_slash_command(line):
                command, args = parse_slash_command(line)

                if not execute_slash_command(command, args, cfg, agent):
                    break

                # Update current model in case it changed
                current_model = cfg.get("default_model", current_model)
                continue

            # Handle shell commands
            first_word = line.split()[0] if line.split() else ""
            if is_shell_command(first_word):
                try:
                    execute_shell_command(line.split())
                except Exception as e:
                    console.print(f"[red]Error:[/red] {e}")
                continue

            # Default: send to agent as natural language
            try:
                response = agent.chat(line)
                display_response(response)
            except ValueError as e:
                # API key not set or other config error
                console.print(f"[red]Error:[/red] {e}")
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        except KeyboardInterrupt:
            console.print("\n[dim]Use /exit or /quit to leave[/dim]")
            continue
        except EOFError:
            break

    console.print("\n[dim]Goodbye![/dim]")
