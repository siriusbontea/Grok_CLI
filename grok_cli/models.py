"""Model name mapping and management.

Maps user-friendly names to actual API model strings.
"""

from typing import Any

# Model name mapping (user-friendly → API string)
MODEL_MAP = {
    "grok41_fast": "grok-4-1-fast-non-reasoning",
    "grok41_heavy": "grok-4-1-fast-reasoning",
    "grok4_fast": "grok-4-fast-non-reasoning",
    "grok4_reasoning": "grok-4-fast-reasoning",
    "grok_code": "grok-code-fast-1",
    "grok4": "grok-4",
    "grok2_image": "grok-2-image-1212",
}

# Reverse mapping (API string → user-friendly name)
REVERSE_MODEL_MAP = {v: k for k, v in MODEL_MAP.items()}


def resolve_model_name(name: str) -> str:
    """Resolve a user-friendly model name to API model string.

    Args:
        name: User-friendly name or API string

    Returns:
        API model string

    Raises:
        ValueError: If model name is unknown
    """
    # If it's already an API string, return as-is
    if name in REVERSE_MODEL_MAP:
        return name

    # Try to resolve from friendly name
    if name in MODEL_MAP:
        return MODEL_MAP[name]

    # Unknown model
    raise ValueError(
        f"Unknown model: {name}\n"
        f"Available models: {', '.join(MODEL_MAP.keys())}\n"
        f"Or use API model string directly"
    )


def get_friendly_name(api_model: str) -> str:
    """Get friendly name for an API model string.

    Args:
        api_model: API model string

    Returns:
        User-friendly name or API string if no mapping
    """
    return REVERSE_MODEL_MAP.get(api_model, api_model)


def is_reasoning_model(model: str) -> bool:
    """Check if a model uses reasoning (heavy mode).

    Args:
        model: Model name (friendly or API string)

    Returns:
        True if model uses reasoning
    """
    api_model = resolve_model_name(model)
    # Check for "-reasoning" suffix but not "non-reasoning"
    return "reasoning" in api_model and "non-reasoning" not in api_model


def list_models() -> list[dict[str, Any]]:
    """List all available models.

    Returns:
        List of model info dictionaries
    """
    models = []
    for friendly, api in MODEL_MAP.items():
        models.append(
            {
                "name": friendly,
                "api_model": api,
                "reasoning": is_reasoning_model(api),
                "description": _get_model_description(friendly),
            }
        )
    return models


def _get_model_description(friendly_name: str) -> str:
    """Get description for a model.

    Args:
        friendly_name: User-friendly model name

    Returns:
        Description string
    """
    descriptions = {
        "grok41_fast": "Default fast model (non-reasoning, cheapest)",
        "grok41_heavy": "Heavy reasoning model (parallel agents)",
        "grok4_fast": "Grok 4 fast (non-reasoning)",
        "grok4_reasoning": "Grok 4 with reasoning",
        "grok_code": "Code-optimized model",
        "grok4": "Grok 4 base model",
        "grok2_image": "Image understanding model",
    }
    return descriptions.get(friendly_name, "No description available")
