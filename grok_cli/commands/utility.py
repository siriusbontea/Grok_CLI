"""Utility commands: model, models, plugins, resume, cost, help."""

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from grok_cli import cache, config, session
from grok_cli.models import list_models, resolve_model_name, get_friendly_name
from grok_cli.plugins import get_registered_commands, get_registered_create_types, discover_plugins

console = Console()


def models_command() -> None:
    """List all available models with descriptions."""
    console.print("\n[bold]Available Models:[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("API Model", style="dim")
    table.add_column("Type", style="yellow")
    table.add_column("Description")

    for model_info in list_models():
        model_type = "Reasoning" if model_info["reasoning"] else "Fast"
        table.add_row(model_info["name"], model_info["api_model"], model_type, model_info["description"])

    console.print(table)
    console.print()


def model_command(model_name: str, cfg: dict[str, Any]) -> None:
    """Switch default model.

    Args:
        model_name: Model to switch to
        cfg: Configuration dictionary
    """
    # Validate model
    try:
        api_model = resolve_model_name(model_name)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        return

    # Update config
    cfg["default_model"] = model_name
    config.save_config(cfg)

    friendly = get_friendly_name(api_model)
    console.print(f"[green]✓[/green] Default model set to: {friendly} ({api_model})")


def plugins_command() -> None:
    """List all loaded plugins and their commands."""
    console.print("\n[bold]Discovering plugins...[/bold]")
    loaded = discover_plugins()

    if not loaded:
        console.print("[dim]No plugins found in ~/.grok/plugins/[/dim]\n")
        return

    console.print(f"[green]Loaded {len(loaded)} plugin(s):[/green]\n")

    # Show registered commands
    commands = get_registered_commands()
    if commands:
        console.print("[bold]Commands:[/bold]")
        for name, (_, help_text) in commands.items():
            console.print(f"  [cyan]{name}[/cyan] - {help_text}")
        console.print()

    # Show registered create types
    create_types = get_registered_create_types()
    if create_types:
        console.print("[bold]File Types:[/bold]")
        for type_name, (ext, desc) in create_types.items():
            console.print(f"  [cyan]{type_name}[/cyan] (.{ext}) - {desc}")
        console.print()


def resume_command(cfg: dict[str, Any]) -> dict[str, Any]:
    """Resume last session.

    Args:
        cfg: Configuration dictionary

    Returns:
        Loaded session data

    Raises:
        FileNotFoundError: If no session found
    """
    try:
        session_data = session.load_session()
        console.print("[green]✓[/green] Resumed session")

        # Show session info
        if "cwd" in session_data:
            console.print(f"  CWD: {session_data['cwd']}")
        if "goal" in session_data:
            console.print(f"  Goal: {session_data['goal']}")

        return session_data

    except FileNotFoundError:
        console.print("[yellow]No session found. Starting new session.[/yellow]")
        return {}


def cost_command() -> None:
    """Display token usage and cost dashboard."""
    console.print("\n[bold]Token Usage Dashboard:[/bold]\n")

    # Get cache stats
    stats = cache.get_cache_stats()

    # Get session list
    sessions = session.list_sessions()

    # Display cache stats
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Cached Responses", str(stats["file_count"]))
    table.add_row("Cache Size", f"{stats['total_size_mb']:.2f} MB")
    table.add_row("Oldest Cache", f"{stats['oldest_age_days']:.1f} days")
    table.add_row("Sessions Saved", str(len(sessions)))

    console.print(table)

    console.print("\n[dim]Note: Detailed cost tracking requires enabling budget_monthly in config.toml[/dim]\n")


def help_command(topic: str | None = None) -> None:
    """Display help information.

    Args:
        topic: Optional specific topic to get help on
    """
    if topic is None:
        # General help
        help_text = """
[bold cyan]Grok CLI - Command Reference[/bold cyan]

[bold]Core Commands:[/bold]
  [cyan]ask <question>[/cyan]              Ask a general question
  [cyan]create <type> <description>[/cyan] Generate a new file
  [cyan]edit <file> <instruction>[/cyan]   Modify an existing file
  [cyan]heavy <task>[/cyan]                Complex task with parallel agents

[bold]Utility Commands:[/bold]
  [cyan]model <name>[/cyan]                Switch default model
  [cyan]models[/cyan]                      List available models
  [cyan]plugins[/cyan]                     List loaded plugins
  [cyan]resume[/cyan]                      Continue last session
  [cyan]cost[/cyan]                        Show token usage dashboard
  [cyan]help [topic][/cyan]                Show this help

[bold]Shell Commands:[/bold]
  [cyan]ls, ll, cd, pwd[/cyan]             Directory navigation
  [cyan]cat, head, tail[/cyan]             View files
  [cyan]mkdir, cp, mv, rm, tree[/cyan]     File operations

[bold]Options:[/bold]
  [cyan]-y, --yes[/cyan]                   Auto-confirm all prompts
  [cyan]--dangerously-allow-entire-fs[/cyan] Disable sandbox (requires typing YES)

[bold]Configuration:[/bold]
  Config file: [cyan]~/.grok/config.toml[/cyan]
  API key: [cyan]export XAI_API_KEY=your_key[/cyan]

[bold]Examples:[/bold]
  grok ask "explain async/await in Python"
  grok create py "binary search algorithm"
  grok edit utils.py "add type hints"
  grok model grok41_heavy

For detailed documentation, see README.md or visit the blueprint.
"""
        console.print(Panel(help_text, border_style="cyan", padding=(1, 2)))

    else:
        # Topic-specific help
        topics = {
            "create": "Create files with AI: grok create <type> <description>\nSupported types: py, js, ts, html, css, md, etc.",
            "edit": "Edit files with AI: grok edit <file> <instruction>\nShows diff preview before applying changes.",
            "ask": "Ask questions: grok ask <question>\nGeneral queries without file access.",
            "heavy": "Complex tasks with parallel agents: grok heavy <task>\nUses 3 agents + meta-resolver for best quality.",
            "models": "List models: grok models\nSwitch model: grok model <name>",
            "sandbox": "All file operations are sandboxed to launch directory.\nUse --dangerously-allow-entire-fs to disable (type YES to confirm).",
        }

        if topic in topics:
            console.print(f"\n[bold]{topic.upper()}:[/bold]\n{topics[topic]}\n")
        else:
            console.print(f"[yellow]Unknown topic:[/yellow] {topic}")
            console.print("Available topics: " + ", ".join(topics.keys()))
