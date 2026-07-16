# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: REDDIT V2 (old.reddit.com HTML scraper)
# Scrapes old.reddit.com HTML listings/comments/about and returns dicts
# whose keys match what app/collector/fetcher.py already consumes.
# Pure functions (no HTTP) — unit-testable in isolation.
# ═══════════════════════════════════════════════════════════════════════════
"""Pure HTML parsers for old.reddit.com pages.

These functions take raw HTML and return plain dicts shaped exactly like the
Reddit public JSON API output (wrapped in ``{"kind": "t3"|"t1", "data": {...}}``)
so that :mod:`app.collector.fetcher` can consume them unchanged.

No network access here — all HTTP is handled by the client module.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Matches suffixed numbers like "1.2k", "3m", "12,345"
_SUFFIX_MULTIPLIERS = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}


def _safe_int(value: str | None) -> int:
    """Parse a Reddit-rendered count that may contain commas / k / m / b suffixes.

    Returns 0 for missing/empty/garbage values.
    """
    if value is None:
        return 0
    text = str(value).strip().replace(",", "").lower()
    if not text:
        return 0
    # Strip trailing non-numeric noise (e.g. "2 points")
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*([kmb]?)", text)
    if not m:
        return 0
    num = float(m.group(1))
    suffix = m.group(2)
    if suffix in _SUFFIX_MULTIPLIERS:
        num *= _SUFFIX_MULTIPLIERS[suffix]
    return int(round(num))


def _iso_to_timestamp(iso_str: str | None) -> float:
    """Convert an ISO-8601 datetime (e.g. ``2026-07-04T16:05:06+00:00``) to epoch seconds.

    Returns 0.0 on failure.
    """
    if not iso_str:
        return 0.0
    try:
        # Python 3.11+ fromisoformat handles the trailing +00:00 offset.
        return datetime.fromisoformat(iso_str).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _ms_to_timestamp(ms: str | None) -> float:
    """Convert a millisecond epoch string (data-timestamp) to epoch seconds."""
    if not ms:
        return 0.0
    try:
        return int(ms) / 1000.0
    except (ValueError, TypeError):
        return 0.0


def _permalink_to_path(href: str | None) -> str:
    """Normalize a Reddit URL to a path starting with ``/``.

    old.reddit emits absolute URLs in ``a.title`` and a path in ``data-permalink``.
    """
    if not href:
        return ""
    path = href.strip()
    # Strip protocol + host if absolute
    m = re.match(r"^https?://[^/]+(/.*)$", path)
    if m:
        path = m.group(1)
    if not path.startswith("/"):
        path = "/" + path
    # Drop query/fragment
    return path.split("?", 1)[0].split("#", 1)[0]


def parse_post_listing(html: str) -> list[dict]:
    """Parse an old.reddit.com subreddit listing page.

    Returns a list of post wrappers ``[{"kind": "t3", "data": {...}}, ...]``.
    """
    soup = BeautifulSoup(html, "lxml")
    things = soup.select("div.thing[data-fullname]")
    results: list[dict] = []

    for thing in things:
        post = _parse_post_thing(thing)
        if post:
            results.append({"kind": "t3", "data": post})

    return results


def _parse_post_thing(thing: BeautifulSoup) -> dict | None:
    """Extract a single post dict from a ``<div class="thing ...">`` node."""
    fullname = thing.get("data-fullname") or ""
    if not fullname.startswith("t3_"):
        return None

    classes = thing.get("class") or []
    title_el = thing.select_one("a.title")
    title = title_el.get_text(strip=True) if title_el else ""

    # created_utc: prefer data-timestamp (ms epoch); fall back to <time datetime>.
    created_utc = _ms_to_timestamp(thing.get("data-timestamp"))
    if not created_utc:
        time_el = thing.select_one(".tagline time[datetime]")
        created_utc = _iso_to_timestamp(time_el.get("datetime") if time_el else None)

    author_el = thing.select_one(".tagline .author")
    author_text = author_el.get_text(strip=True) if author_el else None
    author = None if author_text in (None, "[deleted]") else author_text

    md_el = thing.select_one(".usertext-body .md")
    selftext = md_el.get_text(strip=True) if md_el else None

    flair_el = thing.select_one(".linkflairlabel")
    link_flair_text = flair_el.get_text(strip=True) if flair_el else None

    subreddit = (
        thing.get("data-subreddit")
        or (thing.select_one(".tagline a.subreddit").get_text(strip=True)
            if thing.select_one(".tagline a.subreddit") else "")
    )

    permalink = _permalink_to_path(
        thing.get("data-permalink")
        or (title_el.get("href") if title_el else None)
    )

    distinguished = None
    if any(c == "distinguished-moderator" for c in classes):
        distinguished = "moderator"
    elif any(c == "distinguished-admin" for c in classes):
        distinguished = "admin"

    return {
        "id": fullname[3:],  # strip t3_
        "title": title,
        "permalink": permalink,
        "ups": _safe_int(thing.get("data-score")),
        "num_comments": _safe_int(thing.get("data-comments-count")),
        "upvote_ratio": None,  # not exposed in old.reddit HTML
        "created_utc": created_utc,
        "author": author,
        "selftext": selftext,
        "subreddit": subreddit,
        "link_flair_text": link_flair_text,
        "distinguished": distinguished,
        "stickied": "stickied" in classes,
    }


def parse_comments_page(html: str) -> tuple[dict, list[dict]]:
    """Parse an old.reddit.com comments page.

    Returns ``(post_data, comments_list)`` where ``comments_list`` contains only
    **top-level** comment wrappers (``{"kind": "t1", "data": {...}}``), matching
    v1's flat ``level=0`` behaviour. Nested replies inside ``.child`` are ignored.
    """
    soup = BeautifulSoup(html, "lxml")

    # The post itself (the t3 thing at the top of a comments page).
    post_thing = soup.select_one("div.thing[data-fullname^='t3_']")
    post_data = _parse_post_thing(post_thing) if post_thing else {}
    if not post_data:
        post_data = {"id": "", "title": "", "permalink": ""}

    # Top-level comments only: direct children of div.commentarea div.sitetable.
    commentarea = soup.select_one("div.commentarea div.sitetable")
    comments: list[dict] = []
    if commentarea:
        post_id = post_data.get("id", "")
        for thing in commentarea.select(":scope > div.thing[data-fullname^='t1_']"):
            comment = _parse_comment_thing(thing, post_id)
            if comment:
                comments.append({"kind": "t1", "data": comment})

    return post_data, comments


def _parse_comment_thing(thing: BeautifulSoup, post_id: str) -> dict | None:
    """Extract a single comment dict. Returns None for deleted/missing bodies."""
    fullname = thing.get("data-fullname") or ""
    if not fullname.startswith("t1_"):
        return None

    md_el = thing.select_one(".usertext-body .md")
    body = md_el.get_text(strip=True) if md_el else None
    if not body:
        # Deleted / removed comments have no body — filter them out.
        return None

    # Comment score: old.reddit renders three <span class="score ..."> siblings;
    # the ".unvoted" one's title attribute holds the canonical (fuzzed) point count.
    ups = 0
    score_el = thing.select_one(".tagline .score.unvoted")
    if score_el:
        ups = _safe_int(score_el.get("title") or score_el.get_text(strip=True))
    else:
        # Fallback: any .score element's title.
        any_score = thing.select_one(".tagline .score[title]")
        if any_score:
            ups = _safe_int(any_score.get("title"))

    author_el = thing.select_one(".tagline .author")
    author_text = author_el.get_text(strip=True) if author_el else None
    author = None if author_text in (None, "[deleted]") else author_text

    # parent_id: top-level comments have no .parent link (their parent is the post).
    parent_id = f"t3_{post_id}" if post_id else None

    return {
        "id": fullname[3:],  # strip t1_
        "body": body,
        "ups": ups,
        "author": author,
        "parent_id": parent_id,
    }


def parse_subreddit_about(html: str) -> dict:
    """Parse an old.reddit.com subreddit about page.

    Returns a dict with the keys the rest of the app reads from subreddit info:
    ``display_name``, ``title``, ``public_description``, ``description``,
    ``subscribers``. Returns an empty-ish dict when the page lacks the data.
    """
    soup = BeautifulSoup(html, "lxml")

    title = ""
    title_el = soup.select_one(".titlebox h1")
    if title_el:
        title = title_el.get_text(strip=True)

    display_name = title
    name_el = soup.select_one(".titlebox .redditname a")
    if name_el:
        display_name = name_el.get_text(strip=True)

    public_description = ""
    desc_el = soup.select_one(".titlebox .md, .titlebox .usertext .md")
    if desc_el:
        public_description = desc_el.get_text(strip=True)

    subscribers = 0
    sub_el = soup.select_one(".subscribers .number, .titlebox .subscribers .number")
    if sub_el:
        subscribers = _safe_int(sub_el.get_text(strip=True))

    return {
        "display_name": display_name,
        "title": title,
        "public_description": public_description,
        "description": public_description,
        "subscribers": subscribers,
    }


# ─── smoke entrypoint: ``python -m app.reddit_v2.redditapiv2_parser <url>`` ───
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m app.reddit_v2.redditapiv2_parser <file.html>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as fh:
        content = fh.read()
    posts = parse_post_listing(content)
    print(f"Parsed {len(posts)} posts")
    if posts:
        print(posts[0]["data"])
