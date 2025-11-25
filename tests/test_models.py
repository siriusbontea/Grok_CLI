"""Tests for models module."""

import pytest

from grok_cli import models


def test_resolve_model_name_friendly():
    """Test resolving friendly model names."""
    api_model = models.resolve_model_name("grok41_fast")
    assert api_model == "grok-4-1-fast-non-reasoning"


def test_resolve_model_name_heavy():
    """Test resolving heavy model name."""
    api_model = models.resolve_model_name("grok41_heavy")
    assert api_model == "grok-4-1-fast-reasoning"


def test_resolve_model_name_api_string():
    """Test that API strings pass through unchanged."""
    api_model = models.resolve_model_name("grok-4-1-fast-non-reasoning")
    assert api_model == "grok-4-1-fast-non-reasoning"


def test_resolve_model_name_unknown():
    """Test that unknown models raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        models.resolve_model_name("unknown_model")

    assert "Unknown model" in str(exc_info.value)
    assert "Available models" in str(exc_info.value)


def test_get_friendly_name_known():
    """Test getting friendly name for known API model."""
    friendly = models.get_friendly_name("grok-4-1-fast-non-reasoning")
    assert friendly == "grok41_fast"


def test_get_friendly_name_unknown():
    """Test getting friendly name for unknown API model returns as-is."""
    friendly = models.get_friendly_name("some-unknown-model")
    assert friendly == "some-unknown-model"


def test_is_reasoning_model_true():
    """Test detecting reasoning models."""
    assert models.is_reasoning_model("grok41_heavy") is True
    assert models.is_reasoning_model("grok4_reasoning") is True
    assert models.is_reasoning_model("grok-4-1-fast-reasoning") is True


def test_is_reasoning_model_false():
    """Test detecting non-reasoning models."""
    assert models.is_reasoning_model("grok41_fast") is False
    assert models.is_reasoning_model("grok4_fast") is False
    assert models.is_reasoning_model("grok_code") is False


def test_list_models():
    """Test listing all available models."""
    model_list = models.list_models()

    assert len(model_list) > 0

    # Check structure of each model entry
    for model_info in model_list:
        assert "name" in model_info
        assert "api_model" in model_info
        assert "reasoning" in model_info
        assert "description" in model_info


def test_list_models_includes_grok41_fast():
    """Test that list_models includes the default model."""
    model_list = models.list_models()
    names = [m["name"] for m in model_list]

    assert "grok41_fast" in names


def test_model_map_consistency():
    """Test that MODEL_MAP and REVERSE_MODEL_MAP are consistent."""
    for friendly, api in models.MODEL_MAP.items():
        assert models.REVERSE_MODEL_MAP[api] == friendly


def test_all_models_have_descriptions():
    """Test that all models have descriptions."""
    model_list = models.list_models()

    for model_info in model_list:
        assert model_info["description"]
        assert model_info["description"] != "No description available"


def test_get_model_description():
    """Test getting model descriptions."""
    desc = models._get_model_description("grok41_fast")
    assert "fast" in desc.lower() or "default" in desc.lower()


def test_get_model_description_unknown():
    """Test getting description for unknown model."""
    desc = models._get_model_description("unknown")
    assert desc == "No description available"
