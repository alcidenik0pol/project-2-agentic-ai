"""Reddit API client using public JSON endpoints.

This module provides functions for accessing Reddit's public JSON API.
No authentication required - just use the requests library with a proper User-Agent header.

Rate limit: 10 requests per minute per IP for unauthenticated requests.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import config

logger = logging.getLogger(__name__)


class RedditPublicAPI:
    """Client for Reddit's public JSON API.

    No authentication required. Uses proper User-Agent header.
    Respects rate limit of 10 requests per minute.
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(self):
        """Initialize the API client with session and rate limiting."""
        self.session = requests.Session()

        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Set user agent
        self.session.headers.update({"User-Agent": config.reddit_user_agent})

        self._request_times: list[float] = []
        self._total_requests = 0

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limit."""
        now = time.time()

        # Clean up old request times (older than 60 seconds)
        self._request_times = [t for t in self._request_times if now - t < 60]

        # Configurable rate limit
        limit = config.reddit_requests_per_minute

        if len(self._request_times) >= limit:
            oldest = self._request_times[0]
            wait_time = 60 - (now - oldest) + 1  # +1s buffer
            logger.info(
                "Rate limit reached, waiting",
                extra={"rate_limit_status": self.get_rate_limit_status(), "wait_time": wait_time},
            )
            logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
            self._request_times = []
            logger.info(
                "Rate limit wait complete",
                extra={"rate_limit_status": self.get_rate_limit_status()},
            )

        # Optional pacing: add small delay even when not at limit
        if config.reddit_request_pacing_sleep > 0:
            time.sleep(config.reddit_request_pacing_sleep)

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a rate-limited request to Reddit API."""
        logger.debug(
            "Making API request",
            extra={"rate_limit_status": self.get_rate_limit_status(), "url": url},
        )
        self._wait_for_rate_limit()

        response = self.session.request(method, url, **kwargs)
        self._request_times.append(time.time())
        self._total_requests += 1

        return response

    @property
    def total_requests(self) -> int:
        """Total number of requests made."""
        return self._total_requests

    @property
    def requests_in_window(self) -> int:
        """Number of requests in current 60s window."""
        now = time.time()
        # Count requests within the last 60 seconds
        return sum(1 for t in self._request_times if now - t < 60)

    @property
    def requests_remaining(self) -> int:
        """Requests allowed before throttling."""
        return max(0, config.reddit_requests_per_minute - self.requests_in_window)

    @property
    def window_reset_time(self) -> float:
        """Unix timestamp when window fully resets (oldest request expires)."""
        if not self._request_times:
            return time.time()
        # Clean list to get accurate oldest time
        now = time.time()
        valid_times = [t for t in self._request_times if now - t < 60]
        if not valid_times:
            return time.time()
        return min(valid_times) + 60

    @property
    def seconds_until_reset(self) -> float:
        """Seconds until oldest request expires."""
        if not self._request_times:
            return 0.0
        now = time.time()
        valid_times = [t for t in self._request_times if now - t < 60]
        if not valid_times:
            return 0.0
        oldest = min(valid_times)
        reset_time = 60 - (now - oldest)
        return max(0.0, reset_time)

    @property
    def is_throttled(self) -> bool:
        """Currently waiting due to rate limit."""
        return self.requests_in_window >= config.reddit_requests_per_minute

    @property
    def throttle_wait_time(self) -> float | None:
        """Seconds remaining in current wait, or None if not throttled."""
        if not self.is_throttled:
            return None
        return self.seconds_until_reset

    def get_rate_limit_status(self) -> dict:
        """Get current rate limit status as a dict for frontend consumption."""
        return {
            "requests_in_window": self.requests_in_window,
            "requests_remaining": self.requests_remaining,
            "window_reset_time": self.window_reset_time,
            "seconds_until_reset": round(self.seconds_until_reset, 1),
            "is_throttled": self.is_throttled,
            "throttle_wait_time": round(self.throttle_wait_time, 1) if self.throttle_wait_time is not None else None,
            "limit": config.reddit_requests_per_minute,
            "window_seconds": 60,
        }

    def get_subreddit_info(self, subreddit: str) -> dict | None:
        """Get subreddit information including description.

        Args:
            subreddit: Subreddit name (without r/).

        Returns:
            Subreddit data dict with public_description, description, title,
            subscribers, etc. Returns None if subreddit not found or error occurs.
        """
        url = f"{self.BASE_URL}/r/{subreddit}/about.json"
        response = self._make_request("GET", url)
        response.raise_for_status()
        data = response.json()
        return data.get("data")

    def get_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 25,
        sort: str = "hot",
    ) -> list[dict]:
        """Get posts from a subreddit.

        Args:
            subreddit: Subreddit name (without r/).
            limit: Number of posts to fetch.
            sort: Sort method (hot, new, top).

        Returns:
            List of post data dictionaries (wrapped in {"kind": "t3", "data": {...}}).
        """
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = {"limit": limit}

        response = self._make_request("GET", url, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("data", {}).get("children", [])

    def search_posts(
        self,
        query: str,
        subreddit: str | None = None,
        limit: int = 25,
        sort: str = "relevance",
    ) -> list[dict]:
        """Search for posts matching a query.

        Args:
            query: Search query string.
            subreddit: Optional subreddit to search within.
            limit: Maximum results to return.
            sort: Sort method (relevance, hot, new, top).

        Returns:
            List of post data dictionaries.
        """
        if subreddit:
            # Search within specific subreddit
            url = f"{self.BASE_URL}/r/{subreddit}/search.json"
            params = {
                "q": query,
                "restrict_sr": "on",
                "limit": limit,
                "sort": sort,
            }
        else:
            # Global search
            url = f"{self.BASE_URL}/search.json"
            params = {
                "q": query,
                "limit": limit,
                "sort": sort,
            }

        response = self._make_request("GET", url, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("data", {}).get("children", [])

    def get_post_comments(
        self,
        post_id: str,
        limit: int = 25,
    ) -> list[dict]:
        """Get comments for a specific post.

        Args:
            post_id: Reddit post ID (without t3_ prefix).
            limit: Maximum comments to fetch.

        Returns:
            List containing [post_data, comments_listing].
        """
        url = f"{self.BASE_URL}/comments/{post_id}.json"
        params = {"limit": limit}

        response = self._make_request("GET", url, params=params)
        response.raise_for_status()

        data = response.json()

        # Reddit returns a list: [post_listing, comments_listing]
        return data if isinstance(data, list) else []

    def get_post_by_id(self, post_id: str) -> dict | None:
        """Get a single post by ID.

        Args:
            post_id: Reddit post ID.

        Returns:
            Post data dictionary or None.
        """
        url = f"{self.BASE_URL}/by_id/t3_{post_id}.json"

        response = self._make_request("GET", url)
        response.raise_for_status()

        data = response.json()
        children = data.get("data", {}).get("children", [])

        if children:
            return children[0].get("data", {})
        return None


# Singleton instance
reddit_client = RedditPublicAPI()
