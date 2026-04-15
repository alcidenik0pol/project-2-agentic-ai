"""generate_hypotheses tool: generates business ideas from clustered data."""

import json
import logging
import time

from app.agents.tools.shared import get_shared_data, set_shared_data
from app.analyst.providers import get_provider

logger = logging.getLogger(__name__)

GENERATE_HYPOTHESES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_hypotheses",
        "description": (
            "Generate business hypotheses (top 5 business ideas) from clustered "
            "complaint data. Uses the clustering data from the previous cluster_themes call. "
            "Each idea includes pain point, product description, target user, evidence, "
            "and confidence level."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


def generate_hypotheses() -> str:
    """Generate business hypotheses from clustering results.

    Reads clustered data from shared data store.
    Stores full output in shared data for save_artifact.
    Returns a compact summary to the LLM to avoid truncation.

    Returns:
        JSON string with hypothesis summary (full data in shared store).
    """
    from app.analyst.hypothesis import HypothesisGenerator
    from app.analyst.models import ClusteringResult
    from app.config import config

    # Read from shared data store
    clustered_data = get_shared_data("clustered_data")
    if not clustered_data:
        logger.error("generate_hypotheses called but no clustered_data in shared store")
        return json.dumps({"error": "No clustered data found. Run cluster_themes first."})

    try:
        clustering_result = ClusteringResult(**clustered_data)
    except Exception as e:
        logger.error(
            "Failed to reconstruct ClusteringResult from shared data: %s. "
            "Keys present: %s",
            e, list(clustered_data.keys()) if isinstance(clustered_data, dict) else type(clustered_data).__name__,
        )
        return json.dumps({"error": f"Invalid clustering result: {e}"})

    if not clustering_result.clusters:
        logger.error("ClusteringResult has empty clusters list")
        return json.dumps({"error": "No clusters in clustering result"})

    logger.info(f"  [HYPOTHESIS] Starting generate_hypotheses: {len(clustering_result.clusters)} clusters")
    t0 = time.time()

    provider = get_provider(config.llm_provider)
    generator = HypothesisGenerator(provider=provider)
    result = generator.generate_hypotheses(clustering_result)

    # Store full output for downstream tools (save_artifact)
    full_output = result.model_dump()
    set_shared_data("hypotheses_full", full_output)

    elapsed = time.time() - t0
    logger.info(f"  [HYPOTHESIS] Completed: {len(result.ideas)} ideas in {elapsed:.1f}s")

    # Return compact summary to LLM (avoids truncation by base.py)
    summary = {
        "status": "success",
        "idea_count": len(result.ideas),
        "ideas": [
            {
                "rank": idea.rank,
                "idea_name": idea.idea_name,
                "pain_point": idea.pain_point,
                "solution_description": idea.solution_description,
                "core_features": idea.core_features,
                "revenue_model": idea.revenue_model,
                "first_user_step": idea.first_user_step,
                "target_user": idea.target_user,
                "evidence": {
                    "cluster_name": idea.evidence.cluster_name,
                    "cluster_themes": idea.evidence.cluster_themes,
                    "post_count": idea.evidence.post_count,
                    "total_upvotes": idea.evidence.total_upvotes,
                    "shown_post_count": idea.evidence.shown_post_count,
                    "supporting_posts": [
                        {
                            "title": p.title,
                            "url": p.url,
                            "upvotes": p.upvotes,
                            "subreddit": p.subreddit,
                        }
                        for p in idea.evidence.supporting_posts
                    ],
                },
                "confidence": idea.confidence,
                "confidence_reasoning": idea.confidence_reasoning,
            }
            for idea in result.ideas
        ],
        "analysis_summary": result.analysis_summary,
        "data_limitations": result.data_limitations,
        "source_cluster_count": result.source_cluster_count,
        "message": (
            f"Generated {len(result.ideas)} business ideas. "
            f"Use save_artifact with artifact_type 'hypothesis' to persist the full report."
        ),
    }
    return json.dumps(summary, ensure_ascii=False)
