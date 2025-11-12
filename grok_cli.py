#!/usr/bin/env python3

# BSD 3-Clause License
# 
# Copyright (c) 2025, Sirius T. Bontea
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# This script implements the Grok CLI, an interactive coding assistant powered by xAI's Grok models.
# It provides a terminal-based interface for chatting with AI, managing projects, and automating dev tasks.
import os
import re
import readline
import subprocess
import shlex
import importlib.util
import difflib
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from openai import OpenAI
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import WordCompleter, PathCompleter, Completer

# === Core setup ===
console = Console()
client = OpenAI(api_key=os.getenv("XAI_KEY"), base_url="https://api.x.ai/v1")
MODEL = "grok-4"

# Conversation history starting with system prompt.
# This defines the AI's persona, available models, commands, and guidelines for file edits/tools.
# Interacts with the main chat loop: Appended to every API call for context.
# Uses triple-quoted string for robustness and to prevent concatenation errors during copy/paste.
HISTORY = [{
    "role": "system",
    "content": """You are Grok-4, a powerful general-purpose assistant in CLI mode. 
Models: grok-4, grok-code-fast-1. 
Commands: model, preview, dockerize, review, debug, help, cd, ls, mkdir, touch, rm, mv, cp, 
venv (create/activate), pip install, requirements generate, git (init/status/add/push), 
clear, history, run, test, agent (list/add/help/call), fs (scan/diff), git (status/branch/pr), readme (generate), quit/exit. 
For precise file edits, use: ```artifact
This creates or updates the exact file. Use relative paths. 
For quick scripts, use regular ```python\ncode\n```. 
Agents must use ```artifact``` for multi-file coordination. 
To use agents, output: ```tool fs scan``` or ```tool git status```. 
CLI will execute and return results. Use for file scanning, git status, linting, etc. before planning."""
}]

# Language → extension map
EXTENSION_MAP = {
    "python": ".py", "markdown": ".md", "text": ".txt", "json": ".json",
    "yaml": ".yaml", "html": ".html", "css": ".css", "js": ".js",
    "bash": ".sh", "latex": ".tex", "": ".txt"
}

# Artifact / tool block delimiters
ARTIFACT_START = "```artifact"
ARTIFACT_END = "```"
TOOL_CALL_START = "```tool"
TOOL_CALL_END = "```"

# Security: restrict all file ops to the directory where CLI was started
INITIAL_CWD = os.path.realpath(os.getcwd())

# Agent registry
AGENTS = {}

# Persistent readline history
HISTORY_FILE = Path.home() / ".grok_cli_history"
if HISTORY_FILE.exists():
    try:
        readline.read_history_file(str(HISTORY_FILE))
    except Exception:
        pass

# Auto-activate venv if exists (Priority 3 polish)
# This silently sources .venv on start for seamless env use in run_command (e.g., pip, preview).
# Interacts with run_command: Prefixes cmds with activation if venv active. Forgiving: No-op if no venv.
VENV_ACTIVE = False
venv_path = Path(".venv")
if venv_path.exists():
    os.environ["VIRTUAL_ENV"] = str(venv_path.resolve())
    os.environ["PATH"] = f"{venv_path / 'bin'}:{os.environ['PATH']}"
    VENV_ACTIVE = True

# === Helper functions ===
def get_python() -> Path:
    venv_python = Path(".venv/bin/python") if VENV_ACTIVE else Path("python3")
    return venv_python if venv_python.exists() else Path("python3")

def run_command(cmd: str, bg: bool = False, capture_output: bool = True) -> subprocess.CompletedProcess | bool:
    if VENV_ACTIVE:
        cmd = f". .venv/bin/activate && {cmd}"
    try:
        args = shlex.split(cmd)
        if bg:
            subprocess.Popen(args)
            console.print(f"[green]Started: {' '.join(args)}[/]")
            return True
        kwargs = {'capture_output': capture_output, 'text': True}
        result = subprocess.run(args, **kwargs)
        if capture_output:
            if result.stdout:
                console.print(f"[dim]{result.stdout}[/]")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/]")
        return result if capture_output else result.returncode == 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        return False

def get_context_percentage() -> tuple[str, int]:
    total_tokens = sum(len(m["content"]) for m in HISTORY) // 4
    max_context = 128000
    percent = int((total_tokens / max_context) * 100)
    color = "green" if percent <= 70 else "yellow" if percent <= 85 else "red"
    return color, percent

def get_formatted_cwd() -> str:
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd == home:
        return "~"
    if cwd.startswith(home):
        return "~" + cwd[len(home):].replace("\\", "/")
    return cwd.replace("\\", "/")

color_map = {'green': 'ansigreen', 'yellow': 'ansiyellow', 'red': 'ansired'}

def extract_suggested_filename(user_input: str) -> str | None:
    patterns = [
        r"(?:create|make|generate|write|add)\s+(?:a|the)?\s+file\s+(?:called|named)?\s*([^\s\"';]+?\.\w+)",
        r"(?:populate|fill|update)\s+([^\s\"';]+?\.\w+)\s+(?:with|using)",
        r"file\s+(?:called|named)\s+([^\s\"';]+?\.\w+)"
    ]
    for p in patterns:
        m = re.search(p, user_input, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

# Custom style for secondary prompts
ask_style = PTStyle.from_dict({
    'prompt': 'ansigreen',
    'warning': 'ansiyellow',
})

def ask(prompt_text: str, default: str = "", completer: Completer = None, is_warning: bool = False) -> str:
    """Custom immutable prompt: Cursor stays right of text, preventing visual erasure on backspace."""
    cls = 'warning' if is_warning else 'prompt'
    return prompt(
        [(f'class:{cls}', prompt_text + ' ')],
        style=ask_style,
        default=default,
        completer=completer,
    ).strip()

def handle_artifacts(reply: str, user_input: str) -> None:
    """Unified extraction & saving of code blocks and artifacts."""
    code_matches = re.findall(r"```(\w*)\n(.*?)\n```", reply, re.DOTALL)
    artifact_matches = re.findall(rf"{ARTIFACT_START}\s+([^\n]+)\n(.*?)\n{ARTIFACT_END}", reply, re.DOTALL)

    # Normalize artifacts to same tuple format (lang, code, path|None)
    for path, content in artifact_matches:
        lang = Path(path).suffix.lstrip(".") or "text"
        code_matches.append((lang, content.strip() + "\n", path.strip()))

    for idx, match in enumerate(code_matches):
        if len(match) == 3:  # artifact
            language, code, target_path = match
            save_path = Path(target_path)
            console.print(f"[bold cyan]Artifact → {save_path}[/]")
        else:
            language, code = match
            ext = EXTENSION_MAP.get(language, ".txt")
            suggested = extract_suggested_filename(user_input) if idx == 0 else None
            default = suggested or f"generated_{idx}{ext}"
            save = ask(f"Save {language or 'file'} #{idx+1}? (y/n/[filename])", default="y")
            if save.lower() in {"n", "no"}:
                continue
            path_input = save if save.lower() not in {"y", "yes"} else ask("Save as", default=default, completer=PathCompleter())
            save_path = Path(path_input)

        # Security & write
        full = save_path.resolve()
        if not str(full).startswith(INITIAL_CWD):
            console.print("[red]Blocked: outside project[/]")
            continue
        if full.exists() and ask(f"{full} exists. Overwrite? (y/n)", default="n", is_warning=True).lower() != "y":
            continue
        full.parent.mkdir(parents=True, exist_ok=True)
        try:
            full.write_text(code)
        except UnicodeEncodeError:
            full.write_bytes(code.encode('utf-8', errors='replace'))
        console.print(f"[green]Saved: {full}[/]")

        # Auto-run / test / commit chain
        if full.suffix == ".py" and ask("Run now? (y/n)", default="y", is_warning=True) == "y":
            run_command(f"{get_python()} {full}")
        if (Path("tests").exists() or any(p.name.startswith("test_") for p in Path(".").iterdir())):
            if ask("Run tests? (y/n)", default="y", is_warning=True) == "y":
                run_command("pytest -q")
        if Path(".git").exists() and ask("Git commit? (y/n)", default="y", is_warning=True) == "y":
            summary = reply.split("\n")[0][:50]
            safe_msg = shlex.quote("Grok: " + summary)
            run_command(f"git add . && git commit -m {safe_msg}")

def _query_ai(prompt: str, user_input: str) -> str:
    """Helper to query AI, print reply, handle artifacts. Used for commands/agents."""
    HISTORY.append({"role": "user", "content": prompt})
    with console.status("[bold green]Grok thinking..."):
        resp = client.chat.completions.create(
            model=MODEL, messages=HISTORY, temperature=0.3, max_tokens=4096
        )
    reply = resp.choices[0].message.content
    console.print(Markdown(reply))
    HISTORY.append({"role": "assistant", "content": reply})
    handle_artifacts(reply, user_input)
    return reply

# === Agents ===
class Agent:
    def __init__(self, name: str):
        self.name = name
    def handle_command(self, subcmd: str):
        raise NotImplementedError

class FileSystemAgent(Agent):
    """File system operations with AI integration."""
    def handle_command(self, subcmd: str):
        parts = subcmd.split()
        if not parts:
            console.print("[red]Usage: fs scan | fs diff [path][/]")
            return None

        cmd = parts[0]
        if cmd == "scan":
            structure = self._scan_project()
            console.print(Markdown(f"## Project Scan\n```\n{structure}\n```"))
            if ask("Feed scan to AI? (y/n)", default="y", is_warning=True) == "y":
                HISTORY.append({"role": "user", "content": f"Project scan:\n{structure}"})
                self._query_ai("Analyze this project structure and suggest improvements.")
            return structure

        if cmd == "diff" and len(parts) > 1:
            file = " ".join(parts[1:])
            if not Path(file).exists():
                console.print("[red]File not found[/]")
                return None
            code = Path(file).read_text()
            reply = self._query_ai(f"Generate diff suggestions for this code:\n{code[:10000]}")
            # Colored diffs (Priority 3 polish): If reply has diff format, use difflib + rich for highlighting.
            # Interacts with AI: Post-processes reply for visual UX; no new deps.
            if "diff" in reply.lower():
                lines = reply.splitlines()
                diff_start = next((i for i, line in enumerate(lines) if line.startswith("diff")), None)
                if diff_start is not None:
                    diff_text = "\n".join(lines[diff_start:])
                    highlighted = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
                    console.print(highlighted)
            return reply

        console.print("[red]Supported: scan, diff [path][/]")
        return None

    def _scan_project(self) -> str:
        tree = []
        for root, dirs, files in os.walk("."):
            level = root.count(os.sep) - ".".count(os.sep)
            indent = " " * 4 * level
            tree.append(f"{indent}{os.path.basename(root)}/")
            subindent = " " * 4 * (level + 1)
            for f in files:
                tree.append(f"{subindent}{f}")
        return "\n".join(tree)

    def _query_ai(self, prompt: str) -> str:
        return _query_ai(prompt, "fs command")

class GitAgent(Agent):
    """Git operations."""
    def handle_command(self, subcmd: str):
        parts = subcmd.split()
        if not parts:
            console.print("[red]Usage: git status | branch | pr [title][/]")
            return None

        cmd = parts[0]
        if cmd == "status":
            out = self._run_git("git status -s")
            if out is None:
                return None
            console.print(Markdown(f"## Git Status\n```\n{out}\n```"))
            return out

        if cmd == "branch":
            cur = self._run_git("git symbolic-ref --short HEAD")
            all_br = self._run_git("git branch --format='%(refname:short)'")
            if cur is None or all_br is None:
                return None
            console.print(Markdown(f"## Current Branch\n* **{cur.strip()}**"))
            console.print(Markdown(f"## All Branches\n```\n{all_br}\n```"))
            return f"Current: {cur.strip()}\nBranches:\n{all_br}"

        if cmd == "pr" and len(parts) >= 2:
            # Check for gh CLI
            gh_check = run_command("gh --version")
            if gh_check.returncode != 0:
                console.print("[yellow]gh CLI not found. Install from https://cli.github.com[/]")
                return None
            title = " ".join(parts[1:]) or ask("PR title", default="Update from Grok", is_warning=True)
            body = ask("PR body (optional)", is_warning=True) or ""
            out = self._run_git(f"gh pr create --title {shlex.quote(title)} --body {shlex.quote(body)}")
            if out:
                console.print(f"[green]{out}[/]")
            return out

        console.print("[red]Supported: status, branch, pr [title][/]")
        return None

    def _run_git(self, cmd: str) -> str | None:
        try:
            res = subprocess.run(shlex.split(cmd), capture_output=True, text=True, cwd=os.getcwd())
            if res.returncode != 0:
                console.print(f"[red]Git error: {res.stderr.strip()}[/]")
                return None
            return res.stdout
        except Exception as e:
            console.print(f"[red]Git failed: {e}[/]")
            return None

class LintAgent(Agent):
    """Code linting with AI fixes (Priority 3). Runs pylint/flake8, feeds issues to AI for artifact patches."""
    def handle_command(self, subcmd: str):
        parts = subcmd.split()
        if not parts:
            console.print("[red]Usage: lint run [file or .][/]")
            return None

        cmd = parts[0]
        if cmd == "run" and len(parts) > 1:
            target = " ".join(parts[1:])
            if not Path(target).exists() and target != ".":
                console.print("[red]Target not found[/]")
                return None

            # Determine linter and check/install
            if target.endswith(".py") or target == ".":
                linter = "pylint"
                install_cmd = "pip install pylint"
            else:
                linter = "flake8"
                install_cmd = "pip install flake8"
            # Check if linter installed
            check = run_command(f"pip show {linter}")
            if check.returncode != 0:
                if ask(f"Install {linter}? (y/n)", default="y") == "y":
                    run_command(install_cmd)
                else:
                    return None

            # Run lint
            lint_cmd = f"{linter} {shlex.quote(target)}"
            lint_out = subprocess.run(shlex.split(lint_cmd), capture_output=True, text=True).stdout
            if lint_out:
                console.print(Markdown(f"## Lint Report\n```\n{lint_out}\n```"))
                if ask("Fix with AI? (y/n)", default="y") == "y":
                    self._query_ai(f"Lint issues:\n{lint_out}\nGenerate fixes for {target}.")
            return lint_out

        console.print("[red]Supported: run [file or .][/]")
        return None

    def _query_ai(self, prompt: str) -> str:
        return _query_ai(prompt, "lint command")

class ReadmeAgent(Agent):
    """Generates robust README.md files based on project changes and files, following industry best practices."""
    def handle_command(self, subcmd: str):
        parts = subcmd.split()
        if not parts:
            console.print("[red]Usage: readme generate[/]")
            return None

        cmd = parts[0]
        if cmd == "generate":
            # Gather project info: structure via fs scan (add fs if needed)
            if "fs" not in AGENTS:
                console.print("[yellow]Adding fs agent for scan...[/]")
                AGENTS["fs"] = FileSystemAgent("fs")
            structure = AGENTS["fs"].handle_command("scan")
            if not structure:
                console.print("[red]Project scan failed.[/]")
                return None

            # Gather recent changes: git log if .git exists
            changes = ""
            if Path(".git").exists():
                if "git" not in AGENTS:
                    console.print("[yellow]Adding git agent for changes...[/]")
                    AGENTS["git"] = GitAgent("git")
                changes_out = AGENTS["git"]._run_git("git log -n 5 --pretty=format:'%h - %s (%an, %ar)'")
                if changes_out:
                    changes = changes_out.strip()

            # Query AI to generate README content
            prompt = f"""Generate a robust README.md for this project, suitable for new users. Follow industry best practices: include sections like Project Title (infer from directory name or main files), Description (infer purpose from files/code), Installation (e.g., venv, pip requirements), Usage (examples from main scripts), Contributing, License.
Project structure:
{structure}

Recent changes (if any):
{changes}

Output the content in ```artifact README.md\n<content>\n``` for auto-saving."""
            reply = self._query_ai(prompt)
            # Ensure artifact handling saves to README.md
            handle_artifacts(reply, "generate README.md")
            return reply

        console.print("[red]Supported: generate[/]")
        return None

    def _query_ai(self, prompt: str) -> str:
        return _query_ai(prompt, "readme generate")

class TestAgent(Agent):
    """Test generation and running with AI integration."""
    def handle_command(self, subcmd: str):
        parts = subcmd.split()
        if not parts:
            console.print("[red]Usage: test generate [file] | test run[/]")
            return None
        cmd = parts[0]
        if cmd == "generate":
            target = parts[1] if len(parts) > 1 else "."
            if target != "." and not Path(target).exists():
                console.print("[red]Target not found.[/]")
                return None
            code = Path(target).read_text() if target != "." else "Full project (use fs scan for details)"
            prompt = f"Generate pytest tests for: {code[:5000]}. Output as ```artifact test_{target if target != '.' else 'main'}.py\n<content>\n```"
            return self._query_ai(prompt)
        if cmd == "run":
            # Assume pytest installed; install if not
            check = run_command("pip show pytest")
            if check.returncode != 0:
                if ask("Install pytest? (y/n)", default="y") == "y":
                    run_command("pip install pytest")
                else:
                    return None
            success = run_command("pytest")
            return "Tests passed." if success else "Tests failed."
        console.print("[red]Supported: generate [file or .], run[/]")
        return None

    def _query_ai(self, prompt: str) -> str:
        return _query_ai(prompt, "test generate")

# === Supported Agents Info (for help discovery) ===
SUPPORTED_AGENTS = {
    "fs": {
        "desc": "File system operations with AI integration (scan/diff with optional AI analysis).",
        "examples": ["fs scan (project tree; optional AI improvements)", "fs diff main.py (AI diff suggestions)"]
    },
    "git": {
        "desc": "Git operations (status, branches, PR creation).",
        "examples": ["git status (show status)", "git branch (list branches)", "git pr \"Fix bug\" (create PR)"]
    },
    "lint": {
        "desc": "Code linting with AI fixes (runs pylint/flake8, suggests patches).",
        "examples": ["lint run main.py (lint file)", "lint run . (lint project)"]
    },
    "readme": {
        "desc": "Generates robust README.md files based on project changes and files.",
        "examples": ["readme generate (scans project and generates README)"]
    },
    "test": {
        "desc": "Test generation and running with AI integration.",
        "examples": ["test generate main.py (generate tests for file)", "test run (run pytest)"]
    },
}

# === Command details for deep help ===
COMMAND_HELP = {
    "model": {
        "desc": "Switch model: `model fast` → grok-code-fast-1, `model best` → grok-4",
        "examples": ["model fast", "model best"]
    },
    "preview": {
        "desc": "Auto-detect and start a web server (FastAPI, Flask, Streamlit, Django)",
        "examples": ["preview"]
    },
    "dockerize": {
        "desc": "Generate Dockerfile + docker-compose.yml and build the image",
        "examples": ["dockerize"]
    },
    "review": {
        "desc": "AI code review of all Python files in the project",
        "examples": ["review"]
    },
    "debug": {
        "desc": "Show model, Python path, cwd, venv, git status",
        "examples": ["debug model"]
    },
    "cd": {
        "desc": "Change directory (restricted to project root and subdirs)",
        "examples": ["cd src", "cd ..", "cd ~"]
    },
    "ls": {"desc": "List files", "examples": ["ls"]},
    "mkdir": {"desc": "Create directory", "examples": ["mkdir new_folder"]},
    "touch": {"desc": "Create empty file", "examples": ["touch app.py"]},
    "rm": {"desc": "Delete file/dir (with confirm)", "examples": ["rm old.txt"]},
    "mv": {"desc": "Move/rename", "examples": ["mv a.txt b.txt"]},
    "cp": {"desc": "Copy", "examples": ["cp src/ dest/"]},
    "venv": {
        "desc": "Create/activate virtual environment",
        "examples": ["venv create", "venv activate"]
    },
    "pip": {
        "desc": "Install package in current venv",
        "examples": ["pip install requests"]
    },
    "requirements": {
        "desc": "Generate requirements.txt from imports",
        "examples": ["requirements generate"]
    },
    "git": {
        "desc": "Git shortcuts (init/status/add/push)",
        "examples": ["git init", "git status", "git add .", "git push"]
    },
    "clear": {"desc": "Clear conversation history", "examples": ["clear"]},
    "history": {"desc": "Show conversation summary", "examples": ["history"]},
    "run": {"desc": "Run Python file", "examples": ["run main.py"]},
    "test": {"desc": "Run pytest or generate tests", "examples": ["test"]},
    "agent": {
        "desc": "Manage agents (fs, git, …)",
        "examples": ["agent list", "agent add fs", "agent call fs scan"]
    },
    "fs": {
        "desc": "File system agent (scan/diff)",
        "examples": ["fs scan", "fs diff app.py"]
    },
    "readme": {
        "desc": "README generation agent (generate)",
        "examples": ["readme generate"]
    },
    "quit": {"desc": "Exit CLI", "examples": ["quit", "exit"]},
}

# === Tab completion ===
class CustomCompleter(Completer):
    def __init__(self):
        self.cmds = WordCompleter([
            'model fast', 'model best', 'preview', 'dockerize', 'review', 'debug model',
            'cd ', 'ls', 'mkdir ', 'touch ', 'rm ', 'mv ', 'cp ',
            'venv create', 'venv activate', 'pip install ', 'requirements generate',
            'git init', 'git status', 'git add ', 'git push',
            'clear', 'history', 'run ', 'test', 'help', 'quit', 'exit',
            'agent list', 'agent add ', 'agent help', 'agent call fs scan',
            'agent call fs diff ', 'agent call git status', 'agent call git branch',
            'agent call git pr ', 'fs scan', 'fs diff ', 'readme generate',
            'agent call readme generate', 'agent add readme', 'agent add test',
            'agent call test generate ', 'agent call test run', 'test generate ',
            'test run'
        ], ignore_case=True)
        self.paths = PathCompleter()

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lower()
        path_triggers = (
            'cd ', 'mkdir ', 'touch ', 'rm ', 'mv ', 'cp ', 'run ', 'git add ',
            'fs diff ', 'agent call fs diff ', 'test generate '
        )
        if any(text.startswith(t) for t in path_triggers):
            return self.paths.get_completions(document, complete_event)
        return self.cmds.get_completions(document, complete_event)

# === Startup UI ===
def display_startup_message() -> None:
    logo = """\
                                █                                                         
                              █                                                           
            ████████        ██                                                            
        ███████████████    ██                                                             
      ██████             ████              ██████                             ███         
     ████              █████            ████████████                          ███         
    ████             ███████           ███        ███                         ███         
   ████            ███   ████         ███                ██████   ████████    ███     ███ 
   ████          ██       ███         ███               ███     ████    ████  ███   ███   
   ███         ██         ███         ███     ████████  ███     ███      ███  ███  ███    
   ████                  ████         ███          ███  ███     ███      ███  ████████    
    ███                  ███           ███        ███   ███     ███      ███  ███   ███   
    █████              █████            ████████████    ███      ████  ████   ███    ███  
    ███              █████                 ███████      ███        ██████     ███      ███
   ██     ███████████████                  C O M M A N D   L I N E   I N T E R F A C E
  █        ███████████                                                                    
█                                          get lastest version on GitHub @siriusbontea
                                                                                            """
    console.print(f"\033[37m{logo}\033[0m")
    console.print("[bold]Type 'help' for commands or 'help <cmd>' for details. For agents, try 'help agent' or 'agent help' to see available options.[/]")  # Enhanced onboarding for agents

# === Main chat loop ===
def chat() -> None:
    global MODEL, HISTORY
    display_startup_message()

    style = PTStyle.from_dict({
        'percentage': 'green',
        'cwd': 'ansiblue',
        'prompt-symbol': 'ansigreen',
    })
    completer = CustomCompleter()

    try:
        while True:
            color, pct = get_context_percentage()
            ansi = color_map[color]
            cwd = get_formatted_cwd()
            msg = [
                ('', '(@ '), (f'fg:{ansi}', f'{pct}%'), ('', ') '),
                ('class:cwd', f'{cwd} '), ('class:prompt-symbol', '❯ ')
            ]
            user = prompt(msg, style=style, completer=completer).strip()
            if not user:
                continue
            if user.lower() in {"quit", "exit"}:
                break

            # --- Deep help ---
            if user.lower() == "help":
                table = Table(title="Grok CLI Commands")
                table.add_column("Command", style="cyan")
                table.add_column("Description")
                for cmd, data in COMMAND_HELP.items():
                    table.add_row(cmd, data["desc"])
                console.print(table)
                continue

            if user.lower().startswith("help "):
                parts = user.split(maxsplit=2)
                cmd = parts[1].lower()
                subcmd = parts[2].lower() if len(parts) > 2 else None
                if cmd in {"agent", "agents"}:  # Alias agents/agent
                    cmd = "agent"
                if cmd in COMMAND_HELP:
                    data = COMMAND_HELP[cmd]
                    if cmd == "agent" and subcmd is None:
                        # Show detailed agent help table for "help agent" to improve new user experience
                        # This aligns with "agent help" output, providing a list of built-in agents,
                        # their descriptions, and usage examples directly, reducing cognitive load
                        # for discovering agent features (principle 2: zero cognitive load).
                        t = Table(title="Supported Agents")
                        t.add_column("Agent", style="cyan")
                        t.add_column("Description")
                        t.add_column("Examples")
                        for name, agent_data in SUPPORTED_AGENTS.items():
                            t.add_row(name, agent_data["desc"], "\n".join(agent_data["examples"]))
                        console.print(t)
                        console.print("[dim]Add with 'agent add <name>'; call with 'agent call <name> <cmd>' or shortcuts like 'fs scan'.[/]")
                    elif cmd == "agent" and subcmd:
                        # Sub-help for specific agents (e.g., help agent fs)
                        if subcmd in SUPPORTED_AGENTS:
                            agent_data = SUPPORTED_AGENTS[subcmd]
                            console.print(f"\n[bold cyan]Agent {subcmd} Details[/]")
                            console.print(agent_data["desc"])
                            if agent_data["examples"]:
                                console.print("[dim]Examples:[/]")
                                for ex in agent_data["examples"]:
                                    console.print(f"  {ex}")
                        else:
                            console.print(f"[red]No such agent: {subcmd}. Supported: {', '.join(SUPPORTED_AGENTS.keys())}[/]")
                    else:
                        console.print(f"[bold cyan]help {cmd}[/]")
                        console.print(data["desc"])
                        if data["examples"]:
                            console.print("[dim]Examples:[/]")
                            for ex in data["examples"]:
                                console.print(f"  {ex}")
                else:
                    console.print(f"[red]No help for '{cmd}'[/]")
                continue

            # --- Agent management ---
            if user.lower().startswith("agent "):
                parts = user.split(maxsplit=3)
                sub = parts[1].lower() if len(parts) > 1 else ""

                if sub == "list":
                    if not AGENTS:
                        console.print("[dim]No agents added. Supported agents: {', '.join(SUPPORTED_AGENTS.keys())}. Try 'agent add fs'[/]")
                    else:
                        t = Table(title="Active Agents")
                        t.add_column("Name"); t.add_column("Description")
                        for n, a in AGENTS.items():
                            t.add_row(n, a.__doc__ or "—")
                        console.print(t)

                elif sub == "add" and len(parts) > 2:
                    name = parts[2].lower()
                    if name in AGENTS:
                        console.print("[yellow]Already added[/]")
                    elif name == "fs":
                        AGENTS["fs"] = FileSystemAgent("fs")
                        console.print("[green]FileSystemAgent added → `fs scan` or `agent call fs …`[/]")
                    elif name == "git":
                        AGENTS["git"] = GitAgent("git")
                        console.print("[green]GitAgent added → `git status` or `agent call git …`[/]")
                    elif name == "lint":
                        AGENTS["lint"] = LintAgent("lint")
                        console.print("[green]LintAgent added → `lint run .` or `agent call lint run [file]`[/]")
                    elif name == "readme":
                        AGENTS["readme"] = ReadmeAgent("readme")
                        console.print("[green]ReadmeAgent added → `readme generate` or `agent call readme …`[/]")
                    elif name == "test":
                        AGENTS["test"] = TestAgent("test")
                        console.print("[green]TestAgent added → `test generate` or `agent call test …`[/]")
                    else:
                        console.print(f"[red]Supported agents: {', '.join(SUPPORTED_AGENTS.keys())}[/]")

                elif sub == "help":
                    t = Table(title="Supported Agents")
                    t.add_column("Agent", style="cyan")
                    t.add_column("Description")
                    t.add_column("Examples")
                    for name, data in SUPPORTED_AGENTS.items():
                        t.add_row(name, data["desc"], "\n".join(data["examples"]))
                    console.print(t)
                    console.print("[dim]Add with 'agent add <name>'; call with 'agent call <name> <cmd>' or shortcuts like 'fs scan'.[/]")

                elif sub == "call" and len(parts) >= 4:
                    agent_name, command = parts[2], " ".join(parts[3:])
                    if agent_name not in AGENTS:
                        console.print(f"[red]Add agent first: agent add {agent_name}[/]")
                        continue
                    console.print(f"[dim]Calling {agent_name} → {command}[/]")
                    result = AGENTS[agent_name].handle_command(command)
                    if result:
                        HISTORY.append({"role": "tool", "content": str(result)})

                else:
                    console.print("[red]agent list | add <name> | help | call <name> <cmd>[/]")
                    console.print("[dim]For available agents, try 'agent help'[/]")
                continue

            # --- Legacy fs shortcut ---
            if user.lower().startswith("fs ") and "fs" in AGENTS:
                AGENTS["fs"].handle_command(user.split(maxsplit=1)[1])
                continue

            # --- Readme shortcut ---
            if user.lower().startswith("readme ") and "readme" in AGENTS:
                AGENTS["readme"].handle_command(user.split(maxsplit=1)[1])
                continue

            # --- Test shortcut ---
            if user.lower().startswith("test ") and "test" in AGENTS:
                AGENTS["test"].handle_command(user.split(maxsplit=1)[1])
                continue

            # --- Model switch ---
            if user.lower() in {"model fast", "model best"}:
                MODEL = "grok-code-fast-1" if "fast" in user else "grok-4"
                console.print(f"[green]Model → {MODEL}[/]")
                continue

            # --- Preview command: Auto-start web dev server ---
            # This section detects common web frameworks (e.g., FastAPI, Flask) via simple file/ import heuristics.
            # It leverages the fs agent for project scan if needed, installs missing deps with user confirmation,
            # and runs the server in background on a fixed port (expandable to check free ports).
            # Interacts with AI: Could be called via tool blocks in future for AI-driven previews.
            if user.lower() == "preview":
                if "fs" not in AGENTS:
                    console.print("[yellow]Adding fs agent for scan...[/]")
                    AGENTS["fs"] = FileSystemAgent("fs")
                scan = AGENTS["fs"].handle_command("scan")
                if not scan:
                    console.print("[red]Project scan failed.[/]")
                    continue

                # Detect framework (simple heuristic: check common files and imports; expandable to more frameworks like Streamlit, Django)
                framework = None
                if Path("main.py").exists() and "fastapi" in Path("main.py").read_text().lower():
                    framework = "fastapi"
                elif Path("app.py").exists() and "flask" in Path("app.py").read_text().lower():
                    framework = "flask"
                # TODO: Add more detections, e.g., "streamlit" in requirements.txt or code

                if not framework:
                    console.print("[yellow]No web framework detected. Try manual run?[/]")
                    continue

                # Install deps if needed (secure: user confirmation; runs in project env)
                if ask("Install missing deps? (y/n)", default="y") == "y":
                    if framework == "fastapi":
                        run_command("pip install fastapi uvicorn")
                    elif framework == "flask":
                        run_command("pip install flask")

                # Run in background (fixed port for simplicity; TODO: Add port availability check)
                port = 8000
                if framework == "fastapi":
                    run_command(f"uvicorn main:app --reload --port {port}", bg=True)
                elif framework == "flask":
                    run_command(f"flask --app app run --debug --port {port}", bg=True)
                console.print(f"[green]{framework.capitalize()} app running at http://localhost:{port}[/]")
                continue

            # --- Dockerize command: Generate Dockerfile/compose and build ---
            if user.lower() == "dockerize":
                if "fs" not in AGENTS:
                    console.print("[yellow]Adding fs agent for scan...[/]")
                    AGENTS["fs"] = FileSystemAgent("fs")
                structure = AGENTS["fs"].handle_command("scan")
                if not structure:
                    console.print("[red]Scan failed.[/]")
                    continue
                prompt = f"Generate Dockerfile and docker-compose.yml for this project. Structure:\n{structure}\nOutput as artifacts: ```artifact Dockerfile\n<content>\n``` and ```artifact docker-compose.yml\n<content>\n```"
                reply = _query_ai(prompt, "dockerize")
                if ask("Build image? (y/n)", default="y") == "y":
                    if run_command("docker build -t grok-project ."):
                        console.print("[green]Image built.[/]")
                    if Path("docker-compose.yml").exists() and ask("Run docker-compose up? (y/n)", default="y") == "y":
                        run_command("docker-compose up -d", bg=True)
                continue

            # --- Run command: Execute Python file ---
            if user.lower().startswith("run "):
                file = user.split(maxsplit=1)[1].strip()
                if not Path(file).exists():
                    console.print("[red]File not found.[/]")
                    continue
                run_command(f"{get_python()} {shlex.quote(file)}")
                continue

            # --- Clear history ---
            if user.lower() == "clear":
                HISTORY = [HISTORY[0]]  # Keep system prompt
                console.print("[green]History cleared.[/]")
                continue

            # --- Show history summary ---
            if user.lower() == "history":
                summary = "\n".join([f"{m['role']}: {m['content'][:50]}..." for m in HISTORY[1:]])
                console.print(Markdown(f"## Conversation History\n{summary}"))
                continue

            # --- Core FS Commands: Direct file system ops for zero-load UX ---
            # These implement shell-like basics (mkdir, ls, cd, etc.) with security restrictions.
            # Interacts with agents: Uses fs for deeper ops if needed. Forgiving: Confirms destructive, handles errors.
            # Rationale: Real FS changes for magic feel; restricted to INITIAL_CWD (principle 6).
            if user.lower().startswith("mkdir "):
                dir_name = user.split(maxsplit=1)[1].strip() if len(user.split()) > 1 else ""
                if not dir_name:
                    console.print("[red]Usage: mkdir <dir>[/]")
                    continue
                full = Path(dir_name).resolve()
                if not str(full).startswith(INITIAL_CWD):
                    console.print("[red]Blocked: outside project[/]")
                    continue
                if full.exists():
                    console.print("[yellow]Directory exists.[/]")
                    continue
                if ask(f"Create {dir_name}? (y/n)", default="y") == "y":
                    full.mkdir(parents=True, exist_ok=True)
                    console.print(f"[green]Created: {full}[/]")
                continue

            if user.lower() == "ls":
                files = "\n".join(os.listdir("."))
                console.print(Markdown(f"## Directory Listing\n```\n{files}\n```"))
                continue

            if user.lower().startswith("cd "):
                path = user.split(maxsplit=1)[1].strip() if len(user.split()) > 1 else "~"
                try:
                    os.chdir(path)
                    new_cwd = os.getcwd()
                    if not new_cwd.startswith(INITIAL_CWD):
                        os.chdir(INITIAL_CWD)
                        console.print("[red]Blocked: outside project[/]")
                    else:
                        console.print(f"[green]Changed to: {get_formatted_cwd()}[/]")
                except Exception as e:
                    console.print(f"[red]CD failed: {e}[/]")
                continue

            if user.lower().startswith("requirements generate"):
                # Smarter requirements generate (Priority 3): Scans .py files with importlib for accurate imports.
                # Interacts with FS: Recurses project; outputs to requirements.txt. Forgiving: Skips non-py/errors.
                imports = set()
                for file in Path(".").rglob("*.py"):
                    if str(file.resolve()).startswith(INITIAL_CWD):
                        try:
                            spec = importlib.util.spec_from_file_location("module", file)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            for name in dir(module):
                                obj = getattr(module, name)
                                if hasattr(obj, "__module__") and obj.__module__ not in {"builtins", "__main__"}:
                                    imports.add(obj.__module__.split('.')[0])
                        except Exception:
                            pass
                reqs = "\n".join(sorted(imports))
                Path("requirements.txt").write_text(reqs)
                console.print(f"[green]Generated requirements.txt:\n{reqs}[/]")
                continue

            # --- General AI chat ---
            HISTORY.append({"role": "user", "content": user})
            with console.status("[bold green]Grok thinking..."):
                resp = client.chat.completions.create(
                    model=MODEL, messages=HISTORY, temperature=0.3, max_tokens=4096
                )
            reply = resp.choices[0].message.content
            console.print(Markdown(reply))
            HISTORY.append({"role": "assistant", "content": reply})

            # --- Tool calling (AI-driven) ---
            for agent_name, command in re.findall(rf"{TOOL_CALL_START}\s+(\w+)\s+([^\n]+)\n{TOOL_CALL_END}", reply, re.DOTALL):
                if agent_name not in AGENTS:
                    console.print(f"[yellow]AI requested unknown agent: {agent_name}[/]")
                    continue
                console.print(f"[bold blue]→ AI calls {agent_name}: {command.strip()}[/]")
                result = AGENTS[agent_name].handle_command(command.strip())
                if result:
                    HISTORY.append({"role": "tool", "content": f"Result from {agent_name}: {result}"})

            # --- Artifact / code handling (unified) ---
            handle_artifacts(reply, user)

    except KeyboardInterrupt:
        console.print("\n[dim]Bye![/]")
    finally:
        try:
            readline.write_history_file(str(HISTORY_FILE))
        except Exception:
            pass

if __name__ == "__main__":
    chat()
