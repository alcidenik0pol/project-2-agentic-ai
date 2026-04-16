"""Verification test for Reddit public JSON API access.

Run this test FIRST before proceeding with any development.
No authentication required - uses Reddit's public JSON endpoints.
"""

import pytest
from app.reddit.client import reddit_client


def test_reddit_api_connection():
    """Test that we can connect to Reddit public API and fetch data.

    This is the GO/NO-GO test for the entire project.
    No credentials required - uses public JSON API.
    """
    # Test basic read operation - fetch hot posts from r/python
    posts = reddit_client.get_subreddit_posts("python", limit=3)

    assert posts is not None, "Failed to get response from Reddit API"
    assert len(posts) >= 1, "No posts returned from r/python"

    # Verify post structure
    post_data = posts[0].get("data", {})
    assert "title" in post_data, "Post missing title"
    assert "ups" in post_data, "Post missing upvotes"
    assert "num_comments" in post_data, "Post missing num_comments"

    print(f"Successfully connected to Reddit public API")
    print(f"Fetched test post: {post_data['title'][:50]}...")


def test_search_function():
    """Test that subreddit post fetching works."""
    results = reddit_client.get_subreddit_posts(
        subreddit="python",
        limit=5,
        sort="hot",
    )

    assert results is not None, "Subreddit fetch returned no results"
    assert len(results) >= 1, "No posts returned from r/python hot"

    print(f"Hot posts fetch returned {len(results)} results")


def test_config_loaded():
    """Test that configuration is properly loaded."""
    from app.config import config

    assert config.reddit_user_agent, "REDDIT_USER_AGENT not set"

    print(f"Configuration loaded - user agent: {config.reddit_user_agent[:30]}...")
