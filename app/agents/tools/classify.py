"""classify_posts tool: classifies Reddit posts using the LLM provider."""

import json
import logging

from app.agents.tools.shared import get_shared_data, set_shared_data

logger = logging.getLogger(__name__)

CLASSIFY_POSTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "classify_posts",
        "description": (
            "Classify fetched Reddit posts to extract complaint themes, "
            "intensity levels, and whether each post is a complaint. "
            "Uses the posts data from the previous fetch_posts call. "
            "Returns a summary of classification results."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


def classify_posts() -> str:
    """Classify posts using PostClassifier with the configured provider.

    Reads fetched posts from shared data store (populated by fetch_posts).
    Stores classified posts back to shared data for downstream tools.

    Returns:
        JSON string with classification summary.
    """
    from app.analyst.classifier import PostClassifier
    from app.config import config

    # Read from shared data store
    fetched = get_shared_data("fetched_posts")
    if not fetched:
        return json.dumps({"error": "No fetched posts found. Run fetch_posts first."})

    posts = fetched.get("posts", [])
    if not posts:
        return json.dumps({"error": "No posts in fetched data."})

    logger.info(f"Classifying {len(posts)} posts with {config.llm_provider} provider")

    classifier = PostClassifier(request_delay=0.5)
    result = classifier.classify_batch(posts, max_consecutive_failures=5)

    # Convert to serializable dicts
    classified = []
    for ep in result.posts:
        item = {
            "subreddit": ep.subreddit,
            "category": ep.category,
            "post": ep.post,
            "comments_count": ep.comments_count,
            "classification": ep.classification.model_dump() if ep.classification else None,
            "classification_error": ep.classification_error,
        }
        classified.append(item)

    full_output = {
        "posts": classified,
        "total": result.total_posts,
        "successful": result.successful_classifications,
        "failed": result.failed_classifications,
    }

    # Store for downstream tools
    set_shared_data("classified_posts", full_output)

    logger.info(
        f"Classification done: {result.successful_classifications}/{result.total_posts} successful"
    )

    # Return compact summary to LLM
    summary = {
        "status": "success",
        "total_posts": result.total_posts,
        "successful_classifications": result.successful_classifications,
        "failed_classifications": result.failed_classifications,
        "message": (
            f"Classified {result.successful_classifications}/{result.total_posts} posts. "
            f"Use cluster_themes to group them into themes."
        ),
    }
    return json.dumps(summary)
