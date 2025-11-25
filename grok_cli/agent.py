"""Conversational agent with tool-use capabilities.

Handles the conversation loop, tool execution, and response generation.
Supports streaming responses for better UX.
Auto-saves context after each exchange for persistence.
"""

import json
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from grok_cli import config, sandbox, session
from grok_cli.models import resolve_model_name
from grok_cli.providers.grok import GrokProvider
from grok_cli.tools import TOOL_DEFINITIONS, execute_tool
from grok_cli.ui.tasks import TaskTracker

console = Console()

# Context file name
CONTEXT_FILE = "context.toon"

# Context limit (approximate tokens before warning)
CONTEXT_WARNING_THRESHOLD = 100000  # ~100k tokens

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
        self.compact_mode = cfg.get("compact_mode", False)
        self.messages: list[dict[str, Any]] = []
        self.provider: GrokProvider | None = None
        self.last_response: str = ""  # Store last response for /copy
        self.total_tokens: int = 0  # Running token count
        self.last_elapsed: float = 0.0  # Last response time
        self.task_tracker: TaskTracker = TaskTracker()  # Live task display

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

    def set_compact_mode(self, value: bool) -> None:
        """Set compact mode (hide token counts).

        Args:
            value: True for compact mode
        """
        self.compact_mode = value

    def clear_history(self, delete_context_file: bool = True) -> None:
        """Clear conversation history and optionally delete context file.

        Args:
            delete_context_file: If True, also delete the context.toon file
        """
        self.messages = []
        self.total_tokens = 0

        if delete_context_file:
            context_path = self._get_context_path()
            if context_path.exists():
                context_path.unlink()

    def _get_context_path(self) -> Path:
        """Get path to context file."""
        return config.get_project_dir() / CONTEXT_FILE

    def save_context(self) -> None:
        """Save current conversation to context.toon."""
        if not self.messages:
            return

        context_path = self._get_context_path()
        toon_content = session.messages_to_toon(self.messages)
        context_path.write_text(toon_content)

    def load_context(self) -> bool:
        """Load conversation from context.toon if it exists.

        Returns:
            True if context was loaded, False otherwise
        """
        context_path = self._get_context_path()

        if not context_path.exists():
            return False

        try:
            toon_content = context_path.read_text()
            self.messages = session.toon_to_messages(toon_content)
            # Estimate tokens from loaded messages
            self.total_tokens = sum(len(m.get("content", "")) // 4 for m in self.messages)
            return len(self.messages) > 0
        except Exception:
            return False

    def has_saved_context(self) -> bool:
        """Check if there's a saved context file."""
        return self._get_context_path().exists()

    def get_last_response(self) -> str:
        """Get the last response for clipboard copy."""
        return self.last_response

    def _estimate_tokens(self) -> int:
        """Estimate current context size in tokens (rough: 4 chars = 1 token)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in self.messages)
        return total_chars // 4

    def _check_context_warning(self) -> None:
        """Warn if approaching context limit."""
        estimated = self._estimate_tokens()
        if estimated > CONTEXT_WARNING_THRESHOLD:
            console.print(
                f"\n[yellow]Warning: Context size (~{estimated:,} tokens) is large. "
                f"Consider using /clear to start fresh.[/yellow]"
            )

    def chat(self, user_message: str) -> str:
        """Send a message and get a response with streaming, handling tool calls.

        Args:
            user_message: The user's message

        Returns:
            The assistant's final response text
        """
        provider = self._ensure_provider()
        model = resolve_model_name(self.cfg.get("default_model", "grok41_fast"))

        # Check context warning before adding new message
        self._check_context_warning()

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
        start_time = time.time()

        while iteration < max_iterations:
            iteration += 1

            # First, make a non-streaming call to check for tool use
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
                # xAI API requires content to be explicitly null or a string, not omitted
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message.content if assistant_message.content else None,
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

                # Clear previous tasks and set up new ones
                self.task_tracker.clear()

                # Create task entries for all tool calls
                tool_tasks: dict[str, int] = {}
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                        # Create descriptive task name
                        if tool_name == "read_file":
                            desc = f"Reading {args.get('path', 'file')}"
                        elif tool_name == "write_file":
                            desc = f"Writing {args.get('path', 'file')}"
                        elif tool_name == "edit_file":
                            desc = f"Editing {args.get('path', 'file')}"
                        elif tool_name == "list_files":
                            desc = f"Listing {args.get('path', '.')}"
                        else:
                            desc = tool_name
                    except json.JSONDecodeError:
                        desc = tool_name

                    task_id = self.task_tracker.add_task(desc)
                    tool_tasks[tool_call.id] = task_id

                # Show initial task panel
                self.task_tracker.print_static()

                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    task_id = tool_tasks[tool_call.id]

                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    # Mark task as in progress
                    self.task_tracker.start_task(task_id)
                    console.print(f"\n[cyan]Using tool:[/cyan] {tool_name}")

                    # Execute the tool
                    result = execute_tool(tool_name, arguments, self.auto_confirm)

                    # Update task status based on result
                    if result["success"]:
                        tool_result = result["result"]
                        self.task_tracker.complete_task(task_id)
                    else:
                        tool_result = f"Error: {result['error']}"
                        self.task_tracker.fail_task(task_id, result["error"])

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(tool_result),  # Ensure always a string
                        }
                    )

                # Show final task summary
                console.print()
                self.task_tracker.print_static()

                # Continue loop to let model respond to tool results
                continue

            # No tool calls - stream the final response
            final_content = self._stream_response(provider, model, messages)

            # Track elapsed time
            self.last_elapsed = time.time() - start_time

            # Add to conversation history
            self.messages.append({"role": "assistant", "content": final_content})

            # Store for /copy command
            self.last_response = final_content

            # Update token count (estimate since streaming doesn't give usage)
            self.total_tokens += len(final_content) // 4 + len(user_message) // 4

            # Auto-save context after each exchange
            self.save_context()

            # Show stats unless in compact mode
            if not self.compact_mode:
                console.print(
                    f"\n[dim]Time: {self.last_elapsed:.1f}s | " f"Session tokens: ~{self.total_tokens:,}[/dim]"
                )

            return final_content

        # If we hit max iterations, return what we have
        return "I encountered too many steps. Please try a simpler request."

    def _stream_response(self, provider: GrokProvider, model: str, messages: list[dict[str, Any]]) -> str:
        """Stream response from the model.

        Args:
            provider: API provider
            model: Model name
            messages: Conversation messages

        Returns:
            Complete response text
        """
        console.print()  # Newline before response

        full_response = ""

        try:
            # Use streaming API
            stream = provider.client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.7,
                max_tokens=8192,
                stream=True,
            )

            # Stream and display chunks
            for chunk in stream:
                if hasattr(chunk, "choices") and chunk.choices and chunk.choices[0].delta.content:  # type: ignore[union-attr]
                    content = chunk.choices[0].delta.content  # type: ignore[union-attr]
                    full_response += content
                    console.print(content, end="", markup=False)

            console.print()  # Final newline

        except Exception:
            # Fallback to non-streaming if streaming fails
            console.print("[dim](streaming unavailable, using standard response)[/dim]")
            response = provider.client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.7,
                max_tokens=8192,
            )
            full_response = response.choices[0].message.content or ""
            console.print(full_response)

        return full_response


def display_response(response: str) -> None:
    """Display a response with markdown formatting.

    Note: This is used for non-streaming fallback only.
    Streaming responses are displayed directly.

    Args:
        response: Response text to display
    """
    if response:
        console.print()
        console.print(Markdown(response))
        console.print()
