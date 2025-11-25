"""Create command - intelligent file generation with smart filename suggestion."""

import re
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.syntax import Syntax

from grok_cli import cache, config, sandbox
from grok_cli.providers.grok import GrokProvider
from grok_cli.models import resolve_model_name
from grok_cli.plugins import get_registered_create_types

console = Console()

# Default file type extensions
DEFAULT_EXTENSIONS = {
    "py": "py",
    "python": "py",
    "js": "js",
    "javascript": "js",
    "ts": "ts",
    "typescript": "ts",
    "html": "html",
    "css": "css",
    "json": "json",
    "yaml": "yaml",
    "yml": "yml",
    "toml": "toml",
    "md": "md",
    "markdown": "md",
    "txt": "txt",
    "sh": "sh",
    "bash": "sh",
    "sql": "sql",
    "rs": "rs",
    "rust": "rs",
    "go": "go",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "h": "h",
    "hpp": "hpp",
}


def suggest_filename(file_type: str, description: str) -> str:
    """Suggest a filename based on type and description.

    Args:
        file_type: File type (e.g., "py", "js")
        description: Description of what to create

    Returns:
        Suggested filename
    """
    # Get extension (check plugins first, then defaults)
    plugin_types = get_registered_create_types()
    if file_type in plugin_types:
        extension, _ = plugin_types[file_type]
    else:
        extension = DEFAULT_EXTENSIONS.get(file_type, file_type)

    # Clean description to make valid filename
    # Extract key words from description
    words = re.findall(r"\b\w+\b", description.lower())

    # Filter out common words
    stop_words = {"a", "an", "the", "for", "to", "with", "in", "on", "at", "by", "from", "that", "this"}
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]

    # Take first 2-3 words
    name_parts = meaningful_words[:3] if len(meaningful_words) >= 3 else meaningful_words[:2]

    if not name_parts:
        # Fallback to generic name
        name = "file"
    else:
        name = "_".join(name_parts)

    return f"{name}.{extension}"


def create_command(
    file_type: str, description: str, filename: str | None, cfg: dict[str, Any], auto_yes: bool = False
) -> Path:
    """Create a new file with AI-generated content.

    Args:
        file_type: Type of file to create (py, js, etc.)
        description: Description of what to create
        filename: Optional explicit filename, otherwise auto-suggested
        cfg: Configuration dictionary
        auto_yes: Skip confirmation prompts

    Returns:
        Path to created file

    Raises:
        ValueError: If API key not set or file type invalid
        PermissionError: If path outside sandbox
    """
    # Get API key
    api_key = config.get_api_key()
    if not api_key:
        raise ValueError(
            "XAI_API_KEY not set. Get your key from console.x.ai and:\n" "  export XAI_API_KEY=your_key_here"
        )

    # Suggest filename if not provided
    if filename is None:
        filename = suggest_filename(file_type, description)
        console.print(f"[dim]Suggested filename:[/dim] {filename}")

    # Check file type is valid
    plugin_types = get_registered_create_types()
    if file_type not in DEFAULT_EXTENSIONS and file_type not in plugin_types:
        console.print(f"[yellow]Warning:[/yellow] Unknown file type '{file_type}'")

    # Build file path
    file_path = Path(filename)

    # Check sandbox
    try:
        file_abs = sandbox.check_path_allowed(file_path, "create")
    except PermissionError as e:
        raise PermissionError(f"{e}")

    # Check overwrite protection
    auto_yes_setting = cfg.get("auto_yes", False) or auto_yes
    if not sandbox.check_overwrite_allowed(file_path, auto_yes_setting):
        console.print("[yellow]Cancelled.[/yellow]")
        raise FileExistsError(f"File exists and overwrite denied: {filename}")

    # Initialize provider
    provider = GrokProvider(api_key)

    # Resolve model name
    model = resolve_model_name(cfg.get("default_model", "grok41_fast"))

    # Check lean mode
    lean_mode = cfg.get("lean_mode", False)
    comment_instruction = " Use minimal comments." if lean_mode else " Include clear comments explaining the code."

    # Build prompt based on file type
    system_prompt = (
        f"You are an expert programmer. Generate high-quality {file_type} code based on user requirements."
        f"{comment_instruction} Return ONLY the code, no explanations or markdown fences."
    )

    user_prompt = f"Create a {file_type} file that: {description}"

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    # Check cache
    cached_response = cache.get_cached_response(messages, model, 0.7)

    if cached_response:
        console.print("[dim](from cache)[/dim]")
        content = cached_response["content"]
    else:
        # Generate content
        with console.status("[bold green]Generating...", spinner="dots"):
            response = provider.complete(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=8192,
            )

        content = response["content"]

        # Cache the response
        cache.cache_response(messages, model, 0.7, response)

        # Show token usage
        usage = response.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        console.print(f"[dim]Tokens: {tokens}[/dim]")

    # Clean up content (remove markdown fences if present)
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```language)
        lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    # Preview content
    console.print(f"\n[bold]Preview of {filename}:[/bold]")
    syntax = Syntax(content, file_type, theme="monokai", line_numbers=True)
    console.print(syntax)
    console.print()

    # Write file
    file_abs.write_text(content)
    console.print(f"[green]✓[/green] Created: {filename}")

    return file_abs
