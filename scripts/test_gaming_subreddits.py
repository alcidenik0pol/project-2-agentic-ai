"""Test fetch from gaming subreddits to diagnose 403 blocking.

This tests the same subreddits that were failing in the main fetcher:
- r/gaming
- r/pcgaming
- r/patientgamers
- r/indiegaming
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.collector.fetcher import RedditFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Gaming subreddits that were getting 403s
SUBREDDITS = [
    ("gaming", "General Gaming"),
    ("pcgaming", "PC Gaming"),
    ("patientgamers", "Patient Gamers"),
    ("indiegaming", "Indie Gaming"),
]

POSTS_PER_SUBREDDIT = 10  # Small number for quick test


def format_rate_limit_status(status: dict) -> str:
    """Format rate limit status for display."""
    return (
        f"Requests: {status['requests_in_window']}/{status['limit']} | "
        f"Remaining: {status['requests_remaining']} | "
        f"Reset in: {status['seconds_until_reset']}s"
    )


def main():
    """Fetch and display posts from gaming subreddits."""
    # Ensure data directory exists
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    # Timestamped output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = data_dir / f"gaming_test_{timestamp}.json"

    # Initialize fetcher
    fetcher = RedditFetcher()

    all_posts = []
    total_posts = 0
    total_requests_before = fetcher.api.total_requests

    print("\n" + "=" * 60)
    print("GAMING SUBREDDIT TEST - Checking for 403s")
    print("=" * 60)
    print(f"\nRate limit status (before):")
    print(f"  {format_rate_limit_status(fetcher.api.get_rate_limit_status())}")
    print()

    for subreddit_name, category in SUBREDDITS:
        print(f"=== Fetching from r/{subreddit_name} ===")
        print(f"Category: {category}")

        try:
            posts = fetcher.fetch_subreddit_hot(subreddit_name, limit=POSTS_PER_SUBREDDIT)
            count = len(posts)
            total_posts += count

            print(f"SUCCESS: Fetched {count} posts")
            print(f"Rate limit: {format_rate_limit_status(fetcher.api.get_rate_limit_status())}")

            # Store posts with metadata
            for post_with_comments in posts:
                all_posts.append({
                    "subreddit": subreddit_name,
                    "category": category,
                    "post": post_with_comments.post.model_dump(),
                    "comments_count": len(post_with_comments.comments),
                })

            # Display first few posts
            for i, post_with_comments in enumerate(posts[:3], 1):
                post = post_with_comments.post
                title = post.title[:50] + "..." if len(post.title) > 50 else post.title
                print(f"  [{i}] \"{title}\" ({post.upvotes} upvotes)")

            print()

        except Exception as e:
            logger.error(f"ERROR fetching from r/{subreddit_name}: {e}")
            print(f"  FAILED: {e}\n")
            continue

    # Calculate totals
    total_requests = fetcher.api.total_requests - total_requests_before
    rate_limit_status = fetcher.api.get_rate_limit_status()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total posts: {total_posts}")
    print(f"Total requests: {total_requests}")
    print(f"Successful subreddits: {len([p for p in all_posts if p])}")
    print(f"Failed subreddits: {len(SUBREDDITS) - len(set(p['subreddit'] for p in all_posts))}")
    print(f"Rate limit status (after):")
    print(f"  {format_rate_limit_status(rate_limit_status)}")

    # Save results
    output_data = {
        "fetched_at": datetime.now().isoformat(),
        "subreddits_queried": [s[0] for s in SUBREDDITS],
        "total_posts": total_posts,
        "total_requests": total_requests,
        "rate_limit_status": rate_limit_status,
        "posts": all_posts,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()
