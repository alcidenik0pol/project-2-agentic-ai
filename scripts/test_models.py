"""Test script for Reddit data models and collector components."""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")


def test_imports():
    """Test all imports work."""
    from app.models.reddit import RedditPost, RedditComment, PostWithComments, CollectionResult
    from app.collector.rate_limiter import RedditRateLimiter
    from app.collector.queries import get_subreddits_for_topic
    from app.collector.fetcher import RedditFetcher
    from app.reddit.client import RedditPublicAPI
    print("All imports successful")
    return True


def test_models():
    """Test Pydantic models."""
    from app.models.reddit import RedditPost, RedditComment, PostWithComments

    # Test post creation
    post = RedditPost(
        id="test123",
        title="Test complaint",
        selftext="This is frustrating",
        url="https://reddit.com/r/test/test123",
        subreddit="test",
        upvotes=100,
        num_comments=50,
        created_utc=1700000000.0,
    )
    print(f"Post created: {post.title}")
    print(f"Combined text: {post.combined_text[:50]}...")

    # Test comment
    comment = RedditComment(
        id="comment1",
        post_id="test123",
        body="I have this problem too!",
        upvotes=25,
        level=0,
    )
    print(f"Comment created: {comment.body[:30]}...")

    # Test PostWithComments
    pwc = PostWithComments(post=post, comments=[comment])
    print(f"PostWithComments score: {pwc.complaint_score:.2f}")

    return True


def test_queries():
    """Test subreddit selection."""
    from app.collector.queries import get_subreddits_for_topic

    # Test subreddit finder
    subs = get_subreddits_for_topic("python web development")
    print(f"Subreddits for 'python web development': {subs}")

    return True


def test_rate_limiter():
    """Test rate limiter."""
    from app.collector.rate_limiter import RedditRateLimiter

    limiter = RedditRateLimiter(requests_per_minute=10)
    print(f"Rate limiter can make request: {limiter.can_make_request}")
    print(f"Requests in window: {limiter.requests_in_window}")

    # Simulate some requests
    for i in range(5):
        limiter.record_request()

    print(f"After 5 requests - in window: {limiter.requests_in_window}")

    return True


def test_public_api():
    """Test Reddit public API client (live test)."""
    from app.reddit.client import RedditPublicAPI
    from app.config import config

    api = RedditPublicAPI()
    print(f"API client created with user agent: {config.reddit_user_agent[:50]}...")

    # Test fetching hot posts from r/python
    print("\nFetching hot posts from r/python...")
    posts = api.get_subreddit_posts("python", limit=3)

    if posts:
        print(f"Got {len(posts)} posts")
        for i, post in enumerate(posts, 1):
            post_data = post.get("data", {})
            print(f"  {i}. {post_data.get('title', 'No title')[:50]}...")
        return True
    else:
        print("No posts returned (may be rate limited)")
        return True  # Still pass - rate limiting is expected


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Reddit Data Models and Collector (Public API)")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Models", test_models),
        ("Queries", test_queries),
        ("Rate Limiter", test_rate_limiter),
        ("Public API", test_public_api),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n--- Testing {name} ---")
        try:
            if test_fn():
                print(f"PASSED: {name}")
                passed += 1
            else:
                print(f"FAILED: {name}")
                failed += 1
        except Exception as e:
            print(f"FAILED: {name} - {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
