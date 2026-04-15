"""fetch_posts tool: loads sample data (TEST) or calls Reddit API (LIVE)."""

import json
import logging
import time
from pathlib import Path

from app.agents.tools.shared import set_shared_data
from app.config import config

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
                "query_style": {
                    "type": "string",
                    "description": "Query style. 'loose' (default) uses OR for broader results.",
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
    query_style: str = "loose",
    use_llm_selection: bool = True,
) -> str:
    """Fetch Reddit posts for the given topic.

    In TEST mode: loads data/sample_posts.json.
    In LIVE mode: calls RedditFetcher.fetch_posts_for_topic().

    Stores full data in shared store and returns a compact summary.
    """
    mode = config.agent_mode
    logger.info(f"  [FETCH] Starting fetch_posts: topic='{topic}' mode={mode}")
    t0 = time.time()

    if mode == "test":
        full_data = _fetch_test_data(topic)
    else:
        full_data = _fetch_live(topic, subreddits, query_style, use_llm_selection)

    # Store full data for downstream tools
    set_shared_data("fetched_posts", full_data)

    elapsed = time.time() - t0
    logger.info(f"  [FETCH] Completed: {full_data.get('total_posts', 0)} posts fetched in {elapsed:.1f}s")

    # Persist fetch statistics log
    try:
        from app.agents.tools.run_logger import save_fetch_stats
        save_fetch_stats(
            topic=topic,
            mode=mode,
            total_posts=full_data.get("total_posts", 0),
            subreddits_queried=full_data.get("subreddits_queried", []),
            elapsed_seconds=elapsed,
            source=full_data.get("source", ""),
        )
    except Exception as log_err:
        logger.warning(f"Failed to save fetch stats log: {log_err}")

    # Return compact summary to LLM (not the full JSON)
    summary = {
        "status": "success",
        "topic": full_data.get("topic", topic),
        "total_posts": full_data.get("total_posts", 0),
        "mode": full_data.get("mode", mode),
        "subreddits": full_data.get("subreddits_queried", []),
        "message": (
            f"Fetched {full_data.get('total_posts', 0)} posts. "
            f"The next agent should use classify_posts to analyze them."
        ),
    }
    if "error" in full_data:
        return json.dumps(full_data)

    return json.dumps(summary)


def _fetch_test_data(topic: str) -> dict:
    """Load sample posts from data/sample_posts.json."""
    sample_path = Path("data/sample_posts.json")
    if not sample_path.exists():
        project_root = Path(__file__).resolve().parents[3]
        sample_path = project_root / "data" / "sample_posts.json"

    if not sample_path.exists():
        return {"error": f"Sample data file not found: {sample_path}"}

    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data.get("posts", [])
    logger.info(f"Loaded {len(posts)} sample posts for topic '{topic}'")
    return {
        "topic": topic,
        "posts": posts,
        "total_posts": len(posts),
        "mode": "test",
        "source": str(sample_path),
    }


def _fetch_live(
    topic: str,
    subreddits: list[str] | None = None,
    query_style: str = "loose",
    use_llm_selection: bool = True,
) -> dict:
    """Fetch live data from Reddit API."""
    from app.collector.fetcher import RedditFetcher

    fetcher = RedditFetcher()
    result = fetcher.fetch_posts_for_topic(
        topic=topic,
        subreddits=subreddits,
        query_style=query_style,
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

    logger.info(f"Fetched {len(posts_data)} live posts for topic '{topic}'")
    return {
        "topic": topic,
        "posts": posts_data,
        "total_posts": len(posts_data),
        "mode": "live",
        "subreddits_queried": result.subreddits_queried,
    }
