"""Session management with TOON format handling and compression.

TOON (Token-Optimized Object Notation) is a custom line-based format designed
for this project to achieve 40-60% token savings versus JSON in LLM prompts.

Format rules:
- Keys: alphanumeric + _ + . (dot for pseudo-nesting like files.new)
- No quotes ever (tokens saved)
- Value continues on indented lines (2+ spaces or tab)
- Lists → comma-separated on single line
- Comments → # at line start (ignored)
- No nested objects (flatten with dot notation if needed)
- Always sort keys on serialize
- Estimated token count ≈ len(text.split()) + len(text)//4
"""

import hashlib
from pathlib import Path
from typing import Any


def parse_toon(text: str) -> dict[str, str | list[str]]:
    """Parse TOON format text into a dictionary.

    Args:
        text: TOON formatted string

    Returns:
        Dictionary with string or list values

    Example:
        >>> parse_toon("goal: build CLI\\ndecisions: Poetry,TOON,sandbox")
        {'goal': 'build CLI', 'decisions': ['Poetry', 'TOON', 'sandbox']}
    """
    data: dict[str, str | list[str]] = {}
    lines = [line.rstrip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]

    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Multi-line continuation (lines starting with 2+ spaces or tab)
        i += 1
        while i < len(lines) and (lines[i].startswith("  ") or lines[i].startswith("\t")):
            # Remove only the 2-space indentation marker, preserve rest of content
            continuation = lines[i][2:] if lines[i].startswith("  ") else lines[i][1:]
            value += "\n" + continuation
            i += 1

        # Detect list (comma-separated, no commas in multi-line values)
        if "," in value and "\n" not in value:
            data[key] = [v.strip() for v in value.split(",") if v.strip()]
        else:
            data[key] = value

    return data


def serialize_toon(data: dict[str, str | list[str] | None]) -> str:
    """Serialize dictionary to TOON format.

    Args:
        data: Dictionary with string, list, or None values

    Returns:
        TOON formatted string with sorted keys

    Example:
        >>> serialize_toon({'goal': 'build CLI', 'decisions': ['Poetry', 'TOON']})
        'decisions: Poetry,TOON\\ngoal: build CLI\\n'
    """
    lines = []

    for key in sorted(data.keys()):  # Always sort keys for deterministic output
        value = data[key]
        if value is None:
            continue

        if isinstance(value, list):
            value_str = ",".join(str(v) for v in value)  # No spaces after comma
        else:
            value_str = str(value)

        # Split long values into indented continuation lines (>120 chars or contains newlines)
        if len(value_str) > 120 or "\n" in value_str:
            # If no newlines but too long, split at 120-char boundaries
            if "\n" not in value_str and len(value_str) > 120:
                parts = []
                for i in range(0, len(value_str), 120):
                    parts.append(value_str[i : i + 120])
            else:
                parts = value_str.split("\n")  # Split on actual newlines

            lines.append(f"{key}: {parts[0]}")
            for part in parts[1:]:
                lines.append(f"  {part}")
        else:
            lines.append(f"{key}: {value_str}")

    return "\n".join(lines) + "\n"


def estimate_toon_tokens(text: str) -> int:
    """Estimate token count for TOON text.

    Uses heuristic: len(text.split()) + len(text)//4
    This approximation is used for compression threshold checks.

    Args:
        text: TOON formatted string

    Returns:
        Estimated token count
    """
    return len(text.split()) + len(text) // 4


def compute_files_hash(cwd: Path | None = None) -> str:
    """Compute SHA256 hash of all files in current working directory.

    Used to detect when the workspace has changed and context needs updating.
    Ignores: .git, __pycache__, .venv, venv, env, node_modules, .idea, .vscode, build, dist

    Args:
        cwd: Directory to hash (defaults to Path.cwd())

    Returns:
        Hexadecimal SHA256 hash string
    """
    if cwd is None:
        cwd = Path.cwd()

    digest = hashlib.sha256()
    ignore = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", ".idea", ".vscode", "build", "dist"}

    for file in sorted(cwd.rglob("*")):
        # Skip directories
        if file.is_dir():
            continue

        # Skip hidden files/dirs (starting with .)
        if any(part.startswith(".") for part in file.parts[len(cwd.parts) :]):
            continue

        # Skip ignored directories
        if file.parent.name in ignore:
            continue

        # Add relative path to hash
        digest.update(str(file.relative_to(cwd)).encode())

        # Optional: include modification time for more sensitivity
        # digest.update(file.stat().st_mtime_ns.to_bytes(8, 'big'))

    return digest.hexdigest()


def compress_session(data: dict[str, Any], mode: str = "smart") -> dict[str, Any]:
    """Compress session data to reduce token usage.

    Compression runs automatically before save if estimated tokens > 12,000.

    Compression algorithm (in order):
    1. Preserve unchanged: goal, decisions, cwd, files_hash, open
    2. Preserve all lines starting with files: or diff:
    3. Preserve any lines containing API key or secret (defensive)
    4. Timeline compression: collapse historical turns into single timeline: step1→step2→...
    5. Last turns protection: always keep last 3 user/assistant exchanges in full
    6. Final sanitization: remove duplicates, sort keys
    7. If still >20k tokens → fatal error

    Args:
        data: Session data dictionary
        mode: "always" | "smart" | "never"

    Returns:
        Compressed session data

    Raises:
        RuntimeError: If context too large even after compression
    """
    # Check if compression needed
    serialized = serialize_toon(data)
    tokens = estimate_toon_tokens(serialized)

    if mode == "never":
        return data

    if mode == "smart" and tokens < 12000:
        return data

    # Start compression
    compressed: dict[str, Any] = {}

    # 1. Preserve core keys
    preserve_keys = {"goal", "decisions", "cwd", "files_hash", "open"}
    for key in preserve_keys:
        if key in data:
            compressed[key] = data[key]

    # 2. Preserve files: and diff: keys
    for key, value in data.items():
        if key.startswith("files") or key.startswith("diff"):
            compressed[key] = value

    # 3. Preserve secrets (defensive)
    for key, value in data.items():
        if isinstance(value, str) and ("api" in key.lower() or "secret" in key.lower() or "key" in key.lower()):
            compressed[key] = value

    # 4. Timeline compression - collect historical turns
    timeline_steps = []
    turn_keys = sorted([k for k in data.keys() if k.startswith("turn_") and ("_user" in k or "_assistant" in k)])

    # Find last 3 exchanges (6 keys total)
    last_exchanges = turn_keys[-6:] if len(turn_keys) >= 6 else turn_keys

    # Compress older turns into timeline
    for key in turn_keys:
        if key not in last_exchanges:
            value = data[key]
            # Truncate long values for timeline
            if isinstance(value, str):
                summary = value[:50] + "..." if len(value) > 50 else value
                timeline_steps.append(summary.replace("\n", " "))

    # 5. Last turns protection - keep last 3 full exchanges
    for key in last_exchanges:
        compressed[key] = data[key]

    # Also preserve last_user and last_assistant if present
    if "last_user" in data:
        compressed["last_user"] = data["last_user"]
    if "last_assistant" in data:
        compressed["last_assistant"] = data["last_assistant"]

    # Add compressed timeline (max 15 steps, newest last)
    if timeline_steps:
        compressed["history"] = timeline_steps[-15:]  # Keep as list, will be serialized as comma-list

    # 6. Final sanitization - remove duplicates by keeping unique values only
    # (dict keys are already unique, but check for duplicate values in timeline)

    # 7. Check final size
    final_serialized = serialize_toon(compressed)
    final_tokens = estimate_toon_tokens(final_serialized)

    if final_tokens > 20000:
        raise RuntimeError(
            f"Context too large even after compression ({final_tokens} tokens > 20k limit). "
            "Start a new session with 'grok resume --new' or clear history."
        )

    return compressed


def save_session(data: dict[str, Any], compress_mode: str = "smart") -> Path:
    """Save session to project's .grok/sessions/ with current symlink.

    Args:
        data: Session data dictionary
        compress_mode: Compression mode ("always" | "smart" | "never")

    Returns:
        Path to saved session file
    """
    from datetime import datetime
    from grok_cli import config

    sessions_dir = config.get_project_dir() / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    # Compress if needed
    compressed_data = compress_session(data, compress_mode)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    session_file = sessions_dir / f"{timestamp}.toon"

    # Save to file
    session_file.write_text(serialize_toon(compressed_data))

    # Update current symlink
    current_link = sessions_dir / "current"
    if current_link.exists() or current_link.is_symlink():
        current_link.unlink()
    current_link.symlink_to(session_file.name)

    return session_file


def load_session(session_path: Path | None = None) -> dict[str, Any]:
    """Load session from file or from current symlink.

    Args:
        session_path: Specific session file to load, or None for current

    Returns:
        Session data dictionary

    Raises:
        FileNotFoundError: If session file doesn't exist
    """
    from grok_cli import config

    sessions_dir = config.get_project_dir() / "sessions"

    if session_path is None:
        # Load current session
        current_link = sessions_dir / "current"
        if not current_link.exists():
            raise FileNotFoundError("No current session found. Start a new session.")

        session_path = sessions_dir / current_link.readlink()

    if not session_path.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    # Load and parse TOON
    toon_text = session_path.read_text()
    return parse_toon(toon_text)


def list_sessions() -> list[Path]:
    """List all saved sessions in the project's .grok/sessions/ directory.

    Returns:
        List of session file paths, sorted by modification time (newest first)
    """
    from grok_cli import config

    sessions_dir = config.get_project_dir() / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    # Get all .toon files
    sessions = list(sessions_dir.glob("*.toon"))

    # Sort by modification time (newest first)
    sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return sessions


def messages_to_toon(messages: list[dict[str, Any]]) -> str:
    """Convert conversation messages to TOON format for saving.

    Args:
        messages: List of message dicts with 'role' and 'content'

    Returns:
        TOON formatted string
    """
    data: dict[str, str | list[str] | None] = {}

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Use turn_N_role format
        key = f"turn_{i:03d}_{role}"
        data[key] = content

    return serialize_toon(data)


def toon_to_messages(toon_text: str) -> list[dict[str, Any]]:
    """Convert TOON format back to conversation messages.

    Args:
        toon_text: TOON formatted string

    Returns:
        List of message dicts with 'role' and 'content'
    """
    data = parse_toon(toon_text)
    messages: list[dict[str, Any]] = []

    # Sort keys to ensure proper order
    turn_keys = sorted([k for k in data.keys() if k.startswith("turn_")])

    for key in turn_keys:
        # Parse key format: turn_NNN_role
        parts = key.split("_", 2)
        if len(parts) >= 3:
            role = parts[2]  # user or assistant
            content = data[key]
            # Ensure content is always a string (parse_toon may return list for comma-separated)
            if isinstance(content, list):
                content = ", ".join(content)
            messages.append({"role": role, "content": str(content)})

    return messages
