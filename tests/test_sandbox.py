"""Tests for sandbox enforcement."""

import pytest
from pathlib import Path
from grok_cli import sandbox


def test_sandbox_init():
    """Test sandbox initialization."""
    # This should not raise
    sandbox.init_sandbox()
    assert sandbox.get_current_dir() == Path.cwd().resolve()


def test_check_path_allowed_relative():
    """Test that relative paths within cwd are allowed."""
    sandbox.init_sandbox()
    cwd = Path.cwd()

    # Relative path should be allowed
    test_path = Path("test.txt")
    resolved = sandbox.check_path_allowed(test_path, "test")
    assert resolved == (cwd / "test.txt").resolve()


def test_check_path_allowed_absolute_within():
    """Test that absolute paths within cwd are allowed."""
    sandbox.init_sandbox()
    cwd = Path.cwd()

    # Absolute path within cwd should be allowed
    test_path = cwd / "subdir" / "test.txt"
    resolved = sandbox.check_path_allowed(test_path, "test")
    assert resolved == test_path.resolve()


def test_check_path_denied_outside():
    """Test that paths outside cwd are denied."""
    sandbox.init_sandbox()

    # Path outside cwd should be denied
    test_path = Path("/tmp/test.txt")

    with pytest.raises(PermissionError) as exc_info:
        sandbox.check_path_allowed(test_path, "test")

    assert "outside launch directory" in str(exc_info.value).lower()


def test_set_current_dir_within_sandbox():
    """Test changing directory within sandbox."""
    sandbox.init_sandbox()
    cwd = Path.cwd()

    # Create a subdirectory path (doesn't need to exist for this test)
    subdir = cwd / "subdir"

    # Should allow cd to subdirectory within launch dir
    # Note: This will fail if subdir doesn't exist, so we catch that
    try:
        sandbox.set_current_dir(subdir)
    except FileNotFoundError:
        # Expected if directory doesn't exist - the important thing is
        # it didn't raise PermissionError
        pass


def test_set_current_dir_outside_sandbox():
    """Test that changing to directory outside sandbox is denied."""
    sandbox.init_sandbox()

    # Try to cd outside sandbox
    outside_dir = Path("/tmp")

    with pytest.raises(PermissionError) as exc_info:
        sandbox.set_current_dir(outside_dir)

    assert "outside launch directory" in str(exc_info.value).lower()


def test_sandbox_always_enforced():
    """Test that sandbox cannot be disabled."""
    sandbox.init_sandbox()

    # Path outside cwd should always be denied
    test_path = Path("/etc/passwd")

    with pytest.raises(PermissionError):
        sandbox.check_path_allowed(test_path, "read")
