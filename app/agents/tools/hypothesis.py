"""generate_hypotheses tool: generates business ideas from clustered data."""

import json
import logging

from app.agents.tools.shared import get_shared_data
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
    Returns full hypothesis output to the LLM.

    Returns:
        JSON string of hypothesis output.
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

    logger.info(f"Generating hypotheses from {len(clustering_result.clusters)} clusters")

    provider = get_provider(config.llm_provider)
    generator = HypothesisGenerator(provider=provider)
    result = generator.generate_hypotheses(clustering_result)

    output = result.model_dump()
    logger.info(f"Hypothesis generation done: {len(result.ideas)} ideas")
    return json.dumps(output, ensure_ascii=False, default=str)
