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
