"""Theme clustering pipeline: extract, embed, cluster, name, and assign."""

import logging
import time
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from app.analyst.cluster_prompts import CLUSTER_NAMING_PROMPT
from app.analyst.models import BatchExpansionResult, ClusteringResult, ThemeCluster, ThemeExpansion
from app.analyst.preprocessing import ThemePreprocessor
from app.analyst.providers.base import LLMProvider
from app.config import config

logger = logging.getLogger(__name__)


class ThemeClusterer:
    """Orchestrate the full theme clustering pipeline."""

    def __init__(
        self,
        provider: LLMProvider,
        min_k: int | None = None,
        max_k: int | None = None,
        use_silhouette: bool | None = None,
    ):
        self.provider = provider
        self.min_k = min_k if min_k is not None else config.clustering_min_k
        self.max_k = max_k if max_k is not None else config.clustering_max_k
        self.use_silhouette = (
            use_silhouette
            if use_silhouette is not None
            else config.clustering_use_silhouette
        )
        self.preprocessor = ThemePreprocessor()

    def cluster_posts(self, posts: list[dict[str, Any]]) -> ClusteringResult:
        """Run the full clustering pipeline on classified posts.

        Args:
            posts: List of post dicts, each with a "classification" key
                   containing {"theme": str, ...}.

        Returns:
            ClusteringResult with clusters and posts annotated with cluster info.
        """
        start = time.time()
        substeps: dict[str, float] = {}  # Track substep timing

        # 1. Extract themes
        theme_to_count, theme_to_posts = self._extract_theme_data(posts)
        if not theme_to_count:
            logger.warning("No classified themes found; returning empty result")
            return ClusteringResult(
                posts=posts,
                provider_used=self.provider.provider_name,
                embedding_model=config.clustering_embedding_model,
            )

        # 2. Normalize and deduplicate
        canonical_map = self._canonicalize_themes(theme_to_count, theme_to_posts)
        canonical_themes = sorted(set(canonical_map.values()))
        original_count = len(theme_to_count)
        canonical_count = len(canonical_themes)

        logger.info(
            f"Themes: {original_count} original -> {canonical_count} canonical"
        )

        # Handle edge case: too few themes for clustering
        if canonical_count == 1:
            return self._single_cluster_result(
                posts, canonical_themes, original_count, canonical_count, start
            )

        # 3. Expand themes for better embedding semantics
        logger.info("Starting theme expansion step...")
        t0 = time.time()
        expanded_descriptions = self._expand_themes_for_embeddings(
            canonical_themes, theme_to_posts, posts
        )
        substeps["theme_expansion"] = round(time.time() - t0, 2)
        substeps["theme_expansion_llm"] = round(expanded_descriptions.llm_time_seconds, 2)
        logger.info(
            f"Theme expansion: {len(expanded_descriptions.expansions)} descriptions "
            f"({expanded_descriptions.api_calls_made} API calls, "
            f"{expanded_descriptions.cache_hits} cache hits)"
        )

        # 4. Embed EXPANDED descriptions (not original themes)
        texts_to_embed = [
            expanded_descriptions.expansions[t].expanded_description
            for t in canonical_themes
        ]
        t0 = time.time()
        embeddings = self.provider.get_embeddings(texts_to_embed)
        substeps["embedding_generation"] = round(time.time() - t0, 2)
        logger.info(f"Embeddings shape: {embeddings.shape}")

        # 5. Pick optimal k and cluster
        t0 = time.time()
        k = self._pick_optimal_k(embeddings)
        logger.info(f"Optimal k: {k}")
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(
            embeddings
        )
        substeps["kmeans_clustering"] = round(time.time() - t0, 2)

        # 5. Name each cluster via LLM
        cluster_themes = self._group_by_cluster(canonical_themes, labels, k)
        t0 = time.time()
        cluster_names = self._name_clusters(cluster_themes)
        substeps["cluster_naming"] = round(time.time() - t0, 2)

        # 6. Build cluster metadata
        clusters = self._build_clusters(
            cluster_themes, cluster_names, canonical_map, theme_to_posts, posts
        )

        # 7. Assign cluster info to each post
        theme_to_cluster = self._build_theme_to_cluster_map(
            canonical_map, clusters
        )
        annotated_posts = self._assign_clusters_to_posts(posts, theme_to_cluster)

        elapsed = time.time() - start
        result = ClusteringResult(
            clusters=clusters,
            posts=annotated_posts,
            original_theme_count=original_count,
            canonical_theme_count=canonical_count,
            cluster_count=len(clusters),
            processing_time_seconds=round(elapsed, 2),
            provider_used=self.provider.provider_name,
            embedding_model=config.clustering_embedding_model,
            substep_timing=substeps,
        )
        logger.info(
            f"Clustering complete: {result.cluster_count} clusters in {elapsed:.1f}s "
            f"(expansion={substeps.get('theme_expansion', 0):.1f}s, "
            f"embeddings={substeps.get('embedding_generation', 0):.1f}s, "
            f"kmeans={substeps.get('kmeans_clustering', 0):.1f}s, "
            f"naming={substeps.get('cluster_naming', 0):.1f}s)"
        )
        return result

    def _extract_theme_data(
        self, posts: list[dict[str, Any]]
    ) -> tuple[dict[str, int], dict[str, list[int]]]:
        """Extract unique themes with counts and post indices.

        Returns:
            (theme_to_count, theme_to_post_indices)
        """
        theme_to_count: dict[str, int] = {}
        theme_to_posts: dict[str, list[int]] = {}

        for i, post in enumerate(posts):
            classification = post.get("classification")
            if not classification or not isinstance(classification, dict):
                continue
            if not classification.get("is_complaint", True):
                continue
            theme = classification.get("theme", "").strip()
            if not theme:
                continue
            normalized = self.preprocessor.normalize(theme)
            if not normalized:
                continue
            theme_to_count[normalized] = theme_to_count.get(normalized, 0) + 1
            theme_to_posts.setdefault(normalized, []).append(i)

        return theme_to_count, theme_to_posts

    def _canonicalize_themes(
        self,
        theme_to_count: dict[str, int],
        theme_to_posts: dict[str, list[int]],
    ) -> dict[str, str]:
        """Run deduplication and update post indices.

        Returns:
            mapping of every original theme -> canonical theme
        """
        dedup_map = self.preprocessor.deduplicate_themes(theme_to_count)

        # Merge post indices for merged themes
        merged_to_posts: dict[str, list[int]] = {}
        for original, canonical in dedup_map.items():
            merged_to_posts.setdefault(canonical, []).extend(
                theme_to_posts.get(original, [])
            )
        # Update theme_to_posts in place (caller can use merged version)
        for canonical, indices in merged_to_posts.items():
            theme_to_posts[canonical] = indices

        return dedup_map

    def _expand_themes_for_embeddings(
        self,
        canonical_themes: list[str],
        theme_to_posts: dict[str, list[int]],
        posts: list[dict[str, Any]],
    ) -> BatchExpansionResult:
        """Expand theme labels using LLM for better embedding semantics."""
        from app.analyst.expansion import ThemeExpander

        expander = ThemeExpander(
            provider=self.provider,
            batch_size=config.expansion_batch_size,
            max_context_titles=config.expansion_max_context_titles,
            use_cache=config.expansion_use_cache,
        )

        result = expander.expand_themes(canonical_themes, theme_to_posts, posts)

        if result.themes_failed:
            logger.warning(
                f"{len(result.themes_failed)} themes fell back to simple/original: "
                f"{result.themes_failed[:5]}..."
            )

        return result

    def _pick_optimal_k(self, embeddings: np.ndarray) -> int:
        """Pick optimal k using silhouette score, or fall back to min_k."""
        n_samples = embeddings.shape[0]
        max_k = min(self.max_k, n_samples - 1)
        min_k = min(self.min_k, max_k)

        if min_k < 2:
            return max(min_k, 2)

        if not self.use_silhouette or min_k == max_k:
            return min_k

        best_k = min_k
        best_score = -1.0

        for k in range(min_k, max_k + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(embeddings)
            score = silhouette_score(embeddings, labels)
            logger.debug(f"k={k}, silhouette={score:.4f}")
            if score > best_score:
                best_score = score
                best_k = k

        return best_k

    def _group_by_cluster(
        self, themes: list[str], labels: np.ndarray, k: int
    ) -> dict[int, list[str]]:
        """Group themes by their cluster label."""
        groups: dict[int, list[str]] = {i: [] for i in range(k)}
        for theme, label in zip(themes, labels):
            groups[int(label)].append(theme)
        return groups

    def _name_clusters(
        self, cluster_themes: dict[int, list[str]]
    ) -> dict[int, str]:
        """Use LLM to name each cluster. Fallback to first theme on failure."""
        names: dict[int, str] = {}
        for cid, themes in cluster_themes.items():
            try:
                name = self._call_llm_for_name(themes)
                if name:
                    names[cid] = name
                else:
                    names[cid] = themes[0] if themes else f"Cluster {cid}"
            except Exception as e:
                logger.warning(f"LLM naming failed for cluster {cid}: {e}")
                names[cid] = themes[0] if themes else f"Cluster {cid}"
        return names

    def _call_llm_for_name(self, themes: list[str]) -> str | None:
        """Make a single LLM call to name a cluster, with validation and retry."""
        prompt = CLUSTER_NAMING_PROMPT.format(
            themes="\n".join(f"- {t}" for t in themes)
        )

        for attempt in range(2):
            try:
                raw = self.provider.generate_text(prompt, temperature=0.3, max_tokens=256, use_fast=True)
                if not raw:
                    return None
                name = raw.strip()

                # Validate: reject truncated or too-short names
                if name.endswith("&") or name.endswith(",") or len(name) < 5:
                    if attempt == 0:
                        logger.warning(f"Cluster name truncated/short: '{name}', retrying")
                        # Strengthen prompt for retry
                        prompt = (
                            prompt
                            + "\n\nYour previous attempt was truncated. "
                            "Write a COMPLETE name that is 3-5 words long, ending with a real word."
                        )
                        continue
                    else:
                        logger.warning(f"Cluster name still bad after retry: '{name}', using first theme")
                        return themes[0] if themes else name

                return name
            except Exception as e:
                logger.warning(f"LLM naming failed (attempt {attempt + 1}): {e}")
                if attempt == 1:
                    return None
        return None

    def _build_clusters(
        self,
        cluster_themes: dict[int, list[str]],
        cluster_names: dict[int, str],
        canonical_map: dict[str, str],
        theme_to_posts: dict[str, list[int]],
        posts: list[dict[str, Any]],
    ) -> list[ThemeCluster]:
        """Build ThemeCluster objects with post counts and upvote totals."""
        clusters = []
        for cid in sorted(cluster_themes.keys()):
            themes = cluster_themes[cid]
            # Collect all post indices for themes in this cluster
            cluster_themes_set = set(themes)
            post_indices: list[int] = []
            for original, canonical in canonical_map.items():
                if canonical in cluster_themes_set:
                    post_indices.extend(theme_to_posts.get(original, []))

            total_upvotes = sum(
                posts[idx].get("post", {}).get("upvotes", 0)
                for idx in post_indices
                if idx < len(posts)
            )

            clusters.append(
                ThemeCluster(
                    cluster_id=cid,
                    name=cluster_names.get(cid, f"Cluster {cid}"),
                    themes=themes,
                    post_count=len(post_indices),
                    total_upvotes=total_upvotes,
                )
            )
        return clusters

    def _build_theme_to_cluster_map(
        self,
        canonical_map: dict[str, str],
        clusters: list[ThemeCluster],
    ) -> dict[str, tuple[int, str]]:
        """Map every original theme to (cluster_id, cluster_name).

        Returns:
            {original_theme: (cluster_id, cluster_name)}
        """
        # Build canonical theme -> cluster lookup
        canonical_to_cluster: dict[str, tuple[int, str]] = {}
        for cluster in clusters:
            for theme in cluster.themes:
                canonical_to_cluster[theme] = (cluster.cluster_id, cluster.name)

        # Map every original theme through canonical -> cluster
        result: dict[str, tuple[int, str]] = {}
        for original, canonical in canonical_map.items():
            if canonical in canonical_to_cluster:
                result[original] = canonical_to_cluster[canonical]
        return result

    def _assign_clusters_to_posts(
        self,
        posts: list[dict[str, Any]],
        theme_to_cluster: dict[str, tuple[int, str]],
    ) -> list[dict[str, Any]]:
        """Add cluster info to each post dict."""
        annotated = []
        for post in posts:
            p = dict(post)  # shallow copy
            classification = p.get("classification")
            if classification and isinstance(classification, dict):
                theme = classification.get("theme", "").strip()
                normalized = self.preprocessor.normalize(theme)
                cluster_info = theme_to_cluster.get(normalized)
                if cluster_info:
                    p["cluster"] = {
                        "id": cluster_info[0],
                        "name": cluster_info[1],
                    }
                else:
                    p["cluster"] = None
            else:
                p["cluster"] = None
            annotated.append(p)
        return annotated

    def _single_cluster_result(
        self,
        posts: list[dict[str, Any]],
        canonical_themes: list[str],
        original_count: int,
        canonical_count: int,
        start: float,
    ) -> ClusteringResult:
        """Handle the edge case of a single unique theme."""
        theme_to_count, theme_to_posts = self._extract_theme_data(posts)
        canonical_map = self.preprocessor.deduplicate_themes(theme_to_count)

        clusters = [
            ThemeCluster(
                cluster_id=0,
                name=canonical_themes[0] if canonical_themes else "Single Cluster",
                themes=canonical_themes,
                post_count=len(posts),
                total_upvotes=sum(
                    p.get("post", {}).get("upvotes", 0) for p in posts
                ),
            )
        ]

        theme_to_cluster = self._build_theme_to_cluster_map(canonical_map, clusters)
        annotated_posts = self._assign_clusters_to_posts(posts, theme_to_cluster)

        elapsed = time.time() - start
        return ClusteringResult(
            clusters=clusters,
            posts=annotated_posts,
            original_theme_count=original_count,
            canonical_theme_count=canonical_count,
            cluster_count=1,
            processing_time_seconds=round(elapsed, 2),
            provider_used=self.provider.provider_name,
            embedding_model=config.clustering_embedding_model,
        )
