"""Conversational agent with tool-use capabilities.

Handles the conversation loop, tool execution, and response generation.
"""

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from grok_cli import config, sandbox
from grok_cli.models import resolve_model_name
from grok_cli.providers.grok import GrokProvider
from grok_cli.tools import TOOL_DEFINITIONS, execute_tool

console = Console()

# System prompt for the agent
SYSTEM_PROMPT = """You are Grok CLI, a helpful AI assistant running in a command-line interface.

You have access to tools that let you interact with the user's filesystem (within a sandboxed directory).

Current working directory: {cwd}

Available tools:
- read_file: Read contents of a file
- write_file: Create or overwrite a file
- edit_file: Make targeted edits to an existing file
- list_files: List files in a directory

Guidelines:
1. When the user asks you to create a file or write code, USE the write_file tool - don't just show the code.
2. When modifying existing files, use edit_file for targeted changes or write_file for complete rewrites.
3. Always explain what you're doing before using tools.
4. Be concise but helpful in your responses.
5. If you're unsure what the user wants, ask for clarification.
6. For general questions that don't require file operations, just respond normally without using tools.
"""


class Agent:
    """Conversational agent with tool-use capabilities."""

    def __init__(self, cfg: dict[str, Any]):
        """Initialize the agent.

        Args:
            cfg: Configuration dictionary
        """
        self.cfg = cfg
        self.auto_confirm = cfg.get("auto_yes", False)
        self.messages: list[dict[str, Any]] = []
        self.provider: GrokProvider | None = None

        # Initialize provider
        api_key = config.get_api_key()
        if api_key:
            self.provider = GrokProvider(api_key)

    def _get_system_prompt(self) -> str:
        """Get the system prompt with current directory."""
        cwd = sandbox.get_current_dir()
        return SYSTEM_PROMPT.format(cwd=cwd)

    def _ensure_provider(self) -> GrokProvider:
        """Ensure provider is initialized.

        Returns:
            GrokProvider instance

        Raises:
            ValueError: If API key not set
        """
        if self.provider is None:
            api_key = config.get_api_key()
            if not api_key:
                raise ValueError(
                    "XAI_API_KEY not set. Get your key from console.x.ai and:\n" "  export XAI_API_KEY=your_key_here"
                )
            self.provider = GrokProvider(api_key)
        return self.provider

    def set_auto_confirm(self, value: bool) -> None:
        """Set auto-confirm mode.

        Args:
            value: True to auto-confirm, False to prompt
        """
        self.auto_confirm = value

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []

    def chat(self, user_message: str) -> str:
        """Send a message and get a response, handling tool calls.

        Args:
            user_message: The user's message

        Returns:
            The assistant's final response text
        """
        provider = self._ensure_provider()
        model = resolve_model_name(self.cfg.get("default_model", "grok41_fast"))

        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        # Build messages with system prompt
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            *self.messages,
        ]

        # Conversation loop (handles multiple tool calls)
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Call the model
            with console.status("[bold green]Thinking...", spinner="dots"):
                response = provider.client.chat.completions.create(  # type: ignore[call-overload]
                    model=model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=8192,
                )

            choice = response.choices[0]
            assistant_message = choice.message

            # Check if the model wants to use tools
            if assistant_message.tool_calls:
                # Add assistant message with tool calls to history
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in assistant_message.tool_calls
                        ],
                    }
                )

                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    console.print(f"\n[cyan]Using tool:[/cyan] {tool_name}")

                    # Execute the tool
                    result = execute_tool(tool_name, arguments, self.auto_confirm)

                    # Add tool result to messages
                    if result["success"]:
                        tool_result = result["result"]
                    else:
                        tool_result = f"Error: {result['error']}"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result,
                        }
                    )

                # Continue loop to let model respond to tool results
                continue

            # No tool calls - we have the final response
            final_content = assistant_message.content or ""

            # Add to conversation history (without tool calls for simplicity)
            self.messages.append({"role": "assistant", "content": final_content})

            # Show token usage
            if response.usage:
                console.print(f"\n[dim]Tokens: {response.usage.total_tokens}[/dim]")

            return final_content

        # If we hit max iterations, return what we have
        return "I encountered too many steps. Please try a simpler request."


def display_response(response: str) -> None:
    """Display the agent's response with markdown formatting.

    Args:
        response: Response text to display
    """
    console.print()
    console.print(Markdown(response))
    console.print()
