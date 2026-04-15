# Trace: Pipeline Run Logging (Static Artifact Files)

**Date:** 2026-04-14
**Status:** Implemented and tested

---

## The Problem

The multi-agent pipeline (Orchestrator -> Analyst -> Hypothesis) produces rich intermediate data at every stage -- subreddit selection reasoning, fetch statistics, classification distributions, cluster compositions -- but none of it was persisted to disk. All intermediate results lived only in the shared data store (in-memory dict) and console log output.

This made it impossible to:
1. Review *why* certain subreddits were selected after a run completes
2. Understand classification quality (theme distribution, failure rate, intensity spread)
3. Evaluate clustering parameters (dedup ratio, cluster sizes, theme breakdown)
4. Diagnose prompt quality issues without re-running the entire pipeline

The existing `artifacts.py` only saved final outputs (`hypothesis.json`, `clustering.json`, `classified.json`) -- the raw data, not the analysis of the data.

---

## Solution Overview

Added a centralized `RunLogger` utility that persists structured JSON logs at each pipeline stage. Every tool (`fetch_posts`, `classify_posts`, `cluster_themes`, and the subreddit selector) now saves a summary file to the output directory. A markdown workflow report is auto-generated when the hypothesis artifact is saved (the final step).

### Output Files Per Run

```
output/
  |-- subreddit_selection.json     # LLM reasoning + selected subreddits
  |-- fetch_stats.json             # Posts fetched, subreddits queried, timing
  |-- classification_eda.json      # Theme/intensity distributions, success rate
  |-- clustering_eda.json          # Cluster details, dedup ratio, size stats
  |-- hypothesis.json              # (existing) Final hypotheses
  |-- clustering.json              # (existing) Full clustering data
  |-- classified.json              # (existing) Full classified posts
  |-- workflow_report.md           # NEW: Comprehensive markdown summary
```

---

## Files Changed

### New File: `app/agents/tools/run_logger.py`

Centralized logging utility. Resolves output directory the same way as `artifacts.py` (checks shared data `run_dir`, falls back to `output/`).

**Functions:**

| Function | Output File | Key Data |
|----------|-------------|----------|
| `save_subreddit_selection()` | `subreddit_selection.json` | topic, selected subreddits, LLM reasoning, prompt used, fallback status |
| `save_fetch_stats()` | `fetch_stats.json` | topic, mode, total posts, subreddits queried, elapsed time |
| `save_classification_eda()` | `classification_eda.json` | success/fail counts, rate, model, theme distribution, intensity distribution, top 20 themes, error samples |
| `save_clustering_eda()` | `clustering_eda.json` | original/canonical theme counts, dedup ratio, cluster count, cluster details (name, themes, posts, upvotes, avg), size stats |
| `save_workflow_report()` | `workflow_report.md` | Reads all JSON logs and assembles a markdown report with tables |

**Design decisions:**
- Standalone functions, not a class -- simpler, no state management needed
- Each function is a complete unit: resolves output dir, writes file, logs confirmation
- All wrapped in try/except at call sites so logging failures never break the pipeline

### Modified: `app/collector/subreddit_selector.py`

Two insertion points:

1. **LLM success path** (after line 154): saves selection reasoning, selected list, prompt, and available count
2. **Fallback path** (after `_fallback_selection`): saves with `fallback_used=True` and a note explaining the LLM call failed

This captures the *decision-making* of subreddit selection, which is the first LLM call in the pipeline.

### Modified: `app/agents/tools/fetch.py`

Single insertion after fetch completes: saves topic, mode (test/live), post count, subreddits queried, elapsed time, and source path.

### Modified: `app/agents/tools/classify.py`

Single insertion after classification batch completes. Builds three distributions from the classified posts:

- **Theme distribution**: `{theme: count}` for all classified themes
- **Intensity distribution**: `{high/medium/low: count}`
- **Complaint vs non-complaint**: `{complaint: N, non_complaint: M}`

Also captures a sample of classification error messages (up to 10) for debugging failed parses.

### Modified: `app/agents/tools/cluster.py`

Single insertion after clustering completes. Builds cluster detail dicts with:
- Cluster ID, name, themes list, theme count
- Post count, total upvotes, average upvotes per post
- Sorted by total upvotes descending in the report

### Modified: `app/agents/tools/artifacts.py`

Single insertion: when `artifact_type == "hypothesis"`, calls `save_workflow_report()`. This triggers the report generation at the natural end of the pipeline (hypothesis is always the last artifact saved).

---

## Data Structures

### `subreddit_selection.json`

```json
{
  "timestamp": "2026-04-14T20:00:00Z",
  "topic": "indie game dev",
  "selection_method": "llm",
  "fallback_used": false,
  "available_subreddits_count": 60,
  "selected_subreddits": ["gamedev", "IndieGaming", "INAT", ...],
  "selected_count": 12,
  "llm_reasoning": "Selected game dev subreddits plus general gaming...",
  "prompt_used": "You are selecting relevant subreddits...",
  "error": null
}
```

### `fetch_stats.json`

```json
{
  "timestamp": "2026-04-14T20:05:00Z",
  "topic": "indie game dev",
  "mode": "live",
  "total_posts": 150,
  "subreddits_queried": ["gamedev", "IndieGaming", ...],
  "subreddits_count": 12,
  "elapsed_seconds": 45.2,
  "source": "",
  "posts_per_subreddit": {},
  "error": null
}
```

### `classification_eda.json`

```json
{
  "timestamp": "2026-04-14T20:10:00Z",
  "summary": {
    "total_posts": 150,
    "successful_classifications": 145,
    "failed_classifications": 5,
    "success_rate": 96.7,
    "model_used": "gcloud:gemini-3.1-pro-001",
    "processing_time_seconds": 120.5,
    "posts_per_second": 1.24
  },
  "unique_themes": 42,
  "theme_distribution": {
    "microtransactions": 25,
    "bugs": 20,
    ...
  },
  "top_20_themes": [
    {"theme": "microtransactions", "count": 25},
    {"theme": "bugs", "count": 20},
    ...
  ],
  "intensity_distribution": {
    "high": 45,
    "medium": 60,
    "low": 40
  },
  "complaint_vs_noncomplaint": {
    "complaint": 110,
    "non_complaint": 35
  },
  "errors_sample": ["JSON parse error: ...", ...]
}
```

### `clustering_eda.json`

```json
{
  "timestamp": "2026-04-14T20:15:00Z",
  "summary": {
    "original_theme_count": 120,
    "canonical_theme_count": 45,
    "deduplication_ratio": 0.375,
    "final_cluster_count": 8,
    "processing_time_seconds": 15.3,
    "embedding_model": "text-embedding-004",
    "provider_used": "gcloud",
    "total_posts_in_clusters": 145,
    "total_upvotes_in_clusters": 12500
  },
  "cluster_details": [
    {
      "id": 0,
      "name": "Monetization complaints",
      "themes": ["microtransactions", "loot boxes", "overpriced DLC"],
      "theme_count": 3,
      "post_count": 35,
      "total_upvotes": 2500,
      "avg_upvotes": 71.4
    },
    ...
  ],
  "cluster_size_stats": {
    "min": 5,
    "max": 35,
    "mean": 18.1
  }
}
```

### `workflow_report.md`

Markdown document with five sections:
1. **Subreddit Selection** -- topic, method, reasoning, selected list
2. **Data Fetching** -- mode, post count, subreddits, timing
3. **Classification EDA** -- success rate, throughput, intensity distribution table, top 20 themes table
4. **Clustering EDA** -- dedup stats, cluster details table (sorted by upvotes), theme breakdown by cluster
5. **Hypothesis Summary** -- ideas with pain points, confidence, evidence stats

---

## Error Handling

Every logging call is wrapped in try/except at the call site:

```python
try:
    from app.agents.tools.run_logger import save_classification_eda
    save_classification_eda(...)
except Exception as log_err:
    logger.warning(f"Failed to save classification EDA log: {log_err}")
```

This guarantees:
- Logging failures never break the pipeline
- Failures are visible in console output
- The pipeline returns results even if the output directory is unwritable

---

## Verification

Integration test confirmed:
1. All five log files created in `output/test_debug/`
2. JSON files are valid and contain expected fields
3. `workflow_report.md` renders correctly with tables and sections
4. All modified files compile without errors
5. Import chain works: `run_logger` -> `shared` (shared data store)
