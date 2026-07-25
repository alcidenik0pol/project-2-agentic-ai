"""Rank subreddit candidates from the Pushshift snapshot.

Reads the Jan 2018 Pushshift submissions Parquet, counts posts per subreddit,
drops the curated 89 + spam/bot + NSFW + tiny subs, and writes the top ~80 as
both a markdown table (for human review) and JSON (for the append step).

No Reddit network access — reads the local Parquet via DuckDB only.

Provenance: HuggingFace dataset fddemarco/pushshift-reddit (RS_2018-01_00.parquet).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.collector.subreddit_loader import load_subreddit_descriptions
from app.pushshift.client import PushshiftClient

# ─── filter constants (snapshot-specific; no reuse value in a separate file) ───
SPAM_BOT_BLOCKLIST = {
    "autonewspaper", "newsbotbot", "hotandtrending", "umukhasimautonews",
    "newswhatever", "newstweetfeed", "thenewsfeed", "breakingnews24hr",
    "onlinebargains", "prnewswire", "ecointernet", "miamiheraldauto",
    "removalbot", "thenewsrightnow", "bitcoinall", "pewdiepiesubmissions",
    "ice_poseidon", "megajoi", "the_donald",  # banned/drama
    # Added on review of top-80 output:
    "cbts_stream",            # banned QAnon conspiracy sub (2018)
    "shareyourblogpost",      # blog-promotion spam sub
    "freestuffnyc",           # geo-restricted spam/promo sub
    "noncensored_bitcoin",    # low-quality bitcoin fork/spinoff
}
NSFW_BLOCKLIST = {
    "gonewild", "dirtypenpals", "dirtykikpals", "dirtyr4r",
    "dirtysnapchat", "roleplaykik",
    # Added on review of top-80 output:
    "ageplaypenpals",         # NSFW fetish sub (slipped past name heuristic)
    "hotvids",                # NSFW video sub
}
MIN_POST_COUNT = 500
TOP_N = 80
PULL_DEPTH = 500  # how many top subs to pull from Pushshift before filtering

OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "ideation" / "reddit"


def _reddit_url(name: str) -> str:
    return f"https://reddit.com/r/{name}"


def main() -> None:
    # 1. Curated names (DRY — same source of truth as the rest of the app).
    curated = load_subreddit_descriptions()
    curated_lower = {name.lower() for name in curated}
    print(f"Curated subs loaded: {len(curated)}")

    # 2. Pushshift top-N by post count (direct DuckDB; client.search_posts is
    #    built for keyword/subreddit filtering, not whole-file GROUP BY).
    client = PushshiftClient()
    parquet = client._get_parquet_path()
    conn = client._get_connection()
    rows = conn.execute(
        f"""
        SELECT LOWER(subreddit) AS name, COUNT(*) AS post_count
        FROM read_parquet('{parquet}')
        GROUP BY LOWER(subreddit)
        ORDER BY post_count DESC
        LIMIT {PULL_DEPTH}
        """
    ).fetchall()
    print(f"Pushshift top-{PULL_DEPTH} pulled: {len(rows)} rows")

    # 3. Filter pipeline: subtract curated → drop spam → drop NSFW → drop tiny.
    filtered = []
    stats = {"dropped_curated": 0, "dropped_spam": 0, "dropped_nsfw": 0, "dropped_min_posts": 0}
    for name, post_count in rows:
        if name in curated_lower:
            stats["dropped_curated"] += 1
            continue
        if name in SPAM_BOT_BLOCKLIST:
            stats["dropped_spam"] += 1
            continue
        if name in NSFW_BLOCKLIST:
            stats["dropped_nsfw"] += 1
            continue
        if post_count < MIN_POST_COUNT:
            stats["dropped_min_posts"] += 1
            continue
        filtered.append((name, int(post_count)))

    top = filtered[:TOP_N]
    print(
        f"After filters: {len(filtered)} (dropped: {stats}) — writing top {len(top)}"
    )

    # 4. Write outputs.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Markdown table for human review.
    md = OUTPUT_DIR / "pushshift_candidate_subreddits.md"
    lines = [
        "# Pushshift-derived subreddit candidates",
        "",
        f"Generated: {timestamp}",
        "",
        "Source: `data/pushshift/RS_2018-01_00.parquet` (Jan 2018 submissions,",
        "HuggingFace `fddemarco/pushshift-reddit`). Post counts are January 2018",
        "submission volume — a proxy for activity, not current subscriber count.",
        "",
        f"Pipeline: top {PULL_DEPTH} by post_count → drop curated ({len(curated)})",
        f"→ drop spam/bot ({len(SPAM_BOT_BLOCKLIST)}) → drop NSFW ({len(NSFW_BLOCKLIST)})",
        f"→ drop post_count < {MIN_POST_COUNT} → take top {TOP_N}.",
        "",
        f"Filtered total: {len(filtered)}. Written: {len(top)}.",
        "",
        "| rank | subreddit | post_count | url | notes |",
        "|-----:|-----------|-----------:|-----|-------|",
    ]
    for rank, (name, post_count) in enumerate(top, 1):
        lines.append(f"| {rank} | r/{name} | {post_count:,} | {_reddit_url(name)} | |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # JSON for the append step.
    js = OUTPUT_DIR / "pushshift_candidates.json"
    payload = [
        {"rank": rank, "name": name, "post_count": post_count, "url": _reddit_url(name)}
        for rank, (name, post_count) in enumerate(top, 1)
    ]
    js.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote: {md}")
    print(f"Wrote: {js}")
    print(f"\nSummary: Curated={len(curated)}, Pushshift top-{PULL_DEPTH}={len(rows)}, "
          f"After filters={len(filtered)}, Top-N written={len(top)}")

    # 5. Sanity assertions (would indicate a logic bug if they fire).
    written_names = {name for _, name in [(r["rank"], r["name"]) for r in payload]}
    leaked_spam = written_names & SPAM_BOT_BLOCKLIST
    leaked_nsfw = written_names & NSFW_BLOCKLIST
    leaked_curated = written_names & curated_lower
    assert not leaked_spam, f"Blocklist leak (spam): {leaked_spam}"
    assert not leaked_nsfw, f"Blocklist leak (nsfw): {leaked_nsfw}"
    assert not leaked_curated, f"Curated leak: {leaked_curated}"


if __name__ == "__main__":
    main()
