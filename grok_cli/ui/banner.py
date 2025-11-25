"""Welcome banner and UI elements for first-run experience."""

from rich.console import Console
from rich.text import Text

console = Console()

ASCII_BANNER = """╔══════════════════════════════════════════════════════════════════════════════╗
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
╚══════════════════════════════════════════════════════════════════════════════╝"""


def show_banner() -> None:
    """Display ASCII art banner (shown on every startup)."""
    console.print(ASCII_BANNER, style="bright_black")
    console.print()


def show_welcome_banner() -> None:
    """Display full welcome banner on first run with ASCII art and instructions."""
    show_banner()

    # Welcome message
    welcome_text = Text()
    welcome_text.append("Welcome to Grok CLI\n", style="bold white")
    welcome_text.append("A lean, safe, token-efficient interface for Grok models\n\n", style="white")

    welcome_text.append("Quick Start:\n", style="bold yellow")
    welcome_text.append("  • ", style="dim")
    welcome_text.append("grok create <type> <description>", style="green")
    welcome_text.append(" - Generate files\n", style="white")

    welcome_text.append("  • ", style="dim")
    welcome_text.append("grok edit <file> <instruction>", style="green")
    welcome_text.append(" - Modify files with diff preview\n", style="white")

    welcome_text.append("  • ", style="dim")
    welcome_text.append("grok ask <question>", style="green")
    welcome_text.append(" - Ask questions\n", style="white")

    welcome_text.append("  • ", style="dim")
    welcome_text.append("grok help", style="green")
    welcome_text.append(" - View documentation\n\n", style="white")

    welcome_text.append("Configuration: ", style="dim")
    welcome_text.append("~/.grok/config.toml", style="cyan")
    welcome_text.append("\n", style="dim")

    welcome_text.append("API Key: ", style="dim")
    welcome_text.append("export XAI_API_KEY=your_key_here", style="yellow")

    console.print(welcome_text)
    console.print()
