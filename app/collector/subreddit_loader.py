# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: LEGACY (Reddit API)
# Part of the original Reddit API data collection workflow.
# Used when: get_data_source() == "reddit_live"
# ═══════════════════════════════════════════════════════════════════════════
"""Load and cache subreddit descriptions from JSON."""

import glob
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_descriptions_cache: dict[str, dict] | None = None


def _find_newest_descriptions(project_root: Path) -> Path | None:
    """Find the newest subreddit_descriptions_*.json under data/, recursively.

    Globs data/**/subreddit_descriptions_*.json so the file survives moves to
    subdirectories (e.g. data/smallsample/) and future regenerations without
    code changes. Returns the highest-mtime match, or None if none exist.
    """
    pattern = str(project_root / "data" / "**" / "subreddit_descriptions_*.json")
    candidates = glob.glob(pattern, recursive=True)
    if not candidates:
        return None
    return Path(max(candidates, key=os.path.getmtime))


def load_subreddit_descriptions(
    min_subscribers: int = 1000,
    include_over18: bool = False,
) -> dict[str, dict]:
    """Load subreddit descriptions from JSON, with optional filtering.

    Args:
        min_subscribers: Minimum subscriber count to include.
        include_over18: Whether to include NSFW subreddits.

    Returns:
        Dict mapping subreddit name -> metadata dict with title,
        public_description, description, subscribers.
    """
    global _descriptions_cache

    if _descriptions_cache is not None:
        return _descriptions_cache

    project_root = Path(__file__).resolve().parents[2]
    actual_path = _find_newest_descriptions(project_root)

    if actual_path is None:
        logger.warning(
            "Subreddit descriptions file not found under %s/data; "
            "LLM subreddit selection will fall back to the bare list.",
            project_root,
        )
        return {}

    with open(actual_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered: dict[str, dict] = {}
    for sub in data.get("subreddits", []):
        name = sub.get("name")
        if not name:
            continue
        if sub.get("subscribers", 0) < min_subscribers:
            continue
        if not include_over18 and sub.get("over18", False):
            continue

        filtered[name] = {
            "title": sub.get("title", ""),
            "public_description": sub.get("public_description", ""),
            "description": sub.get("description", ""),
            "subscribers": sub.get("subscribers", 0),
        }

    _descriptions_cache = filtered
    logger.info("Loaded %d subreddit descriptions from %s", len(filtered), actual_path)
    return filtered


def format_subreddit_for_prompt(name: str, metadata: dict) -> str:
    """Format a subreddit for LLM prompt: 'name — title — description'."""
    title = metadata.get("title", name)
    desc = metadata.get("public_description", "")
    if len(desc) > 200:
        desc = desc[:197] + "..."
    return f"{name} — {title} — {desc}"
