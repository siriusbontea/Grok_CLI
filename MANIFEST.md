# Grok CLI - Package Manifest (CURRENT Branch)

**Version:** v1.0.0-CURRENT

## Package Contents

This directory contains the CURRENT development branch of the Grok CLI.

**Warning:** This is active development code. May contain bugs. Use stable tagged releases for production.

### Core Files
- pyproject.toml       - Poetry project configuration
- poetry.lock          - Locked dependencies
- README.md            - User documentation
- LICENSE              - MIT License
- INSTALL.md           - Installation instructions
- .gitignore           - Git ignore rules

### Package Structure
grok_cli/
├── __init__.py        - Package initializer
├── main.py            - CLI entry point (Typer app)
├── repl.py            - Interactive REPL with prompt_toolkit
├── config.py          - TOML configuration management
├── sandbox.py         - Filesystem sandbox enforcement
├── session.py         - TOON session handling
├── cache.py           - Request/response caching
├── models.py          - Model selection logic
├── plugins.py         - Plugin discovery system
├── commands/
│   ├── __init__.py
│   ├── ask.py         - Ask command (general queries)
│   ├── create.py      - Create command (file generation)
│   ├── edit.py        - Edit command (file modification)
│   ├── heavy.py       - Heavy command (parallel agents)
│   ├── shell.py       - Built-in shell commands
│   └── utility.py     - Utility commands (help, cost, etc.)
├── providers/
│   ├── __init__.py
│   ├── base.py        - Base provider interface
│   └── grok.py        - Grok API implementation
└── ui/
    ├── __init__.py
    ├── banner.py      - ASCII banner and welcome
    └── prompt.py      - Custom REPL prompt

### Tests
tests/
├── __init__.py
├── test_sandbox.py    - Sandbox safety tests
└── test_toon.py       - TOON format tests

### Installation
From this directory:
```bash
poetry install
poetry run grok
```

### Features
- Interactive REPL with history and tab completion
- Strict cwd sandbox (use --dangerously-allow-entire-fs to disable)
- TOON format for efficient model communication
- Built-in shell commands (ls, cd, cat, etc.)
- Automatic project awareness
- Git integration in prompt
- Plugin system for extensibility

### Configuration
User config: `~/.grok/config.toml`
API key: `export GROK_API_KEY=your_key_here`
