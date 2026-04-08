"""Core classification logic for Reddit posts using configurable LLM providers.

This module provides a unified interface for classifying Reddit posts using
different LLM backends (LM Studio, Google Cloud Vertex AI, etc.).
"""

import logging
import time
from typing import Any

from app.analyst.models import ClassificationResult, EnrichedPost
from app.analyst.providers import get_provider
from app.analyst.providers.base import LLMProvider
from app.config import config

logger = logging.getLogger(__name__)


class PostClassifier:
    """Classifies Reddit posts using configurable LLM providers."""

    def __init__(
        self,
        provider_name: str | None = None,
        request_delay: float = 1.0,
    ):
        """Initialize the classifier with the specified LLM provider.

        Note: Requests are processed SEQUENTIALLY - each request blocks until
        the response is received before the next one is sent.

        Args:
            provider_name: LLM provider name ("gcloud" or "lm_studio").
                          Defaults to config.llm_provider.
            request_delay: Small delay between requests in seconds (default: 1.0)
        """
        self._provider_name = provider_name or config.llm_provider
        self._provider: LLMProvider = get_provider(self._provider_name)
        self.request_delay = request_delay

        logger.info(f"PostClassifier initialized with provider: {self._provider_name}")
        logger.info(f"Model: {self._provider.model_name}")

    @property
    def provider(self) -> LLMProvider:
        """Get the underlying LLM provider."""
        return self._provider

    @property
    def model_name(self) -> str:
        """Get the model name being used."""
        return self._provider.model_name

    def classify_post(
        self,
        post_data: dict[str, Any],
        subreddit: str,
        category: str,
        comments_count: int,
    ) -> EnrichedPost:
        """Classify a single Reddit post.

        Delegates to the configured provider for actual classification.

        Args:
            post_data: Raw post dictionary from Reddit API
            subreddit: Subreddit name
            category: Post category
            comments_count: Number of comments fetched

        Returns:
            EnrichedPost with classification or error details
        """
        return self._provider.classify_post(
            post_data=post_data,
            subreddit=subreddit,
            category=category,
            comments_count=comments_count,
        )

    def classify_batch(
        self,
        posts: list[dict[str, Any]],
        progress_callback: Any = None,
        max_consecutive_failures: int = 0,
        stop_on_failure_callback: Any = None,
    ) -> ClassificationResult:
        """Classify a batch of posts with progress tracking.

        Args:
            posts: List of post dictionaries with structure:
                   {subreddit, category, post, comments_count}
            progress_callback: Optional callback for progress updates
            max_consecutive_failures: Stop after N consecutive failures (0 = disabled)
            stop_on_failure_callback: Optional callback when stopping due to failures

        Returns:
            ClassificationResult with all enriched posts and metadata
        """
        start_time = time.time()
        enriched_posts: list[EnrichedPost] = []
        total = len(posts)
        consecutive_failures = 0
        stopped_early = False

        logger.info(f"Starting classification of {total} posts...")
        logger.info(f"Provider: {self._provider_name}, Model: {self._provider.model_name}")

        for i, post_item in enumerate(posts, 1):
            # Classify the post
            enriched = self.classify_post(
                post_data=post_item["post"],
                subreddit=post_item["subreddit"],
                category=post_item["category"],
                comments_count=post_item.get("comments_count", 0),
            )
            enriched_posts.append(enriched)

            # Track consecutive failures for early stopping
            if not enriched.classification:
                consecutive_failures += 1
                if max_consecutive_failures > 0 and consecutive_failures >= max_consecutive_failures:
                    logger.error(
                        f"Stopping: {consecutive_failures} consecutive failures. "
                        f"Processed {i}/{total} posts."
                    )
                    if stop_on_failure_callback:
                        stop_on_failure_callback(i, total, consecutive_failures)
                    stopped_early = True
                    break
            else:
                consecutive_failures = 0

            # Progress logging
            if i % 10 == 0 or i == total:
                success_count = sum(1 for p in enriched_posts if p.classification)
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (total - i) / rate if rate > 0 else 0

                logger.info(
                    f"Progress: {i}/{total} ({i/total*100:.1f}%) | "
                    f"Success: {success_count}/{i} | "
                    f"Rate: {rate:.1f} posts/s | "
                    f"ETA: {eta:.0f}s"
                )

                if progress_callback:
                    progress_callback(i, total, enriched)

            # Rate limiting delay
            if i < total:
                time.sleep(self.request_delay)

        elapsed = time.time() - start_time

        result = ClassificationResult(
            posts=enriched_posts,
            model_used=f"{self._provider_name}:{self._provider.model_name}",
            processing_time_seconds=elapsed,
        )

        logger.info(
            f"Classification complete: {result.successful_classifications}/{total} successful | "
            f"Time: {elapsed:.1f}s"
        )

        return result
