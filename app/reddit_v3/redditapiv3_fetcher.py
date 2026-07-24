# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: REDDIT V3 (www.reddit.com Atom RSS feeds)
# Copy of app/reddit_v2/redditapiv2_fetcher.py with the Reddit client swapped
# to the RSS-scraping v3 client and the upvote threshold defaulting to 0
# (RSS doesn't expose upvote counts).
# ═══════════════════════════════════════════════════════════════════════════
"""Reddit data fetcher using the www.reddit.com Atom RSS feeds (v3).

Structural copy of :mod:`app.reddit_v2.redditapiv2_fetcher`. Two differences
from the v2 HTML-scraper fetcher:

1. Client import — uses :class:`RedditAPIv3Client` (RSS feeds) instead of
   :class:`RedditAPIv2Client` (old.reddit.com HTML).
2. ``min_upvotes_for_comments`` default is **0** instead of 100. RSS does not
   expose upvote counts, so the v2 threshold cannot be applied. Comment
   fetching is still capped by ``max_posts_with_comments``, which defaults to
   ``config.reddit_v3_max_posts_with_comments`` (=0 on prod — comment fetches
   were disabled after the 2026-07 login-wall pivot because every /comments/
   429 poisoned the shared circuit breaker that also gates listing fetches).
"""

import logging
import time

from app.agents.tools.shared import PipelineCancelled, is_cancelled
from app.collector.queries import get_subreddits_for_topic
from app.collector.subreddit_selector import select_subreddits_with_llm
from app.config import config
from app.models.reddit import CollectionResult, PostWithComments, RedditComment, RedditPost
from app.reddit.circuit_breaker import CircuitBreakerOpen
from app.reddit_v3.redditapiv3_client import RedditAPIv3Client, redditapiv3_client

logger = logging.getLogger(__name__)


class RedditAPIv3Fetcher:
    """Fetches Reddit posts and comments for complaint analysis (v3 RSS scraper).

    Uses the www.reddit.com Atom RSS feeds — no authentication required.
    Handles rate limiting, progress logging, and error handling.
    Converts raw RSS data to structured Pydantic models.
    """

    def __init__(
        self,
        max_comments_per_post: int = 20,
        comment_depth: int = 2,
        # RSS has no upvote counts, so the v2 threshold (100) can't be applied.
        # Comments are fetched for every post up to max_posts_with_comments.
        min_upvotes_for_comments: int = 0,
        # Defaults to config.reddit_v3_max_posts_with_comments (0 in prod).
        # Override per-instance by passing an explicit int. Background:
        # - v2 defaulted to 30 but was gated by min_upvotes=100, so in practice
        #   it only fetched 5-10.
        # - Without that gate, 30 comment-page fetches at 6s pacing = 3 min of
        #   comment fetching alone, and Reddit's /comments/ endpoint
        #   rate-limits aggressively (verified 2026-07-23). Each 429 also
        #   poisons the shared circuit breaker that gates listing fetches.
        # - The analyst reads only title + selftext, so disabling comments
        #   loses no signal.
        max_posts_with_comments: int | None = None,
    ):
        self.api = redditapiv3_client
        self.max_comments_per_post = max_comments_per_post
        self.comment_depth = comment_depth
        self.min_upvotes_for_comments = min_upvotes_for_comments
        if max_posts_with_comments is None:
            max_posts_with_comments = config.reddit_v3_max_posts_with_comments
        self.max_posts_with_comments = max_posts_with_comments
        self._comments_fetched_count = 0
        self._start_time: float = 0

    def _log_progress(self, current: int, total: int) -> None:
        if current == 0 or self._start_time == 0:
            return

        elapsed = time.time() - self._start_time
        rate = current / elapsed if elapsed > 0 else 0

        rl_status = self.api.get_rate_limit_status()

        if rate > 0:
            remaining = total - current
            eta_minutes = (remaining / rate) / 60
            logger.info(
                f"Progress: {current}/{total} posts | "
                f"ETA: {eta_minutes:.1f} min | "
                f"Rate: {rate:.2f}/s | "
                f"RL: {rl_status['requests_remaining']}/{rl_status['limit']} remaining"
            )

    def fetch_posts_for_topic(
        self,
        topic: str,
        posts_limit: int = 100,
        subreddits: list[str] | None = None,
        sort: str = "hot",
        use_llm_selection: bool = True,
    ) -> CollectionResult:
        """Fetch posts and comments for a topic.

        Args:
            topic: The topic/niche to search for.
            posts_limit: Maximum number of posts to collect.
            subreddits: Optional list of subreddits. Auto-selected if None.
            sort: Reddit sort method (hot, new, top). Default "hot".
            use_llm_selection: Use LLM to select subreddits when subreddits is None.
        """
        self._start_time = time.time()
        start_time = self._start_time

        if subreddits is None:
            # Try dynamic discovery via Reddit's sitewide search RSS first.
            # Falls back to the existing KB-based paths if discovery fails
            # (HTTP error, empty results, WAF block).
            discovered: list[str] = []
            try:
                discovered = self.api.search_subreddits_for_topic(topic, limit=25)
                if discovered:
                    logger.info(
                        f"[REDDIT_V3] Discovered {len(discovered)} subs via search: "
                        f"{discovered[:5]}"
                    )
            except Exception as e:
                logger.warning(
                    f"[REDDIT_V3] Dynamic discovery failed "
                    f"({type(e).__name__}: {e}); falling back to KB-based selection"
                )

            if discovered:
                subreddits = discovered[: config.max_subreddits]
            elif use_llm_selection:
                subreddits = select_subreddits_with_llm(
                    topic=topic,
                    max_subreddits=config.max_subreddits,
                )
                logger.info(f"LLM-selected subreddits ({len(subreddits)}): {subreddits[:10]}...")
            else:
                subreddits = get_subreddits_for_topic(topic, max_subreddits=config.max_subreddits)
                logger.info(f"Static subreddits ({len(subreddits)}): {subreddits}")

        # Pre-flight time estimation
        estimated_requests = len(subreddits)  # One fetch per subreddit
        estimated_requests += min(posts_limit // 5, self.max_posts_with_comments)  # Comment fetches
        estimated_minutes = estimated_requests / 10.0  # 10 req/min rate limit

        logger.info(f"Starting data collection for topic: {topic}")
        logger.info(f"  Target posts: {posts_limit}")
        logger.info(f"  Subreddits: {subreddits}")
        logger.info(f"  Sort: {sort}")
        logger.info(f"  Collection time estimate: ~{estimated_minutes:.1f} minutes ({estimated_requests} requests)")
        logger.info(f"  Rate limit: 10 req/min, will throttle automatically")

        result = CollectionResult(
            topic=topic,
            subreddits_queried=subreddits,
        )

        posts_collected = 0

        for subreddit_name in subreddits:
            if posts_collected >= posts_limit:
                break

            if is_cancelled():
                raise PipelineCancelled()

            try:
                subreddit_posts = self._fetch_from_subreddit(
                    subreddit_name=subreddit_name,
                    sort=sort,
                    limit=min(posts_limit - posts_collected, 50),
                )

                for post_with_comments in subreddit_posts:
                    result.posts.append(post_with_comments)
                    posts_collected += 1

                    if posts_collected >= posts_limit:
                        break

                    if posts_collected % 10 == 0:
                        self._log_progress(posts_collected, posts_limit)

            except CircuitBreakerOpen as e:
                logger.error(
                    f"Circuit breaker open — aborting fetch at r/{subreddit_name}: {e}"
                )
                break

            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                continue

        result.requests_made = self.api.total_requests
        result.collection_time_seconds = time.time() - start_time
        result.rate_limit_status = self.api.get_rate_limit_status()

        logger.info(f"Collection complete:")
        logger.info(f"  Posts: {result.total_posts}")
        logger.info(f"  Comments: {result.total_comments}")
        logger.info(f"  Requests: {result.requests_made}")
        logger.info(f"  Time: {result.collection_time_seconds:.1f}s")

        return result

    def _fetch_from_subreddit(
        self,
        subreddit_name: str,
        sort: str = "hot",
        limit: int = 50,
    ) -> list[PostWithComments]:
        """Fetch posts from a single subreddit via its Atom feed."""
        results: list[PostWithComments] = []

        try:
            posts_data = self.api.get_subreddit_posts(
                subreddit=subreddit_name,
                limit=limit,
                sort=sort,
            )

            if not posts_data:
                logger.warning(f"No posts found in r/{subreddit_name}")
                return results

            for post_wrapper in posts_data:
                if is_cancelled():
                    raise PipelineCancelled()
                try:
                    post_data = post_wrapper.get("data", post_wrapper)
                    post_with_comments = self._process_post_data(post_data)
                    if post_with_comments:
                        results.append(post_with_comments)
                except Exception as e:
                    logger.warning(f"Error processing post: {e}")
                    continue

        except PipelineCancelled:
            raise
        except CircuitBreakerOpen:
            raise
        except Exception as e:
            logger.error(f"Error fetching from r/{subreddit_name}: {e}")

        return results

    def _process_post_data(self, post_data: dict) -> PostWithComments | None:
        """Process raw post data into PostWithComments."""
        try:
            post_id = post_data.get("id", "")
            title = post_data.get("title", "")
            selftext = post_data.get("selftext")
            upvotes = post_data.get("ups", 0)
            num_comments = post_data.get("num_comments", 0)
            upvote_ratio = post_data.get("upvote_ratio")
            created_utc = post_data.get("created_utc", 0.0)
            author = post_data.get("author")
            link_flair_text = post_data.get("link_flair_text")
            permalink = post_data.get("permalink", "")
            subreddit = post_data.get("subreddit", "")

            distinguished = post_data.get("distinguished")
            stickied = post_data.get("stickied", False)

            # Filter out unwanted posts at ingestion time.
            # Note: RSS doesn't expose stickied/distinguished flags, so these
            # filters degrade to just author-based (AutoModerator) skips in
            # practice. That's fine — AutoModerator posts appear first in
            # /hot.rss, so they get filtered naturally.
            if author == "AutoModerator":
                logger.debug(f"Skipping AutoModerator post: {title[:50]}")
                return None
            if distinguished:
                logger.debug(f"Skipping distinguished post by {author}: {title[:50]}")
                return None
            if stickied:
                logger.debug(f"Skipping stickied post: {title[:50]}")
                return None

            post = RedditPost(
                id=post_id,
                title=title,
                selftext=selftext if selftext else None,
                url=f"https://reddit.com{permalink}",
                subreddit=subreddit,
                upvotes=upvotes,
                num_comments=num_comments,
                upvote_ratio=upvote_ratio,
                created_utc=created_utc,
                author=author,
                link_flair_text=link_flair_text,
                distinguished=distinguished,
                stickied=stickied,
            )

            # Fetch comments for posts up to the cap. With RSS we don't have
            # upvote counts, so the threshold (default 0) is effectively just
            # the cap.
            comments = []
            if (
                upvotes >= self.min_upvotes_for_comments
                and self._comments_fetched_count < self.max_posts_with_comments
            ):
                comments = self.fetch_comments_for_post(post_id)
                self._comments_fetched_count += 1
                logger.debug(
                    f"Fetched {len(comments)} comments for post '{title[:30]}...'"
                )
            elif upvotes >= self.min_upvotes_for_comments:
                logger.debug(
                    f"Skipping comments for '{title[:30]}...' - max comment fetches reached"
                )

            return PostWithComments(post=post, comments=comments)

        except Exception as e:
            logger.warning(f"Error processing post data: {e}")
            return None

    def fetch_comments_for_post(self, post_id: str) -> list[RedditComment]:
        """Fetch comments for a specific post via the comments Atom feed."""
        comments: list[RedditComment] = []

        try:
            comments_data = self.api.get_post_comments(post_id, limit=self.max_comments_per_post)

            if not comments_data:
                return comments

            if isinstance(comments_data, list) and len(comments_data) > 1:
                comments_listing = comments_data[1]
                children = comments_listing.get("data", {}).get("children", [])

                for child in children:
                    if child.get("kind") == "t1":
                        comment_data = child.get("data", {})
                        comment = self._process_comment_data(comment_data, post_id)
                        if comment:
                            comments.append(comment)

        except Exception as e:
            logger.warning(f"Error fetching comments for {post_id}: {e}")

        return comments

    def _process_comment_data(
        self,
        comment_data: dict,
        post_id: str,
    ) -> RedditComment | None:
        """Process raw comment data into RedditComment."""
        try:
            body = comment_data.get("body", "")
            if body in ["[deleted]", "[removed]"]:
                return None

            return RedditComment(
                id=comment_data.get("id", ""),
                post_id=post_id,
                parent_id=comment_data.get("parent_id"),
                body=body,
                upvotes=comment_data.get("ups", 0),
                author=comment_data.get("author"),
                level=0,
            )
        except Exception as e:
            logger.debug(f"Error processing comment data: {e}")
            return None

    def fetch_subreddit_hot(
        self,
        subreddit_name: str,
        limit: int = 10,
    ) -> list[PostWithComments]:
        """Fetch hot posts from a subreddit (useful for testing)."""
        results: list[PostWithComments] = []

        try:
            posts_data = self.api.get_subreddit_posts(subreddit_name, limit=limit, sort="hot")

            for post_wrapper in posts_data:
                post_data = post_wrapper.get("data", post_wrapper)
                post_with_comments = self._process_post_data(post_data)
                if post_with_comments:
                    results.append(post_with_comments)

        except Exception as e:
            logger.error(f"Error fetching hot posts from r/{subreddit_name}: {e}")

        return results
