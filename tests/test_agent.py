"""Tests for agent.py — isolated method tests (no API calls)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from grok_cli import sandbox
from grok_cli.agent import CONTEXT_FILE, SYSTEM_PROMPT, Agent


@pytest.fixture(autouse=True)
def sandbox_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Initialize sandbox rooted in tmp_path for every test."""
    monkeypatch.chdir(tmp_path)
    sandbox.init_sandbox()
    yield tmp_path


@pytest.fixture
def mock_project_dir(tmp_path: Path):
    """Patch get_project_dir to return a temp .grok directory."""
    project_dir = tmp_path / ".grok"
    project_dir.mkdir(exist_ok=True)
    (project_dir / "sessions").mkdir(exist_ok=True)
    with patch("grok_cli.config.get_project_dir", return_value=project_dir):
        yield project_dir


@pytest.fixture
def agent(mock_project_dir: Path):
    """Create an Agent with no API key (provider stays None)."""
    with patch("grok_cli.config.get_api_key", return_value=None):
        ag = Agent({"default_model": "grok41_fast", "auto_yes": False, "auto_compress": "never"})
    return ag


# --- __init__ ---


def test_agent_init_defaults(agent: Agent):
    """Agent initializes with sane defaults."""
    assert agent.messages == []
    assert agent.auto_confirm is False
    assert agent.compact_mode is False
    assert agent.total_tokens == 0
    assert agent.last_response == ""
    assert agent.provider is None


# --- set_auto_confirm / set_compact_mode ---


def test_set_auto_confirm(agent: Agent):
    """set_auto_confirm toggles the flag."""
    agent.set_auto_confirm(True)
    assert agent.auto_confirm is True
    agent.set_auto_confirm(False)
    assert agent.auto_confirm is False


def test_set_compact_mode(agent: Agent):
    """set_compact_mode toggles the flag."""
    agent.set_compact_mode(True)
    assert agent.compact_mode is True
    agent.set_compact_mode(False)
    assert agent.compact_mode is False


# --- get_last_response ---


def test_get_last_response(agent: Agent):
    """get_last_response returns whatever was stored."""
    assert agent.get_last_response() == ""
    agent.last_response = "Hello world"
    assert agent.get_last_response() == "Hello world"


# --- _estimate_tokens ---


def test_estimate_tokens_empty(agent: Agent):
    """Empty messages yield 0 tokens."""
    assert agent._estimate_tokens() == 0


def test_estimate_tokens_with_messages(agent: Agent):
    """Token estimate is roughly len/4."""
    agent.messages = [
        {"role": "user", "content": "a" * 400},
        {"role": "assistant", "content": "b" * 400},
    ]
    est = agent._estimate_tokens()
    assert est == 200  # 800 chars / 4


# --- _get_system_prompt ---


def test_get_system_prompt_contains_cwd(agent: Agent):
    """System prompt includes the current working directory."""
    prompt = agent._get_system_prompt()
    cwd = str(sandbox.get_current_dir())
    assert cwd in prompt


def test_get_system_prompt_lean_mode(agent: Agent):
    """Lean mode adds minimal-comments instruction."""
    agent.cfg["lean_mode"] = True
    prompt = agent._get_system_prompt()
    assert "Lean Mode" in prompt


# --- _build_session_data ---


def test_build_session_data(agent: Agent):
    """_build_session_data produces expected keys."""
    agent.messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    data = agent._build_session_data()
    assert "cwd" in data
    assert "files_hash" in data
    assert data["turn_000_user"] == "hello"
    assert data["turn_001_assistant"] == "hi"


# --- save_context / load_context / has_saved_context / clear_history ---


def test_save_and_load_context(agent: Agent, mock_project_dir: Path):
    """Context round-trips through save and load."""
    agent.messages = [
        {"role": "user", "content": "test message"},
        {"role": "assistant", "content": "test reply"},
    ]
    agent.save_context()
    assert agent.has_saved_context() is True

    # Create a fresh agent and load
    with patch("grok_cli.config.get_api_key", return_value=None):
        agent2 = Agent({"default_model": "grok41_fast", "auto_compress": "never"})
    loaded = agent2.load_context()
    assert loaded is True
    assert len(agent2.messages) == 2
    assert agent2.messages[0]["content"] == "test message"


def test_load_context_no_file(agent: Agent, mock_project_dir: Path):
    """load_context returns False when no context file exists."""
    assert agent.load_context() is False


def test_clear_history(agent: Agent, mock_project_dir: Path):
    """clear_history empties messages and deletes context file."""
    agent.messages = [{"role": "user", "content": "hello"}]
    agent.save_context()
    assert agent.has_saved_context() is True

    agent.clear_history(delete_context_file=True)
    assert agent.messages == []
    assert agent.total_tokens == 0
    assert agent.has_saved_context() is False


def test_clear_history_keep_file(agent: Agent, mock_project_dir: Path):
    """clear_history with delete_context_file=False keeps the file."""
    agent.messages = [{"role": "user", "content": "hello"}]
    agent.save_context()

    agent.clear_history(delete_context_file=False)
    assert agent.messages == []
    assert agent.has_saved_context() is True


# --- _ensure_provider ---


def test_ensure_provider_no_key(agent: Agent):
    """_ensure_provider raises ValueError when no API key is set."""
    with patch("grok_cli.config.get_api_key", return_value=None):
        with pytest.raises(ValueError, match="XAI_API_KEY"):
            agent._ensure_provider()
