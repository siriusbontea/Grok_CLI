"""Main entry point for Grok CLI.

Implements Typer app and prompt_toolkit REPL.
"""

import sys

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
    dangerously_allow_entire_fs: bool = typer.Option(
        default=False,
        flag_value=True,
        help="Disable filesystem sandbox (requires typing 'YES')"
    ),
) -> None:
    """Grok CLI - Lean, safe interface for Grok models.

    Run without arguments to enter REPL mode.
    Run with a command to execute directly.
    """
    # Initialize sandbox
    sandbox.init_sandbox(dangerous=dangerously_allow_entire_fs)

    # Load configuration (creates default on first run)
    cfg = config.load_config()

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
