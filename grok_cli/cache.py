"""API response caching with SHA256 hashing and automatic pruning.

Cache is stored globally at ~/.grok/cache/<sha256>.json since API
responses are project-independent (same prompt = same response).

Project-specific data (sessions, history) is stored in .grok/ within
each project directory.

Cache is pruned when >30 days old or total cache size >500 MB
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from grok_cli import config


def _get_cache_dir() -> Path:
    """Get cache directory, creating if needed.

    Returns:
        Path to cache directory
    """
    cache_dir = config.get_grok_dir() / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def _compute_cache_key(messages: list[dict[str, str]], model: str, temperature: float) -> str:
    """Compute SHA256 cache key for request parameters.

    Args:
        messages: Message list
        model: Model name
        temperature: Temperature setting

    Returns:
        SHA256 hex string
    """
    # Create deterministic string representation
    key_data = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_str.encode()).hexdigest()


def get_cached_response(messages: list[dict[str, str]], model: str, temperature: float) -> dict[str, Any] | None:
    """Get cached response if available.

    Args:
        messages: Message list
        model: Model name
        temperature: Temperature setting

    Returns:
        Cached response dict or None if not found
    """
    cache_dir = _get_cache_dir()
    cache_key = _compute_cache_key(messages, model, temperature)
    cache_file = cache_dir / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        cached_data = json.loads(cache_file.read_text())

        # Check if cache is still valid (not older than 30 days)
        cached_time = datetime.fromisoformat(cached_data.get("cached_at", ""))
        if datetime.now() - cached_time > timedelta(days=30):
            # Cache expired, delete it
            cache_file.unlink()
            return None

        response = cached_data.get("response")
        return response if isinstance(response, dict) else None

    except Exception:
        # Invalid cache file, delete it
        try:
            cache_file.unlink()
        except Exception:
            pass
        return None


def cache_response(messages: list[dict[str, str]], model: str, temperature: float, response: dict[str, Any]) -> None:
    """Cache a response.

    Args:
        messages: Message list
        model: Model name
        temperature: Temperature setting
        response: Response to cache
    """
    cache_dir = _get_cache_dir()
    cache_key = _compute_cache_key(messages, model, temperature)
    cache_file = cache_dir / f"{cache_key}.json"

    cache_data = {
        "cached_at": datetime.now().isoformat(),
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "response": response,
    }

    cache_file.write_text(json.dumps(cache_data, indent=2))

    # Prune cache if needed (async, don't block)
    try:
        _prune_cache_if_needed()
    except Exception:
        pass  # Don't fail on pruning errors


def _prune_cache_if_needed() -> None:
    """Prune cache if >30 days old or >500 MB total size.

    Deletes oldest files first until under limits.
    """
    cache_dir = _get_cache_dir()
    cache_files = list(cache_dir.glob("*.json"))

    if not cache_files:
        return

    # Calculate total size
    total_size = sum(f.stat().st_size for f in cache_files)
    max_size = 500 * 1024 * 1024  # 500 MB

    # Sort by modification time (oldest first)
    cache_files.sort(key=lambda f: f.stat().st_mtime)

    # Delete files older than 30 days
    cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 days in seconds
    for cache_file in cache_files[:]:
        try:
            file_stat = cache_file.stat()
            if file_stat.st_mtime < cutoff_time:
                file_size = file_stat.st_size
                cache_file.unlink()
                cache_files.remove(cache_file)
                total_size -= file_size
        except Exception:
            pass

    # Delete oldest files until under size limit
    while total_size > max_size and cache_files:
        oldest_file = cache_files.pop(0)
        try:
            file_size = oldest_file.stat().st_size
            oldest_file.unlink()
            total_size -= file_size
        except Exception:
            pass


def clear_cache() -> int:
    """Clear all cached responses.

    Returns:
        Number of files deleted
    """
    cache_dir = _get_cache_dir()
    cache_files = list(cache_dir.glob("*.json"))

    deleted = 0
    for cache_file in cache_files:
        try:
            cache_file.unlink()
            deleted += 1
        except Exception:
            pass

    return deleted


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics.

    Returns:
        Dictionary with cache stats
    """
    cache_dir = _get_cache_dir()
    cache_files = list(cache_dir.glob("*.json"))

    if not cache_files:
        return {
            "file_count": 0,
            "total_size_mb": 0.0,
            "oldest_age_days": 0,
        }

    total_size = sum(f.stat().st_size for f in cache_files)
    oldest_mtime = min(f.stat().st_mtime for f in cache_files)
    oldest_age_days = (time.time() - oldest_mtime) / (24 * 60 * 60)

    return {
        "file_count": len(cache_files),
        "total_size_mb": total_size / (1024 * 1024),
        "oldest_age_days": oldest_age_days,
    }
