"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any

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
