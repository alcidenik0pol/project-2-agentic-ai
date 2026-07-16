"""Test script for Pushshift (HuggingFace + DuckDB) data access.

Run: conda run -n agentic-ai-p2 python scripts/test_pushshift.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.pushshift.client import PushshiftClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_connection():
    """Test connection to HuggingFace Parquet via DuckDB."""
    print("\n" + "=" * 60)
    print("TEST 1: DuckDB + HuggingFace Connection")
    print("=" * 60)

    client = PushshiftClient()
    result = client.test_connection()

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Parquet Path: {result.get('parquet_path', 'N/A')}")
    print(f"Sample rows retrieved: {result['sample_rows']}")

    if result["data"]:
        print("\nSample posts from dataset:")
        for row in result["data"]:
            print(f"  - [{row['score']} pts] r/{row['subreddit']}")
            print(f"    {row['title'][:60]}...")
            print(f"    By: {row['author']}")

    client.close()
    return result["status"] == "success"


def test_keyword_search():
    """Test searching posts by keyword."""
    print("\n" + "=" * 60)
    print("TEST 2: Keyword Search")
    print("=" * 60)

    client = PushshiftClient()

    try:
        posts = client.search_posts(
            keyword="python",
            min_score=10,
            limit=5,
        )

        print(f"Found {len(posts)} posts containing 'python' with score >= 10")
        for post in posts:
            print(f"\n  [{post['score']} pts] r/{post['subreddit']}")
            print(f"    {post['title'][:80]}")
            if post.get('url'):
                print(f"    {post['url']}")

        client.close()
        return len(posts) > 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        client.close()
        return False


def test_subreddit_filter():
    """Test filtering by subreddit."""
    print("\n" + "=" * 60)
    print("TEST 3: Subreddit Filter")
    print("=" * 60)

    client = PushshiftClient()

    try:
        posts = client.search_posts(
            subreddits=["python", "learnpython"],
            min_score=5,
            limit=5,
        )

        print(f"Found {len(posts)} posts from r/python or r/learnpython")
        for post in posts:
            print(f"\n  [{post['score']} pts] r/{post['subreddit']}")
            print(f"    {post['title'][:80]}")

        client.close()
        return len(posts) > 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        client.close()
        return False


def test_high_score():
    """Test finding high-score posts."""
    print("\n" + "=" * 60)
    print("TEST 4: High-Score Posts (score >= 1000)")
    print("=" * 60)

    client = PushshiftClient()

    try:
        posts = client.search_posts(
            min_score=1000,
            limit=5,
        )

        print(f"Found {len(posts)} posts with score >= 1000")
        for post in posts:
            print(f"\n  [{post['score']} pts, {post.get('num_comments', 0)} comments]")
            print(f"    r/{post['subreddit']}: {post['title'][:60]}")

        client.close()
        return len(posts) > 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        client.close()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PUSHSHIFT CLIENT TEST")
    print("(Local Parquet + DuckDB)")
    print("=" * 60)
    print("Testing connection to local parquet dataset...")
    print("No rate limits, no auth required.")

    results = {
        "connection": test_connection(),
        "keyword_search": test_keyword_search(),
        "subreddit_filter": test_subreddit_filter(),
        "high_score": test_high_score(),
    }

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\nAll tests passed! Pushshift client is working.")
        print("\nData source: HuggingFace + DuckDB")
        print("  - Historical Reddit data from Pushshift archive")
        print("  - No rate limits or authentication required")
        print("  - Fast remote queries via DuckDB httpfs")
    else:
        print("\nSome tests failed. Check the output above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
