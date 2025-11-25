"""Tool definitions for the Grok agent.

These tools allow the model to interact with the filesystem
in a controlled, sandboxed manner.
"""

import difflib
import re
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from grok_cli import sandbox
from grok_cli.validators import validate_file

console = Console()

# Large file threshold (lines)
LARGE_FILE_THRESHOLD = 100

# Max diff lines to show before truncating
MAX_DIFF_LINES = 200

# File type display names
FILE_TYPE_NAMES: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript (ES Module)",
    ".ts": "TypeScript",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".tex": "LaTeX",
    ".latex": "LaTeX",
    ".md": "Markdown",
    ".txt": "Text",
    ".html": "HTML",
    ".css": "CSS",
    ".sh": "Shell Script",
    ".bash": "Bash Script",
    ".sql": "SQL",
    ".xml": "XML",
    ".csv": "CSV",
    ".ini": "INI Config",
    ".cfg": "Config",
    ".conf": "Config",
}


def _get_file_type_name(path: str) -> str:
    """Get human-readable file type name."""
    ext = Path(path).suffix.lower()
    return FILE_TYPE_NAMES.get(ext, ext.lstrip(".").upper() if ext else "Text")

# Diff display styles
DIFF_STYLE_HEADER = "bold white"
DIFF_STYLE_HUNK = "bold cyan"
DIFF_STYLE_ADD = "white on green"
DIFF_STYLE_REMOVE = "white on red"
DIFF_STYLE_CONTEXT = "grey70 on grey23"


def _show_diff(old_content: str, new_content: str, path: str) -> None:
    """Display a colored unified diff between old and new content.

    Shows line numbers with full-line highlighting:
    - Removed lines: white text on red background
    - Added lines: white text on green background
    - Context lines: grey text on dark grey background

    Args:
        old_content: Original file content
        new_content: New file content
        path: File path (for diff header)
    """
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    # Generate diff with context
    diff = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )

    if not diff:
        console.print("[dim]No changes[/dim]")
        return

    # Truncate if too long
    truncated = False
    if len(diff) > MAX_DIFF_LINES:
        diff = diff[:MAX_DIFF_LINES]
        truncated = True

    console.print()

    # Track line numbers
    old_line_num = 0
    new_line_num = 0

    # Get terminal width for full-line highlighting
    term_width = console.width or 80

    for line in diff:
        if line.startswith("---") or line.startswith("+++"):
            # File header
            console.print(f"[{DIFF_STYLE_HEADER}]{line}[/]")
        elif line.startswith("@@"):
            # Hunk header - parse line numbers
            console.print(f"[{DIFF_STYLE_HUNK}]{line}[/]")
            # Extract starting line numbers from @@ -old,count +new,count @@
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match:
                old_line_num = int(match.group(1))
                new_line_num = int(match.group(2))
        elif line.startswith("-"):
            # Removed line - red background
            line_num_str = f"{old_line_num:4d} "
            content = line[1:]  # Remove the - prefix
            padded = f" - {line_num_str}{content}".ljust(term_width)
            console.print(f"[{DIFF_STYLE_REMOVE}]{padded}[/]")
            old_line_num += 1
        elif line.startswith("+"):
            # Added line - green background
            line_num_str = f"{new_line_num:4d} "
            content = line[1:]  # Remove the + prefix
            padded = f" + {line_num_str}{content}".ljust(term_width)
            console.print(f"[{DIFF_STYLE_ADD}]{padded}[/]")
            new_line_num += 1
        else:
            # Context line - grey background
            line_num_str = f"{old_line_num:4d} "
            content = line[1:] if line.startswith(" ") else line
            padded = f"   {line_num_str}{content}".ljust(term_width)
            console.print(f"[{DIFF_STYLE_CONTEXT}]{padded}[/]")
            old_line_num += 1
            new_line_num += 1

    if truncated:
        console.print(f"\n[yellow]... diff truncated (showing first {MAX_DIFF_LINES} lines)[/yellow]")

# Tool definitions for the OpenAI-compatible API
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use this to examine existing code or text files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to read (relative to current directory)",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates the file if it doesn't exist, or overwrites if it does. Always use this when the user asks you to create a file or save code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to write (relative to current directory)",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit an existing file by replacing specific text. Use this for modifications to existing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to edit",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "The exact text to find and replace",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "The text to replace it with",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list (defaults to current directory)",
                        "default": ".",
                    }
                },
                "required": [],
            },
        },
    },
]


def execute_tool(tool_name: str, arguments: dict[str, Any], auto_confirm: bool = False) -> dict[str, Any]:
    """Execute a tool and return the result.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        auto_confirm: If True, skip confirmation prompts

    Returns:
        Dictionary with 'success' boolean and 'result' or 'error' string
    """
    try:
        if tool_name == "read_file":
            return tool_read_file(arguments["path"])
        elif tool_name == "write_file":
            return tool_write_file(arguments["path"], arguments["content"], auto_confirm)
        elif tool_name == "edit_file":
            return tool_edit_file(
                arguments["path"],
                arguments["old_text"],
                arguments["new_text"],
                auto_confirm,
            )
        elif tool_name == "list_files":
            return tool_list_files(arguments.get("path", "."))
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    except PermissionError as e:
        return {"success": False, "error": f"Permission denied: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_read_file(path: str) -> dict[str, Any]:
    """Read a file's contents.

    Args:
        path: File path to read

    Returns:
        Tool result dictionary
    """
    file_path = Path(path)
    abs_path = sandbox.check_path_allowed(file_path, "read")

    if not abs_path.exists():
        return {"success": False, "error": f"File not found: {path}"}

    if not abs_path.is_file():
        return {"success": False, "error": f"Not a file: {path}"}

    content = abs_path.read_text()
    console.print(f"[dim]Read {len(content)} bytes from {path}[/dim]")

    return {"success": True, "result": content}


def tool_write_file(path: str, content: str, auto_confirm: bool = False) -> dict[str, Any]:
    """Write content to a file with enhanced confirmation.

    Features:
    - Shows file info panel (name, type, lines, validation status)
    - Allows filename editing before save
    - Shows preview with syntax highlighting
    - Validates content for supported file types

    Args:
        path: File path to write
        content: Content to write
        auto_confirm: Skip confirmation if True

    Returns:
        Tool result dictionary
    """
    file_path = Path(path)
    current_path = path  # Track potentially modified path

    # Validate path
    try:
        abs_path = sandbox.check_path_allowed(file_path, "write")
    except PermissionError as e:
        return {"success": False, "error": str(e)}

    # Check if file exists
    file_exists = abs_path.exists()
    action = "Overwrite" if file_exists else "Create"

    # Detect file type for syntax highlighting
    suffix = abs_path.suffix.lstrip(".") or "text"
    file_type = _get_file_type_name(path)

    # Count lines
    lines = content.count("\n") + 1

    # Pre-validate to show status in header
    validation = validate_file(content, path)
    has_validator = validation is not None
    validation_status = "Will validate" if has_validator else "No validator"
    if validation and validation.has_errors:
        validation_status = f"[red]{len(validation.errors)} error(s)[/red]"
    elif validation and validation.warnings:
        validation_status = f"[yellow]{len(validation.warnings)} warning(s)[/yellow]"
    elif has_validator:
        validation_status = "[green]Valid[/green]"

    # Build file info panel
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("label", style="dim")
    info_table.add_column("value")
    info_table.add_row("Filename:", f"[bold cyan]{path}[/bold cyan]")
    info_table.add_row("Type:", file_type)
    info_table.add_row("Lines:", str(lines))
    info_table.add_row("Validation:", validation_status)

    console.print()
    console.print(Panel(info_table, title=f"[bold]{action} File[/bold]", border_style="blue"))

    # Show preview
    if file_exists:
        # Show diff for overwrites
        old_content = abs_path.read_text()
        _show_diff(old_content, content, path)
    else:
        # Show content preview for new files
        if lines > LARGE_FILE_THRESHOLD:
            console.print(
                f"\n[yellow]Large file ({lines} lines). Showing first {LARGE_FILE_THRESHOLD}.[/yellow]\n"
            )
            preview_content = "\n".join(content.split("\n")[:LARGE_FILE_THRESHOLD])
            preview_content += f"\n... ({lines - LARGE_FILE_THRESHOLD} more lines)"
        else:
            preview_content = content

        console.print()
        syntax = Syntax(preview_content, suffix, theme="monokai", line_numbers=True)
        console.print(syntax)

    console.print()

    # Show validation errors if any
    if validation and validation.has_errors:
        console.print("[red]Validation errors:[/red]")
        for err in validation.errors:
            console.print(f"  [red]•[/red] {err}")
    if validation and validation.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warn in validation.warnings:
            console.print(f"  [yellow]•[/yellow] {warn}")
        console.print()

    # Confirmation with filename editing option
    if not auto_confirm:
        while True:
            choice = Prompt.ask(
                f"Save as '[cyan]{current_path}[/cyan]'?",
                choices=["y", "n", "e"],
                default="y",
                show_choices=True,
            )

            if choice == "n":
                return {"success": False, "error": "User cancelled"}
            elif choice == "e":
                # Edit filename
                new_name = Prompt.ask("Enter new filename", default=current_path)
                new_name = new_name.strip()
                if new_name and new_name != current_path:
                    try:
                        new_abs_path = sandbox.check_path_allowed(Path(new_name), "write")
                        current_path = new_name
                        abs_path = new_abs_path
                        file_exists = abs_path.exists()
                        action = "Overwrite" if file_exists else "Create"
                        # Re-validate with new extension if changed
                        if Path(new_name).suffix != Path(path).suffix:
                            validation = validate_file(content, new_name)
                            if validation and validation.has_errors:
                                console.print(f"[yellow]Note: Validation for {new_name}:[/yellow]")
                                for err in validation.errors:
                                    console.print(f"  [red]•[/red] {err}")
                        console.print(f"[dim]Filename changed to: {current_path}[/dim]")
                    except PermissionError as e:
                        console.print(f"[red]Invalid path:[/red] {e}")
                        continue
            else:  # 'y'
                break

    # Create parent directories if needed
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    # Final validation check - ask about errors
    if validation and validation.has_errors and not auto_confirm:
        if not Confirm.ask("Save despite validation errors?", default=False):
            return {
                "success": False,
                "error": f"Validation failed:\n{validation.format_report()}",
            }

    # Write file
    abs_path.write_text(content)
    console.print(f"[green]✓[/green] {action}d: {current_path}")

    # Return validation info in result if there were issues
    if validation and (validation.errors or validation.warnings):
        result_msg = f"Wrote {len(content)} bytes to {current_path}, but validation found issues:\n{validation.format_report()}"
        return {"success": True, "result": result_msg, "validation_errors": validation.errors}

    return {"success": True, "result": f"Successfully wrote {len(content)} bytes to {current_path}"}


def tool_edit_file(path: str, old_text: str, new_text: str, auto_confirm: bool = False) -> dict[str, Any]:
    """Edit a file by replacing text with confirmation.

    Args:
        path: File path to edit
        old_text: Text to find
        new_text: Text to replace with
        auto_confirm: Skip confirmation if True

    Returns:
        Tool result dictionary
    """
    file_path = Path(path)
    abs_path = sandbox.check_path_allowed(file_path, "edit")

    if not abs_path.exists():
        return {"success": False, "error": f"File not found: {path}"}

    content = abs_path.read_text()

    if old_text not in content:
        return {"success": False, "error": f"Text not found in {path}"}

    # Count occurrences
    occurrences = content.count(old_text)

    # Create new content
    new_content = content.replace(old_text, new_text)

    # Show diff preview with color
    console.print(f"\n[bold]Edit:[/bold] {path} ({occurrences} occurrence(s))")
    _show_diff(content, new_content, path)
    console.print()

    # Validate new content before applying (for supported file types)
    validation = validate_file(new_content, path)
    if validation and validation.has_errors:
        console.print("\n[red]Validation errors in edited content:[/red]")
        for err in validation.errors:
            console.print(f"  [red]•[/red] {err}")
        if validation.warnings:
            for warn in validation.warnings:
                console.print(f"  [yellow]•[/yellow] {warn}")

        if not auto_confirm:
            if not Confirm.ask("Apply edit anyway despite errors?", default=False):
                return {
                    "success": False,
                    "error": f"Validation failed:\n{validation.format_report()}",
                }

    # Confirm (if validation passed or no validation available)
    elif not auto_confirm:
        if not Confirm.ask("Apply this edit?", default=False):
            return {"success": False, "error": "User cancelled"}

    # Write file
    abs_path.write_text(new_content)
    console.print(f"[green]✓[/green] Edited: {path}")

    # Return validation info if there were issues
    if validation and (validation.errors or validation.warnings):
        result_msg = f"Edited {path} ({occurrences} replacement(s)), but validation found issues:\n{validation.format_report()}"
        return {"success": True, "result": result_msg, "validation_errors": validation.errors}

    return {"success": True, "result": f"Successfully edited {path} ({occurrences} replacement(s))"}


def tool_list_files(path: str = ".") -> dict[str, Any]:
    """List files in a directory.

    Args:
        path: Directory path to list

    Returns:
        Tool result dictionary
    """
    dir_path = Path(path)
    abs_path = sandbox.check_path_allowed(dir_path, "list")

    if not abs_path.exists():
        return {"success": False, "error": f"Directory not found: {path}"}

    if not abs_path.is_dir():
        return {"success": False, "error": f"Not a directory: {path}"}

    items = []
    for item in sorted(abs_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            items.append(f"{item.name}/")
        else:
            items.append(item.name)

    result = "\n".join(items) if items else "(empty directory)"
    return {"success": True, "result": result}
