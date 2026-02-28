"""Tests for slash_commands module — command parsing, dispatch, and handlers."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from grok_cli.slash_commands import (
    COLOR_THEMES,
    SLASH_COMMANDS,
    execute_slash_command,
    is_slash_command,
    parse_slash_command,
    register_slash_command,
)


# --- is_slash_command ---


def test_is_slash_command_true():
    """Strings starting with / are slash commands."""
    assert is_slash_command("/help") is True
    assert is_slash_command("  /model grok41") is True


def test_is_slash_command_false():
    """Regular text is not a slash command."""
    assert is_slash_command("hello") is False
    assert is_slash_command("") is False


# --- parse_slash_command ---


def test_parse_slash_command_simple():
    """Parsing a simple command returns name and empty args."""
    name, args = parse_slash_command("/help")
    assert name == "help"
    assert args == []


def test_parse_slash_command_with_args():
    """Parsing a command with args splits them correctly."""
    name, args = parse_slash_command("/model grok41_heavy")
    assert name == "model"
    assert args == ["grok41_heavy"]


def test_parse_slash_command_no_slash():
    """Parsing text without / returns empty."""
    name, args = parse_slash_command("not a command")
    assert name == ""
    assert args == []


def test_parse_slash_command_multiple_args():
    """Multiple args are split correctly."""
    name, args = parse_slash_command("/create py fibonacci calculator")
    assert name == "create"
    assert args == ["py", "fibonacci", "calculator"]


# --- register_slash_command ---


def test_register_slash_command():
    """Registering a command adds it to SLASH_COMMANDS."""
    called = []

    def handler(args, cfg, agent):
        called.append(True)

    register_slash_command("_test_cmd", handler, "test command", "/test")
    assert "_test_cmd" in SLASH_COMMANDS
    # Clean up
    del SLASH_COMMANDS["_test_cmd"]


# --- execute_slash_command ---


def test_execute_slash_command_exit():
    """Exit commands return False to stop the REPL."""
    for cmd in ("exit", "quit", "q"):
        result = execute_slash_command(cmd, [], {})
        assert result is False


def test_execute_slash_command_unknown():
    """Unknown commands return True (continue REPL)."""
    result = execute_slash_command("nonexistent_command_xyz", [], {})
    assert result is True


def test_execute_slash_command_registered():
    """Registered commands are dispatched and return True."""
    called = []

    def handler(args, cfg, agent):
        called.append(args)

    register_slash_command("_dispatch_test", handler, "test", "")
    try:
        result = execute_slash_command("_dispatch_test", ["arg1"], {"key": "val"})
        assert result is True
        assert called == [["arg1"]]
    finally:
        del SLASH_COMMANDS["_dispatch_test"]


def test_execute_slash_command_handler_exception():
    """Handler exceptions are caught; REPL continues."""

    def bad_handler(args, cfg, agent):
        raise ValueError("boom")

    register_slash_command("_err_test", bad_handler, "test", "")
    try:
        result = execute_slash_command("_err_test", [], {})
        assert result is True  # Should not crash
    finally:
        del SLASH_COMMANDS["_err_test"]


# --- Built-in commands ---


def test_builtin_commands_registered():
    """Core slash commands are all registered."""
    expected = {"help", "h", "model", "m", "models", "cost", "clear", "history",
                "y", "yes", "n", "no", "plugins", "pwd", "copy", "compact",
                "save", "resume", "theme", "heavy", "create", "edit", "ask"}
    assert expected.issubset(set(SLASH_COMMANDS.keys()))


# --- COLOR_THEMES ---


def test_color_themes_has_defaults():
    """All expected themes are defined."""
    assert "default" in COLOR_THEMES
    assert "ocean" in COLOR_THEMES
    assert "forest" in COLOR_THEMES
    assert "sunset" in COLOR_THEMES
    assert "minimal" in COLOR_THEMES


def test_color_themes_have_required_keys():
    """Each theme has all required style keys."""
    required_keys = {"prompt-box", "prompt-name", "prompt-model", "prompt-cwd", "prompt-git", "prompt-git-status"}
    for theme_name, theme in COLOR_THEMES.items():
        assert required_keys.issubset(set(theme.keys())), f"Theme '{theme_name}' missing keys"
