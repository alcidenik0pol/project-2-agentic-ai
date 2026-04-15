"""cluster_themes tool: clusters classified posts into thematic groups."""

import json
import logging
import time

from app.agents.tools.shared import get_shared_data, set_shared_data
from app.analyst.providers import get_provider

logger = logging.getLogger(__name__)

CLUSTER_THEMES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cluster_themes",
        "description": (
            "Cluster classified posts into thematic groups using embeddings and KMeans. "
            "Uses the classified posts data from the previous classify_posts call. "
            "Returns a summary of clusters found."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


def cluster_themes() -> str:
    """Cluster classified posts using ThemeClusterer.

    Reads classified posts from shared data store.
    Stores clustering results for downstream hypothesis generation.

    Returns:
        JSON string with clustering summary.
    """
    from app.analyst.clustering import ThemeClusterer
    from app.config import config

    # Read from shared data store
    classified_data = get_shared_data("classified_posts")
    if not classified_data:
        return json.dumps({"error": "No classified posts found. Run classify_posts first."})

    posts = classified_data.get("posts", [])
    if not posts:
        return json.dumps({"error": "No posts in classified data."})

    # Filter to only classified posts (with a theme)
    classified = [p for p in posts if p.get("classification") and p["classification"].get("theme")]
    if not classified:
        return json.dumps({"error": "No classified posts with themes found"})

    logger.info(f"  [CLUSTER] Starting cluster_themes: {len(classified)} classified posts")
    t0 = time.time()

    provider = get_provider(config.llm_provider)
    clusterer = ThemeClusterer(provider=provider)
    result = clusterer.cluster_posts(classified)

    full_output = {
        "clusters": [c.model_dump() for c in result.clusters],
        "posts": result.posts,
        "cluster_count": result.cluster_count,
        "original_theme_count": result.original_theme_count,
        "canonical_theme_count": result.canonical_theme_count,
        "processing_time_seconds": result.processing_time_seconds,
    }

    # Store for downstream tools
    set_shared_data("clustered_data", full_output)

    elapsed = time.time() - t0
    logger.info(f"  [CLUSTER] Completed: {result.cluster_count} clusters in {elapsed:.1f}s")

    # Build and persist clustering EDA log
    try:
        cluster_details = [
            {
                "id": c.cluster_id,
                "name": c.name,
                "themes": c.themes,
                "theme_count": len(c.themes),
                "post_count": c.post_count,
                "total_upvotes": c.total_upvotes,
                "avg_upvotes": round(c.total_upvotes / c.post_count, 1) if c.post_count > 0 else 0,
            }
            for c in result.clusters
        ]

        from app.agents.tools.run_logger import save_clustering_eda
        save_clustering_eda(
            original_theme_count=result.original_theme_count,
            canonical_theme_count=result.canonical_theme_count,
            cluster_count=result.cluster_count,
            processing_time_seconds=result.processing_time_seconds,
            embedding_model=result.embedding_model,
            provider_used=result.provider_used,
            clusters=cluster_details,
        )
    except Exception as log_err:
        logger.warning(f"Failed to save clustering EDA log: {log_err}")

    # Return compact summary to LLM
    cluster_names = [c.name for c in result.clusters]
    summary = {
        "status": "success",
        "cluster_count": result.cluster_count,
        "clusters": [{"name": c.name, "post_count": c.post_count, "upvotes": c.total_upvotes} for c in result.clusters],
        "message": (
            f"Found {result.cluster_count} clusters. "
            f"Use generate_hypotheses to create business ideas from these themes."
        ),
    }
    return json.dumps(summary)
