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

        cluster_table = self._prepare_cluster_table(clustering_result)
        raw = self._call_llm(cluster_table)
        result = self._parse_response(raw, len(clustering_result.clusters))

        result.processing_time_seconds = round(time.time() - start, 2)
        result.model_used = f"{self._provider.provider_name}:{self._provider.model_name}"

        return result

    def _prepare_cluster_table(self, clustering_result: ClusteringResult) -> list[dict]:
        """Build a flat table of cluster data with sample titles for the LLM.

        For each cluster, finds the top 3 posts by upvotes within that cluster
        and includes their titles as supporting evidence.
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

            # Sort posts by upvotes descending, take top 3 titles
            sorted_posts = sorted(
                cluster_posts,
                key=lambda p: p.get("post", {}).get("upvotes", 0),
                reverse=True,
            )
            sample_titles = [
                p.get("post", {}).get("title", "")[:100]
                for p in sorted_posts[:3]
                if p.get("post", {}).get("title")
            ]

            table.append({
                "cluster_name": cluster.name,
                "post_count": cluster.post_count,
                "total_upvotes": cluster.total_upvotes,
                "sample_titles": sample_titles,
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
            max_tokens=8192,
        )

        if response is None:
            raise RuntimeError("LLM returned no response for hypothesis generation")

        logger.debug("Raw hypothesis response (%d chars): %s", len(response), response[:500])
        return response

    def _parse_response(self, raw: str, cluster_count: int) -> HypothesisOutput:
        """Parse and validate the LLM response into a HypothesisOutput.

        Tries direct JSON parse first, then falls back to extracting JSON
        from markdown code blocks.
        """
        text = raw.strip()

        # Tier 1: Direct JSON parse
        try:
            data = json.loads(text)
            return HypothesisOutput(source_cluster_count=cluster_count, **data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.debug(
                "Hypothesis Tier 1 (direct JSON) failed: %s. Response length=%d",
                e, len(text),
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
                    return HypothesisOutput(source_cluster_count=cluster_count, **data)
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.debug("Hypothesis Tier 2 (code block) parse failed: %s", e)
                    continue

        logger.error(
            "Failed to parse hypothesis response after all tiers. "
            "Response length=%d, first 500 chars: %s, last 500 chars: %s",
            len(text), text[:500], text[-500:],
        )
        raise RuntimeError(
            f"Failed to parse hypothesis response. Raw text:\n{text[:1000]}"
        )
