"""Sandbox enforcement for safe file operations.

All file operations are restricted to the launch directory by default.
The --dangerously-allow-entire-fs flag allows escaping with typed "YES" confirmation.
"""

from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

# Launch directory - where grok was spawned (never changes)
LAUNCH_DIR = Path.cwd().resolve()

# Current directory - updated by cd command, starts at LAUNCH_DIR
CURRENT_DIR = LAUNCH_DIR

# Global flag for dangerous mode
DANGEROUS_MODE_ENABLED = False

console = Console()


def init_sandbox(dangerous: bool = False) -> None:
    """Initialize sandbox with launch directory (where grok was spawned).

    Args:
        dangerous: If True, prompt for "YES" confirmation to allow entire filesystem
    """
    global LAUNCH_DIR, CURRENT_DIR, DANGEROUS_MODE_ENABLED

    # Lock to the directory where grok was spawned
    LAUNCH_DIR = Path.cwd().resolve()
    CURRENT_DIR = LAUNCH_DIR

    console.print(f"[dim]Launch directory: {LAUNCH_DIR}[/dim]")

    if dangerous:
        console.print("\n[bold red]WARNING:[/bold red] You are about to disable filesystem sandboxing!")
        console.print("This will allow operations on your [bold]entire filesystem[/bold].")
        console.print(f"Current sandbox: [cyan]{LAUNCH_DIR}[/cyan]")
        console.print("This could lead to accidental data loss or system damage.\n")

        confirmation = Prompt.ask("Type [bold]YES[/bold] (all caps) to confirm", console=console)

        if confirmation == "YES":
            DANGEROUS_MODE_ENABLED = True
            console.print("[yellow]Sandbox disabled. All filesystem operations enabled.[/yellow]")
            console.print(f"[yellow]Working directory remains: {CURRENT_DIR}[/yellow]\n")
        else:
            console.print("[green]Sandbox remains enabled. Operations restricted to launch directory.[/green]\n")


def get_current_dir() -> Path:
    """Get the current working directory within sandbox.

    Returns:
        Current working directory path
    """
    return CURRENT_DIR


def get_launch_dir() -> Path:
    """Get the launch directory (where grok was spawned).

    Returns:
        Launch directory path (immutable)
    """
    return LAUNCH_DIR


def set_current_dir(path: Path) -> None:
    """Set the current sandbox directory (used by cd command).

    Args:
        path: New current directory

    Raises:
        PermissionError: If path is outside sandbox and dangerous mode not enabled
    """
    global CURRENT_DIR

    resolved = path.resolve()

    if not DANGEROUS_MODE_ENABLED:
        # Check if new path is within launch directory
        try:
            resolved.relative_to(LAUNCH_DIR)
        except ValueError:
            raise PermissionError(
                f"Cannot cd outside launch directory: {LAUNCH_DIR}\n"
                f"Attempted path: {resolved}\n"
                f"Use --dangerously-allow-entire-fs to disable sandbox"
            )

    CURRENT_DIR = resolved


def check_path_allowed(path: Path, operation: str = "access") -> Path:
    """Check if a path is allowed within the sandbox.

    Args:
        path: Path to check
        operation: Description of operation for error message

    Returns:
        Resolved absolute path

    Raises:
        PermissionError: If path is outside sandbox and dangerous mode not enabled
    """
    # Make path absolute relative to CURRENT_DIR
    if not path.is_absolute():
        path = CURRENT_DIR / path

    resolved = path.resolve()

    if not DANGEROUS_MODE_ENABLED:
        # Check if path is within launch directory
        try:
            resolved.relative_to(LAUNCH_DIR)
        except ValueError:
            raise PermissionError(
                f"Cannot {operation} path outside launch directory: {resolved}\n"
                f"Launch directory: {LAUNCH_DIR}\n"
                f"Use --dangerously-allow-entire-fs to disable sandbox"
            )

    return resolved


def check_overwrite_allowed(path: Path, auto_yes: bool = False) -> bool:
    """Check if overwriting a file is allowed.

    Prompts user for confirmation unless auto_yes is True.

    Args:
        path: Path to file
        auto_yes: If True, skip confirmation

    Returns:
        True if overwrite is allowed

    Raises:
        PermissionError: If path is outside sandbox
    """
    # First check sandbox
    resolved = check_path_allowed(path, "overwrite")

    # Check if file exists
    if not resolved.exists():
        return True

    # File exists - need confirmation
    if auto_yes:
        return True

    console.print(f"\n[yellow]File exists:[/yellow] {resolved}")
    confirmation = Prompt.ask("Overwrite? (y/N)", choices=["y", "n", "Y", "N"], default="n", console=console)

    return confirmation.lower() == "y"


def is_dangerous_mode() -> bool:
    """Check if dangerous mode is enabled.

    Returns:
        True if --dangerously-allow-entire-fs was confirmed
    """
    return DANGEROUS_MODE_ENABLED
