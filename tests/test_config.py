"""Tests for config module."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from grok_cli import config


@pytest.fixture
def temp_grok_dir(tmp_path: Path) -> Path:
    """Create a temporary .grok directory."""
    grok_dir = tmp_path / ".grok"
    return grok_dir


@pytest.fixture
def mock_home(temp_grok_dir: Path):
    """Mock Path.home() to return temp directory."""
    home_dir = temp_grok_dir.parent
    with patch.object(Path, "home", return_value=home_dir):
        yield home_dir


def test_get_grok_dir_creates_directories(mock_home: Path):
    """Test that get_grok_dir creates required directories."""
    grok_dir = config.get_grok_dir()

    assert grok_dir.exists()
    assert (grok_dir / "cache").exists()
    assert (grok_dir / "sessions").exists()
    assert (grok_dir / "plugins").exists()


def test_get_config_path(mock_home: Path):
    """Test getting config file path."""
    config_path = config.get_config_path()

    assert config_path.name == "config.toml"
    assert config_path.parent.name == ".grok"


def test_is_first_run_true(mock_home: Path):
    """Test first run detection when config doesn't exist."""
    assert config.is_first_run() is True


def test_is_first_run_false(mock_home: Path):
    """Test first run detection when config exists."""
    # Create config file
    grok_dir = config.get_grok_dir()
    config_path = grok_dir / "config.toml"
    config_path.write_text("default_model = 'grok41_fast'")

    assert config.is_first_run() is False


def test_create_default_config(mock_home: Path):
    """Test creating default configuration."""
    config.create_default_config()

    config_path = config.get_config_path()
    assert config_path.exists()

    content = config_path.read_text()
    assert "default_model" in content
    assert "grok41_fast" in content
    assert "auto_compress" in content
    assert "lean_mode" in content


def test_load_config_creates_default(mock_home: Path):
    """Test that load_config creates default config on first run."""
    cfg = config.load_config()

    assert cfg["default_model"] == "grok41_fast"
    assert cfg["auto_compress"] == "smart"
    assert cfg["auto_yes"] is False
    assert cfg["colour"] is True
    assert cfg["lean_mode"] is False


def test_load_config_preserves_custom_values(mock_home: Path):
    """Test that load_config preserves custom values."""
    # Create custom config
    grok_dir = config.get_grok_dir()
    config_path = grok_dir / "config.toml"
    config_path.write_text('default_model = "grok41_heavy"\nlean_mode = true')

    cfg = config.load_config()

    assert cfg["default_model"] == "grok41_heavy"
    assert cfg["lean_mode"] is True
    # Should still have defaults for missing keys
    assert cfg["auto_compress"] == "smart"


def test_load_config_env_override(mock_home: Path):
    """Test that GROK_LEAN environment variable overrides config."""
    with patch.dict(os.environ, {"GROK_LEAN": "1"}):
        cfg = config.load_config()
        assert cfg["lean_mode"] is True


def test_save_config(mock_home: Path):
    """Test saving configuration."""
    # First create default
    config.load_config()

    # Modify and save
    new_config = {"default_model": "grok4_fast", "lean_mode": True}
    config.save_config(new_config)

    # Reload and verify
    cfg = config.load_config()
    assert cfg["default_model"] == "grok4_fast"
    assert cfg["lean_mode"] is True


def test_get_api_key_from_env():
    """Test getting API key from environment."""
    with patch.dict(os.environ, {"XAI_API_KEY": "test_key_123"}):
        key = config.get_api_key()
        assert key == "test_key_123"


def test_get_api_key_not_set():
    """Test getting API key when not set."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove XAI_API_KEY if it exists
        os.environ.pop("XAI_API_KEY", None)
        key = config.get_api_key()
        assert key is None


def test_default_config_values():
    """Test that DEFAULT_CONFIG has expected keys."""
    assert "default_model" in config.DEFAULT_CONFIG
    assert "auto_compress" in config.DEFAULT_CONFIG
    assert "auto_yes" in config.DEFAULT_CONFIG
    assert "colour" in config.DEFAULT_CONFIG
    assert "lean_mode" in config.DEFAULT_CONFIG
    assert "budget_monthly" in config.DEFAULT_CONFIG
    assert "web_daily_quota" in config.DEFAULT_CONFIG
