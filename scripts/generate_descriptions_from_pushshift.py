"""Generate subreddit descriptions from Pushshift content via LLM.

Bypasses the login-walled `/about/` endpoint by deriving each subreddit's
description from its own top posts in the Pushshift Parquet. For each
candidate, an LLM (1) assumes what the sub is about from its name, then
(2) confirms/disproves/enriches that assumption using its top-scoring
January 2018 posts.

Merges the LLM-derived entries with the existing curated JSON (which keeps
its real sidebar descriptions) and writes a combined
``subreddit_descriptions_<ts>.json`` the loader picks up by mtime.

No Reddit network access — reads the local Parquet + calls the LLM only.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.analyst.providers import get_provider
from app.collector.subreddit_loader import _find_newest_descriptions
from app.config import config
from app.pushshift.client import PushshiftClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CANDIDATES_FILE = (
    Path(__file__).parent.parent / "docs" / "ideation" / "reddit" / "pushshift_candidates.json"
)
OUTPUT_DIR = Path(__file__).parent.parent / "data"

TOP_POSTS_PER_SUB = 15
TITLE_MAX_CHARS = 200
SELFTEXT_MAX_CHARS = 300

# Two-step prompt: assume from name, then confirm/enrich from evidence.
PROMPT_TEMPLATE = """You are characterizing a Reddit subreddit for a complaint-analysis app.

Subreddit name: r/{name}

Step 1 - ASSUMPTION: Based on the name alone, what would you guess this subreddit is about?

Step 2 - EVIDENCE: Here are the top-scoring posts from January 2018 (titles + self-text snippets):
{posts}

Step 3 - SYNTHESIZE: Confirm, disprove, or enrich the assumption using the actual posts. \
Then write a concise description grounded in what the community actually discusses, \
not just what the name implies.

Output STRICT JSON only (no markdown fences, no commentary):
{{
    "title": "<short human-readable title, e.g. 'Personal Finance' or 'League of Legends'>",
    "public_description": "<1-2 sentences describing what the subreddit is about>"
}}"""


def _format_posts(posts: list[dict]) -> str:
    """Render the top-posts block for the LLM prompt."""
    if not posts:
        return "(no posts found in the Jan 2018 snapshot)"
    lines = []
    for i, p in enumerate(posts, 1):
        title = (p.get("title") or "").strip()[:TITLE_MAX_CHARS]
        if not title:
            continue  # skip titleless rows
        selftext = (p.get("selftext") or "").strip()
        if selftext:
            lines.append(f"{i}. {title}\n   \"{selftext[:SELFTEXT_MAX_CHARS]}\"")
        else:
            lines.append(f"{i}. {title}")
    return "\n".join(lines) if lines else "(no usable post titles)"


def main() -> None:
    candidates = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    print(f"\nCandidates to process: {len(candidates)}")

    # Existing curated JSON (real sidebar descriptions) — keep as-is, merge later.
    project_root = Path(__file__).resolve().parents[1]
    existing_path = _find_newest_descriptions(project_root)
    if existing_path is None:
        print("ERROR: no existing subreddit_descriptions_*.json found under data/")
        sys.exit(1)
    existing = json.loads(existing_path.read_text(encoding="utf-8"))
    existing_subs = existing.get("subreddits", [])
    existing_names = {s.get("name", "").lower() for s in existing_subs}
    print(f"Existing entries: {len(existing_subs)} (from {existing_path.name})")

    # Defensive dedupe: skip any candidate already present in the existing JSON.
    to_process = [c for c in candidates if c["name"].lower() not in existing_names]
    skipped = len(candidates) - len(to_process)
    if skipped:
        print(f"Skipping {skipped} candidates already in existing JSON")
    print(f"To generate: {len(to_process)}\n")

    provider = get_provider(config.llm_provider)
    print(f"Provider: {provider.provider_name} / {provider.model_name}")
    pushshift = PushshiftClient()

    new_entries: list[dict] = []
    failed: list[dict] = []
    start_time = time.time()

    for i, cand in enumerate(to_process, 1):
        name = cand["name"]
        post_count = cand["post_count"]
        elapsed = time.time() - start_time
        print(f"[{i}/{len(to_process)}] r/{name:<28s} {elapsed:>5.0f}s elapsed", end="")

        try:
            posts = pushshift.search_posts(subreddits=[name], limit=TOP_POSTS_PER_SUB)
            prompt = PROMPT_TEMPLATE.format(name=name, posts=_format_posts(posts))

            # max_tokens=2048: Gemini 2.5 Flash reasons before emitting JSON;
            # 512 truncates mid-string. 2048 is ample for this simple task.
            raw = provider.generate_structured(
                prompt=prompt, temperature=0.3, max_tokens=2048, use_fast=True
            )
            if not raw:
                print(" -> EMPTY LLM RESPONSE")
                failed.append({"name": name, "error": "empty_llm_response"})
                continue

            # Strip accidental markdown fences before parsing.
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1] if "\n" in text else text
                if text.endswith("```"):
                    text = text[: -3]
            parsed = json.loads(text)

            title = (parsed.get("title") or name).strip()
            desc = (parsed.get("public_description") or "").strip()
            if not desc:
                print(" -> EMPTY DESCRIPTION")
                failed.append({"name": name, "error": "empty_description"})
                continue

            new_entries.append({
                "url": f"https://reddit.com/r/{name}",
                "name": name,
                "title": title,
                "public_description": desc,
                "description": desc,  # match v2 parser convention; loader reads public_description
                "subscribers": post_count,  # proxy: Jan 2018 post volume (no real subscriber count)
                "over18": False,
                "created_utc": 0.0,
            })
            print(f" -> OK ({len(posts)} posts) \"{title}\"")

        except json.JSONDecodeError as e:
            preview = (raw[:200] if raw else "(none)")
            print(f" -> JSON PARSE FAIL")
            logger.warning(f"r/{name}: bad JSON ({e}). raw={preview}")
            failed.append({"name": name, "error": f"json_decode: {e}"})
        except Exception as e:
            print(f" -> ERROR ({type(e).__name__}: {e})")
            logger.warning(f"r/{name}: {type(e).__name__}: {e}")
            failed.append({"name": name, "error": f"{type(e).__name__}: {e}"})

    elapsed_total = time.time() - start_time

    # Merge: existing entries (real sidebars) + LLM-derived new entries.
    combined_subs = existing_subs + new_entries

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"subreddit_descriptions_{timestamp}.json"

    output = {
        "timestamp": timestamp,
        "total_subreddits": len(combined_subs),
        "successful": len(new_entries),
        "failed": len(failed),
        "elapsed_seconds": round(elapsed_total, 1),
        "source": (
            f"{len(existing_subs)} curated (real sidebar, from {existing_path.name}) + "
            f"{len(new_entries)} Pushshift-derived (LLM from top posts, Jan 2018 snapshot)"
        ),
        "subreddits": combined_subs,
        "failed_subreddits": failed,
    }
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"DONE: {len(new_entries)}/{len(to_process)} new generated, "
          f"{len(failed)} failed")
    print(f"Combined: {len(existing_subs)} existing + {len(new_entries)} new = "
          f"{len(combined_subs)} total")
    print(f"Elapsed: {elapsed_total:.0f}s")
    print(f"Output: {output_file}")
    if failed:
        print(f"\nFailed:")
        for entry in failed:
            print(f"  r/{entry['name']}: {entry['error']}")
    print()


if __name__ == "__main__":
    main()
