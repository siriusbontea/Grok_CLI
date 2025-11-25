"""Built-in sandboxed shell commands (pure Python, no subprocess).

All commands respect the sandbox and use pathlib/shutil for safety.
No subprocess calls - works identically on Windows/Mac/Linux.
"""

import shutil
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from grok_cli import sandbox

console = Console()

# Shell commands that are handled by this module
SHELL_COMMANDS = {
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
}


def is_shell_command(cmd: str) -> bool:
    """Check if a command is a built-in shell command.

    Args:
        cmd: Command name

    Returns:
        True if it's a shell command
    """
    return cmd in SHELL_COMMANDS


def cmd_ls(args: list[str]) -> None:
    """List directory contents.

    Args:
        args: Command arguments (directory path optional)
    """
    # Parse arguments
    show_all = "-a" in args or "--all" in args
    long_format = "-l" in args

    # Get target directory
    paths = [arg for arg in args if not arg.startswith("-")]
    target = Path(paths[0]) if len(paths) > 0 else Path(".")

    # Check sandbox
    target_abs = sandbox.check_path_allowed(target, "list")

    if not target_abs.exists():
        console.print(f"[red]Error:[/red] {target} does not exist")
        return

    if not target_abs.is_dir():
        console.print(f"[red]Error:[/red] {target} is not a directory")
        return

    # List contents
    try:
        items = sorted(target_abs.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        console.print(f"[red]Error:[/red] Permission denied: {target}")
        return

    # Filter hidden files unless -a
    if not show_all:
        items = [item for item in items if not item.name.startswith(".")]

    if long_format:
        # Long format table
        table = Table(show_header=False, box=None, padding=(0, 2))
        for item in items:
            stat = item.stat()
            size = stat.st_size
            name = item.name
            if item.is_dir():
                name = f"[blue]{name}/[/blue]"
            elif item.is_symlink():
                name = f"[cyan]{name}@[/cyan]"
            table.add_row(f"{size:>10}", name)
        console.print(table)
    else:
        # Simple format
        for item in items:
            name = item.name
            if item.is_dir():
                console.print(f"[blue]{name}/[/blue]", end="  ")
            elif item.is_symlink():
                console.print(f"[cyan]{name}@[/cyan]", end="  ")
            else:
                console.print(name, end="  ")
        console.print()  # Newline at end


def cmd_ll(args: list[str]) -> None:
    """List directory contents in long format (alias for ls -l).

    Args:
        args: Command arguments
    """
    cmd_ls(["-l"] + args)


def cmd_cd(args: list[str]) -> None:
    """Change current directory.

    Args:
        args: Command arguments (directory path)
    """
    if len(args) < 1:
        # cd with no args goes to launch directory (project root)
        target = sandbox.get_launch_dir()
    else:
        target = Path(args[0])

    # Make absolute relative to current dir
    if not target.is_absolute():
        target = sandbox.get_current_dir() / target

    # Resolve
    try:
        target = target.resolve()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return

    # Check if exists
    if not target.exists():
        console.print(f"[red]Error:[/red] {target} does not exist")
        return

    if not target.is_dir():
        console.print(f"[red]Error:[/red] {target} is not a directory")
        return

    # Try to set (will check sandbox)
    try:
        sandbox.set_current_dir(target)
    except PermissionError:
        # Show prominent warning when trying to escape sandbox
        console.print()
        console.print("[bold red]╔══════════════════════════════════════════════════════════╗[/bold red]")
        console.print("[bold red]║    SANDBOX VIOLATION: Cannot navigate outside project    ║[/bold red]")
        console.print("[bold red]╚══════════════════════════════════════════════════════════╝[/bold red]")
        console.print()
        console.print(f"[yellow]Attempted path:[/yellow] {target}")
        console.print(f"[yellow]Project root:[/yellow]   {sandbox.get_launch_dir()}")
        console.print()
        console.print("[dim]All operations are restricted to the project directory for safety.[/dim]")
        console.print()


def cmd_pwd(args: list[str]) -> None:
    """Print working directory.

    Args:
        args: Command arguments (unused)
    """
    console.print(sandbox.get_current_dir())


def cmd_cat(args: list[str]) -> None:
    """Display file contents.

    Args:
        args: Command arguments (file paths)
    """
    if len(args) < 1:
        console.print("[red]Error:[/red] cat requires at least one file argument")
        return

    for file_path in args:
        target = Path(file_path)
        try:
            target_abs = sandbox.check_path_allowed(target, "read")

            if not target_abs.exists():
                console.print(f"[red]Error:[/red] {file_path} does not exist")
                continue

            if not target_abs.is_file():
                console.print(f"[red]Error:[/red] {file_path} is not a file")
                continue

            content = target_abs.read_text()
            console.print(content, end="")

        except PermissionError as e:
            console.print(f"[red]Error:[/red] {e}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def cmd_head(args: list[str]) -> None:
    """Display first lines of file (default 10).

    Args:
        args: Command arguments (-n NUM file)
    """
    # Parse arguments
    num_lines = 10
    files = []

    i = 0
    while i < len(args):
        if args[i] == "-n" and i + 1 < len(args):
            try:
                num_lines = int(args[i + 1])
                i += 2
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid number: {args[i + 1]}")
                return
        else:
            files.append(args[i])
            i += 1

    if not files:
        console.print("[red]Error:[/red] head requires a file argument")
        return

    for file_path in files:
        target = Path(file_path)
        try:
            target_abs = sandbox.check_path_allowed(target, "read")

            if not target_abs.exists():
                console.print(f"[red]Error:[/red] {file_path} does not exist")
                continue

            if not target_abs.is_file():
                console.print(f"[red]Error:[/red] {file_path} is not a file")
                continue

            lines = target_abs.read_text().splitlines()
            for line in lines[:num_lines]:
                console.print(line)

        except PermissionError as e:
            console.print(f"[red]Error:[/red] {e}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def cmd_tail(args: list[str]) -> None:
    """Display last lines of file (default 10).

    Args:
        args: Command arguments (-n NUM file)
    """
    # Parse arguments
    num_lines = 10
    files = []

    i = 0
    while i < len(args):
        if args[i] == "-n" and i + 1 < len(args):
            try:
                num_lines = int(args[i + 1])
                i += 2
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid number: {args[i + 1]}")
                return
        else:
            files.append(args[i])
            i += 1

    if not files:
        console.print("[red]Error:[/red] tail requires a file argument")
        return

    for file_path in files:
        target = Path(file_path)
        try:
            target_abs = sandbox.check_path_allowed(target, "read")

            if not target_abs.exists():
                console.print(f"[red]Error:[/red] {file_path} does not exist")
                continue

            if not target_abs.is_file():
                console.print(f"[red]Error:[/red] {file_path} is not a file")
                continue

            lines = target_abs.read_text().splitlines()
            for line in lines[-num_lines:]:
                console.print(line)

        except PermissionError as e:
            console.print(f"[red]Error:[/red] {e}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def cmd_mkdir(args: list[str]) -> None:
    """Create directory (supports -p for parents).

    Args:
        args: Command arguments (-p path)
    """
    # Parse arguments
    make_parents = "-p" in args
    paths = [arg for arg in args if not arg.startswith("-")]

    if not paths:
        console.print("[red]Error:[/red] mkdir requires a directory path")
        return

    for dir_path in paths:
        target = Path(dir_path)
        try:
            target_abs = sandbox.check_path_allowed(target, "create")

            if target_abs.exists():
                console.print(f"[yellow]Warning:[/yellow] {dir_path} already exists")
                continue

            if make_parents:
                target_abs.mkdir(parents=True, exist_ok=True)
            else:
                target_abs.mkdir()

            console.print(f"Created: {dir_path}")

        except PermissionError as e:
            console.print(f"[red]Error:[/red] {e}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def cmd_tree(args: list[str]) -> None:
    """Display directory tree.

    Args:
        args: Command arguments (directory path optional)
    """
    # Get target directory
    target = Path(args[0]) if args else Path(".")

    try:
        target_abs = sandbox.check_path_allowed(target, "read")

        if not target_abs.exists():
            console.print(f"[red]Error:[/red] {target} does not exist")
            return

        if not target_abs.is_dir():
            console.print(f"[red]Error:[/red] {target} is not a directory")
            return

        # Build tree
        tree = Tree(f"[bold blue]{target_abs.name or target_abs}/[/bold blue]")
        _build_tree(target_abs, tree, max_depth=3)

        console.print(tree)

    except PermissionError as e:
        console.print(f"[red]Error:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def _build_tree(path: Path, tree: Tree, current_depth: int = 0, max_depth: int = 3) -> None:
    """Recursively build tree structure.

    Args:
        path: Current path
        tree: Tree node to add to
        current_depth: Current recursion depth
        max_depth: Maximum depth to recurse
    """
    if current_depth >= max_depth:
        return

    try:
        items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        # Filter hidden
        items = [item for item in items if not item.name.startswith(".")]

        for item in items:
            if item.is_dir():
                branch = tree.add(f"[blue]{item.name}/[/blue]")
                _build_tree(item, branch, current_depth + 1, max_depth)
            else:
                tree.add(item.name)
    except PermissionError:
        tree.add("[red](permission denied)[/red]")


def cmd_cp(args: list[str]) -> None:
    """Copy files or directories.

    Args:
        args: Command arguments (source dest)
    """
    if len(args) < 2:
        console.print("[red]Error:[/red] cp requires source and destination")
        return

    source = Path(args[0])
    dest = Path(args[1])

    try:
        source_abs = sandbox.check_path_allowed(source, "read")
        dest_abs = sandbox.check_path_allowed(dest, "write")

        if not source_abs.exists():
            console.print(f"[red]Error:[/red] {args[0]} does not exist")
            return

        if source_abs.is_dir():
            shutil.copytree(source_abs, dest_abs)
        else:
            shutil.copy2(source_abs, dest_abs)

        console.print(f"Copied {args[0]} to {args[1]}")

    except PermissionError as e:
        console.print(f"[red]Error:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def cmd_mv(args: list[str]) -> None:
    """Move/rename files or directories.

    Args:
        args: Command arguments (source dest)
    """
    if len(args) < 2:
        console.print("[red]Error:[/red] mv requires source and destination")
        return

    source = Path(args[0])
    dest = Path(args[1])

    try:
        source_abs = sandbox.check_path_allowed(source, "move")
        dest_abs = sandbox.check_path_allowed(dest, "write")

        if not source_abs.exists():
            console.print(f"[red]Error:[/red] {args[0]} does not exist")
            return

        shutil.move(str(source_abs), str(dest_abs))
        console.print(f"Moved {args[0]} to {args[1]}")

    except PermissionError as e:
        console.print(f"[red]Error:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def cmd_rm(args: list[str]) -> None:
    """Remove files or directories.

    Args:
        args: Command arguments (-r for recursive, paths)
    """
    # Parse arguments
    recursive = "-r" in args or "-rf" in args
    paths = [arg for arg in args if not arg.startswith("-")]

    if not paths:
        console.print("[red]Error:[/red] rm requires at least one path")
        return

    for file_path in paths:
        target = Path(file_path)
        try:
            target_abs = sandbox.check_path_allowed(target, "delete")

            if not target_abs.exists():
                console.print(f"[yellow]Warning:[/yellow] {file_path} does not exist")
                continue

            if target_abs.is_dir():
                if not recursive:
                    console.print(f"[red]Error:[/red] {file_path} is a directory (use -r for recursive)")
                    continue
                shutil.rmtree(target_abs)
            else:
                target_abs.unlink()

            console.print(f"Removed: {file_path}")

        except PermissionError as e:
            console.print(f"[red]Error:[/red] {e}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def execute_shell_command(args: list[str]) -> None:
    """Execute a shell command.

    Args:
        args: Command and arguments
    """
    if not args:
        return

    command = args[0]
    cmd_args = args[1:]

    # Dispatch to appropriate handler
    handlers = {
        "ls": cmd_ls,
        "ll": cmd_ll,
        "cd": cmd_cd,
        "pwd": cmd_pwd,
        "cat": cmd_cat,
        "head": cmd_head,
        "tail": cmd_tail,
        "mkdir": cmd_mkdir,
        "tree": cmd_tree,
        "cp": cmd_cp,
        "mv": cmd_mv,
        "rm": cmd_rm,
    }

    handler = handlers.get(command)
    if handler:
        handler(cmd_args)
    else:
        console.print(f"[red]Error:[/red] Unknown shell command: {command}")
