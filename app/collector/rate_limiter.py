"""Rate limiter for Reddit API calls.

Reddit's public API rate limit:
- Unauthenticated: 100 requests per 10 minutes per IP

Uses even pacing: minimum interval between every request to avoid WAF blocking.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RedditRateLimiter:
    """Rate limiter with even pacing for Reddit API calls.

    Paces requests at a minimum interval to avoid burst patterns.
    Default: 100 requests per 10 minutes = 6 seconds between requests.

    Attributes:
        requests_per_window: Maximum requests allowed in the window.
        window_seconds: Duration of the rate limit window in seconds.
        min_interval: Minimum seconds between consecutive requests.
        request_times: Timestamps of recent requests for tracking.
        total_requests: Total requests made since limiter creation.
        start_time: When the limiter was created (for ETA calculation).
    """

    requests_per_window: int = 100
    window_seconds: int = 600  # 10 minutes
    min_interval: float = 6.0  # 600s / 100 requests
    request_times: list[float] = field(default_factory=list)
    total_requests: int = 0
    start_time: float = field(default_factory=time.time)

    def wait_if_needed(self) -> None:
        """Wait to ensure minimum interval between requests.

        Paces every request at least min_interval seconds apart.
        No bursting — consistent, human-like request pattern.
        """
        now = time.time()

        # Wait if last request was too recent
        if self.request_times:
            last_request = self.request_times[-1]
            elapsed = now - last_request

            if elapsed < self.min_interval:
                wait_seconds = self.min_interval - elapsed
                logger.info(
                    f"[Reddit API] Pacing: waiting {wait_seconds:.1f}s "
                    f"(min interval: {self.min_interval}s)"
                )
                time.sleep(wait_seconds)

        # Clean old request times (keep only current window)
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < self.window_seconds]

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
                f"[Reddit API] Progress: {current}/{total} requests | "
                f"ETA: {eta_minutes:.1f} min | "
                f"Rate: {rate:.2f} req/s{desc_part}"
            )
        else:
            logger.info(f"[Reddit API] Progress: {current}/{total} requests")

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.request_times = []
        self.total_requests = 0
        self.start_time = time.time()

    @property
    def requests_in_window(self) -> int:
        """Number of requests in the current window."""
        now = time.time()
        return len([t for t in self.request_times if now - t < self.window_seconds])

    @property
    def can_make_request(self) -> bool:
        """Check if a request can be made without waiting."""
        if not self.request_times:
            return True
        elapsed = time.time() - self.request_times[-1]
        return elapsed >= self.min_interval
