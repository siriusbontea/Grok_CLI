"""File validation for generated content.

Provides syntax validation for common file types to catch errors
before saving and enable auto-fix loops with the model.

Supported file types:
- LaTeX (.tex) - chktex or pdflatex
- Python (.py) - py_compile, ruff if available
- JSON (.json) - json.loads
- YAML (.yaml, .yml) - yaml.safe_load
- TOML (.toml) - tomlkit.parse
- JavaScript (.js) - node --check
"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Optional imports - gracefully handle missing packages
try:
    import yaml  # type: ignore[import-untyped]

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import tomlkit

    HAS_TOML = True
except ImportError:
    HAS_TOML = False


@dataclass
class ValidationResult:
    """Result of file validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def format_report(self) -> str:
        """Format errors and warnings as a string for the model."""
        lines = []
        if self.errors:
            lines.append("ERRORS:")
            for err in self.errors:
                lines.append(f"  - {err}")
        if self.warnings:
            lines.append("WARNINGS:")
            for warn in self.warnings:
                lines.append(f"  - {warn}")
        return "\n".join(lines)


def _check_command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(
            ["which", cmd],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# --- Validators ---


def validate_python(content: str, filename: str = "file.py") -> ValidationResult:
    """Validate Python syntax using py_compile and optionally ruff.

    Args:
        content: Python source code
        filename: Filename for error messages

    Returns:
        ValidationResult with any syntax errors
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Write to temp file for validation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        # Basic syntax check with py_compile
        try:
            import py_compile

            py_compile.compile(temp_path, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax error: {e.msg}")

        # If ruff is available, run it for additional checks
        if _check_command_exists("ruff"):
            try:
                result = subprocess.run(
                    ["ruff", "check", "--select=E,F", temp_path],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    # Parse ruff output - each line is an issue
                    for line in result.stdout.strip().split("\n"):
                        if line and temp_path in line:
                            # Extract just the error part
                            parts = line.split(temp_path)
                            if len(parts) > 1:
                                issue = parts[1].lstrip(":").strip()
                                if "error" in line.lower():
                                    errors.append(issue)
                                else:
                                    warnings.append(issue)
            except Exception:
                pass  # ruff check is optional

    finally:
        Path(temp_path).unlink(missing_ok=True)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_json(content: str, filename: str = "file.json") -> ValidationResult:
    """Validate JSON syntax.

    Args:
        content: JSON content
        filename: Filename for error messages

    Returns:
        ValidationResult with any parse errors
    """
    errors: list[str] = []

    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        errors.append(f"Line {e.lineno}, column {e.colno}: {e.msg}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])


def validate_yaml(content: str, filename: str = "file.yaml") -> ValidationResult:
    """Validate YAML syntax.

    Args:
        content: YAML content
        filename: Filename for error messages

    Returns:
        ValidationResult with any parse errors
    """
    errors: list[str] = []

    if not HAS_YAML:
        # Can't validate without PyYAML
        return ValidationResult(valid=True, errors=[], warnings=["PyYAML not installed, skipping validation"])

    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        if hasattr(e, "problem_mark") and e.problem_mark is not None:
            mark = e.problem_mark
            errors.append(f"Line {mark.line + 1}, column {mark.column + 1}: {getattr(e, 'problem', str(e))}")
        else:
            errors.append(str(e))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])


def validate_toml(content: str, filename: str = "file.toml") -> ValidationResult:
    """Validate TOML syntax.

    Args:
        content: TOML content
        filename: Filename for error messages

    Returns:
        ValidationResult with any parse errors
    """
    errors: list[str] = []

    if not HAS_TOML:
        # Can't validate without tomlkit
        return ValidationResult(valid=True, errors=[], warnings=["tomlkit not installed, skipping validation"])

    try:
        tomlkit.parse(content)
    except tomlkit.exceptions.ParseError as e:
        errors.append(str(e))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])


def validate_latex(content: str, filename: str = "file.tex") -> ValidationResult:
    """Validate LaTeX syntax using chktex or pdflatex.

    Args:
        content: LaTeX content
        filename: Filename for error messages

    Returns:
        ValidationResult with any syntax errors
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Write to temp file for validation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        # Try chktex first (fast linter)
        if _check_command_exists("chktex"):
            try:
                result = subprocess.run(
                    ["chktex", "-q", "-n1", "-n2", "-n3", temp_path],
                    capture_output=True,
                    text=True,
                )
                # chktex outputs warnings/errors to stdout
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if "error" in line.lower():
                        errors.append(line)
                    elif "warning" in line.lower():
                        warnings.append(line)
                    elif line and ":" in line:
                        # Generic issue format
                        warnings.append(line)
            except Exception:
                pass

        # Try pdflatex in draft mode for deeper validation
        if _check_command_exists("pdflatex"):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    result = subprocess.run(
                        [
                            "pdflatex",
                            "-draftmode",
                            "-interaction=nonstopmode",
                            "-halt-on-error",
                            f"-output-directory={tmpdir}",
                            temp_path,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode != 0:
                        # Parse pdflatex output for errors
                        for line in result.stdout.split("\n"):
                            if line.startswith("!"):
                                # LaTeX error line
                                errors.append(line[1:].strip())
                            elif "error" in line.lower() and ":" in line:
                                errors.append(line.strip())
            except subprocess.TimeoutExpired:
                warnings.append("LaTeX compilation timed out")
            except Exception:
                pass

        # If no tools available, check for common issues manually
        if not _check_command_exists("chktex") and not _check_command_exists("pdflatex"):
            # Basic sanity checks
            if "\\begin{document}" in content and "\\end{document}" not in content:
                errors.append("Missing \\end{document}")
            if "\\end{document}" in content and "\\begin{document}" not in content:
                errors.append("Missing \\begin{document}")

            # Check for unmatched braces (simple check)
            open_braces = content.count("{")
            close_braces = content.count("}")
            if open_braces != close_braces:
                errors.append(f"Unmatched braces: {open_braces} opening, {close_braces} closing")

            # Check for common environment mismatches
            begins = re.findall(r"\\begin\{(\w+)\}", content)
            ends = re.findall(r"\\end\{(\w+)\}", content)
            begin_counts: dict[str, int] = {}
            end_counts: dict[str, int] = {}
            for env in begins:
                begin_counts[env] = begin_counts.get(env, 0) + 1
            for env in ends:
                end_counts[env] = end_counts.get(env, 0) + 1

            for env in set(begin_counts.keys()) | set(end_counts.keys()):
                b = begin_counts.get(env, 0)
                e = end_counts.get(env, 0)
                if b != e:
                    errors.append(f"Unmatched environment '{env}': {b} \\begin, {e} \\end")

            if not errors:
                warnings.append("No LaTeX tools (chktex/pdflatex) available, performed basic checks only")

    finally:
        Path(temp_path).unlink(missing_ok=True)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_javascript(content: str, filename: str = "file.js") -> ValidationResult:
    """Validate JavaScript syntax using node --check.

    Args:
        content: JavaScript content
        filename: Filename for error messages

    Returns:
        ValidationResult with any syntax errors
    """
    errors: list[str] = []

    if not _check_command_exists("node"):
        return ValidationResult(valid=True, errors=[], warnings=["Node.js not installed, skipping validation"])

    # Write to temp file for validation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = subprocess.run(
            ["node", "--check", temp_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Parse node error output
            for line in result.stderr.strip().split("\n"):
                if line.strip():
                    errors.append(line.strip())
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])


# --- Validator Registry ---

# Map file extensions to validator functions
VALIDATORS: dict[str, Callable[[str, str], ValidationResult]] = {
    ".py": validate_python,
    ".json": validate_json,
    ".yaml": validate_yaml,
    ".yml": validate_yaml,
    ".toml": validate_toml,
    ".tex": validate_latex,
    ".latex": validate_latex,
    ".js": validate_javascript,
    ".mjs": validate_javascript,
}


def get_validator(filename: str) -> Callable[[str, str], ValidationResult] | None:
    """Get the appropriate validator for a file.

    Args:
        filename: Filename or path

    Returns:
        Validator function or None if no validator available
    """
    ext = Path(filename).suffix.lower()
    return VALIDATORS.get(ext)


def validate_file(content: str, filename: str) -> ValidationResult | None:
    """Validate file content if a validator is available.

    Args:
        content: File content
        filename: Filename (used to determine validator and for error messages)

    Returns:
        ValidationResult or None if no validator available
    """
    validator = get_validator(filename)
    if validator:
        return validator(content, filename)
    return None


def get_supported_extensions() -> list[str]:
    """Get list of file extensions that have validators.

    Returns:
        List of extensions (e.g., ['.py', '.json', ...])
    """
    return list(VALIDATORS.keys())
