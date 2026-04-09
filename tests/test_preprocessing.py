"""Unit tests for theme preprocessing."""

import pytest

from app.analyst.preprocessing import ThemePreprocessor


class TestNormalize:
    """Tests for ThemePreprocessor.normalize()."""

    def setup_method(self):
        self.preprocessor = ThemePreprocessor(case_normalize=True, dedup_threshold=0.95)

    def test_lowercase(self):
        assert self.preprocessor.normalize("Workplace Frustration") == "workplace frustration"

    def test_strip_whitespace(self):
        assert self.preprocessor.normalize("  workplace frustration  ") == "workplace frustration"

    def test_collapse_multiple_spaces(self):
        assert self.preprocessor.normalize("workplace   frustration") == "workplace frustration"

    def test_no_case_normalize(self):
        pp = ThemePreprocessor(case_normalize=False, dedup_threshold=0.95)
        assert pp.normalize("Workplace Frustration") == "Workplace Frustration"

    def test_empty_string(self):
        assert self.preprocessor.normalize("") == ""

    def test_only_whitespace(self):
        assert self.preprocessor.normalize("   ") == ""


class TestDeduplicateThemes:
    """Tests for ThemePreprocessor.deduplicate_themes()."""

    def setup_method(self):
        self.preprocessor = ThemePreprocessor(case_normalize=True, dedup_threshold=0.95)

    def test_exact_duplicates_merge_to_most_frequent(self):
        theme_to_count = {
            "workplace frustration": 10,
            "workplace frustraton": 2,  # typo, similar enough
        }
        mapping = self.preprocessor.deduplicate_themes(theme_to_count)
        assert mapping["workplace frustration"] == "workplace frustration"
        # The typo should map to the more frequent version
        assert mapping["workplace frustraton"] == "workplace frustration"

    def test_distinct_themes_stay_separate(self):
        theme_to_count = {
            "bad management": 5,
            "low salary": 8,
            "toxic culture": 3,
        }
        mapping = self.preprocessor.deduplicate_themes(theme_to_count)
        canonical = set(mapping.values())
        assert len(canonical) == 3

    def test_single_theme(self):
        theme_to_count = {"lonely theme": 5}
        mapping = self.preprocessor.deduplicate_themes(theme_to_count)
        assert mapping["lonely theme"] == "lonely theme"

    def test_empty_input(self):
        mapping = self.preprocessor.deduplicate_themes({})
        assert mapping == {}

    def test_case_variants_merge(self):
        """Case variants should merge. Dedup operates on already-normalized themes,
        so we feed pre-normalized (lowercased) variants that are near-duplicates."""
        theme_to_count = {
            "bad management": 10,
            "bad managment": 3,  # near-duplicate (typo)
        }
        mapping = self.preprocessor.deduplicate_themes(theme_to_count)
        assert mapping["bad management"] == "bad management"
        assert mapping["bad managment"] == "bad management"
