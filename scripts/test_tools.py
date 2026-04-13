"""Test individual tools in TEST mode."""

import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.agents.tools.fetch import fetch_posts
from app.agents.tools.artifacts import save_artifact


def test_fetch_posts():
    print("Testing fetch_posts in TEST mode...")
    result = fetch_posts(topic="personal finance pain points")
    data = json.loads(result)
    print(f"  Mode: {data.get('mode')}")
    print(f"  Total posts: {data.get('total_posts')}")
    print(f"  First post title: {data['posts'][0]['post']['title'][:60]}...")
    assert data["total_posts"] > 0, "Expected posts in test data"
    print("  [OK] fetch_posts test mode works")
    return result


def test_save_artifact():
    print("\nTesting save_artifact...")
    test_data = json.dumps({"test": "hello", "count": 42})
    result = save_artifact(test_data, "report")
    data = json.loads(result)
    print(f"  Status: {data.get('status')}")
    print(f"  Path: {data.get('path')}")
    assert data["status"] == "saved", f"Expected 'saved', got {data.get('status')}"
    print("  [OK] save_artifact works")
    return result


if __name__ == "__main__":
    test_fetch_posts()
    test_save_artifact()
    print("\nAll tool tests passed!")
