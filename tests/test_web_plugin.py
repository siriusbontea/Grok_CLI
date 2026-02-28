"""Tests for the official web plugin (tool_web)."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grok_cli.official_plugins import tool_web
from grok_cli.plugins import registry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    """Remove the 'web' command from the plugin registry before/after each test."""
    registry.commands.pop("web", None)
    yield
    registry.commands.pop("web", None)


@pytest.fixture
def mock_home(tmp_path: Path):
    """Mock Path.home() so config/quota files go to a temp directory."""
    with patch.object(Path, "home", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def quota_file(mock_home: Path) -> Path:
    """Return the path where the quota file would live, ensuring parent exists."""
    grok_dir = mock_home / ".grok"
    grok_dir.mkdir(parents=True, exist_ok=True)
    (grok_dir / "plugins").mkdir(exist_ok=True)
    (grok_dir / "cache").mkdir(exist_ok=True)
    return grok_dir / "web_quota.json"


# ---------------------------------------------------------------------------
# Sample DuckDuckGo HTML
# ---------------------------------------------------------------------------

SAMPLE_DDG_HTML = """
<html><body>
<div class="results">
  <div class="result">
    <a class="result__a" href="https://example.com/page1">First Result Title</a>
    <a class="result__snippet">This is the first snippet.</a>
  </div>
  <div class="result">
    <a class="result__a" href="https://example.com/page2">Second Result Title</a>
    <a class="result__snippet">This is the second snippet.</a>
  </div>
  <div class="result">
    <a class="result__a" href="https://example.com/page3">Third Result</a>
    <td class="result__snippet">Snippet in a td element.</td>
  </div>
</div>
</body></html>
"""


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_register_adds_web_command():
    """register() should add 'web' to the plugin command registry."""
    assert "web" not in registry.commands
    tool_web.register()
    assert "web" in registry.commands

    callback, help_text = registry.commands["web"]
    assert callback is tool_web.web_command
    assert "web" in help_text.lower() or "search" in help_text.lower()


# ---------------------------------------------------------------------------
# DuckDuckGo HTML parsing
# ---------------------------------------------------------------------------

def test_parse_ddg_results_extracts_titles_and_urls():
    """Parser should extract title, url, and snippet from DDG HTML."""
    results = tool_web._parse_ddg_results(SAMPLE_DDG_HTML)
    assert len(results) >= 2

    assert results[0]["title"] == "First Result Title"
    assert results[0]["url"] == "https://example.com/page1"
    assert results[0]["snippet"] == "This is the first snippet."

    assert results[1]["title"] == "Second Result Title"
    assert results[1]["url"] == "https://example.com/page2"


def test_parse_ddg_results_empty_html():
    """Parser should return empty list for HTML with no results."""
    results = tool_web._parse_ddg_results("<html><body>No results</body></html>")
    assert results == []


def test_parse_ddg_results_caps_at_10():
    """Parser should return at most 10 results."""
    links = "".join(
        f'<a class="result__a" href="https://example.com/{i}">Title {i}</a>'
        f'<a class="result__snippet">Snippet {i}</a>'
        for i in range(15)
    )
    html = f"<html><body>{links}</body></html>"
    results = tool_web._parse_ddg_results(html)
    assert len(results) == 10


# ---------------------------------------------------------------------------
# Quota tracking
# ---------------------------------------------------------------------------

def test_load_quota_fresh(quota_file: Path):
    """First load should return today's date with 0 tokens used."""
    data = tool_web._load_quota()
    assert data["date"] == date.today().isoformat()
    assert data["tokens_used"] == 0


def test_save_and_load_quota(quota_file: Path):
    """Saved quota should be loadable."""
    today = date.today().isoformat()
    tool_web._save_quota({"date": today, "tokens_used": 5000})

    data = tool_web._load_quota()
    assert data["tokens_used"] == 5000


def test_quota_resets_on_new_day(quota_file: Path):
    """Quota should reset when the calendar date changes."""
    tool_web._save_quota({"date": "2025-01-01", "tokens_used": 99999})

    data = tool_web._load_quota()
    assert data["date"] == date.today().isoformat()
    assert data["tokens_used"] == 0


def test_check_quota_allows_within_limit(quota_file: Path):
    """_check_quota should return True when under limit."""
    assert tool_web._check_quota(1000) is True


def test_check_quota_denies_over_limit(quota_file: Path):
    """_check_quota should return False when tokens would exceed limit."""
    today = date.today().isoformat()
    tool_web._save_quota({"date": today, "tokens_used": 99_500})

    # Default limit is 100k — 99500 + 1000 > 100000
    assert tool_web._check_quota(1000) is False


def test_check_quota_unlimited_when_zero(quota_file: Path):
    """When web_daily_quota is 0, all requests should be allowed."""
    today = date.today().isoformat()
    tool_web._save_quota({"date": today, "tokens_used": 999_999})

    with patch("grok_cli.official_plugins.tool_web.config.load_config", return_value={"web_daily_quota": 0}):
        assert tool_web._check_quota(999_999) is True


def test_record_tokens(quota_file: Path):
    """_record_tokens should increment today's usage."""
    tool_web._record_tokens(3000)
    tool_web._record_tokens(2000)

    data = tool_web._load_quota()
    assert data["tokens_used"] == 5000


# ---------------------------------------------------------------------------
# _web_search (mocked HTTP)
# ---------------------------------------------------------------------------

def test_web_search_displays_results(quota_file: Path):
    """_web_search should fetch DDG, parse, and print results."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_DDG_HTML
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("grok_cli.official_plugins.tool_web.httpx.Client", return_value=mock_client):
        tool_web._web_search("python tutorial")

    mock_client.get.assert_called_once()
    call_url = mock_client.get.call_args[0][0]
    assert "python+tutorial" in call_url


def test_web_search_quota_exceeded(quota_file: Path):
    """_web_search should abort when daily quota is exceeded."""
    today = date.today().isoformat()
    tool_web._save_quota({"date": today, "tokens_used": 100_000})

    # Should not make any HTTP calls
    with patch("grok_cli.official_plugins.tool_web.httpx.Client") as mock_client_cls:
        tool_web._web_search("anything")
        mock_client_cls.assert_not_called()


# ---------------------------------------------------------------------------
# _web_open (mocked HTTP + trafilatura)
# ---------------------------------------------------------------------------

def test_web_open_fetches_cleans_and_records(quota_file: Path):
    """_web_open should fetch, clean with trafilatura, and record tokens on confirm."""
    mock_resp = MagicMock()
    mock_resp.text = "<html><body><p>Hello world content here</p></body></html>"
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    cleaned = "Hello world content here " * 50  # ~1200 chars → ~300 tokens

    with (
        patch("grok_cli.official_plugins.tool_web.httpx.Client", return_value=mock_client),
        patch("trafilatura.extract", return_value=cleaned),
        patch.object(tool_web.console, "input", return_value="y"),
        patch.object(tool_web.console, "print"),
    ):
        tool_web._web_open("https://example.com")

    data = tool_web._load_quota()
    assert data["tokens_used"] > 0


def test_web_open_cancelled_by_user(quota_file: Path):
    """_web_open should not record tokens when user declines."""
    mock_resp = MagicMock()
    mock_resp.text = "<html><body><p>Content</p></body></html>"
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with (
        patch("grok_cli.official_plugins.tool_web.httpx.Client", return_value=mock_client),
        patch("trafilatura.extract", return_value="Some extracted text"),
        patch.object(tool_web.console, "input", return_value="n"),
        patch.object(tool_web.console, "print"),
    ):
        tool_web._web_open("https://example.com")

    data = tool_web._load_quota()
    assert data["tokens_used"] == 0


# ---------------------------------------------------------------------------
# web_command routing
# ---------------------------------------------------------------------------

def test_web_command_routes_search():
    """web_command('search foo') should call _web_search."""
    with patch.object(tool_web, "_web_search") as mock_search:
        tool_web.web_command("search python async")
        mock_search.assert_called_once_with("python async")


def test_web_command_routes_open():
    """web_command('open <url>') should call _web_open."""
    with patch.object(tool_web, "_web_open") as mock_open:
        tool_web.web_command("open https://example.com")
        mock_open.assert_called_once_with("https://example.com")


def test_web_command_empty_shows_usage():
    """web_command('') should print usage help."""
    with patch.object(tool_web, "_print_usage") as mock_usage:
        tool_web.web_command("")
        mock_usage.assert_called_once()


def test_web_command_unknown_subcommand_shows_usage():
    """web_command('foobar') should print usage help."""
    with patch.object(tool_web, "_print_usage") as mock_usage:
        tool_web.web_command("foobar")
        mock_usage.assert_called_once()
