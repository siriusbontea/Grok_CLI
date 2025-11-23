# Grok CLI - CURRENT Branch Package

**Version:** v1.0.0-CURRENT

This directory contains a complete package for the Grok CLI.

## Package Status: Development Branch (CURRENT)

**Warning:** This is the CURRENT development branch. Like FreeBSD-CURRENT, this contains the latest changes and may have bugs. Use at your own risk. For stable releases, check the tagged versions.

### What's Included

#### Core Configuration Files
- `pyproject.toml` - Poetry project configuration with all dependencies
- `poetry.lock` - Locked dependency versions (67,588 bytes)
- `.gitignore` - Git ignore rules
- `LICENSE` - MIT License
- `README.md` - Complete user documentation
- `INSTALL.md` - Installation instructions
- `Grok_CLI_Blueprint_v1.md` - Design blueprint (locked v1.0)
- `MANIFEST.md` - This package manifest

#### Main Package (`grok_cli/`)
**25 Python files** organized as follows:

**Entry Points & Core:**
- `main.py` - Typer CLI application with sandbox initialization
- `repl.py` - Interactive REPL with prompt_toolkit (history, tab completion)
- `config.py` - TOML configuration management (~/.grok/config.toml)
- `sandbox.py` - Filesystem safety enforcement (cwd-locked by default)
- `session.py` - TOON session handling with compression
- `cache.py` - Request/response caching with SHA256 hashing
- `models.py` - Model selection and switching
- `plugins.py` - Auto-discovery plugin system

**Commands (`grok_cli/commands/`):**
- `ask.py` - General queries (no file access)
- `create.py` - Smart file generation with overwrite protection
- `edit.py` - In-place file modification with diff preview
- `heavy.py` - Parallel agents with meta-resolver
- `shell.py` - Built-in sandboxed shell (ls, cd, cat, etc.)
- `utility.py` - Help, cost tracking, plugins, models

**Providers (`grok_cli/providers/`):**
- `base.py` - Provider interface
- `grok.py` - Official Grok API implementation

**UI (`grok_cli/ui/`):**
- `banner.py` - ASCII art banner (grey) + welcome messages
- `prompt.py` - Custom REPL prompt with git integration

#### Tests (`tests/`)
- `test_sandbox.py` - Sandbox enforcement tests
- `test_toon.py` - TOON format validation

## Latest Build Status

Most recent build tested:

```bash
✓ poetry install     # Successfully installs all dependencies
✓ poetry run grok    # Launches with grey ASCII banner
✓ cd command         # Sandboxed (cannot escape project)
✓ Sandbox warning    # Centered text, proper box formatting
```

Note: Tests passing at time of commit, but CURRENT branch may introduce regressions.

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd <repo-name>

# Install dependencies
poetry install

# Run Grok CLI
poetry run grok
```

## Key Features Implemented

1. **Safety First**
   - Sandbox locked to launch directory (cwd)
   - No silent overwrites - always preview and confirm
   - `--dangerously-allow-entire-fs` requires "YES" confirmation
   - Centered, prominent warning for sandbox violations

2. **Beautiful UX**
   - Grey ASCII art banner on every startup
   - Custom prompt: `┌─ grok  [model]  [~/path]  (git-branch±)`
   - Git status integration (± for uncommitted changes)
   - Rich terminal formatting with colors

3. **Token Efficiency**
   - TOON format for model communication (30-60% savings vs JSON)
   - Smart session compression (>12k tokens)
   - SHA256-based caching system

4. **Developer Friendly**
   - Built-in shell commands (no subprocess calls)
   - Arrow keys + Ctrl+R history search
   - Tab completion for commands
   - Verbose output by default (lean_mode optional)

5. **Extensible**
   - Plugin auto-discovery from `~/.grok/plugins/`
   - Clean provider interface
   - TOML configuration with comments

## File Count Summary

- Python modules: 25 files
- Documentation: 5 files (README, INSTALL, LICENSE, Blueprint, MANIFEST)
- Configuration: 2 files (pyproject.toml, .gitignore)
- Tests: 2 files
- Lock file: 1 file (poetry.lock)

**Total: 35 files ready for deployment**

## What Changed (Latest Session)

1. Fixed Typer option configuration (no more unwanted dangerous mode prompts)
2. Banner now displays on every startup (grey color)
3. SANDBOX VIOLATION box text centered with proper spacing
4. `cd` with no args goes to project root (not home directory)
5. Complete package assembled in CURRENT directory

## Development Status

This is the CURRENT development branch - active development happens here.
Features are tested but may contain bugs. Snapshot as of November 22, 2025.

## Quick Start

```bash
# Set your API key
export GROK_API_KEY=your_key_here

# Run the CLI
poetry run grok

# Or install globally
poetry build
pip install dist/grok_cli-*.whl
grok
```

## Configuration

User configuration is stored at `~/.grok/config.toml` and is created automatically on first run.

See `README.md` for full documentation.
