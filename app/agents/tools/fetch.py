"""fetch_posts tool: routes to different data sources based on config.

─── DATA SOURCE ROUTER ───
Dispatches to workflow based on get_data_source():
- reddit_live:    Legacy Reddit API workflow
- reddit_v2:      old.reddit.com HTML scraper
- pushshift:      HuggingFace historical via DuckDB
- linanqiu:       Local JSON dataset
- sample_*:       Static sample data files
"""

import json
import logging
import time
from pathlib import Path

from app.agents.tools.shared import set_shared_data
from app.config import get_data_source, DataSource

logger = logging.getLogger(__name__)

# Schema for OpenAI function calling
FETCH_POSTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "fetch_posts",
        "description": (
            "Fetch Reddit posts relevant to the user's topic. "
            "Returns a summary of posts found. The full data is stored internally "
            "for use by downstream analysis tools (classify_posts, cluster_themes)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic/niche to search Reddit for.",
                },
                "subreddits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of subreddits to search. Auto-selected by LLM if empty.",
                },
                "use_llm_selection": {
                    "type": "boolean",
                    "description": "Use LLM to select subreddits. Default true.",
                },
            },
            "required": ["topic"],
        },
    },
}


def fetch_posts(
    topic: str,
    subreddits: list[str] | None = None,
    use_llm_selection: bool = True,
) -> str:
    """Fetch posts for the given topic from the configured data source.

    Routes to different data sources based on get_data_source():
    - reddit_live:    Legacy Reddit API workflow
    - reddit_v2:      old.reddit.com HTML scraper
    - pushshift:      HuggingFace historical via DuckDB
    - linanqiu:       Local JSON dataset
    - sample_*:       Static sample data files

    Stores full data in shared store and returns a compact summary.
    """
    data_source = get_data_source()
    logger.info(f"  [FETCH] Starting fetch_posts: topic='{topic}' data_source={data_source}")
    t0 = time.time()

    # ─── DATA SOURCE ROUTER ───
    if data_source == "reddit_live":
        full_data = _fetch_reddit_live(topic, subreddits, use_llm_selection)
    elif data_source == "reddit_v2":
        full_data = _fetch_reddit_v2(topic, subreddits, use_llm_selection)
    elif data_source == "pushshift":
        full_data = _fetch_pushshift(topic, subreddits)
    elif data_source == "linanqiu":
        full_data = _fetch_linanqiu(topic, subreddits)
    elif data_source.startswith("sample_"):
        full_data = _fetch_sample(topic, data_source)
    else:
        return json.dumps({"error": f"Unknown data_source: {data_source}"})

    # Store full data for downstream tools
    set_shared_data("fetched_posts", full_data)

    # Store the original user query so downstream tools (hypothesis, etc.)
    # can ground their output in what the user actually asked about.
    set_shared_data("user_query", topic)

    elapsed = time.time() - t0
    logger.info(f"  [FETCH] Completed: {full_data.get('total_posts', 0)} posts fetched in {elapsed:.1f}s")

    # Persist fetch statistics log
    try:
        from app.agents.tools.run_logger import save_fetch_stats
        save_fetch_stats(
            topic=topic,
            mode=data_source,  # Use data_source as mode for backwards compat
            total_posts=full_data.get("total_posts", 0),
            subreddits_queried=full_data.get("subreddits_queried", []),
            elapsed_seconds=elapsed,
            source=full_data.get("source", ""),
        )
    except Exception as log_err:
        logger.warning(f"Failed to save fetch stats log: {log_err}")

    # Return compact summary to LLM (not the full JSON).
    # Status is honest about the outcome so downstream agents (and the LLM
    # driving them) can decide whether to proceed:
    #   - "error":      the fetch itself failed (network, parse, etc.)
    #   - "no_results": the query succeeded but matched 0 posts; there is
    #                   nothing for classify_posts to work on
    #   - "success":    one or more posts were fetched
    # Reporting "success" + total_posts=0 + "use classify_posts" was a lie
    # that caused downstream agents to invoke tools on an empty store.
    if "error" in full_data:
        return json.dumps(full_data)

    total_posts = full_data.get("total_posts", 0)
    if total_posts == 0:
        status = "no_results"
        message = (
            f"Found 0 posts for topic '{topic}' in {data_source}. "
            f"There is nothing for downstream agents to analyze."
        )
    else:
        status = "success"
        message = (
            f"Fetched {total_posts} posts. "
            f"The next agent should use classify_posts to analyze them."
        )

    summary = {
        "status": status,
        "topic": full_data.get("topic", topic),
        "total_posts": total_posts,
        "data_source": data_source,
        "subreddits": full_data.get("subreddits_queried", []),
        "message": message,
    }
    return json.dumps(summary)


# ═══════════════════════════════════════════════════════════════════════════
# SAMPLE DATA HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

# Map data source names to file paths
SAMPLE_FILES: dict[str, str] = {
    "sample_default": "data/smallsample/sample_posts.json",
    "sample_gaming": "data/smallsample/gaming_test_20260416_105527.json",
}


def _fetch_sample(topic: str, data_source: str) -> dict:
    """Load sample data from a static JSON file.

    Args:
        topic: The user's search topic (for metadata).
        data_source: The sample source key (e.g., "sample_default").

    Returns:
        Dict with posts data in standard format.
    """
    if data_source not in SAMPLE_FILES:
        return {"error": f"Unknown sample data source: {data_source}"}

    relative_path = SAMPLE_FILES[data_source]
    sample_path = Path(relative_path)

    # Try relative path first, then project root
    if not sample_path.exists():
        project_root = Path(__file__).resolve().parents[3]
        sample_path = project_root / relative_path

    if not sample_path.exists():
        return {"error": f"Sample data file not found: {sample_path}"}

    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data.get("posts", [])
    logger.info(f"[SAMPLE] Loaded {len(posts)} posts from {sample_path} for topic '{topic}'")

    return {
        "topic": topic,
        "posts": posts,
        "total_posts": len(posts),
        "data_source": data_source,
        "source": str(sample_path),
        "subreddits_queried": _extract_subreddits(posts),
    }


def _extract_subreddits(posts: list[dict]) -> list[str]:
    """Extract unique subreddit names from posts."""
    subreddits = set()
    for p in posts:
        if "subreddit" in p:
            subreddits.add(p["subreddit"])
        elif "post" in p and "subreddit" in p["post"]:
            subreddits.add(p["post"]["subreddit"])
    return sorted(subreddits)


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: LEGACY (Reddit API)
# Part of the original Reddit API data collection workflow.
# Used when: get_data_source() == "reddit_live"
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_reddit_live(
    topic: str,
    subreddits: list[str] | None = None,
    use_llm_selection: bool = True,
) -> dict:
    """Fetch live data from Reddit API (legacy workflow)."""
    from app.collector.fetcher import RedditFetcher

    fetcher = RedditFetcher()
    result = fetcher.fetch_posts_for_topic(
        topic=topic,
        subreddits=subreddits,
        use_llm_selection=use_llm_selection,
    )

    posts_data = []
    for pwc in result.posts:
        posts_data.append({
            "subreddit": pwc.post.subreddit,
            "category": "",
            "post": pwc.post.model_dump(),
            "comments_count": len(pwc.comments),
        })

    logger.info(f"[REDDIT_LIVE] Fetched {len(posts_data)} posts for topic '{topic}'")
    return {
        "topic": topic,
        "posts": posts_data,
        "total_posts": len(posts_data),
        "data_source": "reddit_live",
        "subreddits_queried": result.subreddits_queried,
    }


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: REDDIT V2 (old.reddit.com HTML scraper)
# Used when: get_data_source() == "reddit_v2"
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_reddit_v2(
    topic: str,
    subreddits: list[str] | None = None,
    use_llm_selection: bool = True,
) -> dict:
    """Fetch live data from old.reddit.com via the v2 HTML scraper."""
    from app.reddit_v2.redditapiv2_fetcher import RedditAPIv2Fetcher

    fetcher = RedditAPIv2Fetcher()
    result = fetcher.fetch_posts_for_topic(
        topic=topic,
        subreddits=subreddits,
        use_llm_selection=use_llm_selection,
    )

    posts_data = []
    for pwc in result.posts:
        posts_data.append({
            "subreddit": pwc.post.subreddit,
            "category": "",
            "post": pwc.post.model_dump(),
            "comments_count": len(pwc.comments),
        })

    logger.info(f"[REDDIT_V2] Fetched {len(posts_data)} posts for topic '{topic}'")
    return {
        "topic": topic,
        "posts": posts_data,
        "total_posts": len(posts_data),
        "data_source": "reddit_v2",
        "subreddits_queried": result.subreddits_queried,
    }


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: PUSHSHIFT (HuggingFace + DuckDB)
# Historical Reddit data via local Parquet query.
# Used when: get_data_source() == "pushshift"
# (Renamed from "arcticshift" — upstream is fddemarco/pushshift-reddit, not
# the separate RoyalFortune24/The-Arctic-Shift dataset.)
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_pushshift(
    topic: str,
    subreddits: list[str] | None = None,
) -> dict:
    """Fetch historical Reddit data from HuggingFace via DuckDB local Parquet."""
    try:
        from app.pushshift.client import PushshiftClient

        client = PushshiftClient()
        posts = client.search_posts(
            subreddits=subreddits,
            keyword=topic,
            min_score=1,
            limit=100,
        )

        # Convert to standard format
        posts_data = []
        subreddits_found = set()
        for post in posts:
            subreddits_found.add(post.get("subreddit", ""))
            posts_data.append({
                "subreddit": post.get("subreddit", ""),
                "category": "",
                "post": post,
                "comments_count": post.get("num_comments", 0),
            })

        logger.info(f"[PUSHSHIFT] Fetched {len(posts_data)} posts for topic '{topic}'")
        return {
            "topic": topic,
            "posts": posts_data,
            "total_posts": len(posts_data),
            "data_source": "pushshift",
            "subreddits_queried": sorted(subreddits_found),
        }
    except Exception as e:
        logger.error(f"[PUSHSHIFT] Failed to fetch data: {e}")
        return {"error": f"Pushshift query failed: {e}"}


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: LINANQIU (local static JSON)
# Historical Reddit data via pre-converted JSON on disk.
# Used when: get_data_source() == "linanqiu"
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_linanqiu(
    topic: str,
    subreddits: list[str] | None = None,
) -> dict:
    """Fetch posts from the linanqiu static dataset (local JSON)."""
    try:
        from app.linanqiu.linanqiu_client import LinanqiuClient

        client = LinanqiuClient()
        posts = client.search_posts(
            subreddits=subreddits,
            keyword=topic,
            min_score=1,
            limit=100,
        )

        # Convert to standard format
        posts_data = []
        subreddits_found = set()
        for post in posts:
            subreddits_found.add(post.get("subreddit", ""))
            posts_data.append({
                "subreddit": post.get("subreddit", ""),
                "category": "",
                "post": post,
                "comments_count": post.get("num_comments", 0),
            })

        logger.info(f"[LINANQIU] Fetched {len(posts_data)} posts for topic '{topic}'")
        return {
            "topic": topic,
            "posts": posts_data,
            "total_posts": len(posts_data),
            "data_source": "linanqiu",
            "subreddits_queried": sorted(subreddits_found),
        }
    except Exception as e:
        logger.error(f"[LINANQIU] Failed to fetch data: {e}")
        return {"error": f"Linanqiu query failed: {e}"}
