"""Slash command handling for the REPL.

Slash commands provide utility functions that don't require
model interaction (e.g., /help, /model, /cost).
"""

from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from grok_cli import config, session, cache
from grok_cli.models import list_models, resolve_model_name, get_friendly_name
from grok_cli.plugins import discover_plugins, get_registered_commands, get_registered_create_types
from grok_cli import sandbox

console = Console()

# Registry of slash commands
SLASH_COMMANDS: dict[str, tuple[Callable[..., Any], str, str]] = {}


def register_slash_command(name: str, handler: Callable[..., Any], description: str, usage: str = "") -> None:
    """Register a slash command.

    Args:
        name: Command name (without the /)
        handler: Function to call when command is invoked
        description: Short description for help
        usage: Usage example (optional)
    """
    SLASH_COMMANDS[name] = (handler, description, usage)


def is_slash_command(text: str) -> bool:
    """Check if input is a slash command.

    Args:
        text: Input text

    Returns:
        True if text starts with /
    """
    return text.strip().startswith("/")


def parse_slash_command(text: str) -> tuple[str, list[str]]:
    """Parse a slash command into name and arguments.

    Args:
        text: Input text (e.g., "/model grok41_heavy")

    Returns:
        Tuple of (command_name, arguments)
    """
    text = text.strip()
    if not text.startswith("/"):
        return "", []

    parts = text[1:].split(None, 1)  # Split on first whitespace
    command = parts[0].lower() if parts else ""
    args = parts[1].split() if len(parts) > 1 else []

    return command, args


def execute_slash_command(command: str, args: list[str], cfg: dict[str, Any], agent: Any = None) -> bool:
    """Execute a slash command.

    Args:
        command: Command name
        args: Command arguments
        cfg: Configuration dictionary
        agent: Agent instance (for commands that need it)

    Returns:
        True if REPL should continue, False to exit
    """
    if command in ("exit", "quit", "q"):
        return False

    if command in SLASH_COMMANDS:
        handler, _, _ = SLASH_COMMANDS[command]
        try:
            handler(args, cfg, agent)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
        return True

    # Unknown command
    console.print(f"[yellow]Unknown command:[/yellow] /{command}")
    console.print("[dim]Type /help for available commands[/dim]")
    return True


def get_slash_command_completions(prefix: str) -> list[str]:
    """Get completions for slash commands.

    Args:
        prefix: Current input prefix (including /)

    Returns:
        List of matching command names
    """
    if not prefix.startswith("/"):
        return []

    search = prefix[1:].lower()
    completions = []

    for cmd in SLASH_COMMANDS:
        if cmd.startswith(search):
            completions.append(f"/{cmd}")

    # Add exit/quit
    for cmd in ("exit", "quit", "q"):
        if cmd.startswith(search):
            completions.append(f"/{cmd}")

    return completions


# --- Command Handlers ---


def cmd_help(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Show help information."""
    if args:
        # Topic-specific help
        topic = args[0].lower()
        topics = {
            "tools": (
                "[bold]File Tools[/bold]\n\n"
                "The assistant can read, write, and edit files in your project.\n"
                "Just ask naturally:\n\n"
                '  • "Create a Python script that sorts a list"\n'
                '  • "Read config.py and explain what it does"\n'
                '  • "Add error handling to utils.py"\n\n'
                "Files are sandboxed to your project directory for safety."
            ),
            "slash": (
                "[bold]Slash Commands[/bold]\n\n"
                "Commands starting with / are utility commands:\n\n"
                + "\n".join(f"  /{name}: {desc}" for name, (_, desc, _) in SLASH_COMMANDS.items())
            ),
            "confirm": (
                "[bold]Confirmation Mode[/bold]\n\n"
                "By default, file operations require confirmation.\n\n"
                "  /y or /yes  - Enable auto-confirm (skip prompts)\n"
                "  /n or /no   - Disable auto-confirm (require prompts)\n\n"
                "Or set auto_yes = true in ~/.grok/config.toml"
            ),
        }

        if topic in topics:
            console.print(Panel(topics[topic], border_style="cyan"))
        else:
            console.print(f"[yellow]Unknown topic:[/yellow] {topic}")
            console.print(f"Available topics: {', '.join(topics.keys())}")
        return

    # General help
    help_text = """[bold cyan]Grok CLI - Natural Language Interface[/bold cyan]

[bold]How to Use:[/bold]
  Just type naturally! The assistant can understand and execute your requests.

  Examples:
    • What is a binary search algorithm?
    • Create a Python script that calculates fibonacci numbers
    • Read main.py and explain what it does
    • Add type hints to utils.py

[bold]Slash Commands:[/bold]
  /help [topic]     Show this help (topics: tools, slash, confirm)
  /model <name>     Switch to a different model
  /models           List available models
  /cost             Show token usage dashboard
  /clear            Clear conversation history
  /history          Show conversation history
  /y, /yes          Enable auto-confirm (skip file operation prompts)
  /n, /no           Disable auto-confirm (require prompts)
  /plugins          List loaded plugins
  /pwd              Show current directory
  /exit, /quit      Exit the REPL

[bold]Shell Commands:[/bold]
  ls, ll, cd, pwd, cat, head, tail, mkdir, tree, cp, mv, rm

[bold]File Operations:[/bold]
  The assistant confirms before writing/editing files.
  Use /y to auto-confirm, or -y flag when starting: grok -y

[bold]Configuration:[/bold]
  Config: ~/.grok/config.toml
  API Key: export XAI_API_KEY=your_key"""

    console.print(Panel(help_text, border_style="cyan", padding=(1, 2)))


def cmd_model(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Switch the default model."""
    if not args:
        current = cfg.get("default_model", "grok41_fast")
        console.print(f"Current model: [cyan]{current}[/cyan]")
        console.print("[dim]Usage: /model <name> (use /models to list)[/dim]")
        return

    model_name = args[0]

    try:
        api_model = resolve_model_name(model_name)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        return

    cfg["default_model"] = model_name
    config.save_config(cfg)

    friendly = get_friendly_name(api_model)
    console.print(f"[green]✓[/green] Model set to: {friendly} ({api_model})")


def cmd_models(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """List available models."""
    console.print("\n[bold]Available Models:[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("API Model", style="dim")
    table.add_column("Type", style="yellow")
    table.add_column("Description")

    current_model = cfg.get("default_model", "grok41_fast")

    for model_info in list_models():
        model_type = "Reasoning" if model_info["reasoning"] else "Fast"
        name = model_info["name"]
        if name == current_model:
            name = f"[bold]{name}[/bold] ←"
        table.add_row(name, model_info["api_model"], model_type, model_info["description"])

    console.print(table)
    console.print()


def cmd_cost(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Show token usage dashboard."""
    console.print("\n[bold]Token Usage Dashboard:[/bold]\n")

    stats = cache.get_cache_stats()
    sessions_list = session.list_sessions()

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Cached Responses", str(stats["file_count"]))
    table.add_row("Cache Size", f"{stats['total_size_mb']:.2f} MB")
    table.add_row("Oldest Cache", f"{stats['oldest_age_days']:.1f} days")
    table.add_row("Sessions Saved", str(len(sessions_list)))

    console.print(table)
    console.print("\n[dim]Note: Detailed cost tracking requires budget_monthly in config.toml[/dim]\n")


def cmd_clear(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Clear conversation history."""
    if agent:
        agent.clear_history()
    console.print("[green]✓[/green] Conversation history cleared")


def cmd_history(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Show conversation history."""
    if not agent or not agent.messages:
        console.print("[dim]No conversation history[/dim]")
        return

    console.print("\n[bold]Conversation History:[/bold]\n")

    for i, msg in enumerate(agent.messages):
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            console.print(f"[bold blue]You:[/bold blue] {content[:100]}{'...' if len(content) > 100 else ''}")
        elif role == "assistant":
            console.print(f"[bold green]Grok:[/bold green] {content[:100]}{'...' if len(content) > 100 else ''}")

    console.print(f"\n[dim]({len(agent.messages)} messages)[/dim]\n")


def cmd_yes(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Enable auto-confirm mode."""
    if agent:
        agent.set_auto_confirm(True)
    console.print("[green]✓[/green] Auto-confirm enabled (file operations will not prompt)")


def cmd_no(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Disable auto-confirm mode."""
    if agent:
        agent.set_auto_confirm(False)
    console.print("[green]✓[/green] Auto-confirm disabled (file operations will prompt)")


def cmd_plugins(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """List loaded plugins."""
    console.print("\n[bold]Discovering plugins...[/bold]")
    loaded = discover_plugins()

    if not loaded:
        console.print("[dim]No plugins found in ~/.grok/plugins/[/dim]\n")
        return

    console.print(f"[green]Loaded {len(loaded)} plugin(s):[/green]\n")

    commands = get_registered_commands()
    if commands:
        console.print("[bold]Commands:[/bold]")
        for name, (_, help_text) in commands.items():
            console.print(f"  [cyan]{name}[/cyan] - {help_text}")
        console.print()

    create_types = get_registered_create_types()
    if create_types:
        console.print("[bold]File Types:[/bold]")
        for type_name, (ext, desc) in create_types.items():
            console.print(f"  [cyan]{type_name}[/cyan] (.{ext}) - {desc}")
        console.print()


def cmd_pwd(args: list[str], cfg: dict[str, Any], agent: Any) -> None:
    """Show current working directory."""
    cwd = sandbox.get_current_dir()
    launch = sandbox.get_launch_dir()

    console.print(f"[cyan]Current:[/cyan] {cwd}")
    if cwd != launch:
        console.print(f"[dim]Launch:  {launch}[/dim]")


# --- Register Commands ---

register_slash_command("help", cmd_help, "Show help information", "/help [topic]")
register_slash_command("h", cmd_help, "Show help (alias)", "/h")
register_slash_command("model", cmd_model, "Switch model", "/model <name>")
register_slash_command("m", cmd_model, "Switch model (alias)", "/m <name>")
register_slash_command("models", cmd_models, "List available models", "/models")
register_slash_command("cost", cmd_cost, "Show token usage", "/cost")
register_slash_command("clear", cmd_clear, "Clear conversation history", "/clear")
register_slash_command("history", cmd_history, "Show conversation history", "/history")
register_slash_command("y", cmd_yes, "Enable auto-confirm", "/y")
register_slash_command("yes", cmd_yes, "Enable auto-confirm", "/yes")
register_slash_command("n", cmd_no, "Disable auto-confirm", "/n")
register_slash_command("no", cmd_no, "Disable auto-confirm", "/no")
register_slash_command("plugins", cmd_plugins, "List loaded plugins", "/plugins")
register_slash_command("pwd", cmd_pwd, "Show current directory", "/pwd")
