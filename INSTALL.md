# Installation Guide

## Quick Start

### 1. Install Poetry (if not installed)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Dependencies

```bash
cd grok-cli
poetry install
```

### 3. Set Your API Key

Get your API key from [console.x.ai](https://console.x.ai) and set it:

```bash
export XAI_API_KEY=your_key_here
```

Add to `~/.bashrc` or `~/.zshrc` to make it permanent:

```bash
echo 'export XAI_API_KEY=your_key_here' >> ~/.zshrc
```

### 4. Run the CLI

```bash
# Enter REPL mode
poetry run grok

# Or run commands directly
poetry run grok ask "explain async/await in Python"
poetry run grok create py "binary search algorithm"
poetry run grok help
```

## Running Tests

```bash
poetry run pytest
poetry run pytest tests/test_toon.py -v
poetry run pytest tests/test_sandbox.py -v
```

## Development Commands

```bash
# Format code
poetry run black grok_cli/

# Lint code
poetry run ruff grok_cli/

# Type check
poetry run mypy grok_cli/
```

## Configuration

On first run, a config file is created at `~/.grok/config.toml`:

```toml
default_model = "grok41_fast"
auto_compress = "smart"      # always | smart | never
auto_yes = false
colour = true
lean_mode = false            # true → minimal comments in generated code
budget_monthly = 0.0         # 0 = disabled
web_daily_quota = 100000     # tokens via web plugin
```

## Directory Structure

```
~/.grok/
├── config.toml              # Configuration
├── cache/<sha256>.json      # API response cache
├── sessions/
│   ├── 2025-11-22T14:30.toon
│   └── current → symlink    # Current session
└── plugins/*.py            # Custom plugins
```

## Available Commands

**Core:**
- `ask <question>` - General queries
- `create <type> <description>` - Generate files
- `edit <file> <instruction>` - Modify files with diff
- `heavy <task>` - Complex tasks (3 agents + meta-resolver)

**Utility:**
- `model <name>` - Switch model
- `models` - List available models
- `plugins` - List loaded plugins
- `resume` - Continue last session
- `cost` - Token usage dashboard
- `help [topic]` - Documentation

**Shell:**
- `ls, ll, cd, pwd, cat, head, tail, mkdir, tree, cp, mv, rm`

## Example Usage

```bash
# Start REPL
poetry run grok

# In REPL:
help
models
model grok41_heavy
create py "binary search with type hints"
edit binary_search.py "add docstrings"
ask "explain time complexity"
ls
pwd
exit
```

## Troubleshooting

**API key not set:**
```
Error: XAI_API_KEY not set
```
Solution: Set the environment variable as shown in step 3.

**Module not found:**
```
ModuleNotFoundError: No module named 'grok_cli'
```
Solution: Run `poetry install` first.

**Permission denied:**
```
Error: Cannot access path outside launch directory
```
Solution: The CLI is sandboxed by default. Use `--dangerously-allow-entire-fs` to disable (requires typing "YES").

## Next Steps

1. Read `README.md` for detailed documentation
2. Check `Grok_CLI_Blueprint_v1.md` for complete architecture
3. Create plugins in `~/.grok/plugins/`

## Support

- Issues: Create a GitHub issue
- Documentation: Run `grok help`
- Blueprint: See `Grok_CLI_Blueprint_v1.md`
