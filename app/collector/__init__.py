# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: LEGACY (Reddit API)
# Part of the original Reddit API data collection workflow.
# Used when: get_data_source() == "reddit_live"
# ═══════════════════════════════════════════════════════════════════════════
"""Data collection components for Reddit complaint analysis."""

from app.collector.fetcher import RedditFetcher

__all__ = ["RedditFetcher"]
