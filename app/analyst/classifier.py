"""Core classification logic for Reddit posts using configurable LLM providers.

This module provides a unified interface for classifying Reddit posts using
different LLM backends (LM Studio, Google Cloud Vertex AI, etc.).

Posts are classified in PARALLEL using ThreadPoolExecutor when
classification_enable_parallel=True (default).
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.analyst.models import ClassificationResult, EnrichedPost
from app.analyst.providers import get_provider
from app.analyst.providers.base import LLMProvider
from app.config import config

logger = logging.getLogger(__name__)


class PostClassifier:
    """Classifies Reddit posts using configurable LLM providers.

    Requests are processed in PARALLEL using ThreadPoolExecutor when
    classification_enable_parallel=True (default). Each worker thread
    makes independent LLM API calls, enabling significant throughput
    improvements over sequential execution.
    """

    def __init__(
        self,
        provider_name: str | None = None,
        request_delay: float = 1.0,
    ):
        """Initialize the classifier with the specified LLM provider.

        Args:
            provider_name: LLM provider name ("gcloud" or "lm_studio").
                          Defaults to config.llm_provider.
            request_delay: Only used in sequential fallback mode.
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
            use_fast=True,
        )

    def classify_batch(
        self,
        posts: list[dict[str, Any]],
        progress_callback: Any = None,
        max_consecutive_failures: int = 0,
        stop_on_failure_callback: Any = None,
    ) -> ClassificationResult:
        """Classify a batch of posts with progress tracking.

        Uses ThreadPoolExecutor for parallel execution when enabled via config.
        Falls back to sequential processing when parallel is disabled or there
        is only one post.

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
        total = len(posts)
        llm_time = 0.0

        use_parallel = config.classification_enable_parallel and total > 1

        if use_parallel:
            enriched_posts, stopped_early, llm_time = self._classify_parallel(
                posts, total, progress_callback, max_consecutive_failures,
                stop_on_failure_callback,
            )
        else:
            enriched_posts, stopped_early, llm_time = self._classify_sequential(
                posts, total, progress_callback, max_consecutive_failures,
                stop_on_failure_callback,
            )

        elapsed = time.time() - start_time
        successful = sum(1 for p in enriched_posts if p.classification)

        # In parallel mode, wall time < total LLM time (threads run concurrently).
        # "serialization_overhead" doesn't apply — use "concurrency_savings" instead.
        if use_parallel:
            timing_label = "concurrency_savings"
            timing_value = round(llm_time - elapsed, 2)
        else:
            timing_label = "serialization_overhead"
            timing_value = round(elapsed - llm_time, 2)

        result = ClassificationResult(
            posts=enriched_posts,
            model_used=f"{self._provider_name}:{self._provider.model_name}",
            processing_time_seconds=elapsed,
            substep_timing={
                "llm_calls": round(llm_time, 2),
                timing_label: timing_value,
                "total_calls": len(enriched_posts),
                "avg_time_per_call": round(llm_time / len(enriched_posts), 3) if enriched_posts else 0,
                "parallel": use_parallel,
                "max_workers": min(config.classification_max_workers, total) if use_parallel else 1,
                "throughput": round(len(enriched_posts) / elapsed, 2) if elapsed > 0 else 0,
            },
        )

        logger.info(
            f"Classification complete: {successful}/{total} successful | "
            f"Time: {elapsed:.1f}s | "
            f"Mode: {'parallel' if use_parallel else 'sequential'}"
        )

        return result

    def _classify_parallel(
        self,
        posts: list[dict[str, Any]],
        total: int,
        progress_callback: Any,
        max_consecutive_failures: int,
        stop_on_failure_callback: Any,
    ) -> tuple[list[EnrichedPost], bool, float]:
        """Classify posts in parallel using ThreadPoolExecutor.

        Returns:
            Tuple of (enriched_posts, stopped_early, total_llm_time)
        """
        max_workers = min(config.classification_max_workers, total, 20)
        request_timeout = config.classification_request_timeout

        logger.info(
            f"Starting PARALLEL classification of {total} posts "
            f"(workers={max_workers}, timeout={request_timeout}s)..."
        )

        results: dict[int, EnrichedPost] = {}
        consecutive_failures = 0
        stopped_early = False
        llm_time = 0.0
        completed_count = 0
        lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    self._classify_post_timed,
                    post_data=post_item["post"],
                    subreddit=post_item["subreddit"],
                    category=post_item["category"],
                    comments_count=post_item.get("comments_count", 0),
                ): idx
                for idx, post_item in enumerate(posts)
            }

            for future in as_completed(future_to_index):
                if stopped_early:
                    break

                idx = future_to_index[future]
                try:
                    enriched, call_time = future.result(timeout=request_timeout)

                    with lock:
                        results[idx] = enriched
                        llm_time += call_time
                        completed_count += 1

                        if not enriched.classification:
                            consecutive_failures += 1
                            if max_consecutive_failures > 0 and consecutive_failures >= max_consecutive_failures:
                                logger.error(
                                    f"Stopping: {consecutive_failures} consecutive failures. "
                                    f"Processed {completed_count}/{total} posts."
                                )
                                if stop_on_failure_callback:
                                    stop_on_failure_callback(completed_count, total, consecutive_failures)
                                stopped_early = True
                                for f in future_to_index:
                                    f.cancel()
                                break
                        else:
                            consecutive_failures = 0

                        # Progress logging every 10 posts
                        if completed_count % 10 == 0 or completed_count == total:
                            elapsed = time.time() - results.get("_start_time", time.time())
                            rate = completed_count / elapsed if elapsed > 0 else 0
                            success_count = sum(1 for p in results.values() if isinstance(p, EnrichedPost) and p.classification)
                            logger.info(
                                f"Progress: {completed_count}/{total} ({completed_count/total*100:.1f}%) | "
                                f"Success: {success_count}/{completed_count} | "
                                f"Rate: {rate:.1f} posts/s"
                            )

                            if progress_callback:
                                progress_callback(completed_count, total, enriched)

                except Exception as e:
                    logger.error(f"Classification failed for post {idx}: {e}")
                    with lock:
                        completed_count += 1
                        consecutive_failures += 1

        # Build ordered list from results dict
        enriched_posts = [results[i] for i in range(total) if i in results]

        return enriched_posts, stopped_early, llm_time

    def _classify_post_timed(
        self,
        post_data: dict[str, Any],
        subreddit: str,
        category: str,
        comments_count: int,
    ) -> tuple[EnrichedPost, float]:
        """Classify a single post and return with timing data.

        Returns:
            Tuple of (EnrichedPost, call_duration_seconds)
        """
        call_start = time.time()
        enriched = self.classify_post(
            post_data=post_data,
            subreddit=subreddit,
            category=category,
            comments_count=comments_count,
        )
        call_time = time.time() - call_start
        return enriched, call_time

    def _classify_sequential(
        self,
        posts: list[dict[str, Any]],
        total: int,
        progress_callback: Any,
        max_consecutive_failures: int,
        stop_on_failure_callback: Any,
    ) -> tuple[list[EnrichedPost], bool, float]:
        """Classify posts sequentially (original behavior, used as fallback).

        Returns:
            Tuple of (enriched_posts, stopped_early, total_llm_time)
        """
        enriched_posts: list[EnrichedPost] = []
        consecutive_failures = 0
        stopped_early = False
        llm_time = 0.0

        logger.info(f"Starting SEQUENTIAL classification of {total} posts...")

        for i, post_item in enumerate(posts, 1):
            call_start = time.time()
            enriched = self.classify_post(
                post_data=post_item["post"],
                subreddit=post_item["subreddit"],
                category=post_item["category"],
                comments_count=post_item.get("comments_count", 0),
            )
            llm_time += time.time() - call_start
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
                elapsed = time.time() - enriched_posts[0].__dict__.get("_start_time", time.time())
                rate = i / elapsed if elapsed > 0 else 0

                logger.info(
                    f"Progress: {i}/{total} ({i/total*100:.1f}%) | "
                    f"Success: {success_count}/{i} | "
                    f"Rate: {rate:.1f} posts/s"
                )

                if progress_callback:
                    progress_callback(i, total, enriched)

            # Rate limiting delay
            if i < total:
                time.sleep(self.request_delay)

        return enriched_posts, stopped_early, llm_time
