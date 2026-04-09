"""CLI script to generate business hypotheses from clustered Reddit complaint data."""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path so app modules are importable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.analyst.hypothesis import HypothesisGenerator
from app.analyst.models import ClusteringResult, ThemeCluster
from app.config import config


def get_provider(provider_name: str | None = None):
    """Instantiate the requested LLM provider."""
    name = provider_name or config.llm_provider

    if name == "gcloud":
        from app.analyst.providers.gcloud import GCloudProvider
        return GCloudProvider()
    elif name == "lm_studio":
        from app.analyst.providers.lm_studio import LMStudioProvider
        return LMStudioProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate business hypotheses from clustered Reddit complaint data."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to *_clustered.json file",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: input with _hypothesis suffix)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["gcloud", "lm_studio"],
        help="LLM provider override",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Resolve input path
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Resolve output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Replace _clustered with _hypothesis, or append _hypothesis
        stem = input_path.stem
        if stem.endswith("_clustered"):
            stem = stem[:-10] + "_hypothesis"
        else:
            stem = stem + "_hypothesis"
        output_path = input_path.with_name(stem + input_path.suffix)

    # Load clustered data
    print(f"Loading clustered data from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate structure
    if not isinstance(data, dict) or "clusters" not in data or "posts" not in data:
        print("Error: Expected JSON with 'clusters' and 'posts' arrays.")
        sys.exit(1)

    clusters = [ThemeCluster(**c) for c in data["clusters"]]
    posts = data["posts"]
    print(f"Loaded {len(clusters)} clusters, {len(posts)} posts")

    # Build ClusteringResult
    clustering_result = ClusteringResult(
        clusters=clusters,
        posts=posts,
        cluster_count=len(clusters),
    )

    # Set up provider and generator
    provider = get_provider(args.provider)
    generator = HypothesisGenerator(provider=provider)

    # Run hypothesis generation
    print(f"Generating hypotheses using {provider.provider_name}:{provider.model_name}...")
    result = generator.generate_hypotheses(clustering_result)

    # Write output
    output_data = result.model_dump(mode="json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)

    # Summary
    print(f"\nHypothesis generation complete!")
    print(f"  Ideas generated: {len(result.ideas)}")
    print(f"  Clusters analyzed: {result.source_cluster_count}")
    print(f"  Time: {result.processing_time_seconds:.1f}s")
    print(f"  Output: {output_path}")
    print()
    print("Business ideas:")
    for idea in result.ideas:
        print(f"\n  #{idea.rank}: {idea.idea_name}")
        print(f"    Pain: {idea.pain_point}")
        print(f"    Product: {idea.product_description}")
        print(f"    Target: {idea.target_user}")
        print(f"    Evidence: {idea.evidence.cluster_name} "
              f"({idea.evidence.post_count} posts, {idea.evidence.total_upvotes:,} upvotes)")
        print(f"    Confidence: {idea.confidence}")
    print(f"\n  Summary: {result.analysis_summary}")
    print(f"  Limitations: {result.data_limitations}")


if __name__ == "__main__":
    main()
