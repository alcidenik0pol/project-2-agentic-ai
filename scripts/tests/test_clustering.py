"""Unit tests for theme clustering pipeline."""

import numpy as np
import pytest

from app.analyst.clustering import ThemeClusterer
from app.analyst.models import ClusteringResult, ThemeCluster


class MockProvider:
    """Mock LLM provider for testing clustering without API calls."""

    def __init__(self, embedding_dim: int = 10):
        self.embedding_dim = embedding_dim
        self._call_count = 0
        self._max_retries = 3

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Return deterministic embeddings based on text hash."""
        self._call_count += 1
        embeddings = []
        for text in texts:
            # Create deterministic but different embeddings per unique text
            rng = np.random.RandomState(hash(text) % (2**31))
            emb = rng.randn(self.embedding_dim).astype(np.float32)
            embeddings.append(emb)
        return np.array(embeddings)

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str | None:
        """Return a dummy JSON for expansion prompts, plain text otherwise."""
        import json
        if "JSON object" in prompt or "JSON" in prompt:
            # Expansion prompt — parse the input themes and return them as keys
            try:
                # Find the JSON data in the prompt (last JSON block)
                start = prompt.rfind("{")
                end = prompt.rfind("}") + 1
                if start >= 0 and end > start:
                    input_data = json.loads(prompt[start:end])
                    return json.dumps(
                        {theme: f"Expanded: {theme} with detailed context"
                         for theme in input_data}
                    )
            except (json.JSONDecodeError, ValueError):
                pass
            return '{"theme": "Expanded description of the complaint"}'
        # Cluster naming prompt
        return "Test Cluster Name"


class MockClusterer(ThemeClusterer):
    """ThemeClusterer that uses MockProvider and overrides LLM naming."""

    def __init__(self, embedding_dim: int = 10, **kwargs):
        provider = MockProvider(embedding_dim=embedding_dim)
        super().__init__(provider=provider, **kwargs)

    def _call_llm_for_name(self, themes: list[str]) -> str | None:
        """Return a deterministic name from themes."""
        if themes:
            return themes[0].title() + " Cluster"
        return None


def _make_posts(themes: list[str]) -> list[dict]:
    """Create test posts with given theme classifications."""
    return [
        {
            "post": {"id": f"post_{i}", "upvotes": i * 10},
            "classification": {"theme": theme, "is_complaint": True, "intensity": "medium"},
        }
        for i, theme in enumerate(themes)
    ]


class TestExtractThemeData:
    """Tests for _extract_theme_data."""

    def test_basic_extraction(self):
        clusterer = MockClusterer()
        posts = _make_posts(["low salary", "bad management", "low salary"])
        theme_to_count, theme_to_posts = clusterer._extract_theme_data(posts)

        assert theme_to_count["low salary"] == 2
        assert theme_to_count["bad management"] == 1
        assert len(theme_to_posts["low salary"]) == 2

    def test_skips_unclassified_posts(self):
        clusterer = MockClusterer()
        posts = [
            {"post": {"id": "1"}, "classification": None},
            {"post": {"id": "2"}, "classification": {"theme": "pain", "is_complaint": True, "intensity": "low"}},
            {"post": {"id": "3"}},  # no classification key at all
        ]
        theme_to_count, _ = clusterer._extract_theme_data(posts)
        assert len(theme_to_count) == 1
        assert theme_to_count["pain"] == 1

    def test_skips_empty_themes(self):
        clusterer = MockClusterer()
        posts = [
            {"post": {"id": "1"}, "classification": {"theme": "  ", "is_complaint": True, "intensity": "low"}},
            {"post": {"id": "2"}, "classification": {"theme": "real theme", "is_complaint": True, "intensity": "low"}},
        ]
        theme_to_count, _ = clusterer._extract_theme_data(posts)
        assert len(theme_to_count) == 1


class TestPickOptimalK:
    """Tests for _pick_optimal_k."""

    def test_returns_min_k_when_silhouette_disabled(self):
        clusterer = MockClusterer(min_k=3, max_k=10, use_silhouette=False)
        embeddings = np.random.randn(50, 10).astype(np.float32)
        k = clusterer._pick_optimal_k(embeddings)
        assert k == 3

    def test_clamps_max_k_to_n_samples(self):
        clusterer = MockClusterer(min_k=3, max_k=20, use_silhouette=False)
        embeddings = np.random.randn(5, 10).astype(np.float32)
        k = clusterer._pick_optimal_k(embeddings)
        # max_k = min(20, 5-1) = 4, min_k = min(3, 4) = 3, silhouette off -> returns min_k = 3
        assert k == 3

    def test_returns_valid_k_with_silhouette(self):
        clusterer = MockClusterer(min_k=2, max_k=5, use_silhouette=True, embedding_dim=10)
        # Create 3 clear clusters
        c1 = np.random.randn(20, 10).astype(np.float32) + 5
        c2 = np.random.randn(20, 10).astype(np.float32) - 5
        c3 = np.random.randn(20, 10).astype(np.float32)
        embeddings = np.vstack([c1, c2, c3])
        k = clusterer._pick_optimal_k(embeddings)
        assert 2 <= k <= 5


class TestClusterPosts:
    """Integration tests for the full clustering pipeline."""

    def test_basic_clustering(self):
        clusterer = MockClusterer(min_k=2, max_k=5)
        posts = _make_posts([
            "low salary", "bad pay", "terrible wages",  # pay cluster
            "bad manager", "toxic boss", "horrible leadership",  # management cluster
        ])
        result = clusterer.cluster_posts(posts)

        assert isinstance(result, ClusteringResult)
        assert result.cluster_count >= 2
        assert result.cluster_count <= 5
        assert len(result.posts) == 6
        assert result.original_theme_count > 0
        assert result.canonical_theme_count > 0

    def test_each_post_gets_cluster_assignment(self):
        clusterer = MockClusterer(min_k=2, max_k=3)
        posts = _make_posts(["theme a", "theme b", "theme c", "theme d"])
        result = clusterer.cluster_posts(posts)

        for post in result.posts:
            assert "cluster" in post
            if post.get("classification"):
                assert post["cluster"] is not None
                assert "id" in post["cluster"]
                assert "name" in post["cluster"]

    def test_empty_posts(self):
        clusterer = MockClusterer()
        result = clusterer.cluster_posts([])
        assert result.cluster_count == 0
        assert result.posts == []

    def test_no_classified_posts(self):
        clusterer = MockClusterer()
        posts = [
            {"post": {"id": "1"}, "classification": None},
            {"post": {"id": "2"}, "classification_error": "Failed"},
        ]
        result = clusterer.cluster_posts(posts)
        assert result.cluster_count == 0

    def test_single_theme_posts(self):
        clusterer = MockClusterer()
        posts = _make_posts(["same theme", "same theme", "same theme"])
        result = clusterer.cluster_posts(posts)
        assert result.cluster_count == 1
        assert result.clusters[0].post_count == 3

    def test_upvotes_aggregated(self):
        clusterer = MockClusterer(min_k=1, max_k=2)
        posts = _make_posts(["theme a", "theme b"])
        result = clusterer.cluster_posts(posts)

        total_upvotes = sum(c.total_upvotes for c in result.clusters)
        expected = sum(p["post"]["upvotes"] for p in posts)
        assert total_upvotes == expected


class TestAssignClustersToPosts:
    """Tests for _assign_clusters_to_posts."""

    def test_unclassified_post_gets_null_cluster(self):
        clusterer = MockClusterer()
        posts = [{"post": {"id": "1"}, "classification": None}]
        result = clusterer._assign_clusters_to_posts(posts, {})
        assert result[0]["cluster"] is None

    def test_preserves_original_post_data(self):
        clusterer = MockClusterer()
        original = {"post": {"id": "1"}, "classification": {"theme": "test"}}
        theme_to_cluster = {"test": (0, "Test Cluster")}
        result = clusterer._assign_clusters_to_posts([original], theme_to_cluster)
        assert result[0]["post"]["id"] == "1"
        assert result[0]["classification"]["theme"] == "test"
        assert result[0]["cluster"]["name"] == "Test Cluster"


class TestExpansionIntegration:
    """Tests verifying expansion is used in the clustering pipeline."""

    def test_expanded_descriptions_are_embedded(self):
        """Verify that expanded descriptions (not short themes) are sent to get_embeddings."""
        clusterer = MockClusterer(min_k=2, max_k=3)
        posts = _make_posts([
            "low salary", "bad pay", "terrible wages",
            "bad manager", "toxic boss",
        ])
        # Add titles so expansion has context
        for i, post in enumerate(posts):
            post["post"]["title"] = f"Title about {post['classification']['theme']}"

        # Spy on what texts get embedded
        original_get_embeddings = clusterer.provider.get_embeddings
        embedded_texts = []

        def capture_embeddings(texts):
            embedded_texts.extend(texts)
            return original_get_embeddings(texts)

        clusterer.provider.get_embeddings = capture_embeddings

        result = clusterer.cluster_posts(posts)

        # All embedded texts should be expanded descriptions, not short themes
        for text in embedded_texts:
            assert len(text) > 5, f"Expected expanded description, got: '{text}'"
            # Expanded descriptions from mock start with "Expanded: "
            assert text.startswith("Expanded:"), f"Expected expanded text, got: '{text}'"

        assert result.cluster_count >= 2

    def test_fallback_still_produces_valid_clustering(self):
        """If expansion fails (generate_text returns None), clustering still works."""
        clusterer = MockClusterer(min_k=2, max_k=3)

        # Make generate_text return None to force fallback
        clusterer.provider.generate_text = lambda prompt, **kwargs: None

        posts = _make_posts([
            "low salary", "bad pay", "terrible wages",
            "bad manager", "toxic boss",
        ])
        for post in posts:
            post["post"]["title"] = f"Title about {post['classification']['theme']}"

        result = clusterer.cluster_posts(posts)

        # Should still produce a valid result with fallback expansions
        assert isinstance(result, ClusteringResult)
        assert result.cluster_count >= 2
        assert len(result.posts) == 5
