"""Tool definitions for the Grok agent.

These tools allow the model to interact with the filesystem
in a controlled, sandboxed manner.
"""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.syntax import Syntax
from rich.prompt import Confirm

from grok_cli import sandbox

console = Console()

# Large file threshold (lines)
LARGE_FILE_THRESHOLD = 100

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
    """Write content to a file with confirmation.

    Args:
        path: File path to write
        content: Content to write
        auto_confirm: Skip confirmation if True

    Returns:
        Tool result dictionary
    """
    file_path = Path(path)
    abs_path = sandbox.check_path_allowed(file_path, "write")

    # Check if file exists
    file_exists = abs_path.exists()
    action = "Overwrite" if file_exists else "Create"

    # Detect file type for syntax highlighting
    suffix = abs_path.suffix.lstrip(".") or "text"

    # Count lines for large file warning
    lines = content.count("\n") + 1

    # Show preview
    console.print(f"\n[bold]{action}:[/bold] {path}")

    if lines > LARGE_FILE_THRESHOLD:
        console.print(
            f"[yellow]Warning: Large file ({lines} lines). Showing first {LARGE_FILE_THRESHOLD} lines.[/yellow]\n"
        )
        preview_content = "\n".join(content.split("\n")[:LARGE_FILE_THRESHOLD])
        preview_content += f"\n... ({lines - LARGE_FILE_THRESHOLD} more lines)"
    else:
        preview_content = content

    syntax = Syntax(preview_content, suffix, theme="monokai", line_numbers=True)
    console.print(syntax)
    console.print()

    # Confirm
    if not auto_confirm:
        if not Confirm.ask(f"{action} this file?", default=False):
            return {"success": False, "error": "User cancelled"}

    # Create parent directories if needed
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    abs_path.write_text(content)
    console.print(f"[green]✓[/green] {action}d: {path}")

    return {"success": True, "result": f"Successfully wrote {len(content)} bytes to {path}"}


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

    # Show diff preview
    console.print(f"\n[bold]Edit:[/bold] {path} ({occurrences} occurrence(s))\n")
    console.print("[red]- " + old_text.replace("\n", "\n- ") + "[/red]")
    console.print("[green]+ " + new_text.replace("\n", "\n+ ") + "[/green]")
    console.print()

    # Confirm
    if not auto_confirm:
        if not Confirm.ask("Apply this edit?", default=False):
            return {"success": False, "error": "User cancelled"}

    # Write file
    abs_path.write_text(new_content)
    console.print(f"[green]✓[/green] Edited: {path}")

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
