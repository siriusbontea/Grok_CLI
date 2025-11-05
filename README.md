# Grok CLI: Interactive Coding Assistant
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
   ██     ███████████████                  C O M M A N D   L I N E   I N T E R F A C E                                               
  █        ███████████                                                                    
█                                          get lastest version on GitHub @siriusbontea

```
Grok CLI is a terminal-based interactive coding assistant powered by xAI's Grok models (Grok-4 and Grok-Code-Fast-1). It allows you to chat with the AI for coding advice, generate and save code, manage Python projects, and automate development tasks like virtual environments, Git operations, Docker setup, and more—all from a single CLI interface.

Designed for developers, it provides a seamless workflow for prototyping, debugging, and building projects with minimal context switching. The CLI is self-contained, with built-in commands for file/directory management, code execution, and AI interactions.

## Features
- **AI-Powered Coding Assistance**: Chat with Grok to generate code, get explanations, or debug issues. Code blocks in responses can be saved, executed, tested, and committed automatically.
- **Project Management**: Create virtual environments, install packages, generate requirements.txt, initialize Git repos, and perform basic Git operations.
- **File and Directory Tools**: Shell-like commands (cd, ls, mkdir, touch, rm, mv, cp) restricted to the project directory for safety.
- **Dev Automation**: Preview web apps (FastAPI/Flask), dockerize projects, perform AI code reviews, run tests, and more.
- **Conversation Management**: Clear history or view summaries to keep sessions organized.
- **Tab Completion**: Intelligent auto-completion for commands and paths.
- **Context Awareness**: Displays context usage percentage to monitor AI conversation limits.
- **Safety Features**: Directory navigation is limited to the starting project folder and its subdirectories to prevent accidental system changes.

## Prerequisites
- Python 3.8+ (tested on 3.12)
- An xAI API key (sign up at [x.ai](https://x.ai) if needed)

## Installation
1. **Download the Script**:
   - Clone the repository or download the `grok` script (it's a single Python file).
`
git clone <repo-url>  # If in a repo
cd grok-cli
`

2. **Install Dependencies**:
- The CLI requires a few Python libraries. Install them via pip:
`
pip install rich openai prompt-toolkit
`
- Optional for full functionality (e.g., testing, web previews):
`
pip install pytest uvicorn fastapi flask docker
`
Note: Some features like `pytest` or `uvicorn` may require additional installs based on your project.

3. **Set Up API Key**:
- Export your xAI API key as an environment variable:
`
export XAI_KEY="your_xai_api_key_here"
`
(Add this to your shell profile like `~/.bashrc` or `~/.zshrc` for persistence.)

4. **Make the Script Executable** (Optional):
- For easier running:
`
chmod +x grok
`

## Quick Start
1. Run the CLI:
`
./grok  # Or python grok
`
- On launch, you'll see an ASCII logo, a list of available commands, and a prompt to type `help` for details.
- The prompt shows context usage (e.g., (@ 0%) ~ ❯) and current directory.

2. **Basic Usage**:
- Type any query to chat with Grok (e.g., "Write a Python function to reverse a string").
- Use commands for actions (e.g., `mkdir src`, `cd src`, `git init`).
- For code generation: If Grok responds with a code block, you'll be prompted to save, run, test, or commit it.
- Exit with `quit` or `exit` (or Ctrl+C).

Example session:
```
(@ 0%) ~ ❯ mkdir myproject
Created directory: myproject
(@ 0%) ~ ❯ cd myproject
Changed to: /path/to/myproject
(@ 0%) ~ ❯ venv create
Virtual environment created in .venv
(@ 0%) ~ ❯ Write a hello world script
[Grok's response with code block]
Save python? (y/n/[filename]): y
Saved: hello.py
Run now? (y): y
Hello, World!
Git commit? (y): y
[Git commit output]
```


## Commands
The CLI starts with a summary of commands. Type `help` for a detailed table. Here's an overview:

- **AI/Model**: `model fast/best` (switch models), `review` (code review), `preview` (start web server), `dockerize` (generate Docker files).
- **Navigation/File Management**: `cd [path]` (change dir, restricted to project), `ls` (list files), `mkdir [dir]`, `touch [file]`, `rm [path]` (with confirm), `mv [src] [dst]`, `cp [src] [dst]`.
- **Python/Venv**: `venv create/activate`, `pip install [pkg]`, `requirements generate`, `run [file.py]`, `test` (run or generate tests).
- **Git**: `git init/status/add [file]/push`.
- **Session**: `clear` (reset history), `history` (view summary), `debug model` (show info), `quit/exit`.
- **General Queries**: Anything else is sent to Grok for AI response.

Tab completion works for commands and paths—press Tab to auto-complete.

## Tips for New Users
- **Onboarding**: The startup screen lists commands; `help` expands them. Start with simple queries or commands—no prior setup needed beyond the API key.
- **Code Handling**: Grok outputs code in fenced blocks. You'll get interactive prompts to save/run/test/commit—answer y/n or provide filenames.
- **Safety**: Can't `cd` outside the launch directory. Destructive commands like `rm` require confirmation.
- **Customization**: Edit the system prompt in the script if needed (in `HISTORY`).
- **Troubleshooting**: If API calls fail, check `XAI_KEY`. For dependency issues, ensure libraries are installed. Use `debug model` to inspect setup.

## Contributing
Feel free to fork and PR improvements! Focus on keeping it lightweight and user-friendly.

## License
Licensed under BSD-3-Clause. Built with ❤️ by Sirius T. Bontea using xAI's Grok.

For questions, chat with Grok in the CLI itself!
