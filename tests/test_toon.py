"""Tests for TOON format parsing, serialization, and session functions."""

from pathlib import Path
from unittest.mock import patch

import pytest

from grok_cli.session import (
    compress_session,
    compute_files_hash,
    estimate_toon_tokens,
    list_sessions,
    load_session,
    messages_to_toon,
    parse_toon,
    save_session,
    serialize_toon,
    toon_to_messages,
)


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
    """Test that long single-line values are preserved without splitting."""
    long_value = "a" * 150  # > 120 chars
    data = {"description": long_value}
    result = serialize_toon(data)
    lines = result.strip().split("\n")
    assert len(lines) == 1  # Long values stay on a single line (no artificial splitting)
    assert lines[0] == f"description: {long_value}"
    # Round-trip preserves the value
    parsed = parse_toon(result)
    assert parsed["description"] == long_value


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
    original = {"code": "def foo():\n    return 42"}
    serialized = serialize_toon(original)
    parsed = parse_toon(serialized)
    assert parsed == original


def test_none_values_skipped():
    """Test that None values are skipped during serialization."""
    data = {"goal": "build CLI", "unused": None}
    result = serialize_toon(data)
    assert "unused" not in result
    assert "goal" in result


def test_turn_keys_with_commas_not_split():
    """Test that turn_* keys containing commas are NOT split into lists.

    Only keys in _LIST_KEYS (history, decisions) get list treatment.
    Content keys like turn_000_assistant can contain arbitrary text with commas.
    """
    code_content = "def foo(a, b, c):\n    return a + b + c"
    data = {"turn_000_assistant": code_content}
    serialized = serialize_toon(data)
    parsed = parse_toon(serialized)
    # Must remain a string, not a list
    assert isinstance(parsed["turn_000_assistant"], str)
    assert parsed["turn_000_assistant"] == code_content


# --- estimate_toon_tokens ---


def test_estimate_toon_tokens():
    """Heuristic returns a reasonable positive count."""
    text = "goal: build a CLI\ndecisions: Poetry,TOON,sandbox\ncwd: /home/user"
    tokens = estimate_toon_tokens(text)
    assert tokens > 0
    # Heuristic: word_count + len//4 — sanity-check the math
    expected = len(text.split()) + len(text) // 4
    assert tokens == expected


# --- compute_files_hash ---


def test_compute_files_hash_deterministic(tmp_path: Path):
    """Same directory contents produce the same hash."""
    (tmp_path / "a.txt").write_text("hello")
    h1 = compute_files_hash(tmp_path)
    h2 = compute_files_hash(tmp_path)
    assert h1 == h2


def test_compute_files_hash_detects_new_file(tmp_path: Path):
    """Adding a file changes the hash."""
    (tmp_path / "a.txt").write_text("hello")
    h1 = compute_files_hash(tmp_path)
    (tmp_path / "b.txt").write_text("world")
    h2 = compute_files_hash(tmp_path)
    assert h1 != h2


def test_compute_files_hash_ignores_git_dir(tmp_path: Path):
    """Files inside .git/ do not affect the hash."""
    (tmp_path / "a.txt").write_text("hello")
    h1 = compute_files_hash(tmp_path)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")
    h2 = compute_files_hash(tmp_path)
    assert h1 == h2


def test_compute_files_hash_empty_dir(tmp_path: Path):
    """Empty directory returns a valid 64-char hex hash."""
    h = compute_files_hash(tmp_path)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# --- messages_to_toon + toon_to_messages ---


def test_messages_to_toon_round_trip():
    """Messages survive serialization and deserialization."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    toon_text = messages_to_toon(messages)
    restored = toon_to_messages(toon_text)
    assert len(restored) == len(messages)
    for original, restored_msg in zip(messages, restored):
        assert original["role"] == restored_msg["role"]
        assert original["content"] == restored_msg["content"]


def test_toon_to_messages_ordering():
    """Messages come back in the correct sequential order."""
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
        {"role": "user", "content": "third"},
        {"role": "assistant", "content": "fourth"},
    ]
    toon_text = messages_to_toon(messages)
    restored = toon_to_messages(toon_text)
    assert [m["content"] for m in restored] == ["first", "second", "third", "fourth"]


# --- compress_session ---


def test_compress_session_never():
    """mode='never' returns data unchanged."""
    data = {"goal": "test", "turn_000_user": "hello", "turn_001_assistant": "hi"}
    result = compress_session(data, mode="never")
    assert result == data


def test_compress_session_smart_below_threshold():
    """Small data passes through uncompressed in smart mode."""
    data = {"goal": "test", "cwd": "/home"}
    result = compress_session(data, mode="smart")
    assert result == data


def test_compress_session_preserves_core_keys():
    """Core keys (goal, decisions, cwd) survive compression."""
    # Build data large enough to trigger compression
    data = {"goal": "important goal", "decisions": ["A", "B"], "cwd": "/home"}
    for i in range(100):
        data[f"turn_{i:03d}_user"] = f"User message {i} " + "x" * 200
        data[f"turn_{i:03d}_assistant"] = f"Assistant reply {i} " + "y" * 200
    result = compress_session(data, mode="always")
    assert result["goal"] == "important goal"
    assert result["decisions"] == ["A", "B"]
    assert result["cwd"] == "/home"


def test_compress_session_keeps_last_exchanges():
    """Last 6 turn keys are kept in full after compression."""
    data = {"goal": "test"}
    for i in range(20):
        data[f"turn_{i:03d}_user"] = f"User message {i} " + "x" * 200
        data[f"turn_{i:03d}_assistant"] = f"Assistant reply {i} " + "y" * 200
    result = compress_session(data, mode="always")
    # Last 3 exchanges = last 6 turn keys (turn_017..turn_019 user+assistant)
    for i in range(17, 20):
        assert f"turn_{i:03d}_user" in result
        assert f"turn_{i:03d}_assistant" in result


def test_compress_session_too_large_raises():
    """>20k tokens after compression raises RuntimeError."""
    data = {"goal": "test"}
    # Create massive last exchanges that can't be compressed away
    for i in range(6):
        data[f"turn_{i:03d}_user"] = "U" * 20000
        data[f"turn_{i:03d}_assistant"] = "A" * 20000
    with pytest.raises(RuntimeError, match="too large"):
        compress_session(data, mode="always")


# --- save_session + load_session + list_sessions ---


@pytest.fixture
def mock_project_dir(tmp_path: Path):
    """Patch config.get_project_dir() to return a temp .grok directory."""
    project_dir = tmp_path / ".grok"
    project_dir.mkdir()
    (project_dir / "sessions").mkdir()
    with patch("grok_cli.config.get_project_dir", return_value=project_dir):
        yield project_dir


def test_save_and_load_session_round_trip(mock_project_dir: Path):
    """Save data, load it back, verify content is preserved."""
    data = {"goal": "round-trip test", "cwd": "/tmp/project", "decisions": ["A", "B"]}
    saved_path = save_session(data, compress_mode="never")
    assert saved_path.exists()

    loaded = load_session(saved_path)
    assert loaded["goal"] == "round-trip test"
    assert loaded["cwd"] == "/tmp/project"
    assert loaded["decisions"] == ["A", "B"]


def test_list_sessions(mock_project_dir: Path):
    """list_sessions returns saved session files."""
    data = {"goal": "test"}
    save_session(data, compress_mode="never")
    sessions = list_sessions()
    assert len(sessions) >= 1
    assert all(s.suffix == ".toon" for s in sessions)
