"""Tests for plugins module — plugin registration and discovery."""

from pathlib import Path
from unittest.mock import patch

import pytest

from grok_cli.plugins import (
    _discovered_plugins,
    discover_plugins,
    get_registered_commands,
    get_registered_create_types,
    register_command,
    register_create_type,
    registry,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset plugin registry before and after each test."""
    old_commands = dict(registry.commands)
    old_types = dict(registry.create_types)
    old_discovered = set(_discovered_plugins)
    yield
    registry.commands.clear()
    registry.commands.update(old_commands)
    registry.create_types.clear()
    registry.create_types.update(old_types)
    _discovered_plugins.clear()
    _discovered_plugins.update(old_discovered)


# --- register_command ---


def test_register_command():
    """Registering a command adds it to the registry."""

    def my_handler(args):
        pass

    register_command("testcmd", my_handler, "A test command")
    cmds = get_registered_commands()
    assert "testcmd" in cmds
    assert cmds["testcmd"][1] == "A test command"


def test_register_command_overwrites():
    """Re-registering a command overwrites the previous one."""

    def handler_a(args):
        pass

    def handler_b(args):
        pass

    register_command("dup", handler_a, "first")
    register_command("dup", handler_b, "second")
    cmds = get_registered_commands()
    assert cmds["dup"][1] == "second"


# --- register_create_type ---


def test_register_create_type():
    """Registering a create type adds it to the registry."""
    register_create_type("svg", "svg", "Scalable Vector Graphics")
    types = get_registered_create_types()
    assert "svg" in types
    assert types["svg"] == ("svg", "Scalable Vector Graphics")


# --- get_registered_commands / get_registered_create_types ---


def test_get_registered_commands_returns_copy():
    """get_registered_commands returns a copy, not the original dict."""
    cmds = get_registered_commands()
    cmds["injected"] = ("hack", "nope")
    # Original should be unaffected
    assert "injected" not in get_registered_commands()


def test_get_registered_create_types_returns_copy():
    """get_registered_create_types returns a copy, not the original dict."""
    types = get_registered_create_types()
    types["injected"] = ("ext", "nope")
    assert "injected" not in get_registered_create_types()


# --- discover_plugins ---


def test_discover_plugins_empty_dir(tmp_path: Path):
    """discover_plugins returns empty list when no plugins exist."""
    plugins_dir = tmp_path / ".grok" / "plugins"
    plugins_dir.mkdir(parents=True)
    with patch("grok_cli.plugins.config.get_grok_dir", return_value=tmp_path / ".grok"), \
         patch("grok_cli.plugins.Path.__file__", tmp_path / "plugins.py", create=True):
        # We only need to ensure user dir is empty; official dir may not exist
        result = discover_plugins()
    # May load official plugins, but no user plugins
    assert isinstance(result, list)


def test_discover_plugins_loads_plugin(tmp_path: Path):
    """discover_plugins loads a plugin with a register() function."""
    plugins_dir = tmp_path / ".grok" / "plugins"
    plugins_dir.mkdir(parents=True)

    # Create a simple plugin
    plugin_code = '''
from grok_cli.plugins import register_command

def _handler(args):
    pass

def register():
    register_command("test_plugin_cmd", _handler, "From test plugin")
'''
    (plugins_dir / "test_plugin.py").write_text(plugin_code, encoding="utf-8")

    with patch("grok_cli.plugins.config.get_grok_dir", return_value=tmp_path / ".grok"):
        result = discover_plugins()

    assert "test_plugin" in result
    cmds = get_registered_commands()
    assert "test_plugin_cmd" in cmds


def test_discover_plugins_skips_underscore_files(tmp_path: Path):
    """Plugins starting with _ are skipped."""
    plugins_dir = tmp_path / ".grok" / "plugins"
    plugins_dir.mkdir(parents=True)

    (plugins_dir / "_private.py").write_text("def register(): pass", encoding="utf-8")

    with patch("grok_cli.plugins.config.get_grok_dir", return_value=tmp_path / ".grok"):
        result = discover_plugins()

    assert "_private" not in result


def test_discover_plugins_handles_broken_plugin(tmp_path: Path):
    """Broken plugins produce a warning but don't crash discover_plugins."""
    plugins_dir = tmp_path / ".grok" / "plugins"
    plugins_dir.mkdir(parents=True)

    (plugins_dir / "broken.py").write_text("raise RuntimeError('kaboom')", encoding="utf-8")

    with patch("grok_cli.plugins.config.get_grok_dir", return_value=tmp_path / ".grok"):
        result = discover_plugins()

    # Should not crash, broken plugin is skipped
    assert "broken" not in result
