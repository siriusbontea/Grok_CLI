"""Base provider interface for model backends."""

from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """Abstract base class for model providers."""

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> dict[str, Any]:
        """Generate a completion from the model.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Response dictionary with 'content', 'usage', etc.

        Raises:
            Exception: On API errors
        """
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models from this provider.

        Returns:
            List of model identifiers
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get provider name.

        Returns:
            Provider name string
        """
        pass
