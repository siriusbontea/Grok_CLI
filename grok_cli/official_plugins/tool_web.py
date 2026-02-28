"""Web plugin — search the web and fetch/clean URLs.

Provides two subcommands accessible via /web:
  /web search <query>  — search DuckDuckGo and display results
  /web open <url>      — fetch a URL, clean with trafilatura, preview + confirm

Token usage is tracked against a configurable daily quota
(web_daily_quota in config.toml, default 100 000 tokens, 0 = unlimited).
"""

import json
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from rich.console import Console
from rich.markdown import Markdown

from grok_cli import config

console = Console()

# ---------------------------------------------------------------------------
# Daily quota helpers
# ---------------------------------------------------------------------------

_QUOTA_FILE_NAME = "web_quota.json"


def _quota_path() -> Path:
    """Return path to ~/.grok/web_quota.json."""
    return config.get_grok_dir() / _QUOTA_FILE_NAME


def _load_quota() -> dict[str, Any]:
    """Load quota state from disk, resetting if the date has changed.

    Returns:
        Dict with keys "date" (str) and "tokens_used" (int).
    """
    path = _quota_path()
    today = date.today().isoformat()

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("date") == today:
                return data
        except (json.JSONDecodeError, KeyError):
            pass

    # First use today or corrupt/missing file — start fresh
    return {"date": today, "tokens_used": 0}


def _save_quota(data: dict[str, Any]) -> None:
    """Persist quota state to disk.

    Args:
        data: Quota dict with "date" and "tokens_used" keys.
    """
    _quota_path().write_text(json.dumps(data), encoding="utf-8")


def _check_quota(tokens_needed: int) -> bool:
    """Check whether *tokens_needed* can be consumed without exceeding the daily quota.

    A quota of 0 means unlimited — always returns True.

    Args:
        tokens_needed: Estimated token count for the operation.

    Returns:
        True if the operation is allowed, False if it would exceed the quota.
    """
    cfg = config.load_config()
    limit = int(cfg.get("web_daily_quota", 100_000))
    if limit == 0:
        return True

    data = _load_quota()
    return data["tokens_used"] + tokens_needed <= limit


def _record_tokens(tokens: int) -> None:
    """Add *tokens* to today's usage counter.

    Args:
        tokens: Number of tokens consumed.
    """
    data = _load_quota()
    data["tokens_used"] += tokens
    _save_quota(data)


# ---------------------------------------------------------------------------
# DuckDuckGo HTML-lite result parser
# ---------------------------------------------------------------------------

class _DDGResultParser(HTMLParser):
    """Minimal parser for DuckDuckGo HTML lite search results."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result_link = False
        self._in_snippet = False
        self._current: dict[str, str] = {}
        self._text_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "a" and attr_dict.get("class") == "result__a":
            self._in_result_link = True
            self._current = {"url": attr_dict.get("href", ""), "title": "", "snippet": ""}
            self._text_buf = []
        elif tag == "a" and attr_dict.get("class") == "result__snippet":
            self._in_snippet = True
            self._text_buf = []
        elif tag == "td" and attr_dict.get("class") and "result__snippet" in (attr_dict.get("class") or ""):
            self._in_snippet = True
            self._text_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_result_link:
            self._current["title"] = "".join(self._text_buf).strip()
            self._in_result_link = False
        elif (tag in ("a", "td")) and self._in_snippet:
            self._current["snippet"] = "".join(self._text_buf).strip()
            self._in_snippet = False
            if self._current.get("title"):
                self.results.append(self._current)
                self._current = {}

    def handle_data(self, data: str) -> None:
        if self._in_result_link or self._in_snippet:
            self._text_buf.append(data)


def _parse_ddg_results(html: str) -> list[dict[str, str]]:
    """Parse DuckDuckGo HTML lite response into a list of result dicts.

    Args:
        html: Raw HTML from DuckDuckGo lite.

    Returns:
        List of dicts with keys "title", "url", "snippet".
    """
    parser = _DDGResultParser()
    parser.feed(html)
    return parser.results[:10]


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _web_search(query: str) -> None:
    """Search DuckDuckGo and display numbered results.

    Args:
        query: Search query string.
    """
    # Estimate ~2k tokens for a search results page
    if not _check_quota(2000):
        console.print("[red]Daily web token quota exceeded.[/red] Reset tomorrow or increase web_daily_quota in config.")
        return

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    try:
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            resp = client.get(url, headers={"User-Agent": "GrokCLI/1.0"})
            resp.raise_for_status()
    except httpx.HTTPError as e:
        console.print(f"[red]Search failed:[/red] {e}")
        return

    results = _parse_ddg_results(resp.text)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    page_tokens = len(resp.text) // 4
    _record_tokens(page_tokens)

    console.print(f"\n[bold]Search results for:[/bold] {query}\n")
    for i, r in enumerate(results, 1):
        console.print(f"  [cyan]{i}.[/cyan] [bold]{r['title']}[/bold]")
        console.print(f"     [dim]{r['url']}[/dim]")
        if r.get("snippet"):
            console.print(f"     {r['snippet']}")
        console.print()

    console.print("[dim]Use /web open <url> to read a page[/dim]\n")


def _web_open(url: str) -> None:
    """Fetch a URL, clean its content, preview, confirm, then display.

    Args:
        url: The URL to fetch and display.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            resp = client.get(url, headers={"User-Agent": "GrokCLI/1.0"})
            resp.raise_for_status()
    except httpx.HTTPError as e:
        console.print(f"[red]Fetch failed:[/red] {e}")
        return

    # Clean HTML with trafilatura
    try:
        import trafilatura
    except ImportError:
        console.print("[red]trafilatura is not installed.[/red] Run: poetry add trafilatura")
        return

    text = trafilatura.extract(resp.text)
    if not text:
        console.print("[yellow]Could not extract readable content from this page.[/yellow]")
        return

    token_estimate = len(text) // 4

    if not _check_quota(token_estimate):
        console.print("[red]Daily web token quota exceeded.[/red] Reset tomorrow or increase web_daily_quota in config.")
        return

    # Preview
    preview = text[:500]
    console.print(f"\n[bold]Preview[/bold] ({token_estimate:,} tokens estimated):\n")
    console.print(f"[dim]{preview}{'...' if len(text) > 500 else ''}[/dim]\n")

    # Confirm
    try:
        answer = console.input("[bold]Load full content? (y/N):[/bold] ")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled[/dim]")
        return

    if answer.lower() not in ("y", "yes"):
        console.print("[dim]Cancelled[/dim]")
        return

    _record_tokens(token_estimate)

    console.print()
    console.print(Markdown(text))
    console.print(f"\n[dim]({token_estimate:,} tokens recorded against daily quota)[/dim]\n")


# ---------------------------------------------------------------------------
# Main command entry point
# ---------------------------------------------------------------------------

def web_command(args_str: str) -> None:
    """Handle /web commands.

    Args:
        args_str: Everything after "/web " as a single string.
    """
    parts = args_str.strip().split(None, 1)
    if not parts:
        _print_usage()
        return

    sub = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if sub == "search":
        if not rest:
            console.print("[yellow]Usage:[/yellow] /web search <query>")
            return
        _web_search(rest)
    elif sub == "open":
        if not rest:
            console.print("[yellow]Usage:[/yellow] /web open <url>")
            return
        _web_open(rest)
    else:
        _print_usage()


def _print_usage() -> None:
    """Print usage help for the web command."""
    console.print("\n[bold]Web Plugin[/bold]\n")
    console.print("  [cyan]/web search <query>[/cyan]  Search the web via DuckDuckGo")
    console.print("  [cyan]/web open <url>[/cyan]      Fetch and display a cleaned web page")
    console.print()
    cfg = config.load_config()
    limit = int(cfg.get("web_daily_quota", 100_000))
    data = _load_quota()
    if limit > 0:
        console.print(f"  [dim]Daily quota: {data['tokens_used']:,} / {limit:,} tokens[/dim]")
    else:
        console.print("  [dim]Daily quota: unlimited[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register() -> None:
    """Register the web command with the plugin system."""
    from grok_cli.plugins import register_command

    register_command("web", web_command, "Search the web or fetch a URL")
