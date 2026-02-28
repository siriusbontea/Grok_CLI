"""Tests for validators module — pure-function validators for file content."""

import pytest
from unittest.mock import patch

from grok_cli.validators import (
    ValidationResult,
    get_validator,
    validate_file,
    validate_json,
    validate_latex,
    validate_python,
    validate_toml,
    validate_yaml,
)


# --- JSON validator ---


def test_validate_json_valid():
    """Valid JSON returns no errors."""
    result = validate_json('{"key": "value", "num": 42}')
    assert result.valid is True
    assert result.errors == []


def test_validate_json_invalid():
    """Malformed JSON returns error with line/column info."""
    result = validate_json('{"key": }')
    assert result.valid is False
    assert len(result.errors) == 1
    assert "line" in result.errors[0].lower() or "Line" in result.errors[0]


def test_validate_json_empty():
    """Empty string is invalid JSON."""
    result = validate_json("")
    assert result.valid is False
    assert len(result.errors) == 1


# --- YAML validator ---


def test_validate_yaml_valid():
    """Valid YAML returns no errors."""
    result = validate_yaml("key: value\nlist:\n  - one\n  - two\n")
    assert result.valid is True
    assert result.errors == []


def test_validate_yaml_invalid():
    """Malformed YAML returns error (skipped if PyYAML not installed)."""
    from grok_cli.validators import HAS_YAML

    if not HAS_YAML:
        pytest.skip("PyYAML not installed")
    result = validate_yaml("key: value\n  bad indent: oops\n    worse: nope")
    assert result.valid is False
    assert len(result.errors) >= 1


# --- TOML validator ---


def test_validate_toml_valid():
    """Valid TOML returns no errors."""
    result = validate_toml('[section]\nkey = "value"\nnum = 42\n')
    assert result.valid is True
    assert result.errors == []


def test_validate_toml_invalid():
    """Malformed TOML returns error."""
    result = validate_toml("[section\nkey = value without quotes\n")
    assert result.valid is False
    assert len(result.errors) >= 1


# --- Python validator ---


def test_validate_python_valid():
    """Valid Python returns no errors."""
    result = validate_python("def greet(name):\n    return f'Hello, {name}!'\n")
    assert result.valid is True
    assert result.errors == []


def test_validate_python_syntax_error():
    """Syntax error is detected."""
    result = validate_python("def broken(\n    return 42\n")
    assert result.valid is False
    assert len(result.errors) >= 1
    assert any("syntax" in e.lower() or "Syntax" in e for e in result.errors)


# --- LaTeX validator (no-tools fallback path) ---


@pytest.fixture
def no_latex_tools():
    """Force the regex-based fallback path by pretending chktex/pdflatex don't exist."""
    with patch("grok_cli.validators._check_command_exists", return_value=False):
        yield


def test_validate_latex_valid_basic(no_latex_tools):
    """Valid LaTeX with matching braces/envs passes basic checks."""
    content = r"""\documentclass{article}
\begin{document}
Hello, world!
\end{document}
"""
    result = validate_latex(content)
    assert result.valid is True
    assert result.errors == []


def test_validate_latex_mismatched_braces(no_latex_tools):
    """Unmatched braces produce an error."""
    content = r"""\documentclass{article}
\begin{document}
{missing close
\end{document}
"""
    result = validate_latex(content)
    assert result.valid is False
    assert any("brace" in e.lower() for e in result.errors)


def test_validate_latex_mismatched_environments(no_latex_tools):
    """\\begin{X} without \\end{X} produces an error."""
    content = r"""\documentclass{article}
\begin{document}
\begin{itemize}
\item one
\end{document}
"""
    result = validate_latex(content)
    assert result.valid is False
    assert any("itemize" in e for e in result.errors)


def test_validate_latex_missing_end_document(no_latex_tools):
    """\\begin{document} without \\end{document} produces an error."""
    content = r"""\documentclass{article}
\begin{document}
Hello, world!
"""
    result = validate_latex(content)
    assert result.valid is False
    assert any("end{document}" in e.lower() or "\\end{document}" in e for e in result.errors)


# --- Dispatch / helper functions ---


@pytest.mark.parametrize("ext", [".py", ".json", ".yaml", ".toml", ".tex", ".js"])
def test_get_validator_known_extensions(ext):
    """Known file extensions return a validator function."""
    validator = get_validator(f"file{ext}")
    assert validator is not None
    assert callable(validator)


@pytest.mark.parametrize("ext", [".rb", ".unknown", ".go", ".rs"])
def test_get_validator_unknown_extension(ext):
    """Unknown file extensions return None."""
    validator = get_validator(f"file{ext}")
    assert validator is None


def test_validate_file_with_validator():
    """validate_file delegates to the correct validator for known types."""
    result = validate_file('{"valid": true}', "data.json")
    assert result is not None
    assert result.valid is True


def test_validate_file_without_validator():
    """validate_file returns None for unknown file types."""
    result = validate_file("some content", "file.unknown")
    assert result is None


def test_format_report_errors_and_warnings():
    """ValidationResult.format_report() includes both errors and warnings."""
    result = ValidationResult(
        valid=False,
        errors=["Syntax error on line 1", "Unexpected token"],
        warnings=["Unused import"],
    )
    report = result.format_report()
    assert "ERRORS:" in report
    assert "Syntax error on line 1" in report
    assert "Unexpected token" in report
    assert "WARNINGS:" in report
    assert "Unused import" in report


def test_format_report_empty():
    """ValidationResult.format_report() returns empty string when no issues."""
    result = ValidationResult(valid=True, errors=[], warnings=[])
    assert result.format_report() == ""
