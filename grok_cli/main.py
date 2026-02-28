"""Main entry point for Grok CLI.

Implements Typer app and prompt_toolkit REPL.
"""

import os
import sys
from typing import Optional

import typer
from rich.console import Console

from grok_cli import config, sandbox

app = typer.Typer(
    name="grok",
    help="Lean, safe interface for Grok models",
    add_completion=False,
    rich_markup_mode=None,  # Disable rich formatting to avoid compatibility issues
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    yes: bool = typer.Option(False, "-y", "--yes", help="Auto-confirm file operations (skip prompts)"),
    allow_entire_fs: bool = typer.Option(
        False,
        "--dangerously-allow-entire-fs",
        help="Disable sandbox (allows access to entire filesystem, requires typing YES)",
    ),
) -> None:
    """Grok CLI - Natural language interface for Grok models.

    Run without arguments to enter interactive mode.
    Type naturally to chat, use /help for commands.
    """
    # Initialize sandbox (always enforced, cannot be disabled)
    sandbox.init_sandbox()

    # Handle --dangerously-allow-entire-fs flag
    if allow_entire_fs:
        console.print(
            "\n[bold red]WARNING: You are about to disable the filesystem sandbox.[/bold red]\n"
            "This allows Grok to read, write, and modify ANY file on your system.\n"
            "This is dangerous and should only be used when you understand the risks.\n"
        )
        confirmation = console.input("[bold]Type YES to confirm: [/bold]")
        if confirmation == "YES":
            sandbox.enable_full_fs_access()
            console.print("[yellow]Sandbox disabled. Full filesystem access enabled.[/yellow]\n")
        else:
            console.print("[green]Sandbox remains active.[/green]\n")

    # Check first-run BEFORE load_config (which creates the config file)
    first_run = config.is_first_run()

    # Load configuration (creates default on first run)
    cfg = config.load_config()

    # Honour colour = false by setting NO_COLOR (Rich reads this natively)
    if not cfg.get("colour", True):
        os.environ["NO_COLOR"] = "1"

    # Discover plugins and bridge their commands into slash commands
    from grok_cli.plugins import discover_plugins
    from grok_cli.slash_commands import bridge_plugin_commands

    discover_plugins()
    bridge_plugin_commands()

    # Override auto_yes if -y flag is passed
    if yes:
        cfg["auto_yes"] = True

    # Store cfg on context so subcommands can access it
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = cfg

    # If no subcommand specified, enter REPL mode
    if ctx.invoked_subcommand is None:
        from grok_cli.ui.banner import show_banner, show_welcome_banner

        # Check for first run (computed before load_config created the file)
        if first_run:
            # First run: show full welcome with instructions
            show_welcome_banner()
        else:
            # Regular run: just show the ASCII art banner
            show_banner()

        if sandbox.is_full_fs_enabled():
            console.print(
                "[bold red on white] ⚠ SANDBOX DISABLED — FULL FILESYSTEM ACCESS ⚠ [/bold red on white]\n"
            )

        from grok_cli.repl import start_repl

        start_repl(cfg)


@app.command()
def create(
    ctx: typer.Context,
    file_type: str = typer.Argument(..., help="File type (py, js, ts, html, css, json, yaml, toml, md, sh, etc.)"),
    description: str = typer.Argument(..., help="Description of what to create"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output filename (auto-suggested if omitted)"),
) -> None:
    """Create a new file with AI-generated content."""
    cfg = ctx.obj["cfg"]
    from grok_cli.commands.create import create_command

    try:
        create_command(file_type, description, output, cfg, cfg.get("auto_yes", False))
    except (ValueError, PermissionError, FileExistsError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def edit(
    ctx: typer.Context,
    filename: str = typer.Argument(..., help="File to edit"),
    instruction: str = typer.Argument(..., help="Editing instruction"),
) -> None:
    """Edit an existing file with AI assistance."""
    cfg = ctx.obj["cfg"]
    from grok_cli.commands.edit import edit_command

    try:
        edit_command(filename, instruction, cfg, cfg.get("auto_yes", False))
    except (ValueError, FileNotFoundError, PermissionError, RuntimeError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def ask(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="Question to ask"),
) -> None:
    """Ask a general question (no file access)."""
    cfg = ctx.obj["cfg"]
    from grok_cli.commands.ask import ask_command, display_answer

    try:
        answer = ask_command(question, cfg)
        display_answer(answer)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def resume(
    ctx: typer.Context,
    new: bool = typer.Option(False, "--new", help="Start a new session (clear previous context)"),
) -> None:
    """Resume last session and enter interactive mode."""
    cfg = ctx.obj["cfg"]

    if new:
        # --new: delete context.toon so the REPL starts fresh
        context_path = config.get_project_dir() / "context.toon"
        if context_path.exists():
            context_path.unlink()
        console.print("[green]Starting fresh session.[/green]")
    else:
        from grok_cli.commands.utility import resume_command
        from grok_cli import session as sess

        try:
            session_data = resume_command(cfg)
            if session_data:
                # Write session data to context.toon so the REPL picks it up
                context_path = config.get_project_dir() / "context.toon"
                # Extract messages from session data (handles both compressed and uncompressed)
                toon_text = sess.serialize_toon(session_data)
                messages = sess.toon_to_messages(toon_text)
                if messages:
                    context_path.write_text(sess.messages_to_toon(messages))
                else:
                    # Compressed session with history key — inject as system context
                    history = session_data.get("history", "")
                    if history:
                        history_str = ", ".join(history) if isinstance(history, list) else str(history)
                        context_path.write_text(
                            sess.messages_to_toon(
                                [{"role": "system", "content": f"Previous session summary: {history_str}"}]
                            )
                        )
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1)

    from grok_cli.repl import start_repl

    start_repl(cfg)


@app.command()
def model(
    ctx: typer.Context,
    model_name: str = typer.Argument(..., help="Model to switch to (use 'grok models' to list)"),
) -> None:
    """Switch the default model."""
    cfg = ctx.obj["cfg"]
    from grok_cli.commands.utility import model_command

    model_command(model_name, cfg)


@app.command()
def models(ctx: typer.Context) -> None:
    """List all available models."""
    from grok_cli.commands.utility import models_command

    models_command()


@app.command()
def cost(ctx: typer.Context) -> None:
    """Show token usage and cost dashboard."""
    from grok_cli.commands.utility import cost_command

    cost_command()


@app.command()
def plugins(ctx: typer.Context) -> None:
    """List loaded plugins."""
    from grok_cli.commands.utility import plugins_command

    plugins_command()


@app.command(name="help")
def help_cmd(
    ctx: typer.Context,
    topic: Optional[str] = typer.Argument(None, help="Help topic (create, edit, ask, heavy, models, sandbox, config)"),
) -> None:
    """Show help information."""
    from grok_cli.commands.utility import help_command

    help_command(topic)


def run() -> None:
    """Entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
