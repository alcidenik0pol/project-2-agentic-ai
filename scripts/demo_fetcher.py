"""Demo script showing the Reddit fetcher in action.

This demonstrates fetching real Reddit data without any credentials.
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

from app.collector.fetcher import RedditFetcher


def main():
    print("=" * 60)
    print("Reddit Fetcher Demo - No Credentials Required")
    print("=" * 60)

    # Create fetcher
    print("\n1. Creating RedditFetcher...")
    fetcher = RedditFetcher(
        requests_per_minute=10,
        max_comments_per_post=5,
    )
    print("   Fetcher created successfully")

    # Fetch hot posts from r/python
    print("\n2. Fetching 3 hot posts from r/python...")
    posts = fetcher.fetch_subreddit_hot("python", limit=3)

    print(f"   Fetched {len(posts)} posts")

    for i, post in enumerate(posts, 1):
        print(f"\n   Post {i}:")
        print(f"      Title: {post.post.title[:60]}...")
        print(f"      Upvotes: {post.post.upvotes}")
        print(f"      Comments: {post.post.num_comments}")
        print(f"      URL: {post.post.url[:60]}...")

    # Fetch posts for a topic
    print("\n3. Fetching hot posts for 'docker'...")
    result = fetcher.fetch_posts_for_topic(
        topic="docker",
        posts_limit=5,
    )

    print(f"\n   Collection results:")
    print(f"      Total posts: {result.total_posts}")
    print(f"      Total comments: {result.total_comments}")
    print(f"      Requests made: {result.requests_made}")
    print(f"      Time: {result.collection_time_seconds:.1f}s")

    if result.posts:
        print(f"\n   Sample post titles:")
        for p in result.posts[:3]:
            print(f"      - {p.post.title[:50]}...")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
