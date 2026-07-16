# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: PUSHSHIFT (Pre-staged Parquet + DuckDB)
# Historical Reddit data via local Parquet query (mounted from GCS in prod).
# Used when: get_data_source() == "pushshift"
# (Renamed from "arcticshift" — upstream is fddemarco/pushshift-reddit, not
# the separate RoyalFortune24/The-Arctic-Shift dataset.)
# ═══════════════════════════════════════════════════════════════════════════
"""Pushshift client for querying historical Reddit data.

Reads pre-staged Parquet from a mounted GCS volume (/app/data in production,
or a local data/pushshift directory in dev), then queries with DuckDB.
This provides access to historical Reddit data without rate limits.

Provenance: HuggingFace dataset fddemarco/pushshift-reddit (RS_2018-01_00.parquet).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Parquet file (pre-staged on GCS bucket, mounted at /app/data in production)
PARQUET_FILENAME = "RS_2018-01_00.parquet"
# Provenance: HuggingFace dataset fddemarco/pushshift-reddit


class PushshiftClient:
    """Client for querying historical Reddit data via DuckDB + local Parquet.

    Reads a pre-staged Parquet file (mounted from GCS in production, or copied
    into data/pushshift in dev), then queries with DuckDB. No rate limits,
    no auth required.
    """

    def __init__(self, cache_dir: str | None = None):
        """Initialize the client.

        Args:
            cache_dir: Optional directory holding the Parquet file.
                      Defaults to data/pushshift relative to project root.
        """
        self._cache_dir = cache_dir
        self._parquet_path: str | None = None
        self._conn = None

    def _get_parquet_path(self) -> str:
        """Resolve path to local Parquet file (mounted from GCS in production).

        Looks at ``data/pushshift/`` first; falls back to the legacy
        ``data/arcticshift/`` bucket prefix if the renamed path is absent
        (the GCS bucket has not yet been renamed to match the code).
        """
        if self._parquet_path is not None:
            return self._parquet_path

        if self._cache_dir is not None:
            candidates = [Path(self._cache_dir) / PARQUET_FILENAME]
        else:
            project_root = Path(__file__).parent.parent.parent
            candidates = [
                project_root / "data" / "pushshift" / PARQUET_FILENAME,
                project_root / "data" / "arcticshift" / PARQUET_FILENAME,  # legacy bucket prefix
            ]

        for candidate in candidates:
            if candidate.exists():
                self._parquet_path = str(candidate)
                if "arcticshift" in self._parquet_path:
                    logger.warning(
                        "[PUSHSHIFT] Reading from legacy data/arcticshift/ path. "
                        "Rename the GCS bucket prefix to pushshift/ to match the code."
                    )
                logger.info(f"[PUSHSHIFT] Using Parquet: {self._parquet_path}")
                return self._parquet_path

        raise FileNotFoundError(
            f"Pushshift Parquet not found. Tried: {[str(c) for c in candidates]}. "
            f"Ensure the datasets volume is mounted at /app/data."
        )

    def _get_connection(self):
        """Get or create DuckDB connection."""
        if self._conn is None:
            import duckdb

            self._conn = duckdb.connect()
            logger.info("[PUSHSHIFT] DuckDB connection initialized")
        return self._conn

    def search_posts(
        self,
        subreddits: list[str] | None = None,
        keyword: str | None = None,
        min_score: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Query local Parquet file via DuckDB for Reddit posts.

        Args:
            subreddits: Optional list of subreddits to filter by.
            keyword: Optional keyword to search in title and selftext.
            min_score: Minimum score (upvotes) filter.
            limit: Maximum number of results to return.

        Returns:
            List of post dictionaries matching the criteria.
        """
        parquet_path = self._get_parquet_path()
        conn = self._get_connection()

        # Build WHERE conditions
        conditions = ["1=1"]

        if subreddits:
            subs_lower = ", ".join(f"'{s.lower()}'" for s in subreddits)
            conditions.append(f"LOWER(subreddit) IN ({subs_lower})")

        if keyword:
            # Escape single quotes in keyword
            safe_keyword = keyword.replace("'", "''").lower()
            terms = safe_keyword.split()
            for term in terms:
                conditions.append(
                    f"(LOWER(COALESCE(title, '')) LIKE '%{term}%' "
                    f"OR LOWER(COALESCE(selftext, '')) LIKE '%{term}%')"
                )

        if min_score > 0:
            conditions.append(f"score >= {min_score}")

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                id,
                title,
                selftext,
                subreddit,
                author,
                score,
                num_comments,
                created_utc
            FROM read_parquet('{parquet_path}')
            WHERE {where_clause}
            ORDER BY score DESC
            LIMIT {limit}
        """

        logger.info(f"[PUSHSHIFT] Executing query: keyword={keyword}, subreddits={subreddits}, limit={limit}")

        try:
            result = conn.execute(query).fetchall()
            columns = ["id", "title", "selftext", "subreddit", "author", "score", "num_comments", "created_utc"]
            posts = [self._row_to_dict(row, columns) for row in result]
            logger.info(f"[PUSHSHIFT] Found {len(posts)} posts")
            return posts
        except Exception as e:
            logger.error(f"[PUSHSHIFT] Query failed: {e}")
            raise

    def _row_to_dict(self, row: tuple, columns: list[str]) -> dict:
        """Convert a DuckDB result row to a dictionary."""
        post = dict(zip(columns, row))

        # Map 'score' to 'upvotes' for compatibility with downstream pipeline
        # (Reddit API uses 'score', our models use 'upvotes')
        if "score" in post:
            post["upvotes"] = post["score"]

        # Convert created_utc to ISO format if it's a timestamp
        if post.get("created_utc"):
            try:
                ts = int(post["created_utc"])
                post["created_datetime"] = datetime.fromtimestamp(ts).isoformat()
            except (ValueError, TypeError):
                pass

        # Generate Reddit URL
        post_id = post.get("id", "")
        subreddit = post.get("subreddit", "")
        if post_id and subreddit:
            post["url"] = f"https://reddit.com/r/{subreddit}/comments/{post_id}"
        else:
            post["url"] = ""

        return post

    def test_connection(self) -> dict[str, Any]:
        """Test the connection by running a simple query.

        Returns:
            Dict with status, sample data, and query info.
        """
        try:
            posts = self.search_posts(limit=5)

            sample_data = []
            for post in posts:
                sample_data.append({
                    "id": post.get("id", ""),
                    "title": (post.get("title") or "")[:60],
                    "score": post.get("score", 0),
                    "subreddit": post.get("subreddit", ""),
                    "author": post.get("author", ""),
                })

            return {
                "status": "success",
                "message": "Connected to local Parquet via DuckDB",
                "parquet_path": self._parquet_path,
                "sample_rows": len(sample_data),
                "data": sample_data,
            }
        except Exception as e:
            logger.error(f"[PUSHSHIFT] Connection test failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "sample_rows": 0,
                "data": [],
            }

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.info("[PUSHSHIFT] Connection closed")
