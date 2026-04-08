"""LLM Provider abstraction layer.

This module provides a factory pattern for switching between different LLM providers
(LM Studio, Google Cloud Vertex AI, etc.) without changing application code.
"""

from app.analyst.providers.base import LLMProvider
from app.analyst.providers.gcloud import GCloudProvider
from app.analyst.providers.lm_studio import LMStudioProvider

# Registry of available providers
_PROVIDERS: dict[str, type[LLMProvider]] = {
    "lm_studio": LMStudioProvider,
    "gcloud": GCloudProvider,
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
    "LLMProvider",
    "LMStudioProvider",
    "GCloudProvider",
    "get_provider",
    "register_provider",
]
