"""Live integration smoke test for the reddit_v2 old.reddit.com HTML scraper.

Mirrors app/tests/test_reddit_api.py but exercises the v2 (HTML) client.

Run: ``pytest app/tests/test_redditapiv2.py -v -s``

These tests hit the network. They auto-skip when old.reddit.com is unreachable
so the offline parser suite stays green.
"""

import pytest

from app.config import config
from app.reddit_v2.redditapiv2_client import redditapiv2_client


def _can_reach_old_reddit() -> bool:
    """Quick connectivity probe — True if old.reddit.com responds 200."""
    try:
        resp = redditapiv2_client.session.get(
            f"{redditapiv2_client.BASE_URL}/r/python/hot/",
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _can_reach_old_reddit(),
    reason="old.reddit.com unreachable from this environment",
)


def test_v2_scrape_post_listing():
    """Scrape r/python hot listing and verify the post wrapper structure."""
    posts = redditapiv2_client.get_subreddit_posts("python", limit=5)

    assert posts, "No posts returned from r/python"
    assert all(p["kind"] == "t3" for p in posts)

    first = posts[0]["data"]
    assert first["title"], "post missing title"
    assert "ups" in first, "post missing ups"
    assert "num_comments" in first, "post missing num_comments"
    assert first["permalink"].startswith("/"), "permalink must be a path"
    assert first["created_utc"] > 0, "created_utc must be a real timestamp"
    print(f"\n[v2] first post: {first['title'][:60]!r} ups={first['ups']}")


def test_v2_scrape_comments_shape():
    """Fetch comments for one post; verify the 2-element JSON-API shape."""
    posts = redditapiv2_client.get_subreddit_posts("python", limit=5)
    # Pick the first non-stickied post with comments, if possible.
    target = next(
        (p["data"] for p in posts if p["data"].get("num_comments", 0) > 0),
        posts[0]["data"],
    )

    result = redditapiv2_client.get_post_comments(target["id"], limit=10)
    assert isinstance(result, list) and len(result) == 2, "must return [post, comments] pair"
    assert result[1]["data"]["children"] is not None

    comment_children = result[1]["data"]["children"]
    for child in comment_children:
        assert child["kind"] == "t1", "comments must be wrapped as kind=t1"
    print(f"\n[v2] post {target['id']} -> {len(comment_children)} top-level comments")


def test_v2_rate_limit_status_keys():
    """Rate-limit status must expose the keys the frontend expects."""
    status = redditapiv2_client.get_rate_limit_status()
    expected = {
        "requests_in_window",
        "requests_remaining",
        "seconds_until_reset",
        "is_throttled",
        "limit",
        "window_seconds",
        "seconds_until_next_request",
    }
    assert expected.issubset(status.keys()), f"missing keys: {expected - set(status.keys())}"
    assert status["limit"] == config.reddit_requests_per_10min
    print(f"\n[v2] rate limit status: {status}")
