"""Interactive REPL implementation using prompt_toolkit.

Provides:
- Arrow key history navigation
- Ctrl+R reverse search
- Context-aware tab completion
- Integration with Typer command parsing
"""

import shlex
from typing import Any, Iterator

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console

from grok_cli import config
from grok_cli.ui.prompt import create_prompt, PROMPT_STYLE

console = Console()


class GrokCompleter(Completer):
    """Tab completer for Grok CLI commands."""

    def __init__(self) -> None:
        """Initialize completer with basic commands."""
        # Basic commands (will be expanded with plugin discovery)
        self.commands = [
            "create",
            "edit",
            "ask",
            "heavy",
            "resume",
            "model",
            "models",
            "cost",
            "plugins",
            "help",
            # Shell commands
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
            # Special
            "exit",
            "quit",
        ]

    def get_completions(self, document: Document, complete_event: Any) -> Iterator[Completion]:
        """Get completions for current input.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor
        words = text.split()

        # If empty or first word, complete command names
        if not words or (len(words) == 1 and not text.endswith(" ")):
            word = words[0] if words else ""
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))

        # TODO: Context-aware completion for arguments
        # For now, just file/directory completion would go here


def parse_command(line: str) -> list[str] | None:
    """Parse command line into arguments.

    Handles quotes and escaping properly.

    Args:
        line: Command line string

    Returns:
        List of arguments or None if empty
    """
    line = line.strip()
    if not line:
        return None

    # Handle exit/quit specially
    if line in ("exit", "quit"):
        return None

    try:
        return shlex.split(line)
    except ValueError as e:
        console.print(f"[red]Parse error:[/red] {e}")
        return []


def execute_command(args: list[str], cfg: dict[str, Any]) -> bool:
    """Execute a command in the REPL.

    Args:
        args: Command arguments
        cfg: Configuration dictionary

    Returns:
        True to continue REPL, False to exit
    """
    if not args:
        return True

    command = args[0]
    cmd_args = args[1:]

    # Check if it's a shell command
    from grok_cli.commands.shell import is_shell_command, execute_shell_command

    if is_shell_command(command):
        try:
            execute_shell_command(args)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
        return True

    # Route to command handlers
    try:
        if command == "ask":
            if not cmd_args:
                console.print("[red]Error:[/red] ask requires a question")
                return True

            from grok_cli.commands.ask import ask_command, display_answer

            question = " ".join(cmd_args)
            answer = ask_command(question, cfg)
            display_answer(answer)

        elif command == "create":
            if len(cmd_args) < 2:
                console.print("[red]Error:[/red] create requires <type> <description>")
                console.print('Example: create py "binary search algorithm"')
                return True

            from grok_cli.commands.create import create_command

            file_type = cmd_args[0]
            description = " ".join(cmd_args[1:])
            create_command(file_type, description, None, cfg)

        elif command == "edit":
            if len(cmd_args) < 2:
                console.print("[red]Error:[/red] edit requires <file> <instruction>")
                console.print('Example: edit utils.py "add type hints"')
                return True

            from grok_cli.commands.edit import edit_command

            filename = cmd_args[0]
            instruction = " ".join(cmd_args[1:])
            edit_command(filename, instruction, cfg)

        elif command == "heavy":
            if not cmd_args:
                console.print("[red]Error:[/red] heavy requires a task description")
                return True

            from grok_cli.commands.heavy import heavy_command, display_heavy_result

            task = " ".join(cmd_args)
            result = heavy_command(task, None, cfg)
            display_heavy_result(result)

        elif command == "models":
            from grok_cli.commands.utility import models_command

            models_command()

        elif command == "model":
            if not cmd_args:
                console.print("[red]Error:[/red] model requires a model name")
                console.print("Use 'models' to list available models")
                return True

            from grok_cli.commands.utility import model_command

            model_command(cmd_args[0], cfg)

        elif command == "plugins":
            from grok_cli.commands.utility import plugins_command

            plugins_command()

        elif command == "resume":
            from grok_cli.commands.utility import resume_command

            resume_command(cfg)

        elif command == "cost":
            from grok_cli.commands.utility import cost_command

            cost_command()

        elif command == "help":
            from grok_cli.commands.utility import help_command

            topic = cmd_args[0] if cmd_args else None
            help_command(topic)

        else:
            console.print(f"[yellow]Unknown command:[/yellow] {command}")
            console.print("[dim]Type 'help' for available commands[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

    return True


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

    # Get current model from config
    current_model = cfg.get("default_model", "grok41_fast")

    console.print("[dim]Entering REPL mode. Type 'exit' or 'quit' to leave, 'help' for commands.[/dim]\n")

    # Main REPL loop
    while True:
        try:
            # Create dynamic prompt
            prompt = create_prompt(model=current_model)

            # Get user input
            line = session.prompt(prompt)

            # Parse command
            args = parse_command(line)

            # Check for exit
            if args is None:
                break

            # Execute command
            if not execute_command(args, cfg):
                break

        except KeyboardInterrupt:
            console.print("\n[dim]Use 'exit' or 'quit' to leave REPL[/dim]")
            continue
        except EOFError:
            break

    console.print("\n[dim]Goodbye![/dim]")
