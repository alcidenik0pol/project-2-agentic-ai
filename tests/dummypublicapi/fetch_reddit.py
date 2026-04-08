"""
Simple Reddit Public API Fetcher

Fetches posts from Reddit's public JSON API without authentication.
Just HTTP GET requests - no API keys, no OAuth required.
"""

import sys
import requests

# Fix Windows console encoding for unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def fetch_hot_posts(subreddit: str, limit: int = 10) -> list[dict]:
    """
    Fetch hot posts from a subreddit using Reddit's public JSON API.

    Args:
        subreddit: Name of the subreddit (e.g., 'python', 'all')
        limit: Number of posts to fetch (max 100)

    Returns:
        List of post dictionaries with title, upvotes, url, etc.
    """
    # Reddit public JSON endpoint
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"

    # Reddit requires a User-Agent header
    headers = {
        "User-Agent": "RedditPainPointFinder/1.0 (educational project)"
    }

    params = {"limit": limit}

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    # Extract post data from the response
    posts = []
    for child in data["data"]["children"]:
        post = child["data"]
        posts.append({
            "title": post["title"],
            "upvotes": post["ups"],
            "url": f"https://reddit.com{post['permalink']}",
            "subreddit": post["subreddit"],
            "author": post.get("author", "[deleted]"),
            "num_comments": post["num_comments"],
            "selftext": post.get("selftext", "")[:200] + "..." if post.get("selftext") else ""
        })

    return posts


def main():
    """Demo: Fetch and print posts from r/python"""
    print("=" * 60)
    print("Reddit Public API Fetcher - No Authentication Required")
    print("=" * 60)
    print()

    subreddit = "python"
    print(f"Fetching hot posts from r/{subreddit}...\n")

    try:
        posts = fetch_hot_posts(subreddit, limit=5)

        for i, post in enumerate(posts, 1):
            print(f"[{i}] {post['title']}")
            print(f"    Upvotes: {post['upvotes']} | Comments: {post['num_comments']}")
            print(f"    URL: {post['url']}")
            if post['selftext']:
                print(f"    Preview: {post['selftext']}")
            print()

        print(f"Successfully fetched {len(posts)} posts!")

    except requests.RequestException as e:
        print(f"Error fetching posts: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
