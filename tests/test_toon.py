"""Tests for TOON format parsing and serialization."""

import pytest
from grok_cli.session import parse_toon, serialize_toon


def test_parse_simple():
    """Test parsing simple TOON format."""
    toon = "goal: build CLI\ncwd: /home/user"
    result = parse_toon(toon)
    assert result == {"goal": "build CLI", "cwd": "/home/user"}


def test_parse_list():
    """Test parsing comma-separated lists."""
    toon = "decisions: Poetry,TOON,sandbox"
    result = parse_toon(toon)
    assert result == {"decisions": ["Poetry", "TOON", "sandbox"]}


def test_parse_multiline():
    """Test parsing multi-line values."""
    toon = "description: This is a long\n  description that spans\n  multiple lines"
    result = parse_toon(toon)
    assert result == {"description": "This is a long\ndescription that spans\nmultiple lines"}


def test_parse_comments():
    """Test that comments are ignored."""
    toon = "# This is a comment\ngoal: build CLI\n# Another comment\ncwd: /home"
    result = parse_toon(toon)
    assert result == {"goal": "build CLI", "cwd": "/home"}


def test_serialize_simple():
    """Test serializing simple data."""
    data = {"goal": "build CLI", "cwd": "/home/user"}
    result = serialize_toon(data)
    # Keys should be sorted
    assert "cwd: /home/user" in result
    assert "goal: build CLI" in result


def test_serialize_list():
    """Test serializing lists (comma-separated, no spaces)."""
    data = {"decisions": ["Poetry", "TOON", "sandbox"]}
    result = serialize_toon(data)
    assert "decisions: Poetry,TOON,sandbox" in result


def test_serialize_long_value():
    """Test serializing long values (indented continuation)."""
    data = {"description": "a" * 150}  # > 120 chars
    result = serialize_toon(data)
    lines = result.strip().split("\n")
    assert len(lines) > 1  # Should be split into multiple lines
    assert lines[0].startswith("description:")
    assert lines[1].startswith("  ")  # Continuation line should be indented


def test_round_trip():
    """Test that parse(serialize(data)) == data."""
    original = {
        "goal": "build fast CLI",
        "decisions": ["Poetry", "TOON", "sandbox"],
        "cwd": "/home/user/project",
    }
    serialized = serialize_toon(original)
    parsed = parse_toon(serialized)
    assert parsed == original


def test_round_trip_multiline():
    """Test round-trip with multi-line values."""
    original = {
        "code": "def foo():\n    return 42"
    }
    serialized = serialize_toon(original)
    parsed = parse_toon(serialized)
    assert parsed == original


def test_none_values_skipped():
    """Test that None values are skipped during serialization."""
    data = {"goal": "build CLI", "unused": None}
    result = serialize_toon(data)
    assert "unused" not in result
    assert "goal" in result
