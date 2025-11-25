"""Edit command - modify files with diff preview and confirmation."""

import difflib
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Prompt

from grok_cli import cache, config, sandbox
from grok_cli.providers.grok import GrokProvider
from grok_cli.models import resolve_model_name

console = Console()


def show_diff(original: str, modified: str, filename: str) -> None:
    """Display colored diff between original and modified content.

    Args:
        original: Original file content
        modified: Modified file content
        filename: Filename for context
    """
    console.print(f"\n[bold]Changes to {filename}:[/bold]\n")

    # Generate unified diff
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines, modified_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}", lineterm=""
    )

    # Display with colors
    for line in diff:
        line = line.rstrip()
        if line.startswith("+++") or line.startswith("---"):
            console.print(line, style="bold")
        elif line.startswith("@@"):
            console.print(line, style="cyan")
        elif line.startswith("+"):
            console.print(line, style="green")
        elif line.startswith("-"):
            console.print(line, style="red")
        else:
            console.print(line, style="dim")

    console.print()


def edit_command(filename: str, instruction: str, cfg: dict[str, Any], auto_yes: bool = False) -> Path:
    """Edit an existing file based on instructions.

    Args:
        filename: File to edit
        instruction: Editing instruction
        cfg: Configuration dictionary
        auto_yes: Skip confirmation prompts

    Returns:
        Path to edited file

    Raises:
        ValueError: If API key not set
        FileNotFoundError: If file doesn't exist
        PermissionError: If path outside sandbox
    """
    # Get API key
    api_key = config.get_api_key()
    if not api_key:
        raise ValueError(
            "XAI_API_KEY not set. Get your key from console.x.ai and:\n" "  export XAI_API_KEY=your_key_here"
        )

    # Build file path
    file_path = Path(filename)

    # Check sandbox
    try:
        file_abs = sandbox.check_path_allowed(file_path, "edit")
    except PermissionError as e:
        raise PermissionError(f"{e}")

    # Check file exists
    if not file_abs.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    # Read original content
    original_content = file_abs.read_text()

    # Detect file type from extension
    file_type = file_abs.suffix.lstrip(".") or "txt"

    # Initialize provider
    provider = GrokProvider(api_key)

    # Resolve model name
    model = resolve_model_name(cfg.get("default_model", "grok41_fast"))

    # Check lean mode
    lean_mode = cfg.get("lean_mode", False)
    comment_instruction = " Use minimal comments." if lean_mode else " Maintain or improve existing comments."

    # Build prompt
    system_prompt = (
        f"You are an expert programmer editing a {file_type} file. "
        f"Follow the user's instructions to modify the code.{comment_instruction} "
        f"Return ONLY the complete modified file content, no explanations or markdown fences."
    )

    user_prompt = (
        f"Original file content:\n\n{original_content}\n\n"
        f"Instructions: {instruction}\n\n"
        f"Return the complete modified file."
    )

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    # Check cache
    cached_response = cache.get_cached_response(messages, model, 0.7)

    if cached_response:
        console.print("[dim](from cache)[/dim]")
        modified_content = cached_response["content"]
    else:
        # Generate modified content
        with console.status("[bold green]Editing...", spinner="dots"):
            response = provider.complete(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=8192,
            )

        modified_content = response["content"]

        # Cache the response
        cache.cache_response(messages, model, 0.7, response)

        # Show token usage
        usage = response.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        console.print(f"[dim]Tokens: {tokens}[/dim]")

    # Clean up content (remove markdown fences if present)
    modified_content = modified_content.strip()
    if modified_content.startswith("```"):
        lines = modified_content.split("\n")
        lines = lines[1:]  # Remove first line (```language)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove last line if it's ```
        modified_content = "\n".join(lines)

    # Show diff
    show_diff(original_content, modified_content, filename)

    # Get confirmation
    auto_yes_setting = cfg.get("auto_yes", False) or auto_yes
    if not auto_yes_setting:
        confirmation = Prompt.ask("Apply changes? (y/N)", choices=["y", "n", "Y", "N"], default="n", console=console)

        if confirmation.lower() != "y":
            console.print("[yellow]Cancelled.[/yellow]")
            raise RuntimeError("Edit cancelled by user")

    # Write modified content
    file_abs.write_text(modified_content)
    console.print(f"[green]✓[/green] Updated: {filename}")

    return file_abs
