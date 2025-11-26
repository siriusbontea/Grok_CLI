# Grok CLI – Complete Build Blueprint v1.0 (FINAL – LOCKED)

**Date locked:** November 22, 2025  
**Version:** 1.0  
**Purpose:** This document is the single, exhaustive, unambiguous source of truth for the design, architecture, and implementation of the Grok CLI. No feature, behaviour, or technical choice may deviate from what is written here without formally updating this blueprint first.

## 1. Core Design Philosophy

The CLI must remain lean, safe, discoverable, and token-efficient at all costs.

- Unix philosophy: do one thing well, compose via pipes and plugins.
- Safety by default: sandbox to the directory where the CLI was launched; never silently overwrite files; never allow escape from cwd without explicit, typed confirmation.
- Token-ruthless: anything that ever crosses the wire to any model must be in TOON format (30-60 % token savings, no quotes on keys, minimal delimiters).
- Human-first configuration: TOML only for user-editable settings (supports comments and hierarchy).
- Verbose, self-documenting code is the default; a global `lean_mode = true` or `GROK_LEAN=1` flag strips non-essential comments for power users who explicitly want minimalism.
- Progressive automation: interactive and safe first, one-flag automation second (`-y` / `--yes`).
- No hidden state in repositories: zero per-project dotfiles or init commands required.
- Extensibility via plugins only: core stays tiny; everything optional lives in `~/.grok/plugins/`.

## 2. Runtime Data Locations (exact)

```text
~/.grok/
├── config.toml              # user preferences, created on first run
├── cache/<sha256>.json      # request → response, pruned >30 days or >500 MB
├── sessions/
│   ├── 2025-11-22T14:30.toon # versioned context snapshots in TOON
│   └── current → symlink     # points to the active session
└── plugins/*.py            # auto-discovered on every launch
```

## 3. Data Format Rules (non-negotiable)

```text
| Data type                     | Format | Reason |
|-------------------------------|--------|--------|
| Prompt/context sent to model  | TOON   | Minimal token usage |
| User configuration            | TOML   | Human-readable, supports comments |
| API cache                     | JSON (hashed filenames) | Native API format |
| Session history & context     | .toon files + current symlink | Versioned, inspectable, diffable |

Example TOON snippet (what is actually sent to the model):

```toon
goal:build fast lean Grok CLI
decisions:Poetry,TOON,cwd sandbox,no SQLite,verbose comments default
cwd:/home/user/projects/grok-cli
files_hash:ab4f2...
files:+src/new.py,-old.txt
open:implement edit command
last:user:add zsh tab completion
```

## 4. Exact Dependencies (pyproject.toml)

```toml
[tool.poetry]
name = "grok-cli"
version = "1.0.0"
description = "Lean, safe command-line interface for Grok models"
authors = ["Sirius <your-email>"]

[tool.poetry.dependencies]
python = "^3.11"
typer = {extras = ["all"], version = "^0.12"}
rich = "^13.8"
prompt-toolkit = "^3.0"
httpx = "^0.27"
pydantic = "^2.9"
tomlkit = "^0.13"
trafilatura = "^1.11"   # only used in official web plugin

[tool.poetry.scripts]
grok = "grok_cli.main:app"

## 5. Source Layout (must match exactly)

```text
grok_cli/
├── __init__.py
├── main.py          # Typer app + prompt_toolkit REPL entrypoint
├── config.py        # TOML handling + defaults
├── session.py       # TOON load/save, client-side compression, files_hash tracking
├── sandbox.py       # cwd enforcement + --dangerously-allow-entire-fs with typed "YES"
├── plugins.py       # auto-discovery + register() protocol
├── providers/
│   ├── base.py
│   └── grok.py      # official Grok API implementation only
├── ui/              # prompt, colours, spinner, welcome banner, status line
├── cache.py
├── models.py        # model selection & switching
└── commands/
    ├── create.py
    ├── edit.py
    ├── shell.py     # ls, ll, cd, pwd, cat, head, tail, mkdir -p, tree, etc.
    └── heavy.py     # parallel agents + meta-resolver
```

## 6. Implementation Order (strict sequence – do not skip or reorder)

1. Interactive REPL with prompt_toolkit (arrow keys, Ctrl+R, full Zsh-style context-aware tab completion)
2. Prompt line: `┌─ grok  [model]  [cwd ~ truncated]  ([git branch±]) \n└─➤ `
3. Built-in sandboxed shell commands: `ls`, `ll`, `cd`, `pwd`, `cat`, `head`, `tail`, `mkdir -p`, `tree`, `cp`, `mv`, `rm`
4. Strict cwd sandbox + overwrite protection + `--dangerously-allow-entire-fs` requiring typed "YES"
5. config.toml loading + first-run welcome banner + live token/cost/status line
6. TOON session handling with client-side rule-based compression + files_hash change detection
7. Plugin system with instant visibility in help, tab completion, and `grok plugins`
8. Model switching (`grok model …`, `grok models`) – Grok models + plugin-provided backends
9. `grok create <type> <description>` with smart filename suggestion + overwrite protection
10. `grok edit <file> <instruction>` with coloured diff preview + confirmation
11. Parallel agents + meta-resolver under `grok heavy …` or when heavy model selected
12. Complete baked-in help system (`grok help [topic]`) – this is the primary documentation

## 7. Default config.toml (created on first run)

```toml
default_model = "grok41_fast"
auto_compress = "smart"      # always | smart | never
auto_yes = false
colour = true
lean_mode = false            # true → minimal comments in generated code
budget_monthly = 0.0         # 0 = disabled
web_daily_quota = 100000     # tokens via web plugin, 0 = disabled
```

## 8. Code Style Requirements (mandatory)

- Every public function/class has a full docstring.
- Every non-trivial block has inline comments explaining intent.
- Default output is verbose and self-documenting.
- `lean_mode = true` or `GROK_LEAN=1` removes non-essential comments at generation time.
- The `lean_mode` option is documented in `grok help config`.

## 9. Project & File Awareness (automatic, no init command)

- On every launch/resume, record absolute cwd and compute files_hash (sha256 of sorted file list, ignoring .git, **pycache**, node_modules, etc.).
- If cwd or files_hash differs from stored session → automatically inform model with compact tree/diff and update hash.
- Model is always aware of current directory contents without wasting tokens on unchanged sessions.

## 10. Web Access (only acceptable implementation)

- Exclusively as official plugin `tool_web.py` (not in core).
- Commands: `grok web search <query>` → pick results → `grok web open <url>`
- Always cleaned with trafilatura, preview + token count shown, confirmation required, daily quota enforced.
- No agent may ever call web automatically.

11. Final Command Set (locked – no additions)

- `grok create …`      – intelligent file generation
- `grok edit …`        – in-place modification with diff
- `grok ask …`         – general query, no file access
- `grok heavy …`       – force parallel agents + meta-resolver
- `grok resume`        – continue last session
- `grok model …` / `grok models` – switch/list models
- `grok cost`          – token/money dashboard
- `grok plugins`       – list loaded plugins
- `grok help [topic]`  – complete built-in documentation
- Shell commands: `ls`, `ll`, `cd`, `pwd`, `cat`, `head`, `tail`, `mkdir`, `tree`, etc.
