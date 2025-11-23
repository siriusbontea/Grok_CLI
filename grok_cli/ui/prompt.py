"""Custom prompt generation for the REPL.

Format: ┌─ grok  [model]  [cwd ~ truncated]  ([git branch±])
        └─➤
"""

import subprocess
from pathlib import Path

from prompt_toolkit.formatted_text import FormattedText

from grok_cli import sandbox


def get_git_branch() -> str | None:
    """Get current git branch name if in a git repository.

    Returns:
        Branch name or None if not in git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1,
            cwd=sandbox.get_current_dir(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_git_status() -> str:
    """Get git status indicator (± for changes).

    Returns:
        Status indicator or empty string
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=1, cwd=sandbox.get_current_dir()
        )
        if result.returncode == 0 and result.stdout.strip():
            return "±"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def truncate_cwd(cwd: Path, max_length: int = 40) -> str:
    """Truncate current working directory path intelligently.

    Shows home as ~ and truncates middle parts if too long.

    Args:
        cwd: Current working directory
        max_length: Maximum length for display

    Returns:
        Truncated path string
    """
    # Replace home with ~
    try:
        relative = cwd.relative_to(Path.home())
        path_str = f"~/{relative}"
    except ValueError:
        path_str = str(cwd)

    # If short enough, return as-is
    if len(path_str) <= max_length:
        return path_str

    # Truncate middle parts
    parts = Path(path_str).parts
    if len(parts) <= 2:
        # Just truncate the string
        return path_str[: max_length - 3] + "..."

    # Keep first and last, truncate middle
    while len(path_str) > max_length and len(parts) > 2:
        parts = parts[:1] + ("...",) + parts[-1:]
        path_str = str(Path(*parts))

    return path_str


def create_prompt(model: str = "grok41_fast") -> FormattedText:
    """Create custom prompt for the REPL.

    Format: ┌─ grok  [model]  [cwd ~ truncated]  ([git branch±])
            └─➤

    Args:
        model: Current model name

    Returns:
        FormattedText for prompt_toolkit
    """
    cwd = sandbox.get_current_dir()
    truncated_cwd = truncate_cwd(cwd)

    # Get git info
    git_branch = get_git_branch()
    git_status = get_git_status()

    # Build top line
    top_parts = [
        ("class:prompt-box", "┌─ "),
        ("class:prompt-name", "grok"),
        ("class:prompt-box", "  ["),
        ("class:prompt-model", model),
        ("class:prompt-box", "]  ["),
        ("class:prompt-cwd", truncated_cwd),
        ("class:prompt-box", "]"),
    ]

    # Add git info if available
    if git_branch:
        top_parts.extend(
            [
                ("class:prompt-box", "  ("),
                ("class:prompt-git", git_branch),
                ("class:prompt-git-status", git_status),
                ("class:prompt-box", ")"),
            ]
        )

    # Build bottom line
    bottom_parts = [
        ("class:prompt-box", "\n└─➤ "),
    ]

    return FormattedText(top_parts + bottom_parts)


# Style for the prompt
PROMPT_STYLE = {
    "prompt-box": "#888888",  # Gray for box drawing
    "prompt-name": "#00ffff bold",  # Cyan bold for "grok"
    "prompt-model": "#ffff00",  # Yellow for model name
    "prompt-cwd": "#00ff00",  # Green for cwd
    "prompt-git": "#ff00ff",  # Magenta for git branch
    "prompt-git-status": "#ff0000 bold",  # Red bold for git status
}
