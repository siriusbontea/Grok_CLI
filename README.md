# Grok CLI: Your Universal AI Terminal
```
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
   ██     ███████████████                  𝘾 𝙊 𝙈 𝙈 𝘼 𝙉 𝘿    𝙇 𝙄 𝙉 𝙀    𝙄 𝙉 𝙏 𝙀 𝙍 𝙁 𝘼 𝘾 𝙀
  █        ███████████                                                                    
█                                               𝘨𝘦𝘵 𝘭𝘢𝘴𝘵𝘦𝘴𝘵 𝘷𝘦𝘳𝘴𝘪𝘰𝘯 𝘰𝘯 𝘎𝘪𝘵𝘏𝘶𝘣 @𝘴𝘪𝘳𝘪𝘶𝘴𝘣𝘰𝘯𝘵𝘦𝘢

```
Grok CLI is a powerful, terminal-based AI assistant powered by xAI's Grok models (Grok-4 and Grok-Code-Fast-1). It's designed as a **universal tool for everyday AI interactions**—from answering general questions, brainstorming ideas, or managing tasks—to serving as a **highly capable coding assistant** for developers. Whether you're a non-technical user chatting with AI for fun or advice, or a programmer automating workflows, Grok CLI makes advanced AI feel intuitive and accessible right from your command line.

Unlike traditional tools, Grok CLI emphasizes safety, discoverability, and minimal setup. It's POSIX-compliant, running seamlessly on systems like FreeBSD, Linux, and macOS. For Windows users, it's easy to replicate via WSL (see below). No web browser needed—just your terminal.

## Features
Grok CLI bridges general AI assistance with specialized dev tools, all in one lightweight interface:

- **Seamless file operations**: Read, write, create, and manage files directly in your project (surpassing Grok Studio's read-only limitations).
- **General-Purpose AI Chat**: Ask anything—from "What's the weather like?" (via tools) to creative writing or problem-solving. Responses are helpful, concise, and context-aware.
- **Multiple Grok Models**: Switch between optimized models like grok-code-fast-1 (fast code gen), grok-4-fast-reasoning (balanced speed), grok-4-fast-non-reasoning (ultra-fast simple tasks), and grok-4-0709 (premium reasoning).
- **Coding Assistance**: Generate code snippets, debug issues, or get explanations. Save, run, test, and commit code with interactive prompts.
- **Project Management**: Handle files/directories (cd, ls, mkdir), virtual environments (venv), packages (pip), and Git ops—all restricted to your project folder for safety.
- **Automation Agents**: Modular "agents" for tasks like file scanning (fs), Git (git), linting (lint), README generation (readme), and testing (test). AI can call them automatically.
- **Dev Shortcuts**: Preview web apps (FastAPI/Flask), dockerize projects, run Python files, generate requirements.txt, and more.
- **User-Friendly Design**: Tab completion, rich help docs, context usage indicators, and confirmations for destructive actions. Forgiving for beginners—e.g., auto-install prompts for tools like pytest.
- **Security & Privacy**: Operations limited to your starting directory. No unintended system changes.

## Prerequisites
- **Python**: Version 3.8+ (tested up to 3.12). Most modern systems have this pre-installed.
- **xAI API Key**: Sign up at [x.ai](https://x.ai) and get your key. (Free tier available for basic use.)
- **Optional for Full Features**: Libraries like `pytest`, `uvicorn`, or `docker`—Grok CLI prompts to install them as needed.

## Installation
Grok CLI is a single Python script—no complex setup required. Here's how to get started:

1. **Download the Script**:
   - Clone the repo or download `grok_cli.py` directly from GitHub.

```
git clone https://github.com/siriusbontea/grok-cli.git
cd grok-cli
```

- (Or just wget/curl the file if you prefer.)

2. **Install Dependencies**:
- Run in your terminal:

```
pip install rich openai prompt-toolkit
```

- These handle formatting, AI calls, and input—lightweight and essential.
- For extras (e.g., testing or web previews):

```
pip install pytest uvicorn fastapi flask docker
```

Grok CLI will guide you if something's missing.

3. **Set Up API Key**:
- Export your xAI key:

```
export XAI_KEY="your_xai_api_key_here"
```

- Add to your shell profile (e.g., `~/.bashrc`, `~/.zshrc`) for persistence:

```
echo 'export XAI_KEY="your_xai_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

4. **Make Executable (Optional)**:
- For easy running:

```
chmod +x grok_cli.py
```

- Now launch with `./grok_cli.py` or `python grok_cli.py`.

## Platform Compatibility
Grok CLI is fully POSIX-compliant, ensuring smooth operation on Unix-like systems:
- **FreeBSD, Linux, macOS**: Runs natively in your terminal—no extras needed. Just open Terminal.app (macOS), GNOME Terminal (Linux), or similar.

For **Windows Users**:
- Use Windows Subsystem for Linux (WSL) to replicate a POSIX environment:
1. Install WSL via Microsoft Store (search for "Ubuntu" or your preferred distro).
2. Launch WSL terminal.
3. Follow the installation steps above inside WSL.
- This gives you full Grok CLI power without native Windows quirks. (Direct Windows support planned for future versions.)

## Quick Start
Launch Grok CLI:

```
./grok_cli.py  # Or python grok_cli.py
```

- You'll see the ASCII logo and a prompt like `(@ 0%) ~ ❯`.
- **General Query Example**: Type "Tell me a joke about AI." → Grok responds conversationally.
- **Coding Example**:

```
(@ 0%) ~ ❯ mkdir myproject
Created: /path/to/myproject
(@ 0%) ~ ❯ cd myproject
Changed to: ~/myproject
(@ 0%) ~ ❯ venv create
Virtual environment created in .venv
(@ 0%) ~ ❯ Write a simple Python script to print 'Hello, World!'
[Grok's response with code block]
Save python? (y/n/[filename]): y
Saved: hello.py
Run now? (y/n): y
Hello, World!
Git commit? (y/n): y
[Git output]
```

- Exit: `quit`, `exit`, or Ctrl+C.

### Getting Started for Non-Developers
If you're new to terminals or AI tools:
- Start with `help` to see all commands in a table.
- Try simple chats: "Explain quantum computing like I'm 5."
- Use agents for tasks: `agent add fs` then `fs scan` to view your folder structure.
- Everything is safe—Grok CLI can't access outside your project folder, and it asks before changes.

## Commands
Type `help` in the CLI for a full table. Highlights:
- **AI/Model**: `model <shorthand>` (e.g., `model code` for grok-code-fast-1, `model best` for grok-4-0709; try `help models` for details), `review` (code review).
- **Navigation/Files**: `cd [path]`, `ls`, `mkdir [dir]`, `touch [file]`, `rm [path]` (confirms delete).
- **Python Tools**: `venv create/activate`, `pip install [pkg]`, `run [file.py]`, `requirements generate`.
- **Dev Automation**: `preview` (start web server), `dockerize` (generate/build Docker), `test generate [file]` or `test run`.
- **Agents**: `agent list/add/help/call`—e.g., `readme generate` for auto-README.
- **Session**: `clear` (reset chat), `history` (view summary).

Tab to auto-complete commands/paths. For details: `help <cmd>` (e.g., `help agent` shows agents with examples).

## Tips for New Users
- **Discoverability**: Stuck? Type `help` or partial commands + Tab.
- **Safety Net**: Destructive actions (e.g., rm) always confirm. Ops stay in your project.
- **Customization**: Edit `grok_cli.py`'s system prompt for tweaks.
- **Troubleshooting**: API issues? Check `XAI_KEY`. Dependency missing? Grok CLI prompts installs.
- **For Coders**: Chain actions—e.g., generate code, save/run/test/commit in one flow.
- **General Use**: Beyond code, use for research, planning, or fun—e.g., "Plan a trip to Tokyo."
- **Permissions Tip**: For file ops (e.g., mkdir, save artifacts), ensure your project directory has write permissions (e.g., `chmod 755 myproject` for owner-write, all-read/execute). CLI restricts to startup dir for safety.

## Contributing
Fork on GitHub, make improvements, and PR! Focus on lightweight, user-first features. Report issues via GitHub.

## License
BSD 3-Clause License. Copyright (c) 2025, Sirius T. Bontea. See [LICENSE](LICENSE) for details.

Questions? Launch Grok CLI and ask it directly!
