"""Hypothesis generation from clustered Reddit complaint themes.

Takes a ClusteringResult (or clustered JSON file), prepares a cluster summary
table with sample post titles, calls an LLM to generate 3 actionable business
ideas grounded in real data, and returns a validated HypothesisOutput.
"""

import json
import logging
import time

from pydantic import ValidationError

from app.analyst.hypothesis_prompts import HYPOTHESIS_PROMPT
from app.analyst.models import ClusteringResult, HypothesisOutput
from app.analyst.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class HypothesisGenerator:
    """Generate business hypotheses from clustered complaint data."""

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def generate_hypotheses(self, clustering_result: ClusteringResult) -> HypothesisOutput:
        """Main entry point: generate business ideas from cluster data.

        Args:
            clustering_result: Output from the clustering pipeline.

        Returns:
            HypothesisOutput with up to 3 ranked business ideas.

        Raises:
            RuntimeError: If LLM call fails or response cannot be parsed.
        """
        start = time.time()

        t0 = time.time()
        cluster_table = self._prepare_cluster_table(clustering_result)
        table_time = time.time() - t0

        t0 = time.time()
        raw = self._call_llm(cluster_table)
        llm_time = time.time() - t0

        result = self._parse_response(raw, len(clustering_result.clusters))

        result.processing_time_seconds = round(time.time() - start, 2)
        result.model_used = f"{self._provider.provider_name}:{self._provider.model_name}"
        result.llm_time_seconds = round(llm_time, 2)
        result.table_preparation_time_seconds = round(table_time, 2)

        return result

    def _prepare_cluster_table(self, clustering_result: ClusteringResult) -> list[dict]:
        """Build a flat table of cluster data with sample posts for the LLM.

        For each cluster, includes all posts sorted by upvotes with their
        full metadata (title, url, upvotes, subreddit).
        """
        # Index posts by their assigned cluster id
        posts_by_cluster: dict[int, list[dict]] = {}
        for post in clustering_result.posts:
            cluster_info = post.get("cluster")
            if cluster_info and isinstance(cluster_info, dict):
                cid = cluster_info.get("id")
                if cid is not None:
                    posts_by_cluster.setdefault(cid, []).append(post)

        table = []
        for cluster in clustering_result.clusters:
            cluster_posts = posts_by_cluster.get(cluster.cluster_id, [])

            # Sort posts by upvotes descending
            sorted_posts = sorted(
                cluster_posts,
                key=lambda p: p.get("post", {}).get("upvotes", 0),
                reverse=True,
            )
            sample_posts = []
            for p in sorted_posts:  # Include all posts, let LLM filter
                post_data = p.get("post", {})
                if post_data.get("title"):
                    sample_posts.append({
                        "title": post_data.get("title", "")[:200],
                        "url": post_data.get("url", ""),
                        "upvotes": post_data.get("upvotes", 0),
                        "subreddit": post_data.get("subreddit", ""),
                    })

            table.append({
                "cluster_name": cluster.name,
                "cluster_themes": cluster.themes,
                "post_count": cluster.post_count,
                "total_upvotes": cluster.total_upvotes,
                "shown_post_count": len(sample_posts),
                "sample_posts": sample_posts,
            })

        return table

    def _call_llm(self, cluster_table: list[dict]) -> str:
        """Send the cluster table to the LLM and return raw JSON response."""
        clusters_json = json.dumps(cluster_table, indent=2, ensure_ascii=False)
        prompt = HYPOTHESIS_PROMPT.format(clusters_json=clusters_json)

        logger.info(
            "Calling LLM for hypothesis generation (%d clusters, prompt=%d chars)",
            len(cluster_table), len(prompt),
        )
        logger.debug("Hypothesis prompt (first 1000 chars): %s", prompt[:1000])

        response = self._provider.generate_structured(
            prompt=prompt,
            temperature=0.3,
            max_tokens=16384,
        )

        if response is None:
            raise RuntimeError("LLM returned no response for hypothesis generation")

        logger.debug("Raw hypothesis response (%d chars): %s", len(response), response[:500])
        return response

    @staticmethod
    def _normalize_confidence(data: dict | list) -> dict | list:
        """Normalize confidence values to valid literals (high/medium/low).

        LLMs sometimes return non-standard values like 'medium-high', 'very high', etc.
        """
        CONFIDENCE_MAP = {
            "very high": "high",
            "medium-high": "medium",
            "medium high": "medium",
            "low-medium": "low",
            "low medium": "low",
            "very low": "low",
        }

        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if k == "confidence" and isinstance(v, str):
                    v = CONFIDENCE_MAP.get(v.lower().strip(), v.lower().strip())
                elif isinstance(v, (dict, list)):
                    v = HypothesisGenerator._normalize_confidence(v)
                result[k] = v
            return result
        elif isinstance(data, list):
            return [HypothesisGenerator._normalize_confidence(item) for item in data]
        return data

    def _parse_response(self, raw: str, cluster_count: int) -> HypothesisOutput:
        """Parse and validate the LLM response into a HypothesisOutput.

        Tries direct JSON parse first, then falls back to extracting JSON
        from markdown code blocks.
        """
        text = raw.strip()

        # Tier 1: Direct JSON parse
        try:
            data = json.loads(text)
            data = self._normalize_confidence(data)
            return HypothesisOutput(source_cluster_count=cluster_count, **data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(
                "Hypothesis Tier 1 (direct JSON) failed: %s. Response length=%d, last 200 chars: %s",
                e, len(text), text[-200:],
            )

        # Tier 2: Extract from markdown code blocks
        import re
        for pattern in [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
        ]:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    data = json.loads(match)
                    data = self._normalize_confidence(data)
                    return HypothesisOutput(source_cluster_count=cluster_count, **data)
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.error("Hypothesis Tier 2 (code block) parse failed: %s", e)
                    continue

        logger.error(
            "Failed to parse hypothesis response after all tiers. "
            "Response length=%d, first 500 chars: %s, last 500 chars: %s",
            len(text), text[:500], text[-500:],
        )
        raise RuntimeError(
            f"Failed to parse hypothesis response. Raw text:\n{text[:1000]}"
        )
