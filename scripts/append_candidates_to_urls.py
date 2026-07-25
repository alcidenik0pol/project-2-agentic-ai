"""Append Pushshift-derived subreddit candidates to subreddit_urls.md.

Reads docs/ideation/reddit/pushshift_candidates.json, dedupes against the
URLs already present in subreddit_urls.md (reusing the fetcher's parser),
and appends the survivors under a single provenance header.

Append-only — non-destructive. ``git checkout docs/ideation/reddit/subreddit_urls.md``
fully reverts.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fetch_subreddit_descriptions import parse_subreddit_urls

ROOT = Path(__file__).resolve().parents[1]
URLS_FILE = ROOT / "docs" / "ideation" / "reddit" / "subreddit_urls.md"
CANDIDATES_FILE = ROOT / "docs" / "ideation" / "reddit" / "pushshift_candidates.json"

HEADER = "# Pushshift-derived additions (Jan 2018 snapshot)"


def main() -> None:
    candidates = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    print(f"Candidates in JSON: {len(candidates)}")

    existing_names = {n.lower() for n in parse_subreddit_urls(URLS_FILE)}
    print(f"Names already in {URLS_FILE.name}: {len(existing_names)}")

    # Preserve rank order from the candidate JSON; skip dupes case-insensitively.
    to_append = [
        c for c in candidates
        if c["name"].lower() not in existing_names
    ]
    skipped = len(candidates) - len(to_append)
    print(f"To append: {len(to_append)} (skipped {skipped} duplicates)")

    if not to_append:
        print("Nothing to append.")
        return

    block = [HEADER, ""]
    for c in to_append:
        block.append(c["url"])
    block.append("")

    # Append (don't overwrite) — preserve the existing categorized sections.
    with open(URLS_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(block) + "\n")

    print(f"\nAppended {len(to_append)} URLs under '{HEADER}'")
    print(f"Revert with: git checkout {URLS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
