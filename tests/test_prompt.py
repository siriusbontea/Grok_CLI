"""Tests for ui/prompt.py — prompt generation and path truncation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from grok_cli import sandbox
from grok_cli.ui.prompt import PROMPT_STYLE, create_prompt, truncate_cwd


# --- truncate_cwd ---


def test_truncate_cwd_short_path():
    """Short paths are returned unchanged."""
    result = truncate_cwd(Path("/home/user"), max_length=40)
    # Should not be truncated
    assert "..." not in result or len(result) <= 40


def test_truncate_cwd_long_path():
    """Long paths are truncated to fit max_length."""
    long_path = Path("/home/user/projects/very/deep/nested/directory/structure")
    result = truncate_cwd(long_path, max_length=30)
    assert len(result) <= 30


def test_truncate_cwd_home_replacement():
    """Home directory is replaced with ~."""
    home = Path.home()
    test_path = home / "projects" / "myapp"
    result = truncate_cwd(test_path)
    assert result.startswith("~/")


def test_truncate_cwd_non_home_path():
    """Paths outside home are shown as absolute."""
    result = truncate_cwd(Path("/opt/data"))
    assert result.startswith("/")


# --- PROMPT_STYLE ---


def test_prompt_style_keys():
    """PROMPT_STYLE has all required keys."""
    required = {"prompt-box", "prompt-name", "prompt-model", "prompt-cwd", "prompt-git", "prompt-git-status"}
    assert required.issubset(set(PROMPT_STYLE.keys()))


# --- create_prompt ---


def test_create_prompt_returns_formatted_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """create_prompt returns a FormattedText with expected structure."""
    monkeypatch.chdir(tmp_path)
    sandbox.init_sandbox()

    with patch("grok_cli.ui.prompt.get_git_branch", return_value=None), \
         patch("grok_cli.ui.prompt.get_git_status", return_value=""):
        result = create_prompt("test_model")

    # FormattedText is a list of (style, text) tuples
    assert len(result) > 0
    # Should contain the model name somewhere
    texts = [text for _, text in result]
    assert "test_model" in texts


def test_create_prompt_includes_git_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """create_prompt includes git branch when available."""
    monkeypatch.chdir(tmp_path)
    sandbox.init_sandbox()

    with patch("grok_cli.ui.prompt.get_git_branch", return_value="main"), \
         patch("grok_cli.ui.prompt.get_git_status", return_value="±"):
        result = create_prompt("grok41_fast")

    texts = [text for _, text in result]
    assert "main" in texts
    assert "±" in texts


def test_create_prompt_no_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """create_prompt omits git info when not in a repo."""
    monkeypatch.chdir(tmp_path)
    sandbox.init_sandbox()

    with patch("grok_cli.ui.prompt.get_git_branch", return_value=None), \
         patch("grok_cli.ui.prompt.get_git_status", return_value=""):
        result = create_prompt("grok41_fast")

    texts = [text for _, text in result]
    # Should NOT contain git branch markers
    styles = [style for style, _ in result]
    assert "class:prompt-git" not in styles
