#!/usr/bin/env python3
"""CLI script to classify Reddit posts using LM Studio.

Usage:
    python scripts/classify_posts.py data/sample_posts_1.json data/sample_posts_2.json

This script:
1. Loads JSON files containing Reddit posts
2. Skips files with empty posts arrays
3. Classifies all posts via LM Studio
4. Saves results to timestamped output file in output/
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.analyst import PostClassifier
from app.analyst.models import ClassificationResult, EnrichedPost

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_posts_from_file(file_path: Path) -> tuple[list[dict], bool]:
    """Load posts from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Tuple of (posts list, is_empty flag)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        posts = data.get("posts", [])

        if not posts:
            logger.warning(f"Skipping empty file: {file_path}")
            return [], True

        logger.info(f"Loaded {len(posts)} posts from {file_path}")
        return posts, False

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {file_path}: {e}")
        return [], True
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return [], True


def save_results(result: ClassificationResult, output_dir: Path) -> Path:
    """Save classification results to a timestamped JSON file.

    Args:
        result: ClassificationResult object
        output_dir: Directory to save output

    Returns:
        Path to the saved file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"classified_posts_{timestamp}.json"

    # Convert to dict for JSON serialization
    output_data = {
        "metadata": {
            "classified_at": result.classified_at.isoformat(),
            "source_files": result.source_files,
            "total_posts": result.total_posts,
            "successful_classifications": result.successful_classifications,
            "failed_classifications": result.failed_classifications,
            "processing_time_seconds": result.processing_time_seconds,
            "model_used": result.model_used,
        },
        "posts": [post.model_dump() for post in result.posts],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return output_file


def print_summary(result: ClassificationResult, output_file: Path) -> None:
    """Print a summary of the classification results."""
    print("\n" + "=" * 60)
    print("CLASSIFICATION COMPLETE")
    print("=" * 60)
    print(f"Output file: {output_file}")
    print(f"Total posts processed: {result.total_posts}")
    print(f"Successful classifications: {result.successful_classifications}")
    print(f"Failed classifications: {result.failed_classifications}")
    print(f"Processing time: {result.processing_time_seconds:.1f}s")
    print(f"Model used: {result.model_used}")

    if result.total_posts > 0:
        success_rate = result.successful_classifications / result.total_posts * 100
        print(f"Success rate: {success_rate:.1f}%")

    # Show sample of classifications
    print("\n" + "-" * 60)
    print("SAMPLE CLASSIFICATIONS (first 5 successful):")
    print("-" * 60)

    sample_count = 0
    for post in result.posts:
        if post.classification and sample_count < 5:
            print(f"\n[{post.subreddit}] {post.title[:50]}...")
            print(f"  Theme: {post.classification.theme}")
            print(f"  Is Complaint: {post.classification.is_complaint}")
            print(f"  Intensity: {post.classification.intensity}")
            sample_count += 1

    print("\n" + "=" * 60)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Classify Reddit posts using LM Studio local LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/classify_posts.py data/sample_posts_1.json
    python scripts/classify_posts.py data/*.json
    python scripts/classify_posts.py file1.json file2.json file3.json

Requirements:
    - LM Studio must be running with the model loaded
    - Default URL: http://localhost:1234/v1
        """,
    )

    parser.add_argument(
        "input_files",
        nargs="+",
        type=Path,
        help="One or more JSON files containing Reddit posts",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory for results (default: output/)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    parser.add_argument(
        "--max-posts",
        type=int,
        default=10,
        help="Maximum number of posts to process (default: 10, use 0 for all)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without calling LM Studio",
    )

    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=5,
        help="Stop after N consecutive failures (default: 5, use 0 to disable)",
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt for large batches",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Collect all posts from input files
    all_posts: list[dict] = []
    source_files: list[str] = []

    for file_path in args.input_files:
        posts, is_empty = load_posts_from_file(file_path)
        if not is_empty:
            all_posts.extend(posts)
            source_files.append(str(file_path))

    if not all_posts:
        logger.error("No posts found in any input files. Exiting.")
        sys.exit(1)

    total_available = len(all_posts)

    # Apply --max-posts limit
    if args.max_posts > 0:
        all_posts = all_posts[: args.max_posts]

    total_posts = len(all_posts)
    logger.info(f"Posts available: {total_available}, will process: {total_posts}")

    # Dry run mode - show what would be processed and exit
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No LM Studio calls will be made")
        print("=" * 60)
        print(f"Input files: {len(source_files)}")
        print(f"Posts available: {total_available}")
        print(f"Posts to process: {total_posts}")
        print(f"Max consecutive failures: {args.max_consecutive_failures}")
        print("\nFirst 5 posts:")
        for i, post in enumerate(all_posts[:5], 1):
            title = post.get("post", {}).get("title", "N/A")[:60]
            subreddit = post.get("subreddit", "N/A")
            print(f"  {i}. [{subreddit}] {title}...")
        print("\nRun without --dry-run to process.")
        return

    # Confirmation prompt for large batches
    if total_posts > 10 and not args.yes:
        print(f"\nAbout to process {total_posts} posts.")
        print(f"Max consecutive failures before stopping: {args.max_consecutive_failures}")
        try:
            response = input("Continue? [y/N]: ")
            if response.lower() != "y":
                print("Aborted.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return

    # Initialize classifier
    try:
        classifier = PostClassifier(
            request_delay=args.delay,
        )
    except Exception as e:
        logger.error(f"Failed to initialize classifier: {e}")
        logger.error("Ensure the LLM provider is correctly configured.")
        sys.exit(1)

    # Run classification
    logger.info("Starting classification...")
    result = classifier.classify_batch(
        all_posts,
        max_consecutive_failures=args.max_consecutive_failures,
    )
    result.source_files = source_files

    # Save results
    output_file = save_results(result, args.output_dir)

    # Print summary
    print_summary(result, output_file)


if __name__ == "__main__":
    main()
