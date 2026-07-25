# ═══════════════════════════════════════════════════════════════════════════
# Unit tests for RedditAPIv3Client.search_subreddits_for_topic.
#
# Verifies that the sitewide /search/.rss endpoint is parsed correctly to
# extract unique source-subreddit names. The HTTP layer (_make_request) is
# mocked — these tests do NOT touch the network.
#
# Fixtures here are hand-built Atom XML that mirrors the structure Reddit
# actually serves (see app/reddit_v3/redditapiv3_parser.py for the contract).
# ═══════════════════════════════════════════════════════════════════════════
"""Offline unit tests for RedditAPIv3Client.search_subreddits_for_topic."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.reddit_v3.redditapiv3_client import RedditAPIv3Client


class _StubResponse:
    """Minimal stand-in for requests.Response used by the client."""

    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _entry(
    post_id: str,
    title: str,
    subreddit: str,
    permalink: str = "",
) -> str:
    """Build one Atom <entry> matching what Reddit's search.rss serves."""
    if not permalink:
        permalink = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/x/"
    return f"""
    <entry>
      <id>{post_id}</id>
      <title>{title}</title>
      <link href="{permalink}"/>
      <author><name>/u/testuser</name></author>
      <category term="{subreddit}"/>
      <published>2026-07-23T18:02:25+00:00</published>
      <content type="html">body</content>
    </entry>
    """


def _feed(entries: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        f"{entries}"
        "</feed>"
    )


# ─── happy path ─────────────────────────────────────────────────────────────


def test_extracts_unique_subs_in_first_seen_order():
    """Two posts from MouseReview, one from MechanicalKeyboards, one from gaming.

    Even though MouseReview appears twice, the result must dedupe and preserve
    first-seen order: [MouseReview, MechanicalKeyboards, gaming].
    """
    xml = _feed(
        _entry("t3_aaa111", "Best gaming mouse for FPS", "MouseReview")
        + _entry("t3_bbb222", "Mouse with broken scroll wheel", "MouseReview")
        + _entry("t3_ccc333", "Keyboard chat-key issue", "MechanicalKeyboards")
        + _entry("t3_ddd444", "My gaming setup", "gaming")
    )
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(xml)) as mock_req:
        subs = client.search_subreddits_for_topic("gaming mouse")

    assert subs == ["MouseReview", "MechanicalKeyboards", "gaming"]
    # Sanity: the request was the right method + URL shape. quote_plus encodes
    # space as '+', so we accept either '+' or '%20' in the q= parameter.
    method, url = mock_req.call_args[0][0], mock_req.call_args[0][1]
    assert method == "GET"
    assert "/search/.rss" in url
    assert "q=gaming+mouse" in url or "q=gaming%20mouse" in url
    assert "sort=relevance" in url


def test_query_with_special_chars_is_url_encoded():
    """Ampersand in the query must be percent-encoded so it doesn't terminate
    the q= parameter early.
    """
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(_feed(""))) as mock_req:
        client.search_subreddits_for_topic("cats & dogs")
    url = mock_req.call_args[0][1]
    # quote_plus encodes both space and ampersand (%26 = '&')
    assert "q=cats+%26+dogs" in url or "q=cats%20%26%20dogs" in url


# ─── edge cases ─────────────────────────────────────────────────────────────


def test_empty_feed_returns_empty_list():
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(_feed(""))):
        subs = client.search_subreddits_for_topic("nonexistent-topic-xyz")
    assert subs == []


def test_entries_without_subreddit_are_skipped():
    """If <category> is missing (rare but seen on some Reddit markup), the
    entry must not contribute an empty string to the result.
    """
    entry_no_category = """
    <entry>
      <id>t3_eee555</id>
      <title>Post with no category</title>
      <link href="https://www.reddit.com/r/X/comments/eee555/x/"/>
      <author><name>/u/x</name></author>
      <published>2026-07-23T18:02:25+00:00</published>
      <content type="html">x</content>
    </entry>
    """
    xml = _feed(
        entry_no_category
        + _entry("t3_fff666", "Real post", "MouseReview")
    )
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(xml)):
        subs = client.search_subreddits_for_topic("x")
    assert subs == ["MouseReview"]


def test_http_error_propagates_to_caller():
    """A non-2xx response must raise — the fetcher relies on this to fall back."""
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse("", status=429)):
        with pytest.raises(Exception):
            client.search_subreddits_for_topic("x")


# ─── search_posts_in_subreddit (in-sub topic-filtered search) ────────────────


def test_search_posts_in_subreddit_builds_correct_url():
    """URL must be /r/X/search.rss with restrict_sr=1, sort=relevance, and the
    query URL-encoded. These are the params that the local probe + prod logs
    confirmed return topic-filtered results.
    """
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(_feed(""))) as mock_req:
        client.search_posts_in_subreddit("MouseReview", "gaming mouse", limit=25)
    method, url = mock_req.call_args[0][0], mock_req.call_args[0][1]
    assert method == "GET"
    assert "/r/MouseReview/search.rss" in url
    assert "restrict_sr=1" in url, "restrict_sr=1 is what scopes results to the subreddit"
    assert "sort=relevance" in url
    assert "limit=25" in url
    assert "q=gaming+mouse" in url or "q=gaming%20mouse" in url


def test_search_posts_in_subreddit_returns_parsed_posts():
    """Posts come back via the same parse_post_listing path as /hot.rss; the
    in-sub search XML shape is identical to the listing XML shape.
    """
    xml = _feed(
        _entry("t3_aaa111", "Need a new gaming mouse! What are you gamers using?", "MouseReview")
        + _entry("t3_bbb222", "Fell into the gaming mouse rabbit hole", "MouseReview")
    )
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(xml)):
        posts = client.search_posts_in_subreddit("MouseReview", "gaming mouse")
    assert len(posts) == 2
    assert all(p["kind"] == "t3" for p in posts)
    assert all(p["data"]["subreddit"] == "MouseReview" for p in posts)


def test_search_posts_in_subreddit_query_with_special_chars_is_url_encoded():
    """A query containing '&' must be percent-encoded so it doesn't terminate
    the q= parameter early.
    """
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(_feed(""))) as mock_req:
        client.search_posts_in_subreddit("MouseReview", "cats & dogs")
    url = mock_req.call_args[0][1]
    assert "q=cats+%26+dogs" in url or "q=cats%20%26%20dogs" in url


def test_search_posts_in_subreddit_respects_limit():
    """Limit must be passed through to the URL — Reddit caps at the requested
    number of entries.
    """
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse(_feed(""))) as mock_req:
        client.search_posts_in_subreddit("MouseReview", "x", limit=10)
    assert "limit=10" in mock_req.call_args[0][1]


def test_search_posts_in_subreddit_http_error_propagates():
    """Fetcher relies on raise_for_status to surface 429s so they hit the
    per-sub try/except and the run continues with other subs.
    """
    client = RedditAPIv3Client()
    with patch.object(client, "_make_request", return_value=_StubResponse("", status=429)):
        with pytest.raises(Exception):
            client.search_posts_in_subreddit("MouseReview", "gaming mouse")
