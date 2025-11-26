"""Tests for cache module."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from grok_cli import cache


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache_dir = tmp_path / ".grok" / "cache"
    cache_dir.mkdir(parents=True)
    return cache_dir


@pytest.fixture
def mock_cache_dir(temp_cache_dir: Path):
    """Mock the cache directory to use temp directory."""
    with patch.object(cache, "_get_cache_dir", return_value=temp_cache_dir):
        yield temp_cache_dir


def test_compute_cache_key():
    """Test cache key computation is deterministic."""
    messages = [{"role": "user", "content": "hello"}]
    model = "grok-4"
    temperature = 0.7

    key1 = cache._compute_cache_key(messages, model, temperature)
    key2 = cache._compute_cache_key(messages, model, temperature)

    assert key1 == key2
    assert len(key1) == 64  # SHA256 hex length


def test_compute_cache_key_different_inputs():
    """Test that different inputs produce different keys."""
    messages1 = [{"role": "user", "content": "hello"}]
    messages2 = [{"role": "user", "content": "goodbye"}]
    model = "grok-4"
    temperature = 0.7

    key1 = cache._compute_cache_key(messages1, model, temperature)
    key2 = cache._compute_cache_key(messages2, model, temperature)

    assert key1 != key2


def test_cache_response_and_get(mock_cache_dir: Path):
    """Test caching and retrieving a response."""
    messages = [{"role": "user", "content": "test question"}]
    model = "grok-4"
    temperature = 0.7
    response = {"content": "test answer", "usage": {"total_tokens": 100}}

    # Cache the response
    cache.cache_response(messages, model, temperature, response)

    # Retrieve it
    cached = cache.get_cached_response(messages, model, temperature)

    assert cached is not None
    assert cached["content"] == "test answer"
    assert cached["usage"]["total_tokens"] == 100


def test_get_cached_response_not_found(mock_cache_dir: Path):
    """Test getting a non-existent cached response."""
    messages = [{"role": "user", "content": "not cached"}]
    model = "grok-4"
    temperature = 0.7

    cached = cache.get_cached_response(messages, model, temperature)

    assert cached is None


def test_get_cached_response_expired(mock_cache_dir: Path):
    """Test that expired cache entries are not returned."""
    messages = [{"role": "user", "content": "old question"}]
    model = "grok-4"
    temperature = 0.7

    # Create an expired cache entry
    cache_key = cache._compute_cache_key(messages, model, temperature)
    cache_file = mock_cache_dir / f"{cache_key}.json"

    old_time = (datetime.now() - timedelta(days=31)).isoformat()
    cache_data = {
        "cached_at": old_time,
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "response": {"content": "old answer"},
    }
    cache_file.write_text(json.dumps(cache_data))

    # Should return None and delete the file
    cached = cache.get_cached_response(messages, model, temperature)

    assert cached is None
    assert not cache_file.exists()


def test_clear_cache(mock_cache_dir: Path):
    """Test clearing all cached responses."""
    # Create some cache files
    for i in range(5):
        cache_file = mock_cache_dir / f"test{i}.json"
        cache_file.write_text("{}")

    deleted = cache.clear_cache()

    assert deleted == 5
    assert len(list(mock_cache_dir.glob("*.json"))) == 0


def test_get_cache_stats_empty(mock_cache_dir: Path):
    """Test getting stats for empty cache."""
    stats = cache.get_cache_stats()

    assert stats["file_count"] == 0
    assert stats["total_size_mb"] == 0.0
    assert stats["oldest_age_days"] == 0


def test_get_cache_stats_with_files(mock_cache_dir: Path):
    """Test getting stats for cache with files."""
    # Create some cache files
    for i in range(3):
        cache_file = mock_cache_dir / f"test{i}.json"
        cache_file.write_text('{"test": "data"}')

    stats = cache.get_cache_stats()

    assert stats["file_count"] == 3
    assert stats["total_size_mb"] > 0
    assert stats["oldest_age_days"] >= 0
