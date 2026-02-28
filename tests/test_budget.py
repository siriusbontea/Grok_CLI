"""Tests for budget tracking and enforcement."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from grok_cli.budget import BudgetTracker


@pytest.fixture
def tracker(tmp_path: Path) -> BudgetTracker:
    """Create a BudgetTracker with a temporary usage file."""
    return BudgetTracker(usage_path=tmp_path / "usage.json")


def test_tracker_init_empty(tracker: BudgetTracker) -> None:
    """Test that a new tracker starts with empty data."""
    summary = tracker.get_summary()
    assert summary["total_cost_usd"] == 0.0
    assert summary["total_prompt_tokens"] == 0
    assert summary["total_completion_tokens"] == 0
    assert summary["calls"] == 0


def test_record_usage_calculates_cost(tracker: BudgetTracker) -> None:
    """Test that record_usage correctly calculates cost from known pricing."""
    # grok-4-1-fast-non-reasoning: $0.20/1M input, $0.50/1M output
    tracker.record_usage("grok-4-1-fast-non-reasoning", 1_000_000, 1_000_000)
    summary = tracker.get_summary()

    assert summary["total_prompt_tokens"] == 1_000_000
    assert summary["total_completion_tokens"] == 1_000_000
    assert summary["calls"] == 1
    assert abs(summary["total_cost_usd"] - 0.70) < 0.001  # $0.20 + $0.50


def test_check_budget_disabled(tracker: BudgetTracker) -> None:
    """Test that check_budget returns None when budget is 0 (disabled)."""
    tracker.record_usage("grok-4-1-fast-non-reasoning", 1_000_000, 1_000_000)
    assert tracker.check_budget(0.0) is None


def test_check_budget_under_threshold(tracker: BudgetTracker) -> None:
    """Test that check_budget returns None when under 80%."""
    # Cost will be $0.70
    tracker.record_usage("grok-4-1-fast-non-reasoning", 1_000_000, 1_000_000)
    # Budget is $10 → 7% used → should return None
    assert tracker.check_budget(10.0) is None


def test_check_budget_approaching(tracker: BudgetTracker) -> None:
    """Test that check_budget warns at >= 80%."""
    # Cost will be $0.70
    tracker.record_usage("grok-4-1-fast-non-reasoning", 1_000_000, 1_000_000)
    # Budget is $0.80 → 87.5% used → should return approaching warning
    result = tracker.check_budget(0.80)
    assert result is not None
    assert "Approaching" in result


def test_check_budget_exceeded(tracker: BudgetTracker) -> None:
    """Test that check_budget warns at >= 100%."""
    # Cost will be $0.70
    tracker.record_usage("grok-4-1-fast-non-reasoning", 1_000_000, 1_000_000)
    # Budget is $0.50 → 140% used → should return exceeded warning
    result = tracker.check_budget(0.50)
    assert result is not None
    assert "EXCEEDED" in result


def test_month_auto_reset(tmp_path: Path) -> None:
    """Test that tracker resets when calendar month changes."""
    usage_path = tmp_path / "usage.json"

    # Write data for a past month
    old_data = {
        "month": "2020-01",
        "total_cost_usd": 99.99,
        "total_prompt_tokens": 5_000_000,
        "total_completion_tokens": 2_000_000,
        "calls": 100,
    }
    usage_path.write_text(json.dumps(old_data))

    # New tracker should reset because month differs
    tracker = BudgetTracker(usage_path=usage_path)
    summary = tracker.get_summary()
    assert summary["total_cost_usd"] == 0.0
    assert summary["calls"] == 0
    assert summary["month"] != "2020-01"


def test_persistence_across_instances(tmp_path: Path) -> None:
    """Test that usage data persists across tracker instances."""
    usage_path = tmp_path / "usage.json"

    # Record usage in first tracker
    tracker1 = BudgetTracker(usage_path=usage_path)
    tracker1.record_usage("grok-4-1-fast-non-reasoning", 500_000, 200_000)

    # Load in second tracker
    tracker2 = BudgetTracker(usage_path=usage_path)
    summary = tracker2.get_summary()

    assert summary["total_prompt_tokens"] == 500_000
    assert summary["total_completion_tokens"] == 200_000
    assert summary["calls"] == 1
    assert summary["total_cost_usd"] > 0
