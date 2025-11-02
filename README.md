# Grok CLI: A Terminal Interface for Grok AI
```                               █                                                         
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
     ██     ███████████████                                                                 
    █        ███████████                                                                    
  █
```
Grok CLI is a Python-based command-line tool that provides an interactive interface to xAI's Grok AI models (grok-4 and grok-code-fast-1). It allows you to generate code, save files, run scripts, commit to git, and more, all from your terminal. Ideal for coding workflows, project bootstrapping, and quick AI assistance.

## Features
- **Interactive Chat**: Talk to Grok AI for code generation, debugging, and advice.
- **Model Switching**: Use `model fast` for speed or `model best` for accuracy.
- **Project Initialization**: Bootstrap projects with templates like FastAPI, Flask, or custom.
- **File Saving**: Automatically detects and saves code blocks (Python, Markdown, etc.).
- **Run & Test**: Execute Python scripts and run pytest if tests exist.
- **Git Integration**: Auto-commit changes.
- **Preview, Dockerize, Review**: Start web servers, generate Docker files, or get AI code reviews.
- **Arrow Key Editing**: Full line editing in prompts.

## Prerequisites
- Python 3.8+.
- xAI API key (required for Grok AI access).
- Installed packages: `openai`, `rich`, `readline` (for arrow keys; may need `gnureadline` on macOS/conda).

### Getting an API Key
1. Sign up or log in at [x.ai](https://x.ai).
2. Go to the API dashboard at [https://x.ai/api](https://x.ai/api).
3. Generate an API key and copy it.
4. Set it as an environment variable: Add `export XAI_KEY="your_key_here"` to your `~/.zshrc` or `~/.bash_profile`, then `source ~/.zshrc`.

Note: API usage requires a paid plan; free tier has limits. Check xAI docs for pricing: [https://x.ai/api](https://x.ai/api).

## Installation
1. Install dependencies:

```pip install openai rich gnureadline```

2. Create the script:
- Open a text editor (e.g., Sublime, nano ~/bin/grok).
- Paste the full script code (from this repo).
- Save.

3. Make executable and add to PATH:

```
mkdir -p ~/bin
chmod +x ~/bin/grok
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

4. Set permissions for project directories (to allow file creation):

```
mkdir ~/your_project_dir
chmod -R 775 ~/your_project_dir  # Owner/group write access
```

## Usage
Launch from terminal:

```
cd ~/your_project_dir
grok
```

### Commands (Type in CLI)
- `help`: Show command table.
- `model fast/best`: Switch models.
- `init [template] [--git --venv]`: Bootstrap project (templates: fastapi, flask, cli, custom).
- `preview`: Start web server (for FastAPI/Flask).
- `dockerize`: Generate Dockerfile and docker-compose.yml.
- `review`: AI code review of .py files.
- `debug model`: Show current setup info.
- `quit`: Exit.

### Generating and Saving Files
- Prompt Grok: "Write a Markdown story in a code block for story.md".
- CLI detects code block (e.g., ```markdown ... ```).
- Prompt: "Save markdown? (y/n/[filename])" — Enter y or filename (defaults to .md).
- Saves to current dir.
- For Python: Also prompts to run/test/commit.

### Troubleshooting
- **Arrow Keys Not Working**: Ensure `gnureadline` is installed (`pip install gnureadline`). Restart terminal.
- **Permission Denied**: Check dir permissions (`ls -l`). Use `chmod 775 dir/` for write access. Run as owner (not sudo).
- **API Errors**: Verify $XAI_KEY with `echo $XAI_KEY`. Regenerate if invalid.
- **No Code Block Detected**: Ask Grok to use ```language ... ``` format.
- **Conda Issues**: Activate base env or use system Python.

For bugs or contributions, open an issue/PR on this repo.

Licensed under BSD-3-Clause. Built with ❤️ by Sirius T. Bontea using xAI's Grok.
