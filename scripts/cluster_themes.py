"""CLI script to run theme clustering on classified post JSON files."""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path so app modules are importable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.analyst.clustering import ThemeClusterer
from app.analyst.models import ClusteringResult
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
        description="Cluster complaint themes from classified Reddit posts."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to classified_posts_*.json file",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: input with _clustered suffix)",
    )
    parser.add_argument(
        "--min-k",
        type=int,
        default=None,
        help=f"Minimum number of clusters (default: {config.clustering_min_k})",
    )
    parser.add_argument(
        "--max-k",
        type=int,
        default=None,
        help=f"Maximum number of clusters (default: {config.clustering_max_k})",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["gcloud", "lm_studio"],
        help="LLM provider override",
    )
    parser.add_argument(
        "--no-silhouette",
        action="store_true",
        help="Skip silhouette score optimization, use min-k",
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
        output_path = input_path.with_name(
            input_path.stem + "_clustered" + input_path.suffix
        )

    # Load posts
    print(f"Loading posts from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both bare list and wrapped {"metadata": ..., "posts": ...} formats
    if isinstance(data, list):
        posts = data
    elif isinstance(data, dict) and "posts" in data:
        posts = data["posts"]
    else:
        print("Error: Unrecognized JSON format. Expected list or {posts: [...]}.")
        sys.exit(1)

    classified_count = sum(
        1 for p in posts if p.get("classification") and isinstance(p.get("classification"), dict)
    )
    print(f"Loaded {len(posts)} posts ({classified_count} classified)")

    if classified_count == 0:
        print("Error: No classified posts found. Run classification first.")
        sys.exit(1)

    # Set up provider and clusterer
    provider = get_provider(args.provider)
    clusterer = ThemeClusterer(
        provider=provider,
        min_k=args.min_k,
        max_k=args.max_k,
        use_silhouette=not args.no_silhouette,
    )

    # Run clustering
    print("Running theme clustering...")
    result = clusterer.cluster_posts(posts)

    # Write output
    output_data = {
        "metadata": {
            "source_file": str(input_path),
            "original_theme_count": result.original_theme_count,
            "canonical_theme_count": result.canonical_theme_count,
            "cluster_count": result.cluster_count,
            "processing_time_seconds": result.processing_time_seconds,
            "provider_used": result.provider_used,
            "embedding_model": result.embedding_model,
        },
        "clusters": [c.model_dump() for c in result.clusters],
        "posts": result.posts,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\nClustering complete!")
    print(f"  Themes: {result.original_theme_count} original -> {result.canonical_theme_count} canonical")
    print(f"  Clusters: {result.cluster_count}")
    print(f"  Time: {result.processing_time_seconds:.1f}s")
    print(f"  Output: {output_path}")
    print()
    print("Cluster summary:")
    for cluster in sorted(result.clusters, key=lambda c: c.post_count, reverse=True):
        print(f"  [{cluster.cluster_id:2d}] {cluster.name:40s} | {cluster.post_count:3d} posts | {cluster.total_upvotes:>8d} upvotes")


if __name__ == "__main__":
    main()
