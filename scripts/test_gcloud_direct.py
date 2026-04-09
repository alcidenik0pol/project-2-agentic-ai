#!/usr/bin/env python
"""Direct test of Gemini API call to debug response parsing."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analyst.providers.gcloud import GCloudProvider
from app.analyst.prompts import CLASSIFICATION_PROMPT


def main():
    p = GCloudProvider()

    # Use the exact first post from sample_posts.json
    post_data = {
        "id": "1i79k8z",
        "title": "X, Meta, and CCP-affiliated content is no longer permitted",
        "selftext": "Hello, everyone! Following recent events in social media, we are updating our content policy.",
        "subreddit": "antiwork",
    }

    title = post_data["title"]
    selftext = post_data["selftext"]
    subreddit = post_data["subreddit"]

    prompt = CLASSIFICATION_PROMPT.format(title=title, selftext=selftext, subreddit=subreddit)

    print("=" * 60)
    print("PROMPT SENT TO GEMINI:")
    print("=" * 60)
    print(prompt)
    print()

    print("=" * 60)
    print("RAW API CALL:")
    print("=" * 60)

    response = p._client.generate_content(
        prompt,
        generation_config={
            "temperature": 0.1,
            "max_output_tokens": 1024,
        },
    )

    print(f"Type of response: {type(response)}")
    print(f"Dir of response: {[a for a in dir(response) if not a.startswith('_')]}")
    print()

    # Check response.text
    print("=" * 60)
    print("RESPONSE.TEXT:")
    print("=" * 60)
    print(repr(response.text))
    print()
    print(response.text)
    print()

    # Check candidates
    print("=" * 60)
    print("CANDIDATES:")
    print("=" * 60)
    if hasattr(response, 'candidates') and response.candidates:
        for i, cand in enumerate(response.candidates):
            print(f"Candidate {i}:")
            print(f"  finish_reason: {cand.finish_reason if hasattr(cand, 'finish_reason') else 'N/A'}")
            if hasattr(cand, 'content') and cand.content:
                print(f"  content parts: {len(cand.content.parts) if hasattr(cand.content, 'parts') else 'N/A'}")
                if hasattr(cand.content, 'parts'):
                    for j, part in enumerate(cand.content.parts):
                        print(f"  Part {j}: {repr(part.text)[:200] if hasattr(part, 'text') else 'no text attr'}")
    print()

    # Try parsing
    print("=" * 60)
    print("PARSE ATTEMPT:")
    print("=" * 60)
    result = p.parse_classification(response.text)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
