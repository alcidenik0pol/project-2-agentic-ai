"""LLM Provider abstraction layer.

This module provides a factory pattern for switching between different LLM providers
(LM Studio, Google Cloud Vertex AI, OpenAI Gemini, etc.) without changing application code.
"""

from app.analyst.providers.base import ChatToolResponse, LLMProvider, ToolCallInfo
from app.analyst.providers.gcloud import GCloudProvider
from app.analyst.providers.lm_studio import LMStudioProvider
from app.analyst.providers.openai_gemini import OpenAIGeminiProvider

# Registry of available providers
_PROVIDERS: dict[str, type[LLMProvider]] = {
    "lm_studio": LMStudioProvider,
    "gcloud": GCloudProvider,
    "openai_gemini": OpenAIGeminiProvider,
}


def get_provider(provider_name: str) -> LLMProvider:
    """Get an instance of the specified LLM provider.

    Args:
        provider_name: Name of the provider ("lm_studio" or "gcloud")

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: If provider_name is not recognized
    """
    if provider_name not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider: {provider_name}. Available: {available}"
        )

    return _PROVIDERS[provider_name]()


def register_provider(name: str, provider_class: type[LLMProvider]) -> None:
    """Register a new provider type.

    Args:
        name: Provider name to register
        provider_class: Provider class (must inherit from LLMProvider)
    """
    _PROVIDERS[name] = provider_class


__all__ = [
    "ChatToolResponse",
    "LLMProvider",
    "LMStudioProvider",
    "GCloudProvider",
    "OpenAIGeminiProvider",
    "ToolCallInfo",
    "get_provider",
    "register_provider",
]
