# Grok CLI

```text
╔══════════════════════════════════════════════════════════════════════════════╗ 
║           ,╓▄▄,,        ▄`                                                   ║
║      ,▄███████████▀  ,██                                                     ║
║    ,████▀          ,███▌          ,▄██████▄                        ██        ║
║   ╓███           ╓█████▌        ,███`    ▀██▌                      ██        ║
║  ┌███          ▄█▀  ╙███        ██▌        ╙╙   ╓█████  ▄██████    ██    ▄██ ║
║  ╟██         ▄▀      ███       ╞██     ▄▄▄▄▄▄╕  ██    ┌██▀    ██▌  ██  ╓██Γ  ║
║  ▐██▌      ⌐         ███       └██         ██▌  ██    ╫█▌     ▐██  ██x███    ║
║   ███µ              ███▌        ▀██╖      ▄██   ██    ╙██     ███  ██  ╙██▄  ║
║   ▐███`           ▄███▀           ▀████████▀    ██     ╙███████▀   ██    ▀██ ║
║  █▀   ,▄█▄▄▄▄▄█████▀                                                         ║
║╓▀     `▀▀██████▀▀                C O M M A N D   L I N E   I N T E R F A C E ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

A lean, safe, token-efficient command-line interface for Grok models.

## Design Philosophy

- **Unix philosophy**: Do one thing well, compose via pipes and plugins
- **Safety by default**: Sandbox to launch directory, never silently overwrite files
- **Token-ruthless**: TOON format achieves 40-60% token savings vs JSON in prompts
- **Human-first config**: TOML for user settings (supports comments)
- **Progressive automation**: Interactive first, `-y/--yes` for automation
- **Zero hidden state**: No per-project dotfiles or init commands
- **Extensibility via plugins**: Core stays tiny, optional features in `~/.grok/plugins/`

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
# Enter interactive REPL mode
grok

# Or run commands directly
grok create py "binary search algorithm"
grok edit utils.py "add type hints"
grok ask "explain async/await in Python"
```

## Features

### Interactive REPL

- Full arrow key history navigation
- Ctrl+R reverse search
- Zsh-style context-aware tab completion
- Custom prompt showing model, cwd, and git branch

### Built-in Sandboxed Shell

Pure Python implementations (no subprocess, works on all platforms):

```bash
ls, ll, cd, pwd, cat, head, tail, mkdir -p, tree, cp, mv, rm
```

**Sandbox enforcement:**
- All operations restricted to the directory where you launched `grok`
- Cannot `cd` or access files outside your project directory
- Safe by default - no accidental system-wide file operations

### Core Commands

- `grok create <type> <description>` - Generate files with smart naming
- `grok edit <file> <instruction>` - Modify files with diff preview
- `grok ask <question>` - General queries without file access
- `grok heavy <task>` - Parallel agents + meta-resolver for complex tasks
- `grok resume` - Continue last session
- `grok model <name>` / `grok models` - Switch/list models
- `grok cost` - Token and money dashboard
- `grok plugins` - List loaded plugins
- `grok help [topic]` - Complete documentation

### Safety Features

- **Filesystem sandbox**: All operations restricted to the directory where `grok` was launched
  - CLI always starts in your project directory (where you ran `grok`)
  - Cannot access files outside the launch directory by default
  - `cd` and file operations are locked to the launch directory tree
- **Overwrite protection**: Confirmation required for file modifications
- **No auto-web-access**: Web plugin requires explicit user commands
- `--dangerously-allow-entire-fs`: Escape sandbox (requires typing "YES" in all caps)
  - Displays warning with current sandbox location
  - Working directory remains at launch location
  - Only disables path restrictions, doesn't change your location

### TOON Format

Custom format for 40-60% token savings vs JSON:

```toon
goal: build fast lean Grok CLI
decisions: Poetry,TOON,cwd sandbox,no SQLite
cwd: /home/user/projects/grok-cli
files: +src/new.py,-old.txt
open: implement edit command
```

- No quotes (tokens saved)
- Flat key:value structure
- Comma-lists for arrays
- Deterministic (sorted keys)

### Session Management

- Automatic context tracking with TOON compression
- Smart compression when >12k tokens
- Files hash detection for workspace changes
- Session history at `~/.grok/sessions/`

### Plugin System

Auto-discovered from `~/.grok/plugins/*.py`:

```python
# Example plugin: ~/.grok/plugins/my_plugin.py
from grok_cli.plugins import register_command

def my_command():
    print("Hello from plugin!")

def register():
    register_command("hello", my_command, "Say hello")
```

Instantly available in help, tab completion, and `grok plugins`.

### Caching

- SHA256-hashed request/response cache
- Automatic pruning (>30 days or >500 MB)
- Location: `~/.grok/cache/`

## Configuration

Default config created at `~/.grok/config.toml`:

```toml
default_model = "grok41_fast"
auto_compress = "smart"      # always | smart | never
auto_yes = false
colour = true
lean_mode = false            # true → minimal comments in generated code
budget_monthly = 0.0         # 0 = disabled
web_daily_quota = 100000     # tokens via web plugin
```

Environment variable overrides:
- `GROK_LEAN=1` - Enable lean mode

## Models

Available models:

- `grok41_fast` - Default (non-reasoning, fastest, cheapest)
- `grok41_heavy` - Reasoning model (enables parallel agents)
- `grok4_fast` - Grok 4 fast
- `grok4_reasoning` - Grok 4 with reasoning
- `grok_code` - Code-optimized
- `grok4` - Grok 4 base
- `grok2_image` - Image understanding

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

See `Grok_CLI_Blueprint_v1.md` for complete technical specifications.

### Key Design Decisions

1. **TOON over JSON** - Custom format for maximum token efficiency
2. **TOML for config** - Human-readable with comments
3. **Pure Python shell** - No subprocess, cross-platform safety
4. **Plugin-based extensibility** - Core stays minimal
5. **Session compression** - Smart context management
6. **Strict sandbox** - Safety by default

### Directory Structure

```
grok_cli/
├── main.py          # Typer app + REPL entrypoint
├── config.py        # TOML handling
├── session.py       # TOON format + compression
├── sandbox.py       # Filesystem safety
├── plugins.py       # Auto-discovery
├── providers/       # API backends
├── ui/              # Prompt, colors, banner
├── cache.py         # Response caching
├── models.py        # Model mapping
└── commands/        # Command implementations
```

## License

BSD-3-Clause License

Copyright (c) 2025, Sirius T. Bontea

## Contributing

### Design Philosophy
The Grok CLI design philosophy is built on four unwavering principles: lean, safe, discoverable, and token-efficient. Following Unix philosophy, it does one thing well and composes via pipes and plugins, keeping the core minimal while extensibility lives in ~/.grok/plugins/. Safety is paramount—operations are sandboxed to the launch directory by default, file overwrites require confirmation, and escaping the sandbox demands typing "YES" explicitly. Token efficiency is achieved through TOON format (30-60% savings vs JSON) for all model communications, while human-facing configuration uses TOML for readability and comments. The CLI embraces verbose, self-documenting code by default with an optional lean mode for power users, follows progressive automation (interactive-first, then --yes flag), and maintains zero hidden state with no per-project dotfiles or init commands required—everything is transparent, inspectable, and diffable in ~/.grok/.

- Grok CLI is designed to be extensible via plugins.
- Contribute with a pull request in the CURRENT branch for testing and evaluation, and integration.

## Support

- Issues: GitHub Issues
- Documentation: `grok help`
