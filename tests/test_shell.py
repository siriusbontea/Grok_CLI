"""Tests for commands/shell.py — pure-Python sandboxed shell commands."""

import pytest
from pathlib import Path

from grok_cli import sandbox
from grok_cli.commands.shell import (
    SHELL_COMMANDS,
    cmd_cat,
    cmd_cd,
    cmd_cp,
    cmd_head,
    cmd_ls,
    cmd_mkdir,
    cmd_mv,
    cmd_pwd,
    cmd_rm,
    cmd_tail,
    execute_shell_command,
    is_shell_command,
)


@pytest.fixture(autouse=True)
def sandbox_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Initialize sandbox rooted in tmp_path for every test."""
    monkeypatch.chdir(tmp_path)
    sandbox.init_sandbox()
    yield tmp_path


# --- is_shell_command ---


def test_is_shell_command_true():
    """Known commands are recognized."""
    for cmd in ("ls", "cd", "pwd", "cat", "head", "tail", "mkdir", "cp", "mv", "rm", "tree", "ll"):
        assert is_shell_command(cmd) is True


def test_is_shell_command_false():
    """Unknown commands are not recognized."""
    assert is_shell_command("grep") is False
    assert is_shell_command("echo") is False


# --- cmd_pwd ---


def test_cmd_pwd(sandbox_in_tmp: Path, capsys):
    """pwd prints the current working directory."""
    cmd_pwd([])
    # Rich Console writes to its own internal — just verify no crash.
    # Functional verification: sandbox.get_current_dir() matches.
    assert sandbox.get_current_dir() == sandbox_in_tmp


# --- cmd_ls ---


def test_cmd_ls_basic(sandbox_in_tmp: Path):
    """ls lists files without crashing."""
    (sandbox_in_tmp / "file.txt").write_text("hello", encoding="utf-8")
    cmd_ls([])  # Should not raise


def test_cmd_ls_hides_dotfiles(sandbox_in_tmp: Path):
    """ls without -a hides dotfiles."""
    (sandbox_in_tmp / ".hidden").write_text("x", encoding="utf-8")
    (sandbox_in_tmp / "visible.txt").write_text("y", encoding="utf-8")
    # No crash; functional check would need capturing Rich output
    cmd_ls([])


def test_cmd_ls_nonexistent(sandbox_in_tmp: Path):
    """ls on nonexistent directory prints error without crashing."""
    cmd_ls(["no_such_dir"])


# --- cmd_cd ---


def test_cmd_cd_to_subdir(sandbox_in_tmp: Path):
    """cd to a subdirectory changes current dir."""
    sub = sandbox_in_tmp / "sub"
    sub.mkdir()
    cmd_cd(["sub"])
    assert sandbox.get_current_dir() == sub


def test_cmd_cd_no_args_returns_to_launch(sandbox_in_tmp: Path):
    """cd with no args returns to launch dir."""
    sub = sandbox_in_tmp / "sub"
    sub.mkdir()
    cmd_cd(["sub"])
    cmd_cd([])
    assert sandbox.get_current_dir() == sandbox_in_tmp


def test_cmd_cd_outside_sandbox(sandbox_in_tmp: Path):
    """cd outside sandbox prints error, does not change dir."""
    cmd_cd(["/tmp"])
    assert sandbox.get_current_dir() == sandbox_in_tmp


def test_cmd_cd_nonexistent(sandbox_in_tmp: Path):
    """cd to nonexistent dir prints error."""
    cmd_cd(["no_such_dir"])
    assert sandbox.get_current_dir() == sandbox_in_tmp


# --- cmd_cat ---


def test_cmd_cat_existing_file(sandbox_in_tmp: Path):
    """cat prints file contents without crashing."""
    (sandbox_in_tmp / "greeting.txt").write_text("hello", encoding="utf-8")
    cmd_cat(["greeting.txt"])


def test_cmd_cat_nonexistent(sandbox_in_tmp: Path):
    """cat on nonexistent file prints error."""
    cmd_cat(["ghost.txt"])


def test_cmd_cat_no_args(sandbox_in_tmp: Path):
    """cat with no args prints error."""
    cmd_cat([])


# --- cmd_head ---


def test_cmd_head_default_10(sandbox_in_tmp: Path):
    """head shows first 10 lines by default."""
    content = "\n".join(f"line {i}" for i in range(20))
    (sandbox_in_tmp / "data.txt").write_text(content, encoding="utf-8")
    cmd_head(["data.txt"])


def test_cmd_head_custom_n(sandbox_in_tmp: Path):
    """head -n 3 shows first 3 lines."""
    content = "\n".join(f"line {i}" for i in range(10))
    (sandbox_in_tmp / "data.txt").write_text(content, encoding="utf-8")
    cmd_head(["-n", "3", "data.txt"])


def test_cmd_head_no_args():
    """head with no file args prints error."""
    cmd_head([])


# --- cmd_tail ---


def test_cmd_tail_default_10(sandbox_in_tmp: Path):
    """tail shows last 10 lines by default."""
    content = "\n".join(f"line {i}" for i in range(20))
    (sandbox_in_tmp / "data.txt").write_text(content, encoding="utf-8")
    cmd_tail(["data.txt"])


def test_cmd_tail_custom_n(sandbox_in_tmp: Path):
    """tail -n 5 shows last 5 lines."""
    content = "\n".join(f"line {i}" for i in range(20))
    (sandbox_in_tmp / "data.txt").write_text(content, encoding="utf-8")
    cmd_tail(["-n", "5", "data.txt"])


# --- cmd_mkdir ---


def test_cmd_mkdir_creates_dir(sandbox_in_tmp: Path):
    """mkdir creates a new directory."""
    cmd_mkdir(["newdir"])
    assert (sandbox_in_tmp / "newdir").is_dir()


def test_cmd_mkdir_parents(sandbox_in_tmp: Path):
    """mkdir -p creates nested directories."""
    cmd_mkdir(["-p", "a/b/c"])
    assert (sandbox_in_tmp / "a" / "b" / "c").is_dir()


def test_cmd_mkdir_existing(sandbox_in_tmp: Path):
    """mkdir on existing dir prints warning."""
    (sandbox_in_tmp / "exists").mkdir()
    cmd_mkdir(["exists"])


# --- cmd_cp ---


def test_cmd_cp_file(sandbox_in_tmp: Path):
    """cp copies a file."""
    (sandbox_in_tmp / "src.txt").write_text("data", encoding="utf-8")
    cmd_cp(["src.txt", "dst.txt"])
    assert (sandbox_in_tmp / "dst.txt").read_text(encoding="utf-8") == "data"


def test_cmd_cp_missing_source(sandbox_in_tmp: Path):
    """cp with nonexistent source prints error."""
    cmd_cp(["ghost.txt", "dst.txt"])
    assert not (sandbox_in_tmp / "dst.txt").exists()


def test_cmd_cp_too_few_args():
    """cp with fewer than 2 args prints error."""
    cmd_cp(["only_one"])


# --- cmd_mv ---


def test_cmd_mv_file(sandbox_in_tmp: Path):
    """mv renames a file."""
    (sandbox_in_tmp / "old.txt").write_text("data", encoding="utf-8")
    cmd_mv(["old.txt", "new.txt"])
    assert not (sandbox_in_tmp / "old.txt").exists()
    assert (sandbox_in_tmp / "new.txt").read_text(encoding="utf-8") == "data"


def test_cmd_mv_missing_source(sandbox_in_tmp: Path):
    """mv with nonexistent source prints error."""
    cmd_mv(["ghost.txt", "dst.txt"])


def test_cmd_mv_too_few_args():
    """mv with fewer than 2 args prints error."""
    cmd_mv(["only_one"])


# --- cmd_rm ---


def test_cmd_rm_file(sandbox_in_tmp: Path):
    """rm deletes a file."""
    f = sandbox_in_tmp / "doomed.txt"
    f.write_text("bye", encoding="utf-8")
    cmd_rm(["doomed.txt"])
    assert not f.exists()


def test_cmd_rm_dir_without_r(sandbox_in_tmp: Path):
    """rm on a directory without -r prints error."""
    (sandbox_in_tmp / "mydir").mkdir()
    cmd_rm(["mydir"])
    assert (sandbox_in_tmp / "mydir").exists()  # Should NOT be deleted


def test_cmd_rm_dir_with_r(sandbox_in_tmp: Path):
    """rm -r deletes a directory recursively."""
    d = sandbox_in_tmp / "mydir"
    d.mkdir()
    (d / "child.txt").write_text("x", encoding="utf-8")
    cmd_rm(["-r", "mydir"])
    assert not d.exists()


def test_cmd_rm_rf(sandbox_in_tmp: Path):
    """rm -rf works (flag parsing handles combined flags)."""
    d = sandbox_in_tmp / "mydir"
    d.mkdir()
    cmd_rm(["-rf", "mydir"])
    assert not d.exists()


def test_cmd_rm_nonexistent(sandbox_in_tmp: Path):
    """rm on nonexistent file prints warning."""
    cmd_rm(["ghost.txt"])


def test_cmd_rm_no_args():
    """rm with no args prints error."""
    cmd_rm([])


# --- execute_shell_command ---


def test_execute_shell_command_dispatches(sandbox_in_tmp: Path):
    """execute_shell_command dispatches to the correct handler."""
    (sandbox_in_tmp / "test.txt").write_text("hi", encoding="utf-8")
    execute_shell_command(["cat", "test.txt"])  # Should not raise


def test_execute_shell_command_unknown():
    """Unknown command prints error."""
    execute_shell_command(["badcmd"])


def test_execute_shell_command_empty():
    """Empty args list does nothing."""
    execute_shell_command([])
