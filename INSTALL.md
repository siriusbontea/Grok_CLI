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
poetry run grok
```

## Usage

### Natural Language (Default)

Just type what you want:

```
grok> What is Python?
grok> Create a hello world script in Python
grok> Read main.py and summarize it
grok> Add docstrings to utils.py
```

### Slash Commands

```
grok> /help              # Show help
grok> /models            # List available models
grok> /model grok41_heavy # Switch model
grok> /cost              # Show token usage
grok> /y                 # Enable auto-confirm
grok> /exit              # Exit
```

### Shell Commands

```
grok> ls                 # List files
grok> cd src             # Change directory
grok> cat README.md      # View file
grok> pwd                # Print working directory
```

### Command Line Options

```bash
# Start with auto-confirm (skip file operation prompts)
poetry run grok -y
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
auto_yes = false             # true → skip file operation prompts
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
└── plugins/*.py             # Custom plugins
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
Solution: The CLI is sandboxed to the directory where you launched it. This is a safety feature and cannot be disabled. Navigate to the directory you want to work in, then run `grok` from there.

## Next Steps

1. Read `README.md` for detailed documentation
2. Type `/help` in the CLI for interactive help
3. Create plugins in `~/.grok/plugins/`

## Support

- Issues: Create a GitHub issue
- Documentation: Type `/help` in the CLI
