# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: REDDIT V2 (old.reddit.com HTML scraper)
# Scrapes old.reddit.com HTML instead of the dead .json endpoints.
# Session/retry/proxy/pacing/rate-limit logic is intentionally identical to
# app/reddit/client.py so it behaves the same under the rate-limit UI.
# ═══════════════════════════════════════════════════════════════════════════
"""Reddit HTML-scraping client (old.reddit.com).

Reddit killed the public ``.json`` endpoints (they now return 403). This client
scrapes ``old.reddit.com`` HTML, which still returns 200 and exposes every field
we need via ``data-*`` attributes.

The HTTP layer (Session, Retry, HTTPAdapter, User-Agent, proxy, pacing,
rate-limit bookkeeping) is copied from :mod:`app.reddit.client` so the existing
rate-limit tracker and UI work unchanged. Only the three data-access methods
differ: they GET HTML and delegate to :mod:`app.reddit_v2.redditapiv2_parser`.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import config
from app.reddit_v2.redditapiv2_parser import (
    parse_comments_page,
    parse_post_listing,
    parse_subreddit_about,
)

logger = logging.getLogger(__name__)


class RedditAPIv2Client:
    """Client that scrapes old.reddit.com HTML.

    Shares the same pacing/rate-limit contract as :class:`app.reddit.client.RedditPublicAPI`,
    so :mod:`backend.app.services.rate_limit_tracker` can poll either one.
    """

    BASE_URL = "https://old.reddit.com"

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

        # Configure proxy if enabled
        if config.proxy_enabled and config.proxy_url:
            self.session.proxies = {
                "http": config.proxy_url,
                "https": config.proxy_url,
            }
            logger.info(f"[PROXY] Enabled: {config.proxy_url}")

        self._request_times: list[float] = []
        self._total_requests = 0

    def _pace_request(self, url: str) -> None:
        """Ensure minimum interval between requests (no bursting).

        Reddit allows 100 requests per 10 minutes. Instead of bursting
        then waiting, we pace every request at minimum 6 seconds apart.
        """
        now = time.time()

        # Wait if last request was too recent
        if self._request_times:
            last_request = self._request_times[-1]
            elapsed = now - last_request
            min_interval = config.reddit_min_request_interval_seconds

            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.info(f"[Reddit V2] Rate limit: waiting {wait_time:.1f}s before request to {url}")
                time.sleep(wait_time)

        # Clean old request times (keep 10-minute window)
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 600]

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a paced request to Reddit."""
        logger.debug(
            "Making API request",
            extra={"rate_limit_status": self.get_rate_limit_status(), "url": url},
        )
        self._pace_request(url)

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
        """Number of requests in current 600s (10 min) window."""
        now = time.time()
        return sum(1 for t in self._request_times if now - t < 600)

    @property
    def requests_remaining(self) -> int:
        """Requests allowed before hitting 100-per-10min limit."""
        return max(0, config.reddit_requests_per_10min - self.requests_in_window)

    @property
    def window_reset_time(self) -> float:
        """Unix timestamp when window fully resets (oldest request expires)."""
        if not self._request_times:
            return time.time()
        now = time.time()
        valid_times = [t for t in self._request_times if now - t < 600]
        if not valid_times:
            return time.time()
        return min(valid_times) + 600

    @property
    def seconds_until_reset(self) -> float:
        """Seconds until oldest request expires."""
        if not self._request_times:
            return 0.0
        now = time.time()
        valid_times = [t for t in self._request_times if now - t < 600]
        if not valid_times:
            return 0.0
        oldest = min(valid_times)
        reset_time = 600 - (now - oldest)
        return max(0.0, reset_time)

    @property
    def seconds_until_next_request(self) -> float:
        """Seconds until next request can be made (6-second pacing)."""
        if not self._request_times:
            return 0.0
        now = time.time()
        last_request = self._request_times[-1]
        elapsed = now - last_request
        min_interval = config.reddit_min_request_interval_seconds
        return max(0.0, min_interval - elapsed)

    @property
    def is_throttled(self) -> bool:
        """Currently waiting due to rate limit."""
        return self.requests_in_window >= config.reddit_requests_per_10min

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
            "limit": config.reddit_requests_per_10min,
            "window_seconds": 600,
            "seconds_until_next_request": round(self.seconds_until_next_request, 1),
        }

    # ─── data-access methods (HTML scraping, delegate to parser) ───

    def get_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 25,
        sort: str = "hot",
    ) -> list[dict]:
        """Get posts from a subreddit by scraping the old.reddit HTML listing.

        Returns a list of post wrappers ``[{"kind": "t3", "data": {...}}, ...]``.
        """
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}/"
        response = self._make_request("GET", url)
        response.raise_for_status()
        posts = parse_post_listing(response.text)
        return posts[:limit]

    def get_post_comments(
        self,
        post_id: str,
        limit: int = 25,
    ) -> list[dict]:
        """Get comments for a post by scraping its old.reddit comments page.

        Returns the same 2-element shape the JSON API returned:
        ``[{"data": {"children": [post]}}, {"data": {"children": [comments]}}]``.
        The fetcher reads element ``[1]``. Only top-level comments are included.
        """
        url = f"{self.BASE_URL}/comments/{post_id}/"
        response = self._make_request("GET", url)
        response.raise_for_status()

        post_data, comments = parse_comments_page(response.text)
        return [
            {"data": {"children": [{"kind": "t3", "data": post_data}]}},
            {"data": {"children": comments[:limit]}},
        ]

    def get_subreddit_info(self, subreddit: str) -> dict | None:
        """Get subreddit info by scraping the old.reddit about page.

        Returns None on 404 (old.reddit about is frequently gated for
        unauthenticated access) or any other error.
        """
        url = f"{self.BASE_URL}/r/{subreddit}/about/"
        response = self._make_request("GET", url)
        if response.status_code == 404:
            logger.debug(f"[Reddit V2] /r/{subreddit}/about/ returned 404")
            return None
        response.raise_for_status()
        return parse_subreddit_about(response.text)


# Singleton instance
redditapiv2_client = RedditAPIv2Client()
