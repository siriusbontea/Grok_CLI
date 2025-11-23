"""Grok API provider implementation using OpenAI SDK.

Uses official OpenAI SDK with Grok API endpoint compatibility.
Implements retry logic with exponential backoff for rate limits.
"""

import os
import time
from typing import Any

from openai import OpenAI, RateLimitError, APIError, AuthenticationError

from grok_cli.providers.base import Provider


class GrokProvider(Provider):
    """Grok API provider using OpenAI SDK."""

    def __init__(self, api_key: str | None = None):
        """Initialize Grok provider.

        Args:
            api_key: Grok API key (defaults to GROK_API_KEY env var)

        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("GROK_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GROK_API_KEY environment variable not set.\n"
                "Get your API key from console.grok.com and set it:\n"
                "  export GROK_API_KEY=your_key_here"
            )

        # Initialize OpenAI client with Grok endpoint
        self.client = OpenAI(base_url="https://api.x.ai/v1", api_key=self.api_key)

    @property
    def name(self) -> str:
        """Get provider name.

        Returns:
            Provider name string
        """
        return "grok"

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> dict[str, Any]:
        """Generate a completion from Grok.

        Implements retry logic with exponential backoff for rate limits.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Response dictionary with 'content', 'usage', etc.

        Raises:
            AuthenticationError: If API key is invalid
            APIError: On other API errors after retries
        """
        # Retry configuration
        max_retries = 5
        initial_delay = 1.0
        max_delay = 60.0

        for attempt in range(max_retries):
            try:
                # Make API call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Extract response data
                return {
                    "content": response.choices[0].message.content or "",
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    },
                    "model": response.model,
                    "finish_reason": response.choices[0].finish_reason,
                }

            except RateLimitError as e:
                if attempt < max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (2**attempt), max_delay)

                    # Add some jitter
                    import random

                    delay *= 0.5 + random.random()

                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    raise ValueError(
                        f"Rate limit exceeded after {max_retries} retries. "
                        f"Please try again later or check your quota at console.grok.com"
                    ) from e

            except AuthenticationError as e:
                # Don't retry authentication errors
                raise ValueError(
                    "Invalid API key. Please check your GROK_API_KEY.\n" "Get your API key from console.grok.com"
                ) from e

            except APIError as e:
                if attempt < max_retries - 1:
                    # Retry on server errors (5xx)
                    if hasattr(e, "status_code") and 500 <= e.status_code < 600:
                        delay = min(initial_delay * (2**attempt), max_delay)
                        time.sleep(delay)
                        continue

                # Don't retry client errors (4xx)
                raise

        # Should never reach here, but just in case
        raise RuntimeError("Unknown error occurred in API call")

    def list_models(self) -> list[str]:
        """List available models from Grok API.

        Returns:
            List of model identifiers
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception:
            # If API call fails, return known models
            return [
                "grok-4-1-fast-non-reasoning",
                "grok-4-1-fast-reasoning",
                "grok-4-fast-reasoning",
                "grok-4-fast-non-reasoning",
                "grok-code-fast-1",
                "grok-4",
                "grok-2-image-1212",
            ]
