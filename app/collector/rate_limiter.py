"""Rate limiter for Reddit API calls.

Reddit's public API has strict rate limits:
- Unauthenticated: 10 requests per minute per IP
- Authenticated (OAuth): 60 requests per minute

This module provides a rate limiter that:
1. Tracks request timestamps
2. Calculates wait times when limits are reached
3. Logs progress clearly for long-running collections
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RedditRateLimiter:
    """Rate limiter with logging for Reddit API calls.

    Tracks requests per minute and automatically waits when limits are reached.
    Provides progress logging for long-running collection jobs.

    Attributes:
        requests_per_minute: Maximum requests allowed per minute.
        request_times: Timestamps of recent requests for tracking.
        total_requests: Total requests made since limiter creation.
        start_time: When the limiter was created (for ETA calculation).
    """

    requests_per_minute: int = 10
    request_times: list[float] = field(default_factory=list)
    total_requests: int = 0
    start_time: float = field(default_factory=time.time)

    def wait_if_needed(self) -> None:
        """Wait if rate limit has been reached.

        Calculates how long to wait based on oldest request in the window.
        Logs wait time and progress clearly.
        """
        now = time.time()
        # Keep only requests within the last 60 seconds
        self.request_times = [t for t in self.request_times if now - t < 60]

        if len(self.request_times) >= self.requests_per_minute:
            # Calculate wait time based on oldest request in window
            oldest_request = self.request_times[0]
            wait_seconds = 60 - (now - oldest_request) + 1  # +1s buffer

            if wait_seconds > 0:
                logger.info(
                    f"Rate limit reached. Waiting {wait_seconds:.1f}s before next request"
                )
                logger.debug(
                    f"  Progress: {len(self.request_times)}/{self.requests_per_minute} "
                    f"requests used in last minute"
                )
                time.sleep(wait_seconds)
                # Clear old requests after waiting
                self.request_times = [t for t in self.request_times if time.time() - t < 60]

    def record_request(self) -> None:
        """Record that a request was made."""
        now = time.time()
        self.request_times.append(now)
        self.total_requests += 1

    def log_progress(self, current: int, total: int, description: str = "") -> None:
        """Log collection progress with ETA.

        Args:
            current: Current request/item count.
            total: Total expected requests/items.
            description: Optional description of current operation.
        """
        if current == 0:
            return

        elapsed = time.time() - self.start_time
        rate = current / elapsed if elapsed > 0 else 0

        if rate > 0:
            remaining = total - current
            eta_seconds = remaining / rate
            eta_minutes = eta_seconds / 60

            desc_part = f" | {description}" if description else ""
            logger.info(
                f"Progress: {current}/{total} requests | "
                f"ETA: {eta_minutes:.1f} min | "
                f"Rate: {rate:.2f} req/s{desc_part}"
            )
        else:
            logger.info(f"Progress: {current}/{total} requests")

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.request_times = []
        self.total_requests = 0
        self.start_time = time.time()

    @property
    def requests_in_window(self) -> int:
        """Number of requests in the current 60-second window."""
        now = time.time()
        return len([t for t in self.request_times if now - t < 60])

    @property
    def can_make_request(self) -> bool:
        """Check if a request can be made without waiting."""
        return self.requests_in_window < self.requests_per_minute
