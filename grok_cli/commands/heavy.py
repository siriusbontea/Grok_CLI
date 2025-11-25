"""Heavy mode - 3 parallel agents + meta-resolver for complex tasks."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from grok_cli import config
from grok_cli.providers.grok import GrokProvider
from grok_cli.session import serialize_toon

console = Console()


# Fixed agent roles (hard-coded as per blueprint)
AGENT_ROLES = {
    "coder": "Pure coder – output only perfect code, no explanation",
    "reviewer": "Security & correctness reviewer – focus on bugs, edge cases, tests",
    "optimizer": "Performance & style optimizer – focus on speed, readability, idioms",
}

# Always use reasoning model for heavy mode
REASONING_MODEL = "grok-4-1-fast-reasoning"


def heavy_command(task: str, session_context: dict[str, Any] | None, cfg: dict[str, Any]) -> str:
    """Execute task with 3 parallel agents + meta-resolver.

    Total cost: ~3.5× single call but significantly higher quality.

    Args:
        task: Task description
        session_context: Optional session context in TOON format
        cfg: Configuration dictionary

    Returns:
        Meta-resolver's unified response

    Raises:
        ValueError: If API key not set
    """
    # Get API key
    api_key = config.get_api_key()
    if not api_key:
        raise ValueError(
            "XAI_API_KEY not set. Get your key from console.x.ai and:\n" "  export XAI_API_KEY=your_key_here"
        )

    # Initialize provider
    provider = GrokProvider(api_key)

    # Prepare context string from session if provided
    context_str = ""
    if session_context:
        context_str = f"Context from session:\n{serialize_toon(session_context)}\n\n"

    console.print("[bold cyan]Heavy Mode:[/bold cyan] Running 3 parallel agents + meta-resolver...\n")

    # Run 3 agents in parallel
    with console.status("[bold green]Agent A (Coder)...", spinner="dots"):
        agent_responses = _run_parallel_agents(provider, task, context_str)

    # Run meta-resolver
    with console.status("[bold green]Meta-resolver synthesizing...", spinner="dots"):
        final_response = _run_meta_resolver(provider, task, agent_responses)

    return final_response


def _run_parallel_agents(provider: GrokProvider, task: str, context_str: str) -> dict[str, str]:
    """Run 3 agents in parallel with different roles.

    Args:
        provider: Grok provider instance
        task: Task description
        context_str: Context string from session (TOON format)

    Returns:
        Dictionary of agent_name → response
    """
    responses = {}

    # Use ThreadPoolExecutor for parallel API calls
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}

        for agent_name, agent_role in AGENT_ROLES.items():
            # Build messages for this agent
            system_prompt = f"{context_str}You are {agent_role}."
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": task}]

            # Submit async call
            future = executor.submit(
                provider.complete,
                messages=messages,
                model=REASONING_MODEL,
                temperature=0.7,
                max_tokens=8192,
            )
            futures[agent_name] = future

        # Collect results
        for agent_name, future in futures.items():
            response = future.result()
            responses[agent_name] = response["content"]
            console.print(f"[green]✓[/green] Agent {agent_name.upper()}: {len(response['content'])} chars")

    return responses


def _run_meta_resolver(provider: GrokProvider, task: str, agent_responses: dict[str, str]) -> str:
    """Run meta-resolver to synthesize agent responses.

    Args:
        provider: Grok provider instance
        task: Original task
        agent_responses: Responses from each agent

    Returns:
        Final synthesized response
    """
    # Build meta-resolver prompt
    system_prompt = (
        "You are the final coordinator. You have 3 expert opinions. "
        "Produce ONE unified, perfect output. "
        "If they conflict, choose the most correct/safe. "
        "If code, output the best version with inline comments explaining choices."
    )

    agents_output = "\n\n".join([f"AGENT {name.upper()}: {response}" for name, response in agent_responses.items()])

    user_prompt = f"Original task: {task}\n\n{agents_output}"

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    # Get final synthesis
    response = provider.complete(
        messages=messages,
        model=REASONING_MODEL,
        temperature=0.7,
        max_tokens=8192,
    )

    console.print(f"[green]✓[/green] Meta-resolver: {len(response['content'])} chars")

    # Show total token usage
    usage = response.get("usage", {})
    # Note: This is just the meta-resolver usage, actual total is ~3.5× this
    console.print(f"\n[dim]Meta-resolver tokens: {usage.get('total_tokens', 0)}[/dim]")
    console.print("[dim]Total cost ≈ 3.5× single call[/dim]\n")

    return str(response.get("content", ""))


def display_heavy_result(result: str) -> None:
    """Display heavy mode result with markdown formatting.

    Args:
        result: Result text to display
    """
    console.print("[bold]Final Result:[/bold]\n")
    console.print(Markdown(result))
    console.print()
