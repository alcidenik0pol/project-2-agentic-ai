# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: LINANQIU (local static JSON)
# Historical Reddit data via pre-converted JSON on disk.
# Used when: get_data_source() == "linanqiu"
# ═══════════════════════════════════════════════════════════════════════════
"""Linanqiu client for querying a static, pre-converted Reddit dataset.

Loads ``data/linanqiu/linanqiu_dataset.json`` once (cached on the instance),
then filters in-memory. The JSON is pre-converted to the app's standard post
schema by ``scripts/convert_linanqiu.py`` (10,170 posts across 51 subreddits,
originally from github.com/linanqiu/reddit-dataset, Feb 2016 era).

No network, no DuckDB, no new dependencies — stdlib ``json`` only.

Dataset: https://github.com/linanqiu/reddit-dataset
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default location of the converted dataset relative to project root
DEFAULT_DATA_FILENAME = "linanqiu_dataset.json"


class LinanqiuClient:
    """Client for querying the linanqiu static Reddit dataset.

    Loads the pre-converted JSON from disk lazily and caches it on the
    instance. Filters in-memory: subreddit intersection (case-insensitive),
    keyword substring on ``title`` OR ``selftext``, ``min_score`` floor,
    sort by ``upvotes`` desc, then truncate to ``limit``.

    The instance is cheap to construct and safe to instantiate per-request,
    mirroring the ``PushshiftClient`` usage pattern.
    """

    def __init__(self, data_path: str | None = None):
        """Initialize the client.

        Args:
            data_path: Optional explicit path to the converted JSON file.
                      Defaults to ``data/linanqiu/linanqiu_dataset.json``
                      relative to the project root.
        """
        self._data_path = data_path
        self._posts: list[dict] | None = None

    def _resolve_data_path(self) -> Path:
        """Resolve the path to the converted dataset JSON."""
        if self._data_path is not None:
            return Path(self._data_path)

        project_root = Path(__file__).resolve().parents[2]
        return project_root / "data" / "linanqiu" / DEFAULT_DATA_FILENAME

    def _load_posts(self) -> list[dict]:
        """Load and cache the inner post dicts from the converted JSON.

        The JSON on disk stores each record as
        ``{category, comments_count, post: {...}, subreddit}``; we return
        only the inner ``post`` sub-dict so the shape matches
        :meth:`PushshiftClient.search_posts`.
        """
        if self._posts is not None:
            return self._posts

        path = self._resolve_data_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Linanqiu dataset not found at {path}. "
                f"Run scripts/convert_linanqiu.py to generate it."
            )

        logger.info(f"[LINANQIU] Loading dataset from {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_posts = data.get("posts", []) if isinstance(data, dict) else data
        # Extract the inner post sub-dict; fall back to the record itself
        # if the file shape differs (defensive — keeps client usable on
        # alternative inputs without crashing).
        posts: list[dict] = []
        for record in raw_posts:
            if isinstance(record, dict) and "post" in record:
                posts.append(record["post"])
            elif isinstance(record, dict):
                posts.append(record)

        self._posts = posts
        logger.info(f"[LINANQIU] Loaded {len(self._posts)} posts")
        return self._posts

    def search_posts(
        self,
        subreddits: list[str] | None = None,
        keyword: str | None = None,
        min_score: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Filter the in-memory dataset and return matching posts.

        Args:
            subreddits: Optional list of subreddits to filter by
                (case-insensitive intersection).
            keyword: Optional keyword matched as a case-insensitive substring
                against ``title`` OR ``selftext``.
            min_score: Minimum ``upvotes`` floor. Kept for parity with
                :meth:`PushshiftClient.search_posts` even though the
                converted dataset is already pre-filtered to ``ups >= 1``.
            limit: Maximum number of results to return (after sorting by
                ``upvotes`` descending).

        Returns:
            List of post dictionaries in the same shape the pushshift
            client returns (``id, title, selftext, subreddit, author,
            upvotes, num_comments, created_utc, url, ...``).
        """
        posts = self._load_posts()

        subs_lower: set[str] | None = None
        if subreddits:
            subs_lower = {s.lower() for s in subreddits}

        kw_lower = keyword.lower() if keyword else None

        filtered: list[dict] = []
        for post in posts:
            subreddit = post.get("subreddit", "") or ""
            if subs_lower is not None and subreddit.lower() not in subs_lower:
                continue

            upvotes = post.get("upvotes")
            if upvotes is None:
                upvotes = post.get("score", 0)
            if min_score > 0 and (upvotes or 0) < min_score:
                continue

            if kw_lower is not None:
                haystack = (
                    (post.get("title") or "") + " " + (post.get("selftext") or "")
                ).lower()
                # Match each whitespace-separated term independently (AND across
                # terms, OR across title/body via combined haystack). A single
                # contiguous substring test would require a multi-word topic to
                # appear verbatim, which almost never happens in real posts.
                terms = kw_lower.split()
                if not all(term in haystack for term in terms):
                    continue

            filtered.append(post)

        # Sort by upvotes desc (fall back to score for safety), then truncate
        filtered.sort(
            key=lambda p: p.get("upvotes") or p.get("score") or 0,
            reverse=True,
        )
        result = filtered[:limit]

        logger.info(
            f"[LINANQIU] Found {len(result)} posts "
            f"(keyword={keyword!r}, subreddits={subreddits}, min_score={min_score}, limit={limit})"
        )
        return result
