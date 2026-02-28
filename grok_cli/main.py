"""Main entry point for Grok CLI.

Implements Typer app and prompt_toolkit REPL.
"""

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
) -> None:
    """Grok CLI - Natural language interface for Grok models.

    Run without arguments to enter interactive mode.
    Type naturally to chat, use /help for commands.
    """
    # Initialize sandbox (always enforced, cannot be disabled)
    sandbox.init_sandbox()

    # Load configuration (creates default on first run)
    cfg = config.load_config()

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

        # Check for first run
        if config.is_first_run():
            # First run: show full welcome with instructions
            show_welcome_banner()
        else:
            # Regular run: just show the ASCII art banner
            show_banner()

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
def resume(ctx: typer.Context) -> None:
    """Resume last session and enter interactive mode."""
    cfg = ctx.obj["cfg"]
    from grok_cli.commands.utility import resume_command
    from grok_cli import session as sess

    try:
        session_data = resume_command(cfg)
        if session_data:
            # Write session data to context.toon so the REPL picks it up
            context_path = config.get_project_dir() / "context.toon"
            context_path.write_text(sess.serialize_toon(session_data))
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
