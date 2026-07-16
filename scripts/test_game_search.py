"""Quick test of pushshift search for 'game'."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pushshift.client import PushshiftClient

client = PushshiftClient()
posts = client.search_posts(keyword="game", min_score=1, limit=10)
print(f"Found {len(posts)} posts for 'game'")
if posts:
    for p in posts[:5]:
        print(f"  - [{p.get('score', 0)}] {p.get('title', '')[:60]}")
else:
    print("No posts found. Trying without keyword filter...")
    all_posts = client.search_posts(limit=5)
    print(f"Sample posts without filter: {len(all_posts)}")
    for p in all_posts:
        print(f"  - [{p.get('score', 0)}] {p.get('title', '')[:60]}")
client.close()
