"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from app.analyst.models import ComplaintClassification, EnrichedPost


class LLMProvider(ABC):
    """Abstract base class for LLM classification providers.

    All LLM providers (LM Studio, Google Cloud, etc.) must implement this interface.
    """

    @abstractmethod
    def classify_post(
        self,
        post_data: dict[str, Any],
        subreddit: str,
        category: str,
        comments_count: int,
    ) -> EnrichedPost:
        """Classify a single Reddit post.

        Args:
            post_data: Raw post dictionary from Reddit API
            subreddit: Subreddit name
            category: Post category
            comments_count: Number of comments fetched

        Returns:
            EnrichedPost with classification or error details
        """
        pass

    @abstractmethod
    def parse_classification(self, raw_response: str) -> ComplaintClassification | None:
        """Parse LLM response into classification.

        Args:
            raw_response: Raw text from LLM

        Returns:
            ComplaintClassification or None if parsing fails
        """
        pass

    @abstractmethod
    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str | None:
        """Generate raw text from LLM.

        Args:
            prompt: The text prompt to send.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text, or None on failure.
        """
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | None:
        """Generate structured JSON from LLM.

        Args:
            prompt: The text prompt to send.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated JSON string, or None on failure.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name/identifier being used."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'lm_studio', 'gcloud')."""
        pass
