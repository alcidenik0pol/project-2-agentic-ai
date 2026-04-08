"""Run the Reddit fetcher and save output to a timestamped file."""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"collection_{timestamp}.json"

    print(f"Running fetcher at {timestamp}")
    print(f"Output will be saved to: {output_file}")

    # Create fetcher
    fetcher = RedditFetcher(
        max_comments_per_post=10,
    )

    # Fetch posts for a topic
    topic = "python"
    print(f"\nFetching posts for topic: {topic}")

    result = fetcher.fetch_posts_for_topic(
        topic=topic,
        posts_limit=10,
        query_style="broad",
    )

    # Also fetch comments for the first few posts
    print(f"\nFetching comments for top {min(3, len(result.posts))} posts...")
    for i, post in enumerate(result.posts[:3]):
        comments = fetcher.fetch_comments_for_post(post.post.id)
        post.comments = comments
        print(f"  Post {i+1}: {len(comments)} comments")

    # Save to JSON
    output_data = {
        "timestamp": timestamp,
        "topic": result.topic,
        "subreddits_queried": result.subreddits_queried,
        "total_posts": result.total_posts,
        "total_comments": result.total_comments,
        "requests_made": result.requests_made,
        "collection_time_seconds": result.collection_time_seconds,
        "posts": [
            {
                "id": p.post.id,
                "title": p.post.title,
                "subreddit": p.post.subreddit,
                "upvotes": p.post.upvotes,
                "num_comments": p.post.num_comments,
                "url": p.post.url,
                "selftext": p.post.selftext[:500] if p.post.selftext else None,
                "created_utc": p.post.created_utc,
                "comments": [
                    {
                        "id": c.id,
                        "body": c.body[:500] if c.body else None,
                        "upvotes": c.upvotes,
                        "author": c.author,
                    }
                    for c in p.comments
                ],
            }
            for p in result.posts
        ],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"RESULTS SAVED TO: {output_file}")
    print(f"{'='*60}")
    print(f"Total posts: {result.total_posts}")
    print(f"Total comments: {result.total_comments}")
    print(f"Collection time: {result.collection_time_seconds:.1f}s")

    return output_file


if __name__ == "__main__":
    main()
