"""Run logger: persists intermediate workflow results to JSON files.

Saves structured logs for each pipeline stage (subreddit selection,
fetch, classification, clustering) so they can be reviewed after a run
to evaluate prompt quality, data coverage, and model behavior.

Uses the same output directory resolution as artifacts.py.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.tools.shared import get_shared_data

logger = logging.getLogger(__name__)


def _resolve_output_dir() -> Path:
    """Get the output directory for this run.

    Checks shared data for a run_dir set by the CLI.
    Falls back to output/ if not found.
    """
    run_dir = get_shared_data("run_dir")
    if run_dir:
        return Path(run_dir)

    output_dir = Path("output")
    if not output_dir.exists():
        project_root = Path(__file__).resolve().parents[3]
        output_dir = project_root / "output"
    return output_dir


def _save_log(data: dict[str, Any], filename: str) -> Path:
    """Save a JSON log file to the output directory.

    Args:
        data: The data to save.
        filename: Name of the file (e.g. "subreddit_selection.json").

    Returns:
        Path to the saved file.
    """
    output_dir = _resolve_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"[RUN LOG] Saved {filename} ({filepath.stat().st_size:,} bytes)")
    return filepath


def _timestamp() -> str:
    """Return ISO 8601 timestamp for the current UTC time."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Subreddit selection logging
# ---------------------------------------------------------------------------

def save_subreddit_selection(
    topic: str,
    selected: list[str],
    reasoning: str,
    prompt: str,
    fallback_used: bool,
    available_count: int = 0,
    error: str | None = None,
) -> Path:
    """Save subreddit selection results with LLM reasoning.

    Args:
        topic: The user's topic/niche.
        selected: List of selected subreddit names.
        reasoning: LLM's reasoning text (or empty string).
        prompt: The prompt sent to the LLM.
        fallback_used: Whether keyword fallback was used instead of LLM.
        available_count: Number of subreddits available for selection.
        error: Error message if selection failed.

    Returns:
        Path to the saved file.
    """
    data = {
        "timestamp": _timestamp(),
        "topic": topic,
        "selection_method": "fallback" if fallback_used else "llm",
        "fallback_used": fallback_used,
        "available_subreddits_count": available_count,
        "selected_subreddits": selected,
        "selected_count": len(selected),
        "llm_reasoning": reasoning,
        "prompt_used": prompt,
        "error": error,
    }
    return _save_log(data, "subreddit_selection.json")


# ---------------------------------------------------------------------------
# Fetch statistics logging
# ---------------------------------------------------------------------------

def save_fetch_stats(
    topic: str,
    mode: str,
    total_posts: int,
    subreddits_queried: list[str],
    elapsed_seconds: float,
    source: str = "",
    posts_per_subreddit: dict[str, int] | None = None,
    error: str | None = None,
) -> Path:
    """Save fetch statistics for the run.

    Args:
        topic: The user's topic/niche.
        mode: "test" or "live".
        total_posts: Number of posts fetched.
        subreddits_queried: List of subreddits that were queried.
        elapsed_seconds: Time spent fetching.
        source: Data source path (for test mode).
        posts_per_subreddit: Optional dict of subreddit -> post count.
        error: Error message if fetch failed.

    Returns:
        Path to the saved file.
    """
    data = {
        "timestamp": _timestamp(),
        "topic": topic,
        "mode": mode,
        "total_posts": total_posts,
        "subreddits_queried": subreddits_queried,
        "subreddits_count": len(subreddits_queried),
        "elapsed_seconds": round(elapsed_seconds, 2),
        "source": source,
        "posts_per_subreddit": posts_per_subreddit or {},
        "error": error,
    }
    return _save_log(data, "fetch_stats.json")


# ---------------------------------------------------------------------------
# Classification EDA logging
# ---------------------------------------------------------------------------

def save_classification_eda(
    total_posts: int,
    successful: int,
    failed: int,
    model_used: str,
    processing_time_seconds: float,
    theme_distribution: dict[str, int],
    intensity_distribution: dict[str, int],
    complaint_vs_noncomplaint: dict[str, int] | None = None,
    errors_sample: list[str] | None = None,
) -> Path:
    """Save classification EDA with distributions and stats.

    Args:
        total_posts: Total posts attempted.
        successful: Successfully classified posts.
        failed: Failed classifications.
        model_used: LLM model identifier.
        processing_time_seconds: Time spent classifying.
        theme_distribution: Dict of theme -> count.
        intensity_distribution: Dict of intensity -> count.
        complaint_vs_noncomplaint: Dict of {"complaint": N, "non_complaint": M}.
        errors_sample: Sample of classification error messages.

    Returns:
        Path to the saved file.
    """
    # Sort themes by frequency descending
    sorted_themes = sorted(
        theme_distribution.items(), key=lambda x: -x[1]
    )

    data = {
        "timestamp": _timestamp(),
        "summary": {
            "total_posts": total_posts,
            "successful_classifications": successful,
            "failed_classifications": failed,
            "success_rate": round(successful / total_posts * 100, 1) if total_posts > 0 else 0,
            "model_used": model_used,
            "processing_time_seconds": round(processing_time_seconds, 2),
            "posts_per_second": round(total_posts / processing_time_seconds, 2) if processing_time_seconds > 0 else 0,
        },
        "unique_themes": len(theme_distribution),
        "theme_distribution": theme_distribution,
        "top_20_themes": [
            {"theme": t, "count": c} for t, c in sorted_themes[:20]
        ],
        "intensity_distribution": intensity_distribution,
        "complaint_vs_noncomplaint": complaint_vs_noncomplaint or {},
        "errors_sample": (errors_sample or [])[:10],
    }
    return _save_log(data, "classification_eda.json")


# ---------------------------------------------------------------------------
# Clustering EDA logging
# ---------------------------------------------------------------------------

def save_clustering_eda(
    original_theme_count: int,
    canonical_theme_count: int,
    cluster_count: int,
    processing_time_seconds: float,
    embedding_model: str,
    provider_used: str,
    clusters: list[dict[str, Any]],
) -> Path:
    """Save clustering EDA with cluster details and stats.

    Args:
        original_theme_count: Themes before canonicalization.
        canonical_theme_count: Themes after canonicalization.
        cluster_count: Number of final clusters.
        processing_time_seconds: Time spent clustering.
        embedding_model: Embedding model used.
        provider_used: LLM provider name.
        clusters: List of cluster detail dicts.

    Returns:
        Path to the saved file.
    """
    total_posts = sum(c.get("post_count", 0) for c in clusters)
    total_upvotes = sum(c.get("total_upvotes", 0) for c in clusters)

    data = {
        "timestamp": _timestamp(),
        "summary": {
            "original_theme_count": original_theme_count,
            "canonical_theme_count": canonical_theme_count,
            "deduplication_ratio": round(
                canonical_theme_count / original_theme_count, 3
            ) if original_theme_count > 0 else 0,
            "final_cluster_count": cluster_count,
            "processing_time_seconds": round(processing_time_seconds, 2),
            "embedding_model": embedding_model,
            "provider_used": provider_used,
            "total_posts_in_clusters": total_posts,
            "total_upvotes_in_clusters": total_upvotes,
        },
        "cluster_details": clusters,
        "cluster_size_stats": {
            "min": min(c.get("post_count", 0) for c in clusters) if clusters else 0,
            "max": max(c.get("post_count", 0) for c in clusters) if clusters else 0,
            "mean": round(total_posts / len(clusters), 1) if clusters else 0,
        },
    }
    return _save_log(data, "clustering_eda.json")


# ---------------------------------------------------------------------------
# Workflow report (markdown summary)
# ---------------------------------------------------------------------------

def _load_json_log(filepath: Path) -> dict[str, Any] | None:
    """Load a JSON log file, returning None if not found or invalid."""
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_workflow_report() -> Path | None:
    """Generate a comprehensive markdown workflow report from all log files.

    Reads the individual JSON logs and assembles a human-readable summary.
    Safe to call even if some logs are missing (skips absent sections).

    Returns:
        Path to the saved report, or None if output dir could not be resolved.
    """
    output_dir = _resolve_output_dir()

    sub_log = _load_json_log(output_dir / "subreddit_selection.json")
    fetch_log = _load_json_log(output_dir / "fetch_stats.json")
    class_log = _load_json_log(output_dir / "classification_eda.json")
    cluster_log = _load_json_log(output_dir / "clustering_eda.json")
    hyp_log = _load_json_log(output_dir / "hypothesis.json")

    lines: list[str] = []
    lines.append("# Workflow Report")
    lines.append(f"_Generated: {_timestamp()}_")
    lines.append("")

    # --- Subreddit Selection ---
    if sub_log:
        lines.append("## 1. Subreddit Selection")
        lines.append("")
        lines.append(f"**Topic:** {sub_log.get('topic', 'N/A')}")
        lines.append(f"**Method:** {sub_log.get('selection_method', 'N/A')}")
        lines.append(f"**Fallback used:** {sub_log.get('fallback_used', False)}")
        lines.append(f"**Subreddits available:** {sub_log.get('available_subreddits_count', 'N/A')}")
        lines.append(f"**Subreddits selected:** {sub_log.get('selected_count', 0)}")
        lines.append("")
        if sub_log.get("llm_reasoning"):
            lines.append("### LLM Reasoning")
            lines.append(f"> {sub_log['llm_reasoning']}")
            lines.append("")
        if sub_log.get("selected_subreddits"):
            lines.append("### Selected Subreddits")
            for s in sub_log["selected_subreddits"]:
                lines.append(f"- r/{s}")
            lines.append("")
        if sub_log.get("error"):
            lines.append(f"**Error:** {sub_log['error']}")
            lines.append("")

    # --- Fetch Stats ---
    if fetch_log:
        lines.append("## 2. Data Fetching")
        lines.append("")
        lines.append(f"**Topic:** {fetch_log.get('topic', 'N/A')}")
        lines.append(f"**Mode:** {fetch_log.get('mode', 'N/A')}")
        lines.append(f"**Total posts:** {fetch_log.get('total_posts', 0)}")
        lines.append(f"**Subreddits queried:** {fetch_log.get('subreddits_count', 0)}")
        lines.append(f"**Time:** {fetch_log.get('elapsed_seconds', 0):.1f}s")
        if fetch_log.get("source"):
            lines.append(f"**Source:** {fetch_log['source']}")
        lines.append("")
        if fetch_log.get("subreddits_queried"):
            lines.append("### Subreddits Queried")
            for s in fetch_log["subreddits_queried"]:
                count = fetch_log.get("posts_per_subreddit", {}).get(s, "")
                extra = f" ({count} posts)" if count else ""
                lines.append(f"- r/{s}{extra}")
            lines.append("")

    # --- Classification EDA ---
    if class_log:
        summary = class_log.get("summary", {})
        lines.append("## 3. Classification EDA")
        lines.append("")
        lines.append(f"**Total posts:** {summary.get('total_posts', 0)}")
        lines.append(f"**Successful:** {summary.get('successful_classifications', 0)}")
        lines.append(f"**Failed:** {summary.get('failed_classifications', 0)}")
        lines.append(f"**Success rate:** {summary.get('success_rate', 0)}%")
        lines.append(f"**Model:** {summary.get('model_used', 'N/A')}")
        lines.append(f"**Processing time:** {summary.get('processing_time_seconds', 0):.1f}s")
        lines.append(f"**Throughput:** {summary.get('posts_per_second', 0):.1f} posts/s")
        lines.append(f"**Unique themes:** {class_log.get('unique_themes', 0)}")
        lines.append("")

        complaint = class_log.get("complaint_vs_noncomplaint", {})
        if complaint:
            lines.append("### Complaint vs Non-Complaint")
            lines.append(f"- Complaints: {complaint.get('complaint', 0)}")
            lines.append(f"- Non-complaints: {complaint.get('non_complaint', 0)}")
            lines.append("")

        intensity = class_log.get("intensity_distribution", {})
        if intensity:
            lines.append("### Intensity Distribution")
            for level in ["high", "medium", "low"]:
                lines.append(f"- {level}: {intensity.get(level, 0)}")
            lines.append("")

        top_themes = class_log.get("top_20_themes", [])
        if top_themes:
            lines.append("### Top 20 Themes")
            lines.append("")
            lines.append("| # | Theme | Count |")
            lines.append("|---|-------|-------|")
            for i, entry in enumerate(top_themes, 1):
                lines.append(f"| {i} | {entry['theme']} | {entry['count']} |")
            lines.append("")

        errors = class_log.get("errors_sample", [])
        if errors:
            lines.append("### Sample Classification Errors")
            for e in errors[:5]:
                lines.append(f"- `{e}`")
            lines.append("")

    # --- Clustering EDA ---
    if cluster_log:
        csummary = cluster_log.get("summary", {})
        lines.append("## 4. Clustering EDA")
        lines.append("")
        lines.append(f"**Original themes:** {csummary.get('original_theme_count', 0)}")
        lines.append(f"**Canonical themes:** {csummary.get('canonical_theme_count', 0)}")
        lines.append(f"**Deduplication ratio:** {csummary.get('deduplication_ratio', 0):.3f}")
        lines.append(f"**Final clusters:** {csummary.get('final_cluster_count', 0)}")
        lines.append(f"**Embedding model:** {csummary.get('embedding_model', 'N/A')}")
        lines.append(f"**Provider:** {csummary.get('provider_used', 'N/A')}")
        lines.append(f"**Processing time:** {csummary.get('processing_time_seconds', 0):.1f}s")
        lines.append(f"**Total posts in clusters:** {csummary.get('total_posts_in_clusters', 0)}")
        lines.append(f"**Total upvotes in clusters:** {csummary.get('total_upvotes_in_clusters', 0):,}")
        lines.append("")

        size_stats = cluster_log.get("cluster_size_stats", {})
        if size_stats:
            lines.append("### Cluster Size Stats")
            lines.append(f"- Min posts: {size_stats.get('min', 0)}")
            lines.append(f"- Max posts: {size_stats.get('max', 0)}")
            lines.append(f"- Mean posts: {size_stats.get('mean', 0)}")
            lines.append("")

        details = cluster_log.get("cluster_details", [])
        if details:
            lines.append("### Cluster Details")
            lines.append("")
            lines.append("| # | Name | Themes | Posts | Upvotes | Avg Upvotes |")
            lines.append("|---|------|--------|-------|---------|-------------|")
            for c in sorted(details, key=lambda x: -x.get("total_upvotes", 0)):
                lines.append(
                    f"| {c.get('id', '?')} | {c.get('name', 'N/A')} "
                    f"| {c.get('theme_count', 0)} | {c.get('post_count', 0)} "
                    f"| {c.get('total_upvotes', 0):,} | {c.get('avg_upvotes', 0):.1f} |"
                )
            lines.append("")

            # Detailed cluster theme breakdown
            lines.append("### Theme Breakdown by Cluster")
            lines.append("")
            for c in sorted(details, key=lambda x: -x.get("total_upvotes", 0)):
                lines.append(f"**{c.get('name', 'N/A')}** ({c.get('post_count', 0)} posts, {c.get('total_upvotes', 0):,} upvotes)")
                for t in c.get("themes", []):
                    lines.append(f"  - {t}")
                lines.append("")

    # --- Hypothesis Summary ---
    if hyp_log:
        lines.append("## 5. Hypothesis Summary")
        lines.append("")
        ideas = hyp_log.get("ideas", [])
        if ideas:
            lines.append(f"**Total ideas generated:** {len(ideas)}")
            lines.append("")
            for idea in ideas:
                lines.append(f"### #{idea.get('rank', '?')} {idea.get('idea_name', 'N/A')}")
                lines.append(f"**Pain point:** {idea.get('pain_point', 'N/A')}")
                lines.append(f"**Target user:** {idea.get('target_user', 'N/A')}")
                lines.append(f"**Confidence:** {idea.get('confidence', 'N/A')}")
                if idea.get("core_features"):
                    lines.append(f"**Core features:** {idea['core_features']}")
                if idea.get("revenue_model"):
                    lines.append(f"**Revenue model:** {idea['revenue_model']}")
                evidence = idea.get("evidence", {})
                if evidence:
                    lines.append(f"**Evidence:** {evidence.get('post_count', 0)} posts, {evidence.get('total_upvotes', 0):,} upvotes")
                lines.append("")

        if hyp_log.get("analysis_summary"):
            lines.append("### Analysis Summary")
            lines.append(hyp_log["analysis_summary"])
            lines.append("")
        if hyp_log.get("data_limitations"):
            lines.append("### Data Limitations")
            lines.append(hyp_log["data_limitations"])
            lines.append("")

    report_text = "\n".join(lines)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "workflow_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info(f"[RUN LOG] Saved workflow_report.md ({report_path.stat().st_size:,} bytes)")
    return report_path
