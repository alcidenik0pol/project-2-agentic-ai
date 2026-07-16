# Parser unit tests for the reddit_v2 old.reddit.com HTML scraper.
# Runs fully offline against real saved HTML fixtures in app/tests/fixtures/.
# These lock in the parser's contract with the HTML structure Reddit actually
# serves, so a Reddit markup change is caught here rather than at runtime.
"""Offline unit tests for app.reddit_v2.redditapiv2_parser.

Run: ``pytest app/tests/test_redditapiv2_parser.py -v``
"""

from pathlib import Path

import pytest

from app.reddit_v2.redditapiv2_parser import (
    _iso_to_timestamp,
    _permalink_to_path,
    _safe_int,
    parse_comments_page,
    parse_post_listing,
    parse_subreddit_about,
)

FIXTURES = Path(__file__).parent / "fixtures"

REQUIRED_POST_KEYS = {
    "id",
    "title",
    "permalink",
    "ups",
    "num_comments",
    "upvote_ratio",
    "created_utc",
    "author",
    "selftext",
    "subreddit",
    "link_flair_text",
    "distinguished",
    "stickied",
}
REQUIRED_COMMENT_KEYS = {"id", "body", "ups", "author", "parent_id"}


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ─── helpers ────────────────────────────────────────────────────────────────

def test_safe_int_handles_suffixes_and_noise():
    assert _safe_int("1.2k") == 1200
    assert _safe_int("3m") == 3_000_000
    assert _safe_int("12,345") == 12345
    assert _safe_int("2 points") == 2
    assert _safe_int(None) == 0
    assert _safe_int("") == 0
    assert _safe_int("garbage") == 0


def test_iso_to_timestamp():
    assert _iso_to_timestamp("2026-07-04T16:05:06+00:00") == pytest.approx(1783181106.0)
    assert _iso_to_timestamp(None) == 0.0
    assert _iso_to_timestamp("not-a-date") == 0.0


def test_permalink_normalization():
    assert _permalink_to_path("https://old.reddit.com/r/Python/comments/1unctej/x/") == "/r/Python/comments/1unctej/x/"
    assert _permalink_to_path("/r/Python/comments/1unctej/x/") == "/r/Python/comments/1unctej/x/"
    assert _permalink_to_path(None) == ""


# ─── post listing ───────────────────────────────────────────────────────────

def test_parse_post_listing_returns_wrapped_t3():
    posts = parse_post_listing(_read("subreddit_listing.html"))
    assert len(posts) >= 5, "expected a non-empty listing"
    assert all(p["kind"] == "t3" for p in posts), "every post must be wrapped as kind=t3"


def test_parse_post_listing_has_required_keys():
    posts = parse_post_listing(_read("subreddit_listing.html"))
    for p in posts:
        data = p["data"]
        missing = REQUIRED_POST_KEYS - set(data.keys())
        assert not missing, f"post {data.get('id')} missing keys: {missing}"


def test_parse_post_listing_permalink_is_path():
    posts = parse_post_listing(_read("subreddit_listing.html"))
    for p in posts:
        permalink = p["data"]["permalink"]
        assert permalink.startswith("/"), f"permalink must be a path: {permalink!r}"
        assert "?" not in permalink and "#" not in permalink


def test_parse_post_listing_created_utc_positive():
    posts = parse_post_listing(_read("subreddit_listing.html"))
    for p in posts:
        assert p["data"]["created_utc"] > 0, "created_utc must be a real timestamp"


def test_parse_post_listing_upvote_ratio_is_none():
    """old.reddit HTML does not expose upvote_ratio; parser must return None."""
    posts = parse_post_listing(_read("subreddit_listing.html"))
    for p in posts:
        assert p["data"]["upvote_ratio"] is None


def test_parse_post_listing_ids_stripped():
    """Post ids must not carry the t3_ prefix."""
    posts = parse_post_listing(_read("subreddit_listing.html"))
    for p in posts:
        assert not p["data"]["id"].startswith("t3_"), p["data"]["id"]


# ─── comments page ──────────────────────────────────────────────────────────

def test_parse_comments_page_returns_post_and_comments():
    post_data, comments = parse_comments_page(_read("comments_page.html"))
    assert post_data.get("id"), "post id must be parsed from the comments page"
    assert len(comments) >= 1, "expected at least one top-level comment"
    assert all(c["kind"] == "t1" for c in comments), "every comment must be wrapped as kind=t1"


def test_parse_comments_page_has_required_keys():
    _, comments = parse_comments_page(_read("comments_page.html"))
    for c in comments:
        missing = REQUIRED_COMMENT_KEYS - set(c["data"].keys())
        assert not missing, f"comment missing keys: {missing}"


def test_parse_comments_page_filters_deleted():
    """Comments without a body (deleted/removed) must be dropped."""
    _, comments = parse_comments_page(_read("comments_page.html"))
    for c in comments:
        assert c["data"]["body"], "deleted comment with empty body was not filtered"


def test_parse_comments_page_parent_id_links_to_post():
    """Top-level comments' parent_id must reference the post (t3_{post_id})."""
    post_data, comments = parse_comments_page(_read("comments_page.html"))
    expected_parent = f"t3_{post_data['id']}"
    for c in comments:
        assert c["data"]["parent_id"] == expected_parent


def test_parse_comments_page_comment_ids_stripped():
    _, comments = parse_comments_page(_read("comments_page.html"))
    for c in comments:
        assert not c["data"]["id"].startswith("t1_"), c["data"]["id"]


def test_parse_comments_page_only_top_level():
    """Only direct children of the comment area are returned (matches v1 level=0)."""
    _, comments = parse_comments_page(_read("comments_page.html"))
    # Sanity: count of t1 things anywhere in the page should be >= top-level count.
    # We can't assert strict equality (nesting varies), but each returned id must
    # correspond to a top-level <div.thing> in the commentarea sitetable.
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_read("comments_page.html"), "lxml")
    top_ids = {
        t.get("data-fullname", "")[3:]
        for t in soup.select("div.commentarea div.sitetable > div.thing[data-fullname^='t1_']")
    }
    returned_ids = {c["data"]["id"] for c in comments}
    assert returned_ids == top_ids, "returned comments must exactly equal the top-level set"


# ─── about (graceful on missing data) ───────────────────────────────────────

def test_parse_subreddit_about_returns_dict_on_empty_html():
    """About is gated on old.reddit; parser must not crash on junk input."""
    result = parse_subreddit_about("<html><body>nothing here</body></html>")
    assert isinstance(result, dict)
    assert result.get("subscribers") == 0
