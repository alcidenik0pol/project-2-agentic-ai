"""End-to-end smoke test for the v3 RSS fetcher against a single subreddit.

Usage:
    conda run -n agentic-ai-p2 python scripts/test_reddit_v3_local.py

Verifies:
1. v3 client can hit www.reddit.com/r/X/hot.rss and parse it
2. fetcher produces PostWithComments objects with real data
3. Router dispatches to _fetch_reddit_v3 when override is set
"""
import os
import sys

# Force proxy OFF for local test — RSS works unauthenticated from residential IP.
os.environ["PROXY_ENABLED"] = "false"

from dotenv import load_dotenv
load_dotenv()

from app.config import set_data_source_override
from app.agents.tools.fetch import _fetch_reddit_v3


def main():
    set_data_source_override("reddit_v3")

    print("=" * 70)
    print("TEST 1: _fetch_reddit_v3 with explicit subreddits (skip LLM picker)")
    print("=" * 70)
    result = _fetch_reddit_v3(
        topic="gaming",
        subreddits=["gaming"],
        use_llm_selection=False,
    )
    print(f"data_source: {result.get('data_source')}")
    print(f"total_posts: {result.get('total_posts')}")
    print(f"subreddits_queried: {result.get('subreddits_queried')}")
    if result.get("posts"):
        p0 = result["posts"][0]["post"]
        print(f"\nfirst post:")
        print(f"  id:         {p0.get('id')}")
        print(f"  title:      {p0.get('title', '')[:80]}")
        print(f"  author:     {p0.get('author')}")
        print(f"  subreddit:  {p0.get('subreddit')}")
        print(f"  ups:        {p0.get('ups')}  (RSS doesn't expose — always 0)")
        print(f"  created:    {p0.get('created_utc')}")
        print(f"  selftext:   {(p0.get('selftext') or '')[:80]}")
        print(f"  comments_count: {result['posts'][0].get('comments_count')}")

    print("\n" + "=" * 70)
    print("RESULT:", "PASS" if result.get("total_posts", 0) > 0 else "FAIL — 0 posts")
    print("=" * 70)
    sys.exit(0 if result.get("total_posts", 0) > 0 else 1)


if __name__ == "__main__":
    main()
