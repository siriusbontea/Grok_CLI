"""Sandbox enforcement for safe file operations.

All file operations are strictly restricted to the launch directory.
This cannot be disabled - safety is mandatory.
"""

from pathlib import Path

from rich.console import Console

# Launch directory - where grok was spawned (never changes)
LAUNCH_DIR = Path.cwd().resolve()

# Current directory - updated by cd command, starts at LAUNCH_DIR
CURRENT_DIR = LAUNCH_DIR

console = Console()


def init_sandbox() -> None:
    """Initialize sandbox with launch directory (where grok was spawned)."""
    global LAUNCH_DIR, CURRENT_DIR

    # Lock to the directory where grok was spawned
    LAUNCH_DIR = Path.cwd().resolve()
    CURRENT_DIR = LAUNCH_DIR

    # Share launch directory with config module for project-local storage
    from grok_cli import config

    config.set_launch_dir(LAUNCH_DIR)


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
        PermissionError: If path is outside sandbox
    """
    global CURRENT_DIR

    resolved = path.resolve()

    # Check if new path is within launch directory
    try:
        resolved.relative_to(LAUNCH_DIR)
    except ValueError:
        raise PermissionError(f"Cannot cd outside launch directory: {LAUNCH_DIR}\n" f"Attempted path: {resolved}")

    CURRENT_DIR = resolved


def check_path_allowed(path: Path, operation: str = "access") -> Path:
    """Check if a path is allowed within the sandbox.

    Args:
        path: Path to check
        operation: Description of operation for error message

    Returns:
        Resolved absolute path

    Raises:
        PermissionError: If path is outside sandbox
    """
    # Make path absolute relative to CURRENT_DIR
    if not path.is_absolute():
        path = CURRENT_DIR / path

    resolved = path.resolve()

    # Check if path is within launch directory
    try:
        resolved.relative_to(LAUNCH_DIR)
    except ValueError:
        raise PermissionError(
            f"Cannot {operation} path outside launch directory: {resolved}\n" f"Launch directory: {LAUNCH_DIR}"
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
    from rich.prompt import Prompt

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
