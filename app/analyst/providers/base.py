"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.analyst.models import ComplaintClassification, EnrichedPost


@dataclass
class ToolCallInfo:
    """Represents a single tool call requested by the LLM."""

    id: str
    name: str
    arguments: str  # JSON string of arguments


@dataclass
class ChatToolResponse:
    """Response from an LLM that may contain tool calls."""

    content: str | None = None
    tool_calls: list[ToolCallInfo] = field(default_factory=list)


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
        use_fast: bool = False,
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
        use_fast: bool = False,
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
        use_fast: bool = False,
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

    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.3,
        use_fast: bool = False,
    ) -> ChatToolResponse:
        """Send a chat request with optional tool definitions.

        The LLM may respond with text content, tool calls, or both.

        Args:
            messages: Conversation messages in OpenAI format
                [{"role": "system"|"user"|"assistant"|"tool", "content": str, ...}]
            tools: Tool definitions in OpenAI function-calling format
            temperature: Sampling temperature

        Returns:
            ChatToolResponse with content and/or tool_calls
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
