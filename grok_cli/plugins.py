"""Plugin system with auto-discovery and registration.

Plugins are discovered from ~/.grok/plugins/*.py
Each plugin must implement a register() function that calls registration functions.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from grok_cli import config

# Plugin registry
# Stores registered commands, create types, and model providers
registry = SimpleNamespace(
    commands={},  # name → (callback, help)
    create_types={},  # type_name → (extension, description)
    model_providers=[],  # list of provider classes
)


def register_command(name: str, callback: Callable[..., Any], help_text: str) -> None:
    """Register a new command from a plugin.

    Args:
        name: Command name (e.g., "web")
        callback: Function to call when command is invoked
        help_text: Help text for the command
    """
    registry.commands[name] = (callback, help_text)


def register_create_type(type_name: str, extension: str, description: str) -> None:
    """Register a new file type for the create command.

    Args:
        type_name: Type identifier (e.g., "svg")
        extension: File extension (e.g., "svg")
        description: Description of the file type
    """
    registry.create_types[type_name] = (extension, description)


def register_model_provider(provider_class: type) -> None:
    """Register a new model provider.

    Args:
        provider_class: Provider class (must implement Provider interface)
    """
    registry.model_providers.append(provider_class)


def _load_plugins_from_dir(plugins_dir: Path, loaded_plugins: list[str]) -> None:
    """Load plugins from a directory, skipping already-loaded names.

    Args:
        plugins_dir: Directory to scan for .py plugin files
        loaded_plugins: List of already-loaded plugin stems (mutated in place)
    """
    if not plugins_dir.is_dir():
        return

    for plugin_file in plugins_dir.glob("*.py"):
        if plugin_file.name.startswith("_"):
            continue

        # Skip if a plugin with this stem was already loaded (user overrides official)
        if plugin_file.stem in loaded_plugins:
            continue

        try:
            module_name = f"grok_plugin_{plugin_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)

            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "register"):
                module.register()
                loaded_plugins.append(plugin_file.stem)

        except Exception as e:
            from rich.console import Console

            console = Console()
            console.print(f"[yellow]Warning:[/yellow] Failed to load plugin {plugin_file.name}: {e}")


def discover_plugins() -> list[str]:
    """Discover and load plugins from user dir (~/.grok/plugins/) then official dir.

    User plugins are loaded first and take precedence — if a user has a plugin
    with the same stem as an official one, the official version is skipped.

    Returns:
        List of loaded plugin names
    """
    loaded_plugins: list[str] = []

    # 1. User plugins (highest priority)
    user_plugins_dir = config.get_grok_dir() / "plugins"
    user_plugins_dir.mkdir(exist_ok=True)
    _load_plugins_from_dir(user_plugins_dir, loaded_plugins)

    # 2. Official bundled plugins (shipped with the package)
    official_plugins_dir = Path(__file__).parent / "official_plugins"
    _load_plugins_from_dir(official_plugins_dir, loaded_plugins)

    return loaded_plugins


def get_registered_commands() -> dict[str, tuple[Callable[..., Any], str]]:
    """Get all registered commands from plugins.

    Returns:
        Dictionary of command name → (callback, help text)
    """
    return dict(registry.commands)


def get_registered_create_types() -> dict[str, tuple[str, str]]:
    """Get all registered create types from plugins.

    Returns:
        Dictionary of type name → (extension, description)
    """
    return dict(registry.create_types)


def get_registered_providers() -> list[type]:
    """Get all registered model providers from plugins.

    Returns:
        List of provider classes
    """
    return list(registry.model_providers)
