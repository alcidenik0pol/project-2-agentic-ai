"""Fetch subreddit descriptions from Reddit and output as JSON.

Reads subreddit URLs from docs/ideation/reddit/subreddit_urls.md,
fetches metadata for each via Reddit's public API, and saves
structured JSON with descriptions, subscriber counts, etc.

Rate limited to 10 requests/minute. ~110 subreddits = ~11 minutes.
"""

import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.reddit.client import RedditPublicAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

INPUT_FILE = Path(__file__).parent.parent / "docs" / "ideation" / "reddit" / "subreddit_urls.md"
OUTPUT_DIR = Path(__file__).parent.parent / "data"


def parse_subreddit_urls(filepath: Path) -> list[str]:
    """Extract subreddit names from the markdown file.

    Returns:
        List of subreddit names (without r/ prefix), preserving order and deduped.
    """
    names = []
    seen = set()
    url_pattern = re.compile(r"https://reddit\.com/r/(\w+)", re.IGNORECASE)

    for line in filepath.read_text(encoding="utf-8").splitlines():
        match = url_pattern.search(line.strip())
        if match:
            name = match.group(1)
            if name.lower() not in seen:
                seen.add(name.lower())
                names.append(name)

    return names


def format_eta(seconds: float) -> str:
    """Format seconds into a human-readable ETA string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def main():
    """Fetch subreddit descriptions and save to JSON."""
    # Parse input
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    subreddit_names = parse_subreddit_urls(INPUT_FILE)
    total = len(subreddit_names)
    print(f"\nParsed {total} subreddits from {INPUT_FILE.name}")

    # Estimate time
    client = RedditPublicAPI()
    estimated_minutes = total / 10
    print(f"Estimated time: ~{estimated_minutes:.0f} minutes (at 10 req/min rate limit)")
    print()

    # Output file
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"subreddit_descriptions_{timestamp}.json"

    results = []
    failed = []
    start_time = time.time()

    for i, name in enumerate(subreddit_names, 1):
        elapsed = time.time() - start_time
        remaining = total - i + 1
        # Rough ETA: remaining items / 10 per minute * 60 seconds
        eta_seconds = (remaining / 10) * 60
        print(f"[{i}/{total}] r/{name:<30s} {format_eta(elapsed)} elapsed, ~{format_eta(eta_seconds)} remaining", end="")

        try:
            data = client.get_subreddit_info(name)
            if data is None:
                print(" -> EMPTY RESPONSE")
                failed.append({"name": name, "error": "empty_response"})
                continue

            results.append({
                "url": f"https://reddit.com/r/{name}",
                "name": name,
                "title": data.get("title", ""),
                "public_description": data.get("public_description", ""),
                "description": data.get("description", ""),
                "subscribers": data.get("subscribers", 0),
                "over18": data.get("over18", False),
                "created_utc": data.get("created_utc", 0),
            })
            subs = data.get("subscribers", 0)
            print(f" -> OK ({subs:,} subscribers)")

        except Exception as e:
            status = getattr(e, "response", None)
            status_code = status.status_code if status is not None else None
            reason = f"HTTP {status_code}" if status_code else str(e)
            print(f" -> FAILED ({reason})")
            logger.warning(f"Failed to fetch r/{name}: {reason}")
            failed.append({
                "name": name,
                "error": reason,
            })

    elapsed_total = time.time() - start_time

    # Build output
    output = {
        "timestamp": timestamp,
        "total_subreddits": total,
        "successful": len(results),
        "failed": len(failed),
        "elapsed_seconds": round(elapsed_total, 1),
        "rate_limit": {
            "requests_per_minute": 10,
            "estimated_time_minutes": round(estimated_minutes, 1),
        },
        "subreddits": results,
        "failed_subreddits": failed,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"DONE - {len(results)}/{total} successful, {len(failed)} failed")
    print(f"Elapsed: {format_eta(elapsed_total)}")
    print(f"Output: {output_file}")
    if failed:
        print(f"\nFailed subreddits:")
        for entry in failed:
            print(f"  r/{entry['name']}: {entry['error']}")
    print()


if __name__ == "__main__":
    main()
