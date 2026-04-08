"""Live test script for Reddit fetcher.

Run this to verify the fetcher works with real Reddit API.
Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT env vars.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def main():
    """Test fetching data from Reddit."""
    from app.collector.fetcher import RedditFetcher

    print("=" * 60)
    print("Testing Reddit Fetcher with Live Data")
    print("=" * 60)

    # Create fetcher with conservative settings
    print("\nCreating RedditFetcher...")
    fetcher = RedditFetcher(
        requests_per_minute=10,
        max_comments_per_post=5,  # Fewer comments for quick test
    )
    print("Fetcher created successfully")

    # Test fetching hot posts from r/python
    print("\n--- Testing fetch_subreddit_hot ---")
    posts = fetcher.fetch_subreddit_hot("python", limit=3)

    print(f"Fetched {len(posts)} posts from r/python")

    for i, post in enumerate(posts, 1):
        print(f"\nPost {i}:")
        print(f"  Title: {post.post.title[:60]}...")
        print(f"  Upvotes: {post.post.upvotes}")
        print(f"  Comments: {len(post.comments)}")
        print(f"  Complaint Score: {post.complaint_score:.2f}")
        if post.comments:
            print(f"  First comment preview: {post.comments[0].body[:50]}...")

    # Print rate limiter stats
    print("\n--- Rate Limiter Stats ---")
    print(f"Total requests made: {fetcher.rate_limiter.total_requests}")
    print(f"Requests in current window: {fetcher.rate_limiter.requests_in_window}")

    print("\n" + "=" * 60)
    print("Live test complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
