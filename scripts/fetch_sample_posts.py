"""Fetch hot posts from selected subreddits for data exploration.

This script fetches posts from 3 subreddits known for complaints:
- r/antiwork (work & career complaints)
- r/personalfinance (money struggles)
- r/ADHD (productivity challenges)

Outputs rate limit metrics and saves results to data/sample_posts.json.
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

# Selected subreddits for complaint analysis
SUBREDDITS = [
    ("antiwork", "Work & Career"),
    ("personalfinance", "Finance & Money"),
    ("ADHD", "Mental Health"),
]

POSTS_PER_SUBREDDIT = 100


def format_rate_limit_status(status: dict) -> str:
    """Format rate limit status for display."""
    return (
        f"Requests: {status['requests_in_window']}/{status['limit']} | "
        f"Remaining: {status['requests_remaining']} | "
        f"Reset in: {status['seconds_until_reset']}s"
    )


def main():
    """Fetch and display posts from selected subreddits."""
    # Ensure data directory exists
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    # Timestamped output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = data_dir / f"sample_posts_{timestamp}.json"

    # Initialize fetcher
    fetcher = RedditFetcher()

    all_posts = []
    total_posts = 0
    total_requests_before = fetcher.api.total_requests

    print("\n" + "=" * 60)
    print("REDDIT POST FETCHER - Sample Data Collection")
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

            print(f"Fetched {count} posts")
            print(f"Rate limit: {format_rate_limit_status(fetcher.api.get_rate_limit_status())}")

            # Store posts with metadata FIRST (before display to avoid encoding issues)
            for post_with_comments in posts:
                all_posts.append({
                    "subreddit": subreddit_name,
                    "category": category,
                    "post": post_with_comments.post.model_dump(),
                    "comments_count": len(post_with_comments.comments),
                })

            # Display posts (may fail on some characters, but data is already saved)
            try:
                for i, post_with_comments in enumerate(posts, 1):
                    post = post_with_comments.post
                    # Truncate title for display
                    title = post.title[:50] + "..." if len(post.title) > 50 else post.title
                    print(f"  [{i}] \"{title}\" ({post.upvotes} upvotes)")
            except UnicodeEncodeError:
                print(f"  (display skipped due to encoding)")

            print()

        except Exception as e:
            logger.error(f"Error fetching from r/{subreddit_name}: {e}")
            print(f"  ERROR: {e}\n")
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

    # Show throttling info if applicable
    if rate_limit_status["is_throttled"]:
        print("NOTE: Rate limit was reached during collection.")
        print(f"      Throttle wait time: {rate_limit_status['throttle_wait_time']}s")


if __name__ == "__main__":
    main()
