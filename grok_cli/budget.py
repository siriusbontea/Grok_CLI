"""Budget tracking and monthly cost enforcement.

Tracks cumulative API costs per calendar month and warns (does not block)
when approaching or exceeding the configured budget_monthly limit.
Usage data is persisted to ~/.grok/usage.json.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from grok_cli.config import get_grok_dir
from grok_cli.models import get_model_pricing

console = Console()

# Module-level singleton
_tracker: "BudgetTracker | None" = None


class BudgetTracker:
    """Tracks monthly API usage and cost."""

    def __init__(self, usage_path: Path | None = None):
        """Initialize budget tracker.

        Args:
            usage_path: Path to usage.json file. Defaults to ~/.grok/usage.json.
        """
        self._path = usage_path or (get_grok_dir() / "usage.json")
        self._lock = threading.Lock()
        self._data: dict[str, Any] = self._load()

    def _current_month(self) -> str:
        """Get current month as YYYY-MM string."""
        return datetime.now().strftime("%Y-%m")

    def _empty_data(self) -> dict[str, Any]:
        """Return empty usage data for the current month."""
        return {
            "month": self._current_month(),
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "calls": 0,
        }

    def _load(self) -> dict[str, Any]:
        """Load usage data from disk, resetting if month changed."""
        if not self._path.exists():
            return self._empty_data()

        try:
            data = json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return self._empty_data()

        # Auto-reset on new month
        if data.get("month") != self._current_month():
            return self._empty_data()

        return data

    def _save(self) -> None:
        """Persist usage data to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2) + "\n")

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token usage and calculate cost.

        Thread-safe: uses a lock so parallel heavy-mode agents don't race.

        Args:
            model: API model string
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
        """
        input_price, output_price = get_model_pricing(model)
        cost = (prompt_tokens / 1_000_000) * input_price + (completion_tokens / 1_000_000) * output_price

        with self._lock:
            self._data["total_cost_usd"] += cost
            self._data["total_prompt_tokens"] += prompt_tokens
            self._data["total_completion_tokens"] += completion_tokens
            self._data["calls"] += 1
            self._save()

    def check_budget(self, budget_monthly: float) -> str | None:
        """Check if budget threshold has been reached.

        Args:
            budget_monthly: Monthly budget in USD. 0 means disabled.

        Returns:
            Warning string if at or above 80%, None otherwise.
        """
        if budget_monthly <= 0:
            return None

        cost = self._data["total_cost_usd"]
        ratio = cost / budget_monthly

        if ratio >= 1.0:
            return (
                f"Monthly budget EXCEEDED: ${cost:.2f} / ${budget_monthly:.2f} "
                f"({ratio:.0%})"
            )
        elif ratio >= 0.8:
            return (
                f"Approaching monthly budget: ${cost:.2f} / ${budget_monthly:.2f} "
                f"({ratio:.0%})"
            )

        return None

    def get_summary(self) -> dict[str, Any]:
        """Get usage summary for display.

        Returns:
            Dictionary with month, cost, token counts, and call count.
        """
        return {
            "month": self._data["month"],
            "total_cost_usd": self._data["total_cost_usd"],
            "total_prompt_tokens": self._data["total_prompt_tokens"],
            "total_completion_tokens": self._data["total_completion_tokens"],
            "calls": self._data["calls"],
        }


def get_tracker() -> BudgetTracker:
    """Get the module-level BudgetTracker singleton.

    Returns:
        BudgetTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = BudgetTracker()
    return _tracker


def record_and_warn(model: str, prompt_tokens: int, completion_tokens: int, budget_monthly: float) -> None:
    """Record usage and print a warning if budget threshold is reached.

    Convenience function for use at API call sites.

    Args:
        model: API model string
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        budget_monthly: Monthly budget in USD from config (0 = disabled)
    """
    tracker = get_tracker()
    tracker.record_usage(model, prompt_tokens, completion_tokens)

    warning = tracker.check_budget(budget_monthly)
    if warning:
        if "EXCEEDED" in warning:
            console.print(f"\n[bold red]{warning}[/bold red]")
        else:
            console.print(f"\n[yellow]{warning}[/yellow]")
