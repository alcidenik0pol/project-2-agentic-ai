# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: REDDIT V3 (www.reddit.com Atom RSS feeds)
# Reddit killed all unauthenticated .json + old.reddit.com access in July 2026
# (HTTP 302 → /login?reason=lor2 sitewide; HTTP 403 on www.reddit.com/.json
# for all UAs). The only unauthenticated surface left is the Atom feed.
# Session/retry/proxy/pacing/rate-limit logic is intentionally identical to
# app/reddit_v2/redditapiv2_client.py so the existing rate-limit UI keeps
# working.
# ═══════════════════════════════════════════════════════════════════════════
"""Reddit RSS-scraping client (www.reddit.com Atom feeds).

Reddit rolled out a sitewide login wall on 2026-07-XX: every unauthenticated
request to ``old.reddit.com/r/X/...`` returns HTTP 302 → ``/login?reason=lor2``,
and every ``www.reddit.com/r/X.json`` returns HTTP 403 with the modern web UI
shell (regardless of User-Agent). The IPVanish SOCKS5 proxy cannot help
because the wall is served to all unauthenticated clients, not just data
center IPs.

The only unauthenticated public surface left is the Atom feed:
- Listing: ``GET /r/{subreddit}/{sort}.rss?limit=N`` (sort ∈ hot/new/top)
- Search:  ``GET /r/{subreddit}/search.rss?q=...&restrict_sr=1``
- Comments: ``GET /comments/{post_id}/.rss?limit=N``

The HTTP layer (Session, Retry, HTTPAdapter, User-Agent, proxy, pacing,
rate-limit bookkeeping) is copied from :mod:`app.reddit_v2.redditapiv2_client`
so the existing rate-limit tracker and UI work unchanged. Only the data-access
methods differ: they GET Atom XML and delegate to
:mod:`app.reddit_v3.redditapiv3_parser`.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib.parse import quote_plus
from urllib3.util.retry import Retry

from app.config import config
from app.reddit.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from app.reddit_v3.redditapiv3_parser import (
    parse_comments_page,
    parse_post_listing,
)

logger = logging.getLogger(__name__)


class RedditAPIv3Client:
    """Client that scrapes www.reddit.com Atom RSS feeds.

    Shares the same pacing/rate-limit contract as
    :class:`app.reddit_v2.redditapiv2_client.RedditAPIv2Client`, so
    :mod:`backend.app.services.rate_limit_tracker` can poll either one.
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(self):
        """Initialize the API client with session and rate limiting."""
        self.session = requests.Session()

        # Set up retry strategy. Note: 429 and 403 are NOT retried.
        # - 403 is Reddit's WAF block; it's sticky and retrying just burns
        #   the rate-limit budget.
        # - 429 retried via urllib3 means each user-level request becomes 4
        #   HTTP attempts in rapid succession, which makes throttling worse.
        #   The circuit breaker in _make_request handles 429s at the right
        #   level (process-wide cooldown instead of per-request retry).
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Set user agent
        self.session.headers.update({"User-Agent": config.reddit_user_agent})

        # Configure proxy if enabled (kept identical to v1/v2 so prod can
        # still route through IPVanish if we later find a UA the WAF accepts).
        if config.proxy_enabled and config.proxy_url:
            self.session.proxies = {
                "http": config.proxy_url,
                "https": config.proxy_url,
            }
            logger.info(f"[PROXY] Enabled: {config.proxy_url}")

        self._request_times: list[float] = []
        self._total_requests = 0

        # Shared circuit breaker — sees the aggregate 429 rate across all
        # concurrent pipeline runs that funnel through this singleton.
        self._breaker = CircuitBreaker()

    def _pace_request(self, url: str) -> None:
        """Ensure minimum interval between requests (no bursting).

        Reddit allows 100 requests per 10 minutes. We pace every request at
        minimum 6 seconds apart (matches the v1/v2 contract).
        """
        now = time.time()

        if self._request_times:
            last_request = self._request_times[-1]
            elapsed = now - last_request
            min_interval = config.reddit_min_request_interval_seconds

            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.info(
                    f"[Reddit V3] Rate limit: waiting {wait_time:.1f}s before request to {url}"
                )
                time.sleep(wait_time)

        # Clean old request times (keep 10-minute window)
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 600]

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a paced request to Reddit.

        Passes through the shared circuit breaker: blocks during 429 cooldowns
        and fails fast with ``CircuitBreakerOpen`` once the breaker trips.
        """
        logger.debug(
            "Making API request",
            extra={"rate_limit_status": self.get_rate_limit_status(), "url": url},
        )
        # Gate: blocks during cooldown, raises CircuitBreakerOpen if tripped.
        self._breaker.before_request()
        self._pace_request(url)

        try:
            response = self.session.request(method, url, **kwargs)
        except RequestException as e:
            # urllib3 Retry exhaustion (500/502/503/504) surfaces here. 429 is
            # no longer in status_forcelist (it made throttling worse), so the
            # only way a 429 reaches this branch is via connection-level errors.
            if "429" in str(e):
                self._breaker.on_429()
            raise

        # Detect 429 on the response status (the common path now that 429 is
        # not in status_forcelist). Counting it via the breaker is what gates
        # the next _pace_request from hammering Reddit.
        if response.status_code == 429:
            self._breaker.on_429()
        else:
            self._breaker.on_success()
        self._request_times.append(time.time())
        self._total_requests += 1

        return response

    @property
    def total_requests(self) -> int:
        return self._total_requests

    @property
    def requests_in_window(self) -> int:
        now = time.time()
        return sum(1 for t in self._request_times if now - t < 600)

    @property
    def requests_remaining(self) -> int:
        return max(0, config.reddit_requests_per_10min - self.requests_in_window)

    @property
    def window_reset_time(self) -> float:
        if not self._request_times:
            return time.time()
        now = time.time()
        valid_times = [t for t in self._request_times if now - t < 600]
        if not valid_times:
            return time.time()
        return min(valid_times) + 600

    @property
    def seconds_until_reset(self) -> float:
        if not self._request_times:
            return 0.0
        now = time.time()
        valid_times = [t for t in self._request_times if now - t < 600]
        if not valid_times:
            return 0.0
        oldest = min(valid_times)
        return max(0.0, 600 - (now - oldest))

    @property
    def seconds_until_next_request(self) -> float:
        if not self._request_times:
            return 0.0
        now = time.time()
        last_request = self._request_times[-1]
        elapsed = now - last_request
        return max(0.0, config.reddit_min_request_interval_seconds - elapsed)

    @property
    def is_throttled(self) -> bool:
        return self.requests_in_window >= config.reddit_requests_per_10min

    @property
    def throttle_wait_time(self) -> float | None:
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
            "throttle_wait_time": round(self.throttle_wait_time, 1)
            if self.throttle_wait_time is not None
            else None,
            "limit": config.reddit_requests_per_10min,
            "window_seconds": 600,
            "seconds_until_next_request": round(self.seconds_until_next_request, 1),
        }

    # ─── data-access methods (Atom RSS, delegate to parser) ───

    def search_subreddits_for_topic(
        self,
        query: str,
        limit: int = 25,
    ) -> list[str]:
        """Discover subreddits that talk about ``query`` via Reddit's sitewide
        search RSS feed.

        Calls ``GET /search/.rss?q={query}&sort=relevance&limit={limit}`` and
        returns the unique source subreddit names (without ``r/`` prefix),
        ordered by first appearance in the relevance-ranked results.

        Used by the v3 fetcher as the primary subreddit-discovery step before
        the KB-based LLM fallback. Reddit's own relevance algorithm decides
        which subs talk about the topic — no curation needed, works for any
        product niche including ones absent from the local KB.

        Raises ``HTTPError`` on non-2xx (caller is expected to catch broadly
        and fall back). Returns an empty list when Reddit returns no entries.
        """
        url = (
            f"{self.BASE_URL}/search/.rss"
            f"?q={quote_plus(query)}&sort=relevance&limit={limit}"
        )
        response = self._make_request("GET", url)
        response.raise_for_status()
        posts = parse_post_listing(response.text)
        # dict.fromkeys preserves insertion order in Py3.7+; first-seen wins
        # on duplicates (so a viral crosspost doesn't re-order the result).
        seen = dict.fromkeys(
            p["data"]["subreddit"]
            for p in posts
            if p["data"].get("subreddit")
        )
        return list(seen)

    def get_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 25,
        sort: str = "hot",
    ) -> list[dict]:
        """Get posts from a subreddit via its Atom feed.

        Returns a list of post wrappers ``[{"kind": "t3", "data": {...}}, ...]``.
        ``sort`` is one of ``hot``, ``new``, ``top`` (Reddit silently falls
        back to ``hot`` for unknown values).
        """
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.rss"
        response = self._make_request("GET", url)
        response.raise_for_status()
        posts = parse_post_listing(response.text)
        return posts[:limit]

    def get_post_comments(
        self,
        post_id: str,
        limit: int = 25,
    ) -> list[dict]:
        """Get a post and its comments via the comments Atom feed.

        Returns the same 2-element shape the v2 client returned (which the
        fetcher reads element ``[1]`` of):
        ``[{"data": {"children": [post]}}, {"data": {"children": [comments]}}]``.

        Only top-level comments are included (Reddit's RSS doesn't expose
        nesting; every entry in the feed is treated as level 0).
        """
        url = f"{self.BASE_URL}/comments/{post_id}/.rss"
        response = self._make_request("GET", url)
        response.raise_for_status()

        post_data, comments = parse_comments_page(response.text)
        return [
            {"data": {"children": [{"kind": "t3", "data": post_data}]}},
            {"data": {"children": comments[:limit]}},
        ]


# Singleton instance
redditapiv3_client = RedditAPIv3Client()
