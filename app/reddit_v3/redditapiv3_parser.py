# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: REDDIT V3 (www.reddit.com Atom RSS feeds)
# Pure functions (no HTTP) — unit-testable in isolation.
# ═══════════════════════════════════════════════════════════════════════════
"""Pure Atom/XML parsers for Reddit's public RSS feeds.

Reddit killed all unauthenticated access to ``.json`` and ``old.reddit.com``
in July 2026 (302 login wall + 403 WAF). The only unauthenticated public
surface left is the Atom feed: ``https://www.reddit.com/r/X/{sort}.rss`` and
``https://www.reddit.com/comments/{post_id}/.rss``.

These functions return dicts shaped exactly like the v2 HTML scraper's output
(wrapped in ``{"kind": "t3"|"t1", "data": {...}}``) so
:mod:`app.reddit_v3.redditapiv3_fetcher` (a structural copy of the v2 fetcher)
can consume them unchanged.

What RSS gives us vs. v2 HTML scrape:
- ✅ id, title, author, permalink, published (created_utc), subreddit, selftext
- ❌ ups, num_comments, upvote_ratio, link_flair_text, distinguished, stickied
      (These are set to None/0/False; the v3 fetcher drops the upvote-gated
      comment-fetching threshold accordingly.)

No network access here — all HTTP is handled by the client module.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Reddit wraps self-text in <!-- SC_OFF -->...<!-- SC_ON --> markers.
# Link posts have no SC markers — their <content> is just a thumbnail table.
_SC_PATTERN = re.compile(r"<!-- SC_OFF -->(.*?)<!-- SC_ON -->", re.DOTALL)


def _iso_to_timestamp(iso_str: str | None) -> float:
    """Convert an ISO-8601 datetime (e.g. ``2026-07-23T18:02:25+00:00``) to epoch seconds.

    Returns 0.0 on failure.
    """
    if not iso_str:
        return 0.0
    try:
        # Python 3.11+ fromisoformat handles the trailing +00:00 offset.
        return datetime.fromisoformat(iso_str).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _permalink_to_path(href: str | None) -> str:
    """Normalize a Reddit URL to a path starting with ``/``."""
    if not href:
        return ""
    path = href.strip()
    m = re.match(r"^https?://[^/]+(/.*)$", path)
    if m:
        path = m.group(1)
    if not path.startswith("/"):
        path = "/" + path
    return path.split("?", 1)[0].split("#", 1)[0]


def _strip_author(raw: str | None) -> str | None:
    """``/u/username`` → ``username``. Returns None for deleted/missing."""
    if not raw:
        return None
    name = raw.replace("/u/", "").strip()
    if not name or name == "[deleted]":
        return None
    return name


def _extract_selftext(content_html_escaped: str) -> str | None:
    """Extract plain-text selftext from an Atom <content type="html"> payload.

    Returns None for link posts (no SC markers) or empty selftext.
    """
    if not content_html_escaped:
        return None
    # Atom XML already un-escapes the outer XML entity layer when we read text
    # content via BeautifulSoup. What remains is HTML with HTML entities.
    decoded = html.unescape(content_html_escaped)
    m = _SC_PATTERN.search(decoded)
    inner = m.group(1) if m else None
    if not inner:
        return None  # link post — content is just thumbnail metadata
    return BeautifulSoup(inner, "lxml").get_text(" ", strip=True) or None


def parse_post_listing(xml: str) -> list[dict]:
    """Parse a Reddit listing Atom feed (``/r/X/{sort}.rss`` or ``/search.rss``).

    Returns a list of post wrappers ``[{"kind": "t3", "data": {...}}, ...]``.
    Non-``t3_`` entries (e.g. comments leaking into the feed) are skipped.
    """
    soup = BeautifulSoup(xml, "xml")
    entries = soup.find_all("entry")
    results: list[dict] = []

    for entry in entries:
        post = _parse_post_entry(entry)
        if post:
            results.append({"kind": "t3", "data": post})

    return results


def _parse_post_entry(entry) -> dict | None:
    """Extract a post dict from a single Atom ``<entry>``.

    Returns None if the entry is not a post (``t3_``) — e.g. comment entries
    in a comments feed.
    """
    id_el = entry.find("id")
    full_id = id_el.get_text(strip=True) if id_el else ""
    if not full_id.startswith("t3_"):
        return None

    title_el = entry.find("title")
    title = title_el.get_text(strip=True) if title_el else ""

    author_el = entry.find("author")
    author = _strip_author(
        author_el.find("name").get_text(strip=True)
        if author_el and author_el.find("name")
        else None
    )

    link_el = entry.find("link")
    href = link_el.get("href") if link_el else ""
    permalink = _permalink_to_path(href)

    published_el = entry.find("published")
    created_utc = _iso_to_timestamp(
        published_el.get_text(strip=True) if published_el else None
    )

    content_el = entry.find("content")
    selftext = (
        _extract_selftext(content_el.get_text(strip=True)) if content_el else None
    )

    # First <category> on a listing entry is the subreddit.
    subreddit = ""
    cat_el = entry.find("category")
    if cat_el and cat_el.get("term"):
        subreddit = cat_el["term"]

    return {
        "id": full_id[3:],  # strip t3_
        "title": title,
        "permalink": permalink,
        "ups": 0,                 # not in RSS
        "num_comments": 0,        # not in RSS (populated indirectly via comment fetch)
        "upvote_ratio": None,     # not in RSS
        "created_utc": created_utc,
        "author": author,
        "selftext": selftext,
        "subreddit": subreddit,
        "link_flair_text": None,  # not in RSS
        "distinguished": None,    # not in RSS — fetcher won't filter on this
        "stickied": False,        # not in RSS — see AutoModerator-skip in fetcher
    }


def parse_comments_page(xml: str) -> tuple[dict, list[dict]]:
    """Parse a Reddit comments Atom feed (``/comments/{post_id}/.rss``).

    Returns ``(post_data, comments_list)`` where:
    - ``post_data`` is the parent post dict (or ``{}`` if missing)
    - ``comments_list`` contains top-level comment wrappers
      ``{"kind": "t1", "data": {...}}``

    The feed lists the post itself as the first entry (``t3_``) followed by
    top-level comments (``t1_``). Reddit's RSS doesn't expose nesting —
    every comment in the feed is treated as level 0, matching v2's behaviour.
    """
    soup = BeautifulSoup(xml, "xml")
    entries = soup.find_all("entry")

    post_data: dict = {}
    comments: list[dict] = []

    for entry in entries:
        id_el = entry.find("id")
        full_id = id_el.get_text(strip=True) if id_el else ""

        if full_id.startswith("t3_"):
            parsed = _parse_post_entry(entry)
            if parsed:
                post_data = parsed
        elif full_id.startswith("t1_"):
            comment = _parse_comment_entry(entry, post_data.get("id", ""))
            if comment:
                comments.append({"kind": "t1", "data": comment})

    return post_data, comments


def _parse_comment_entry(entry, post_id: str = "") -> dict | None:
    """Extract a single comment dict. Returns None for deleted/empty bodies."""
    id_el = entry.find("id")
    full_id = id_el.get_text(strip=True) if id_el else ""
    if not full_id.startswith("t1_"):
        return None

    content_el = entry.find("content")
    body: str = ""
    if content_el:
        decoded = html.unescape(content_el.get_text(strip=True))
        m = _SC_PATTERN.search(decoded)
        inner = m.group(1) if m else decoded
        body = BeautifulSoup(inner, "lxml").get_text(" ", strip=True)

    if not body or body in ("[deleted]", "[removed]"):
        return None

    author_el = entry.find("author")
    author = _strip_author(
        author_el.find("name").get_text(strip=True)
        if author_el and author_el.find("name")
        else None
    )

    # Derive parent_id from the comment permalink:
    # https://www.reddit.com/r/X/comments/{post_id}/.../{comment_id}/
    parent_id = f"t3_{post_id}" if post_id else None
    link_el = entry.find("link")
    if link_el and link_el.get("href"):
        m = re.search(r"/comments/(\w+)/", urlparse(link_el["href"]).path)
        if m:
            parent_id = f"t3_{m.group(1)}"

    return {
        "id": full_id[3:],  # strip t1_
        "body": body,
        "ups": 0,           # not in RSS
        "author": author,
        "parent_id": parent_id,
    }


# ─── smoke entrypoint: ``python -m app.reddit_v3.redditapiv3_parser <file.xml>`` ───
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m app.reddit_v3.redditapiv2_parser <file.xml>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as fh:
        content = fh.read()
    posts = parse_post_listing(content)
    print(f"Parsed {len(posts)} posts")
    if posts:
        print(posts[0]["data"])
