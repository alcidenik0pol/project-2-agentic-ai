"""Quick manual test to verify Reddit API access.

Run this before pytest for faster iteration during setup.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.reddit.client import create_reddit_client, test_api_access


def main():
    print("Testing Reddit API access...")
    print("-" * 40)

    try:
        client = create_reddit_client()
        print("Reddit client created")

        if test_api_access(client):
            print("API access verified")

            # Demonstrate fetching data
            subreddit = client.subreddit("python")
            print(f"\nFetching posts from r/{subreddit.display_name}...")

            for i, post in enumerate(subreddit.hot(limit=3), 1):
                print(f"\n{i}. {post.title}")
                print(f"   {post.ups} upvotes | {post.num_comments} comments")
                print(f"   Link: {post.url}")

            print("\n" + "-" * 40)
            print("SUCCESS: Reddit API is working!")
            return True
        else:
            print("API test failed")
            return False

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has correct credentials")
        print("2. Verify credentials at https://www.reddit.com/prefs/apps")
        print("3. Ensure your app is set to 'script' type")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
