"""Tests for commands/create.py — filename suggestion and extension mapping."""

import pytest

from grok_cli.commands.create import DEFAULT_EXTENSIONS, suggest_filename


# --- DEFAULT_EXTENSIONS ---


def test_default_extensions_common_types():
    """Common file types are mapped correctly."""
    assert DEFAULT_EXTENSIONS["py"] == "py"
    assert DEFAULT_EXTENSIONS["python"] == "py"
    assert DEFAULT_EXTENSIONS["js"] == "js"
    assert DEFAULT_EXTENSIONS["javascript"] == "js"
    assert DEFAULT_EXTENSIONS["tex"] == "tex"
    assert DEFAULT_EXTENSIONS["latex"] == "tex"
    assert DEFAULT_EXTENSIONS["rust"] == "rs"
    assert DEFAULT_EXTENSIONS["go"] == "go"


# --- suggest_filename ---


def test_suggest_filename_basic():
    """Generates a meaningful filename from description."""
    name = suggest_filename("py", "binary search algorithm")
    assert name.endswith(".py")
    assert "binary" in name or "search" in name or "algorithm" in name


def test_suggest_filename_filters_stop_words():
    """Stop words (a, the, for, etc.) are filtered out."""
    name = suggest_filename("py", "a script for the user")
    # "a", "for", "the" should be filtered; "script" and "user" kept
    assert "script" in name or "user" in name
    assert name.endswith(".py")


def test_suggest_filename_fallback_generic():
    """Empty or all-stop-word description falls back to 'file'."""
    name = suggest_filename("py", "a")
    assert name == "file.py"


def test_suggest_filename_limits_words():
    """At most 3 meaningful words are used."""
    name = suggest_filename("py", "implement quick sort merge sort heap sort bubble sort")
    stem = name.rsplit(".", 1)[0]
    parts = stem.split("_")
    assert len(parts) <= 3


def test_suggest_filename_unknown_type():
    """Unknown type uses the type string as extension."""
    name = suggest_filename("xyz", "some description")
    assert name.endswith(".xyz")


def test_suggest_filename_javascript():
    """JavaScript type maps to .js extension."""
    name = suggest_filename("js", "event handler")
    assert name.endswith(".js")


def test_suggest_filename_latex():
    """LaTeX type maps to .tex extension."""
    name = suggest_filename("latex", "quantum physics paper")
    assert name.endswith(".tex")


def test_suggest_filename_underscore_separator():
    """Words are joined with underscores."""
    name = suggest_filename("py", "binary search tree")
    stem = name.rsplit(".", 1)[0]
    assert "_" in stem
