#!/usr/bin/env python3
"""Quick test of single post classification."""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.analyst import PostClassifier

# Load one post from the file
with open(project_root / "data" / "sample_posts_20260407_145826.json") as f:
    data = json.load(f)
    single_post = data["posts"][:1]

print("Testing single post classification...")
print(f"Post title: {single_post[0]['post']['title'][:60]}...")

classifier = PostClassifier(request_delay=2.0)  # Short delay for single test
result = classifier.classify_batch(single_post)

post = result.posts[0]
print(f"\nResult:")
print(f"  Theme: {post.classification.theme if post.classification else 'FAILED'}")
print(f"  Is Complaint: {post.classification.is_complaint if post.classification else 'N/A'}")
print(f"  Intensity: {post.classification.intensity if post.classification else 'N/A'}")
print(f"  Attempts: {post.classification_attempts}")
