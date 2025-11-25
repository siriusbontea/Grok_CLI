"""Configuration management using TOML format.

Storage locations:
- Global config: ~/.grok/config.toml (user preferences, plugins)
- Project data: .grok/ in launch directory (sessions, history, context)

This separation allows per-project conversation history while sharing
user preferences across all projects.
"""

import os
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit import document, comment, nl


# Default configuration values
DEFAULT_CONFIG = {
    "default_model": "grok41_fast",
    "auto_compress": "smart",  # always | smart | never
    "auto_yes": False,
    "colour": True,
    "lean_mode": False,  # true → minimal comments in generated code
    "budget_monthly": 0.0,  # 0 = disabled
    "web_daily_quota": 100000,  # tokens via web plugin, 0 = disabled
}

# Store the launch directory (set by sandbox.init_sandbox)
_launch_dir: Path | None = None


def set_launch_dir(path: Path) -> None:
    """Set the launch directory (called by sandbox.init_sandbox).

    Args:
        path: The directory where grok was launched
    """
    global _launch_dir
    _launch_dir = path


def get_launch_dir() -> Path:
    """Get the launch directory.

    Returns:
        Path to launch directory (defaults to cwd if not set)
    """
    return _launch_dir or Path.cwd()


def get_grok_dir() -> Path:
    """Get the global ~/.grok directory for user config, plugins, and cache.

    Returns:
        Path to ~/.grok directory
    """
    grok_dir = Path.home() / ".grok"
    grok_dir.mkdir(exist_ok=True)

    # Global subdirectories
    (grok_dir / "plugins").mkdir(exist_ok=True)
    (grok_dir / "cache").mkdir(exist_ok=True)

    return grok_dir


def get_project_dir() -> Path:
    """Get the project-local .grok directory for sessions and context.

    This directory is created in the launch directory and stores:
    - sessions/ - Saved conversations
    - context.toon - Current session context
    - history - Command history

    Returns:
        Path to .grok directory in project
    """
    project_dir = get_launch_dir() / ".grok"
    project_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (project_dir / "sessions").mkdir(exist_ok=True)

    return project_dir


def get_config_path() -> Path:
    """Get the path to config.toml.

    Returns:
        Path to ~/.grok/config.toml
    """
    return get_grok_dir() / "config.toml"


def is_first_run() -> bool:
    """Check if this is the first run (no config file exists).

    Returns:
        True if config.toml doesn't exist
    """
    return not get_config_path().exists()


def create_default_config() -> None:
    """Create default config.toml with comments explaining each option."""
    config_path = get_config_path()

    # Build TOML document with comments
    doc = document()

    doc.add(comment("Grok CLI Configuration"))
    doc.add(comment("This file is created automatically on first run"))
    doc.add(nl())

    doc.add(comment("Default model to use (grok41_fast | grok41_heavy)"))
    doc["default_model"] = DEFAULT_CONFIG["default_model"]
    doc.add(nl())

    doc.add(comment("Session compression mode: always | smart | never"))
    doc.add(comment("smart = compress only when >12k tokens (recommended)"))
    doc["auto_compress"] = DEFAULT_CONFIG["auto_compress"]
    doc.add(nl())

    doc.add(comment("Auto-confirm all prompts (use -y/--yes flag equivalent)"))
    doc["auto_yes"] = DEFAULT_CONFIG["auto_yes"]
    doc.add(nl())

    doc.add(comment("Enable colored output"))
    doc["colour"] = DEFAULT_CONFIG["colour"]
    doc.add(nl())

    doc.add(comment("Lean mode: minimal comments in generated code"))
    doc.add(comment("Set to true or use GROK_LEAN=1 environment variable"))
    doc["lean_mode"] = DEFAULT_CONFIG["lean_mode"]
    doc.add(nl())

    doc.add(comment("Monthly budget limit in USD (0 = disabled)"))
    doc["budget_monthly"] = DEFAULT_CONFIG["budget_monthly"]
    doc.add(nl())

    doc.add(comment("Daily token quota for web plugin (0 = disabled)"))
    doc["web_daily_quota"] = DEFAULT_CONFIG["web_daily_quota"]

    # Write to file
    config_path.write_text(tomlkit.dumps(doc))


def load_config() -> dict[str, Any]:
    """Load configuration from ~/.grok/config.toml.

    Creates default config if it doesn't exist.

    Returns:
        Configuration dictionary
    """
    config_path = get_config_path()

    # Create default config on first run
    if not config_path.exists():
        create_default_config()

    # Load and parse TOML
    config_text = config_path.read_text()
    config = tomlkit.parse(config_text)

    # Convert to regular dict and merge with defaults (for any missing keys)
    result = DEFAULT_CONFIG.copy()
    result.update(dict(config))

    # Environment variable overrides
    if os.getenv("GROK_LEAN") == "1":
        result["lean_mode"] = True

    return result


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to ~/.grok/config.toml.

    Args:
        config: Configuration dictionary to save
    """
    config_path = get_config_path()

    # Load existing to preserve comments if possible
    if config_path.exists():
        doc = tomlkit.parse(config_path.read_text())
        # Update values
        for key, value in config.items():
            doc[key] = value
    else:
        # Create new document
        doc = tomlkit.document()
        for key, value in config.items():
            doc[key] = value

    config_path.write_text(tomlkit.dumps(doc))


def get_api_key() -> str | None:
    """Get Grok API key from environment.

    Returns:
        API key string or None if not set
    """
    return os.getenv("XAI_API_KEY")
