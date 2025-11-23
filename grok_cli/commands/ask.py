"""Ask command - general queries without file access."""

from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from grok_cli import cache, config
from grok_cli.providers.grok import GrokProvider
from grok_cli.models import resolve_model_name

console = Console()


def ask_command(question: str, cfg: dict[str, Any]) -> str:
    """Ask a general question to the model.

    Does not access files or current directory context.

    Args:
        question: Question to ask
        cfg: Configuration dictionary

    Returns:
        Model response as string
    """
    # Get API key
    api_key = config.get_api_key()
    if not api_key:
        raise ValueError(
            "GROK_API_KEY not set. Get your key from console.grok.com and:\n" "  export GROK_API_KEY=your_key_here"
        )

    # Initialize provider
    provider = GrokProvider(api_key)

    # Resolve model name
    model = resolve_model_name(cfg.get("default_model", "grok41_fast"))

    # Build messages
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Provide clear, accurate, and concise answers."},
        {"role": "user", "content": question},
    ]

    # Check cache first
    cached_response = cache.get_cached_response(messages, model, temperature=0.7)

    if cached_response:
        console.print("[dim](from cache)[/dim]")
        response_content = cached_response["content"]
    else:
        # Make API call with spinner
        with console.status("[bold green]Thinking...", spinner="dots"):
            response = provider.complete(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=8192,
            )

        response_content = response["content"]

        # Cache the response
        cache.cache_response(messages, model, 0.7, response)

        # Show token usage
        usage = response.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        console.print(f"\n[dim]Tokens: {tokens}[/dim]")

    return str(response_content)


def display_answer(answer: str) -> None:
    """Display answer with markdown formatting.

    Args:
        answer: Answer text to display
    """
    console.print()
    console.print(Markdown(answer))
    console.print()
