"""One-shot converter: linanqiu/reddit-dataset CSVs -> app-compatible JSON.

Reads all `*.csv` files in `data/linanqiu/`, transforms each row into the
app's `RedditPost` schema (matching the shape consumed by
`app/agents/tools/fetch.py::_fetch_test_data`), samples the top-N highest-
upvoted non-empty posts per subreddit, and writes a single combined JSON.

Output schema mirrors `data/_old/sample_posts_*.json` so the result can
drop into the existing test-mode loader with a one-line path change.

CSV header row is `,0,1,2,...,10` (pandas numeric headers + an unnamed
index column). The real field names come from `headers.txt`:
    text, id, subreddit, meta, time, author, ups, downs,
    authorlinkkarma, authorkarma, authorisgold

Usage:
    conda run -n agentic-ai-p2 python scripts/convert_linanqiu.py \\
        [--per-sub 200] [--out data/linanqiu/linanqiu_dataset.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "linanqiu"
DEFAULT_OUT = DATA_DIR / "linanqiu_dataset.json"

# Real column names (from headers.txt). The CSVs were written by pandas
# with one or more unnamed index columns at the front; we detect the count
# per-file and pad with `_index_*` placeholders so the data columns line up.
DATA_COLUMNS = [
    "text",
    "id",
    "subreddit",
    "meta",
    "time",
    "author",
    "ups",
    "downs",
    "authorlinkkarma",
    "authorkarma",
    "authorisgold",
]


def get_fieldnames_for_csv(csv_path: Path) -> list[str]:
    """Inspect the header row and build fieldnames matching its width.

    The dataset is inconsistent: most CSVs have 12 columns (1 index + 11
    data), but ~4 files have 13 columns (2 index + 11 data) because pandas
    wrote the row index twice. We trust the trailing 11 columns to be the
    data fields in the documented order, and pad the front with placeholders.
    """
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    n = len(header)
    if n <= len(DATA_COLUMNS):
        return DATA_COLUMNS[:n]
    extras = n - len(DATA_COLUMNS)
    return [f"_index_{i}" for i in range(extras)] + DATA_COLUMNS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("convert_linanqiu")


def synthesize_title(text: str, max_len: int = 80) -> str:
    """Truncate body text to a title-length string at the last word boundary."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space >= 20:  # only cut at a word if it leaves meaningful content
        truncated = truncated[:last_space]
    return truncated.rstrip(" ,.;:!?-—") + "…"


def synthesize_url(subreddit: str, post_id: str) -> str:
    """Build Reddit's canonical URL format for a post ID."""
    return f"https://www.reddit.com/r/{subreddit}/comments/{post_id}"


def parse_filename(filename: str) -> tuple[str, str]:
    """`<category>_<subreddit>.csv` -> (category, subreddit)."""
    stem = filename.removesuffix(".csv")
    if "_" not in stem:
        return ("uncategorized", stem)
    category, subreddit = stem.split("_", 1)
    return (category, subreddit)


def to_int(value: str | None) -> int:
    """Parse a float-as-string from the CSV into a non-negative int."""
    try:
        return max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def to_float(value: str | None) -> float:
    """Parse a float-as-string from the CSV into a float (0.0 on failure)."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def convert_subreddit_csv(
    csv_path: Path,
    category: str,
    subreddit: str,
    per_sub: int,
    min_ups: int = 1,
) -> tuple[list[dict], dict]:
    """Read one CSV; return (top-N posts, stats)."""
    posts: list[dict] = []
    seen_ids: set[str] = set()
    rows_read = 0
    rows_skipped_empty_text = 0
    rows_skipped_low_ups = 0
    rows_skipped_dup_id = 0
    rows_skipped_parse = 0

    fieldnames = get_fieldnames_for_csv(csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, fieldnames=fieldnames)
        # Skip the original numeric-header row (`,0,1,2,...`)
        try:
            next(reader)
        except StopIteration:
            return [], {"rows_read": 0}

        for raw in reader:
            rows_read += 1

            post_id = (raw.get("id") or "").strip()
            text = (raw.get("text") or "").strip()

            if not post_id:
                rows_skipped_parse += 1
                continue
            if post_id in seen_ids:
                rows_skipped_dup_id += 1
                continue
            if not text:
                rows_skipped_empty_text += 1
                continue

            ups = to_int(raw.get("ups"))
            if ups < min_ups:
                rows_skipped_low_ups += 1
                continue

            seen_ids.add(post_id)
            posts.append({
                "subreddit": subreddit,
                "category": category,
                "post": {
                    "id": post_id,
                    "title": synthesize_title(text),
                    "selftext": text,
                    "url": synthesize_url(subreddit, post_id),
                    "subreddit": subreddit,
                    "upvotes": ups,
                    "num_comments": 0,  # no threading info in source dataset
                    "upvote_ratio": None,  # not provided
                    "created_utc": to_float(raw.get("time")),
                    "author": (raw.get("author") or "").strip() or None,
                    "link_flair_text": None,
                    "distinguished": None,
                    "stickied": False,
                },
                "comments_count": 0,
            })

    posts.sort(key=lambda p: p["post"]["upvotes"], reverse=True)
    sampled = posts[:per_sub] if per_sub > 0 else posts

    stats = {
        "rows_read": rows_read,
        "kept": len(sampled),
        "filtered_total": rows_read - len(sampled),
        "skipped_empty_text": rows_skipped_empty_text,
        "skipped_low_ups": rows_skipped_low_ups,
        "skipped_dup_id": rows_skipped_dup_id,
        "skipped_parse": rows_skipped_parse,
        "discarded_by_cap": len(posts) - len(sampled) if per_sub > 0 else 0,
        "max_upvotes": sampled[0]["post"]["upvotes"] if sampled else 0,
        "min_upvotes": sampled[-1]["post"]["upvotes"] if sampled else 0,
    }
    return sampled, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert linanqiu CSVs to app-compatible JSON.",
    )
    parser.add_argument(
        "--per-sub",
        type=int,
        default=200,
        help="Top N posts per subreddit by upvotes (0 = keep all). Default 200.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON path. Default: {DEFAULT_OUT}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-subreddit log lines.",
    )
    args = parser.parse_args()

    if not DATA_DIR.is_dir():
        log.error("Dataset directory not found: %s", DATA_DIR)
        return 2

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        log.error("No CSV files found in %s", DATA_DIR)
        return 2

    log.info("Found %d CSV files in %s", len(csv_files), DATA_DIR)

    all_posts: list[dict] = []
    subreddits_queried: list[str] = []
    category_map: dict[str, str] = {}
    per_sub_stats: dict[str, dict] = {}
    total_rows_read = 0
    total_kept = 0

    for csv_path in csv_files:
        category, subreddit = parse_filename(csv_path.name)
        posts, stats = convert_subreddit_csv(
            csv_path, category, subreddit, args.per_sub,
        )
        all_posts.extend(posts)
        if subreddit not in subreddits_queried:
            subreddits_queried.append(subreddit)
        category_map[subreddit] = category
        per_sub_stats[subreddit] = stats
        total_rows_read += stats["rows_read"]
        total_kept += stats["kept"]
        if not args.quiet:
            log.info(
                "  %-40s rows=%7d  kept=%5d  ups=[%d..%d]",
                csv_path.name,
                stats["rows_read"],
                stats["kept"],
                stats["max_upvotes"],
                stats["min_upvotes"],
            )

    output = {
        "source": "linanqiu/reddit-dataset",
        "source_url": "https://github.com/linanqiu/reddit-dataset",
        "converted_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "notes": (
            "Converted from CSV (text/id/subreddit/meta/time/author/ups/downs) "
            "into the app's RedditPost schema. Source has no parent_id/link_id, "
            "so threads and comments are indistinguishable; num_comments is "
            "set to 0 and comments arrays are empty. title is synthesized "
            "from the first 80 chars of text. url is synthesized in Reddit's "
            "canonical format."
        ),
        "sampling": {
            "per_subreddit_cap": args.per_sub,
            "filters": ["text non-empty", f"ups >= {1}"],
            "sort": "ups desc",
            "total_rows_read": total_rows_read,
            "total_kept": total_kept,
        },
        "categories": category_map,
        "subreddits_queried": subreddits_queried,
        "total_posts": len(all_posts),
        "posts": all_posts,
        "per_subreddit_stats": per_sub_stats,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    size_mb = args.out.stat().st_size / 1024 / 1024
    log.info("=" * 60)
    log.info("Wrote %d posts across %d subreddits to %s",
             len(all_posts), len(subreddits_queried), args.out)
    log.info("File size: %.1f MB", size_mb)
    log.info("Total rows read: %d | kept: %d (%.1f%%)",
             total_rows_read, total_kept,
             100.0 * total_kept / total_rows_read if total_rows_read else 0.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
