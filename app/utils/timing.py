"""Timing utilities for performance monitoring."""

import functools
import logging
import time
from typing import Any, Callable

from app.config import config

logger = logging.getLogger(__name__)


def timed(operation_name: str | None = None):
    """Decorator to time function execution and log results.

    Args:
        operation_name: Custom name for logging. Defaults to function name.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not config.agent_enable_timing:
                return func(*args, **kwargs)

            name = operation_name or func.__name__
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"[TIMING] {name} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"[TIMING] {name} failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator
