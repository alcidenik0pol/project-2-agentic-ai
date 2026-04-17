"""Exponential backoff retry decorator for LLM API calls.

Provides a reusable decorator that retries on transient errors (429, 500, 502,
503, 504) with exponential backoff and jitter. Applied to all provider methods
that call external LLM APIs.

Retry behavior (default: 5 attempts, 1s initial backoff, 2x multiplier):
    Attempt 1: Immediate
    Attempt 2: Wait ~1.0s
    Attempt 3: Wait ~2.0s
    Attempt 4: Wait ~4.0s
    Attempt 5: Wait ~8.0s
"""

import functools
import logging
import random
import time
from typing import Any, Callable

from app.config import config

logger = logging.getLogger(__name__)

# HTTP status codes that indicate transient errors worth retrying
RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retriable_error(exc: Exception) -> bool:
    """Check if an exception is worth retrying.

    Handles:
    - OpenAI SDK RateLimitError, APIConnectionError, APITimeoutError
    - requests HTTPError with retriable status codes
    - Generic exceptions with status_code attribute
    """
    exc_type = type(exc).__name__
    exc_module = type(exc).__module__

    # OpenAI SDK errors
    if "openai" in exc_module:
        if exc_type in ("RateLimitError", "APIConnectionError", "APITimeoutError"):
            return True
        if exc_type == "APIStatusError" and hasattr(exc, "status_code"):
            return exc.status_code in RETRIABLE_STATUS_CODES

    # requests HTTPError
    if exc_type == "HTTPError" and hasattr(exc, "response"):
        if exc.response is not None and hasattr(exc.response, "status_code"):
            return exc.response.status_code in RETRIABLE_STATUS_CODES

    # Generic: check for status_code attribute (e.g. httpx, google API errors)
    if hasattr(exc, "status_code"):
        return exc.status_code in RETRIABLE_STATUS_CODES

    return False


def _calculate_backoff(
    attempt: int,
    initial_backoff: float,
    multiplier: float,
    max_backoff: float,
    enable_jitter: bool,
) -> float:
    """Calculate backoff duration for a given attempt number (1-indexed)."""
    backoff = initial_backoff * (multiplier ** (attempt - 1))
    backoff = min(backoff, max_backoff)

    if enable_jitter:
        jitter_range = backoff * 0.1
        backoff += random.uniform(-jitter_range, jitter_range)

    return max(0.1, backoff)


def retry_with_exponential_backoff(
    max_attempts: int | None = None,
    initial_backoff: float | None = None,
    max_backoff: float | None = None,
    backoff_multiplier: float | None = None,
    enable_jitter: bool | None = None,
) -> Callable:
    """Decorator that retries a function with exponential backoff.

    All parameters default to values from config, which in turn default to
    sensible values. Override any parameter for specific methods.

    Args:
        max_attempts: Maximum number of attempts (default from config, 5).
        initial_backoff: First retry wait in seconds (default from config, 1.0).
        max_backoff: Maximum wait between retries in seconds (default from config, 60.0).
        backoff_multiplier: Multiplier for each subsequent retry (default from config, 2.0).
        enable_jitter: Add ±10% randomness to prevent thundering herd (default from config, True).
    """
    _max_attempts = max_attempts if max_attempts is not None else config.retry_max_attempts
    _initial_backoff = initial_backoff if initial_backoff is not None else config.retry_initial_backoff_seconds
    _max_backoff = max_backoff if max_backoff is not None else config.retry_max_backoff_seconds
    _multiplier = backoff_multiplier if backoff_multiplier is not None else config.retry_backoff_multiplier
    _jitter = enable_jitter if enable_jitter is not None else config.retry_enable_jitter

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__qualname__

            for attempt in range(1, _max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    is_retriable = _is_retriable_error(exc)

                    if not is_retriable or attempt >= _max_attempts:
                        if attempt >= _max_attempts and is_retriable:
                            logger.error(
                                "Max retries (%d) exceeded for %s: %s",
                                _max_attempts, func_name, exc,
                            )
                        raise

                    backoff = _calculate_backoff(
                        attempt, _initial_backoff, _multiplier,
                        _max_backoff, _jitter,
                    )
                    logger.warning(
                        "Retryable error in %s (attempt %d/%d): %s. "
                        "Retrying in %.1fs...",
                        func_name, attempt, _max_attempts,
                        type(exc).__name__, backoff,
                    )
                    time.sleep(backoff)

            # Should not reach here, but safety net
            return func(*args, **kwargs)

        return wrapper
    return decorator
