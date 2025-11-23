"""Plugin system with auto-discovery and registration.

Plugins are discovered from ~/.grok/plugins/*.py
Each plugin must implement a register() function that calls registration functions.
"""

import importlib.util
import sys
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


def discover_plugins() -> list[str]:
    """Discover and load all plugins from ~/.grok/plugins/

    Returns:
        List of loaded plugin names

    Raises:
        Exception: If plugin loading fails
    """
    plugins_dir = config.get_grok_dir() / "plugins"
    plugins_dir.mkdir(exist_ok=True)

    loaded_plugins = []

    # Find all .py files in plugins directory
    for plugin_file in plugins_dir.glob("*.py"):
        # Skip __init__.py and files starting with _
        if plugin_file.name.startswith("_"):
            continue

        try:
            # Load module from file
            module_name = f"grok_plugin_{plugin_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)

            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Call register() if it exists
            if hasattr(module, "register"):
                module.register()
                loaded_plugins.append(plugin_file.stem)

        except Exception as e:
            # Log error but don't crash - plugin loading is optional
            from rich.console import Console

            console = Console()
            console.print(f"[yellow]Warning:[/yellow] Failed to load plugin {plugin_file.name}: {e}")

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
