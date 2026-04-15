"""Unit tests for theme expansion logic."""

import json
from unittest.mock import MagicMock

import pytest

from app.analyst.expansion import ThemeExpander
from app.analyst.models import BatchExpansionResult, ThemeExpansion


def _make_posts_with_titles(titles_and_upvotes: list[tuple[str, int]]) -> list[dict]:
    """Create test posts with titles and upvotes."""
    return [
        {
            "post": {"id": f"post_{i}", "title": title, "upvotes": upvotes},
            "classification": {"theme": f"theme_{i}", "is_complaint": True, "intensity": "medium"},
        }
        for i, (title, upvotes) in enumerate(titles_and_upvotes)
    ]


class MockExpansionProvider:
    """Mock provider that returns configurable JSON for expansion calls."""

    def __init__(self, response: dict[str, str] | None = None):
        self._response = response
        self._max_retries = 3
        self.calls: list[str] = []

    def generate_text(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024) -> str | None:
        self.calls.append(prompt)
        if self._response is not None:
            return json.dumps(self._response)
        return None


class TestBuildContextMap:
    """Tests for _build_context_map — selects top posts by upvotes."""

    def test_selects_top_3_by_upvotes(self):
        provider = MockExpansionProvider()
        expander = ThemeExpander(provider=provider, max_context_titles=3)

        posts = _make_posts_with_titles([
            ("Low effort post", 5),
            ("Medium post", 50),
            ("Popular post", 500),
            ("Very popular post", 1000),
            ("Another post", 100),
        ])

        theme_to_posts = {"test_theme": [0, 1, 2, 3, 4]}
        context_map = expander._build_context_map(["test_theme"], theme_to_posts, posts)

        titles = [t for _, t, _ in context_map["test_theme"]]
        assert titles == ["Very popular post", "Popular post", "Another post"]

    def test_handles_empty_posts(self):
        provider = MockExpansionProvider()
        expander = ThemeExpander(provider=provider, max_context_titles=3)

        context_map = expander._build_context_map(["theme"], {}, [])
        assert context_map["theme"] == []

    def test_handles_posts_without_titles(self):
        provider = MockExpansionProvider()
        expander = ThemeExpander(provider=provider, max_context_titles=3)

        posts = [{"post": {"id": "1", "upvotes": 100}}]  # no title
        context_map = expander._build_context_map(["theme"], {"theme": [0]}, posts)
        assert context_map["theme"] == []


class TestLLMExpansion:
    """Tests for LLM-based expansion."""

    def test_successful_expansion(self):
        response = {
            "workplace frustration": "Frustration with toxic workplace and unreasonable demands",
            "low salary": "Complaints about inadequate compensation and unfair pay",
        }
        provider = MockExpansionProvider(response=response)
        expander = ThemeExpander(provider=provider)

        themes = ["workplace frustration", "low salary"]
        theme_to_posts = {"workplace frustration": [0], "low salary": [1]}
        posts = _make_posts_with_titles([
            ("Boss is terrible", 10),
            ("Pay is too low", 20),
        ])

        result = expander.expand_themes(themes, theme_to_posts, posts)

        assert isinstance(result, BatchExpansionResult)
        assert len(result.expansions) == 2
        assert result.expansions["workplace frustration"].expansion_method == "llm"
        assert result.expansions["low salary"].expansion_method == "llm"
        assert result.api_calls_made == 1
        assert result.themes_failed == []

    def test_partial_llm_failure_uses_fallback(self):
        """LLM returns only one of two themes — the missing one gets fallback."""
        response = {
            "workplace frustration": "Frustration with toxic workplace",
            # "low salary" is missing from LLM response
        }
        provider = MockExpansionProvider(response=response)
        expander = ThemeExpander(provider=provider)

        themes = ["workplace frustration", "low salary"]
        theme_to_posts = {"workplace frustration": [0], "low salary": [1]}
        posts = _make_posts_with_titles([
            ("Boss is terrible", 10),
            ("Pay is too low", 20),
        ])

        result = expander.expand_themes(themes, theme_to_posts, posts)

        assert result.expansions["workplace frustration"].expansion_method == "llm"
        assert result.expansions["low salary"].expansion_method != "llm"
        assert "low salary" in result.themes_failed


class TestFallbackExpansion:
    """Tests for fallback when LLM fails."""

    def test_fallback_with_titles(self):
        provider = MockExpansionProvider(response=None)  # returns None
        expander = ThemeExpander(provider=provider, use_cache=False)

        themes = ["bad pay"]
        theme_to_posts = {"bad pay": [0]}
        posts = _make_posts_with_titles([("Salary is too low", 10)])

        result = expander.expand_themes(themes, theme_to_posts, posts)

        expansion = result.expansions["bad pay"]
        assert expansion.expansion_method == "fallback_simple"
        assert "Bad pay" in expansion.expanded_description
        assert "bad pay" in result.themes_failed

    def test_fallback_without_titles(self):
        provider = MockExpansionProvider(response=None)
        expander = ThemeExpander(provider=provider, use_cache=False)

        result = expander.expand_themes(["lonely"], {"lonely": []}, [])

        expansion = result.expansions["lonely"]
        assert expansion.expansion_method == "fallback_original"
        assert "lonely" in expansion.expanded_description.lower()


class TestCaching:
    """Tests for expansion caching."""

    def test_cache_hit_on_duplicate_theme(self):
        response = {"pain point": "Expanded description for pain point"}
        provider = MockExpansionProvider(response=response)
        expander = ThemeExpander(provider=provider, use_cache=True)

        themes = ["pain point"]
        theme_to_posts = {"pain point": [0]}
        posts = _make_posts_with_titles([("Some title", 10)])

        # First call
        result1 = expander.expand_themes(themes, theme_to_posts, posts)
        assert result1.api_calls_made == 1
        assert result1.cache_hits == 0

        # Second call — should hit cache
        result2 = expander.expand_themes(themes, theme_to_posts, posts)
        assert result2.cache_hits == 1
        assert result2.api_calls_made == 0

    def test_cache_disabled(self):
        response = {"pain point": "Expanded description"}
        provider = MockExpansionProvider(response=response)
        expander = ThemeExpander(provider=provider, use_cache=False)

        themes = ["pain point"]
        theme_to_posts = {"pain point": [0]}
        posts = _make_posts_with_titles([("Some title", 10)])

        result1 = expander.expand_themes(themes, theme_to_posts, posts)
        result2 = expander.expand_themes(themes, theme_to_posts, posts)

        # Both calls should go to LLM
        assert result1.api_calls_made == 1
        assert result2.api_calls_made == 1
        assert result2.cache_hits == 0


class TestBatchProcessing:
    """Tests for batch size behavior."""

    def test_batch_size_limits_calls(self):
        themes = [f"theme_{i}" for i in range(25)]
        response = {t: f"Expanded: {t}" for t in themes}
        provider = MockExpansionProvider(response=response)
        expander = ThemeExpander(provider=provider, batch_size=10, use_cache=False)

        theme_to_posts = {t: [i] for i, t in enumerate(themes)}
        posts = [
            {"post": {"id": f"p_{i}", "title": f"Title {i}", "upvotes": i * 10},
             "classification": {"theme": t, "is_complaint": True, "intensity": "low"}}
            for i, t in enumerate(themes)
        ]

        result = expander.expand_themes(themes, theme_to_posts, posts)

        # 25 themes / 10 per batch = 3 calls
        assert result.api_calls_made == 3
        assert len(result.expansions) == 25
