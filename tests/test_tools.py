"""Tests for tools module — file-operation tools used by the agent."""

import pytest
from pathlib import Path

from grok_cli import sandbox
from grok_cli.tools import (
    TOOL_DEFINITIONS,
    _get_file_type_name,
    execute_tool,
    tool_list_files,
    tool_read_file,
    tool_edit_file,
    tool_write_file,
)


@pytest.fixture(autouse=True)
def sandbox_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Initialize sandbox rooted in tmp_path for every test."""
    monkeypatch.chdir(tmp_path)
    sandbox.init_sandbox()
    yield tmp_path


# --- _get_file_type_name ---


def test_get_file_type_name_known():
    """Known extensions return human-readable names."""
    assert _get_file_type_name("main.py") == "Python"
    assert _get_file_type_name("config.toml") == "TOML"
    assert _get_file_type_name("style.css") == "CSS"


def test_get_file_type_name_unknown():
    """Unknown extensions return uppercased extension."""
    assert _get_file_type_name("file.rb") == "RB"


def test_get_file_type_name_no_extension():
    """Files with no extension return 'Text'."""
    assert _get_file_type_name("Makefile") == "Text"


# --- TOOL_DEFINITIONS ---


def test_tool_definitions_has_four_tools():
    """Exactly four tool definitions are registered."""
    assert len(TOOL_DEFINITIONS) == 4


def test_tool_definitions_names():
    """Tool definitions have the expected names."""
    names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    assert names == {"read_file", "write_file", "edit_file", "list_files"}


# --- tool_read_file ---


def test_read_file_success(sandbox_in_tmp: Path):
    """Reading an existing file returns its content."""
    (sandbox_in_tmp / "hello.txt").write_text("hello world", encoding="utf-8")
    result = tool_read_file("hello.txt")
    assert result["success"] is True
    assert result["result"] == "hello world"


def test_read_file_not_found():
    """Reading a nonexistent file returns an error."""
    result = tool_read_file("nonexistent.txt")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_read_file_directory(sandbox_in_tmp: Path):
    """Reading a directory returns an error."""
    (sandbox_in_tmp / "subdir").mkdir()
    result = tool_read_file("subdir")
    assert result["success"] is False
    assert "not a file" in result["error"].lower()


def test_read_file_too_large(sandbox_in_tmp: Path):
    """Files over 1 MB are rejected."""
    big_file = sandbox_in_tmp / "big.bin"
    big_file.write_bytes(b"x" * (1_048_577))
    result = tool_read_file("big.bin")
    assert result["success"] is False
    assert "too large" in result["error"].lower()


# --- tool_write_file ---


def test_write_file_creates_new(sandbox_in_tmp: Path):
    """Writing to a new file creates it (auto_confirm=True)."""
    result = tool_write_file("new.txt", "content here", auto_confirm=True)
    assert result["success"] is True
    assert (sandbox_in_tmp / "new.txt").read_text(encoding="utf-8") == "content here"


def test_write_file_overwrites(sandbox_in_tmp: Path):
    """Writing to an existing file overwrites it."""
    (sandbox_in_tmp / "exists.txt").write_text("old", encoding="utf-8")
    result = tool_write_file("exists.txt", "new", auto_confirm=True)
    assert result["success"] is True
    assert (sandbox_in_tmp / "exists.txt").read_text(encoding="utf-8") == "new"


def test_write_file_creates_parent_dirs(sandbox_in_tmp: Path):
    """Writing to a nested path creates parent directories."""
    result = tool_write_file("a/b/c.txt", "deep", auto_confirm=True)
    assert result["success"] is True
    assert (sandbox_in_tmp / "a" / "b" / "c.txt").read_text(encoding="utf-8") == "deep"


# --- tool_edit_file ---


def test_edit_file_success(sandbox_in_tmp: Path):
    """Editing replaces old_text with new_text."""
    (sandbox_in_tmp / "code.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    result = tool_edit_file("code.py", "x = 1", "x = 42", auto_confirm=True)
    assert result["success"] is True
    assert "x = 42" in (sandbox_in_tmp / "code.py").read_text(encoding="utf-8")


def test_edit_file_text_not_found(sandbox_in_tmp: Path):
    """Editing with text that doesn't exist returns error."""
    (sandbox_in_tmp / "code.py").write_text("x = 1\n", encoding="utf-8")
    result = tool_edit_file("code.py", "NONEXISTENT", "replacement", auto_confirm=True)
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_edit_file_not_found():
    """Editing a nonexistent file returns error."""
    result = tool_edit_file("ghost.py", "old", "new", auto_confirm=True)
    assert result["success"] is False
    assert "not found" in result["error"].lower()


# --- tool_list_files ---


def test_list_files_success(sandbox_in_tmp: Path):
    """Listing a directory returns its contents."""
    (sandbox_in_tmp / "file_a.txt").write_text("a", encoding="utf-8")
    (sandbox_in_tmp / "file_b.txt").write_text("b", encoding="utf-8")
    result = tool_list_files(".")
    assert result["success"] is True
    assert "file_a.txt" in result["result"]
    assert "file_b.txt" in result["result"]


def test_list_files_empty(sandbox_in_tmp: Path):
    """Listing an empty directory returns the empty marker."""
    (sandbox_in_tmp / "empty").mkdir()
    result = tool_list_files("empty")
    assert result["success"] is True
    assert "empty" in result["result"].lower()


def test_list_files_hides_dotfiles(sandbox_in_tmp: Path):
    """Hidden files (starting with .) are excluded."""
    (sandbox_in_tmp / ".hidden").write_text("secret", encoding="utf-8")
    (sandbox_in_tmp / "visible.txt").write_text("hi", encoding="utf-8")
    result = tool_list_files(".")
    assert ".hidden" not in result["result"]
    assert "visible.txt" in result["result"]


def test_list_files_dirs_before_files(sandbox_in_tmp: Path):
    """Directories appear before files in listing."""
    (sandbox_in_tmp / "zebra.txt").write_text("z", encoding="utf-8")
    (sandbox_in_tmp / "alpha_dir").mkdir()
    result = tool_list_files(".")
    lines = result["result"].split("\n")
    # alpha_dir/ should come before zebra.txt
    dir_idx = next(i for i, l in enumerate(lines) if "alpha_dir" in l)
    file_idx = next(i for i, l in enumerate(lines) if "zebra.txt" in l)
    assert dir_idx < file_idx


def test_list_files_not_found():
    """Listing a nonexistent directory returns error."""
    result = tool_list_files("no_such_dir")
    assert result["success"] is False


# --- execute_tool dispatch ---


def test_execute_tool_unknown():
    """Unknown tool name returns error."""
    result = execute_tool("unknown_tool", {})
    assert result["success"] is False
    assert "unknown" in result["error"].lower()


def test_execute_tool_read_missing_args():
    """read_file without path returns error."""
    result = execute_tool("read_file", {})
    assert result["success"] is False
    assert "path" in result["error"].lower()


def test_execute_tool_write_missing_args():
    """write_file without content returns error."""
    result = execute_tool("write_file", {"path": "x.txt"})
    assert result["success"] is False


def test_execute_tool_edit_missing_args():
    """edit_file without required args returns error."""
    result = execute_tool("edit_file", {"path": "x.txt"})
    assert result["success"] is False


def test_execute_tool_dispatches_list(sandbox_in_tmp: Path):
    """execute_tool correctly dispatches list_files."""
    (sandbox_in_tmp / "test.txt").write_text("data", encoding="utf-8")
    result = execute_tool("list_files", {"path": "."})
    assert result["success"] is True
    assert "test.txt" in result["result"]
