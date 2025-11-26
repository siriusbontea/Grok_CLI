# Grok CLI

```text
╔══════════════════════════════════════════════════════════════════════════════╗
║          ▁▂▂▄▄▂▂        ▄`                                                   ║
║      ▁▄▇██████████▀  ,▟█                                                     ║
║    ▁████▀▔         ,▟██▌          ▃▆█████▆▃                        ██        ║
║   ▗███▔          ▗█████▌        ▗██▛▔   ▔▀██▖                      ██        ║
║  ▗███▘         ▄█▀▔ ▝███       ▗██▘       ▔▀▀   ▗█████ ▗▆▇███▇▆▖   ██    ▄██ ║
║  ▐██▘        ▄▀▔     ███       ▐██     ▄▄▄▄▄▄▖  ██    ▗█▛▔   ▔▜█▖  ██  ▗██▘  ║
║  ▐██▌      ⌐▔       ▗███       ▝██▖    ▔▔▔▔██▌  ██    ▐█▌     ▐█▌  ██▂▟██    ║
║   ███▖             ▗███▌        ▀██▄▂    ▂▄██   ██    ▝█▙▁   ▁▟█▘  ██  ▝██▄  ║
║   ▟██▛`          ▂▄███▛          ▔▀████████▀    ██     ▝▜█████▛▘   ██    ▀██ ║
║  ▟▀▔  ▁▄█▄▄▄▄▄█████▛▀▔                                                       ║
║╓▀     ▔▀▀██████▛▀▀▔              C O M M A N D   L I N E   I N T E R F A C E ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

A command-line interface for Grok models that reads, writes, and edits files directly on your filesystem.

## Why a CLI?

Browser-based AI interfaces cannot access your local files. This CLI can. It operates directly in your project directory, creating, modifying, and validating files as you describe them in plain language.

**File Operations**
- Create files from natural language descriptions ("write a Python script that...")
- Edit existing files with automatic diff preview
- Read and analyze any file in your project

**Built-in Validation**

Files are validated before saving. Syntax errors are caught and can be corrected automatically:

| File Type | Validation |
|-----------|------------|
| Python (.py) | Syntax check + linting via ruff |
| JSON (.json) | Parse validation |
| YAML (.yaml) | Parse validation |
| TOML (.toml) | Parse validation |
| LaTeX (.tex) | chktex/pdflatex + environment matching |
| JavaScript (.js) | Node.js syntax check |

**Workflow**

```
You: "Create a Python script that calculates fibonacci numbers"
      ↓
CLI: Shows preview with syntax highlighting
      ↓
CLI: Validates Python syntax
      ↓
You: Approve, edit filename, or cancel
      ↓
CLI: Writes file to disk
```

## Design Principles

- **Direct file access**: Read, write, and edit files in your project directory
- **Validation before save**: Catch syntax errors before they reach disk
- **Safety by default**: Preview all changes, sandboxed to launch directory
- **Natural language**: No commands to memorize for file operations
- **Progressive automation**: Interactive prompts, or `-y` flag for scripts

## Installation

### Requirements

- Python ^3.11
- Poetry (recommended) or pip

### Install with Poetry

```bash
# Clone repository
git clone https://github.com/yourusername/grok-cli.git
cd grok-cli

# Install dependencies
poetry install

# Run
poetry run grok
```

### Install with pip

```bash
pip install grok-cli
```

## Quick Start

### 1. Set your API key

Get your API key from [console.x.ai](https://console.x.ai) and set it:

```bash
export XAI_API_KEY=your_key_here
```

Add to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### 2. Run the CLI

```bash
grok
```

### 3. Just type naturally

```
grok> What is a binary search algorithm?

grok> Create a Python script that implements binary search

grok> Read main.py and explain what it does

grok> Add error handling to utils.py

grok> /help
```

The assistant can:
- **Answer questions** - Just ask anything
- **Create files** - "Create a Python script that..." (confirms before writing)
- **Read files** - "Read config.py and explain..."
- **Edit files** - "Add type hints to utils.py" (shows diff, confirms before applying)

## Features

### Natural Language Interaction

No rigid command syntax. Just describe what you want:

```
grok> explain async/await in Python
grok> create a REST API client for the GitHub API
grok> what does the function on line 42 of main.py do?
grok> refactor the User class to use dataclasses
```

### Slash Commands

Utility commands start with `/`:

| Command | Description |
|---------|-------------|
| `/help [topic]` | Show help (topics: tools, slash, confirm) |
| `/model <name>` | Switch to a different model |
| `/models` | List available models |
| `/cost` | Show token usage dashboard |
| `/clear` | Clear conversation history |
| `/history` | Show conversation history |
| `/y`, `/yes` | Enable auto-confirm (skip prompts) |
| `/n`, `/no` | Disable auto-confirm |
| `/plugins` | List loaded plugins |
| `/exit`, `/quit` | Exit the CLI |

### Shell Commands

Built-in sandboxed shell commands (pure Python, no subprocess):

```bash
ls, ll, cd, pwd, cat, head, tail, mkdir -p, tree, cp, mv, rm
```

### File Operation Safety

- **Preview before write**: See exactly what will be created/changed
- **Confirmation required**: Must approve file operations (unless `-y` flag)
- **Large file warning**: Warns when previewing files >100 lines
- **Diff preview for edits**: See changes before applying

```bash
# Auto-confirm all file operations
grok -y

# Or toggle in session
grok> /y    # Enable auto-confirm
grok> /n    # Disable auto-confirm
```

### Filesystem Sandbox

- All operations restricted to the directory where you launched `grok`
- Cannot access files outside your project directory
- This cannot be disabled - safety is mandatory

## Configuration

### Storage Locations

**Global (user preferences):** `~/.grok/`
```
~/.grok/
├── config.toml     # User configuration
├── plugins/        # Custom plugins
└── cache/          # API response cache
```

**Project-local (per-project data):** `.grok/` in your project directory
```
your-project/.grok/
├── sessions/       # Saved conversations (.toon files)
├── history         # Command history
└── context.toon    # Current session context
```

### Config File

Default config at `~/.grok/config.toml`:

```toml
default_model = "grok41_fast"
auto_compress = "smart"      # always | smart | never
auto_yes = false             # true → skip file operation prompts
colour = true
lean_mode = false            # true → minimal comments in generated code
budget_monthly = 0.0         # 0 = disabled
web_daily_quota = 100000     # tokens via web plugin
```

## Models

Available models (use `/models` to list, `/model <name>` to switch):

- `grok41_fast` - Default (non-reasoning, fastest, cheapest)
- `grok41_heavy` - Reasoning model
- `grok4_fast` - Grok 4 fast
- `grok4_reasoning` - Grok 4 with reasoning
- `grok_code` - Code-optimized
- `grok4` - Grok 4 base
- `grok2_image` - Image understanding

## Command Line Options

```bash
grok                    # Start interactive mode
grok -y                 # Start with auto-confirm enabled
grok --help             # Show help
```

## Development

### Run tests

```bash
poetry run pytest
```

### Code quality

```bash
poetry run black grok_cli/  # Format
poetry run ruff grok_cli/   # Lint
poetry run mypy grok_cli/   # Type check
```

### Build

```bash
poetry build
```

## Architecture

### Directory Structure

```
grok_cli/
├── main.py           # Typer app entrypoint
├── repl.py           # Interactive REPL
├── agent.py          # Conversational agent with tool-use
├── tools.py          # File operation tools (read/write/edit)
├── slash_commands.py # Slash command handlers
├── config.py         # TOML handling
├── session.py        # TOON format + compression
├── sandbox.py        # Filesystem safety
├── plugins.py        # Auto-discovery
├── providers/        # API backends
├── ui/               # Prompt, colors, banner
├── cache.py          # Response caching
├── models.py         # Model mapping
└── commands/         # Legacy command implementations
```

## License

BSD-3-Clause License

Copyright (c) 2025, Sirius T. Bontea

## Support

- Issues: GitHub Issues
- Documentation: `/help` in the CLI
