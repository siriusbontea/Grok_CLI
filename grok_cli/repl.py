"""Interactive REPL implementation using prompt_toolkit.

Provides:
- Natural language interaction by default
- Slash commands for utility functions (/help, /model, etc.)
- Shell commands (ls, cd, etc.)
- Arrow key history navigation
- Ctrl+R reverse search
- Context-aware tab completion
- File path completion
- Ctrl+L to clear screen
- Multiline input (paste support)
- Auto-suggestions from history
"""

from typing import Any, Iterator

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console

from grok_cli import config, sandbox
from grok_cli.ui.prompt import create_prompt, PROMPT_STYLE
from grok_cli.agent import Agent
from grok_cli.slash_commands import (
    is_slash_command,
    parse_slash_command,
    execute_slash_command,
    SLASH_COMMANDS,
)
from grok_cli.commands.shell import is_shell_command, execute_shell_command

console = Console()

# Create key bindings
kb = KeyBindings()


@kb.add("c-l")
def clear_screen_(event: Any) -> None:
    """Clear the screen with Ctrl+L."""
    event.app.renderer.clear()


class GrokCompleter(Completer):
    """Tab completer for Grok CLI with file path support."""

    def __init__(self) -> None:
        """Initialize completer."""
        # Slash commands
        self.slash_commands = [f"/{cmd}" for cmd in SLASH_COMMANDS.keys()]
        self.slash_commands.extend(["/exit", "/quit", "/q"])

        # Shell commands that take file arguments
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

        # Commands that expect file/directory arguments
        self.file_commands = {"cat", "head", "tail", "cp", "mv", "rm", "cd", "ls", "ll", "tree", "mkdir"}

        # Path completer for file arguments
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document: Document, complete_event: Any) -> Iterator[Completion]:
        """Get completions for current input.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor
        stripped = text.strip()

        # Slash command completion
        if stripped.startswith("/"):
            for cmd in self.slash_commands:
                if cmd.startswith(stripped):
                    yield Completion(cmd, start_position=-len(stripped))
            return

        # Parse the input
        words = stripped.split()

        # Shell command completion (only at start of line, first word)
        if not words or (len(words) == 1 and not text.endswith(" ")):
            word = words[0] if words else ""
            for cmd in self.shell_commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))
            return

        # File path completion for shell commands that take file arguments
        if words and words[0] in self.file_commands:
            # Get the current word being typed
            if text.endswith(" "):
                # Starting a new word - complete from current directory
                current_word = ""
                start_pos = 0
            else:
                # Completing the last word
                current_word = words[-1] if len(words) > 1 else ""
                start_pos = -len(current_word)

            # Get completions from the sandbox directory
            try:
                cwd = sandbox.get_current_dir()
                search_path = cwd / current_word if current_word else cwd

                # If partial path, get the directory part
                if current_word and not current_word.endswith("/"):
                    search_dir = search_path.parent if "/" in current_word else cwd
                    prefix = search_path.name
                else:
                    search_dir = search_path if search_path.is_dir() else cwd
                    prefix = ""

                if search_dir.exists() and search_dir.is_dir():
                    for item in sorted(search_dir.iterdir()):
                        name = item.name
                        if name.startswith("."):
                            continue  # Skip hidden files
                        if prefix and not name.lower().startswith(prefix.lower()):
                            continue

                        # Build the completion text
                        if "/" in current_word:
                            # Include the directory part
                            dir_part = current_word.rsplit("/", 1)[0] + "/"
                            completion_text = dir_part + name
                        else:
                            completion_text = name

                        if item.is_dir():
                            completion_text += "/"

                        yield Completion(
                            completion_text,
                            start_position=start_pos,
                            display=name + ("/" if item.is_dir() else ""),
                        )
            except Exception:
                pass  # Silently ignore path completion errors


def start_repl(cfg: dict[str, Any]) -> None:
    """Start the interactive REPL.

    Args:
        cfg: Configuration dictionary
    """
    # Set up project-local history file
    history_file = config.get_project_dir() / "history"
    history = FileHistory(str(history_file))

    # Create prompt session with history, completion, key bindings, and auto-suggest
    session: PromptSession[str] = PromptSession(
        history=history,
        completer=GrokCompleter(),
        complete_while_typing=True,
        style=Style.from_dict(PROMPT_STYLE),
        key_bindings=kb,
        auto_suggest=AutoSuggestFromHistory(),
        multiline=False,  # Single line by default, but paste works
        mouse_support=True,
        enable_history_search=True,
    )

    # Initialize agent
    agent = Agent(cfg)

    # Auto-load previous context if it exists
    if agent.load_context():
        msg_count = len(agent.messages)
        console.print(f"[dim]Resumed previous conversation ({msg_count} messages)[/dim]")
        console.print("[dim]Use /clear to start fresh[/dim]\n")
    else:
        console.print("[dim]Type naturally to chat, /help for commands, Ctrl+L to clear, /exit to quit[/dim]\n")

    # Get current model from config
    current_model = cfg.get("default_model", "grok41_fast")

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
            # Response is streamed directly by the agent
            try:
                agent.chat(line)
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
