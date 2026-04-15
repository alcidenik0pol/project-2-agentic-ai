# Trace: Pipeline Run Logging with Substep Timing

**Date:** 2026-04-15
**Status:** Implemented and tested (supersedes 2026-04-14 version)

---

## The Problem

The multi-agent pipeline (Orchestrator -> Analyst -> Hypothesis) produces rich intermediate data at every stage, but none of it was persisted to disk. Additionally, while top-level timing was visible (e.g. "analyst round took 521s"), there was no breakdown of what happened *within* each stage -- how much time was spent on LLM calls vs embeddings vs KMeans, etc.

This made it impossible to:
1. Review *why* certain subreddits were selected after a run completes
2. Understand classification quality (theme distribution, failure rate, intensity spread)
3. Evaluate clustering parameters (dedup ratio, cluster sizes, theme breakdown)
4. Identify which substep is the bottleneck (LLM calls? embeddings? KMeans?)
5. Diagnose prompt quality issues without re-running the entire pipeline

---

## Solution Overview

Two-phase implementation:

**Phase 1 (2026-04-14):** Added a centralized `RunLogger` utility that persists structured JSON logs at each pipeline stage. Every tool (`fetch_posts`, `classify_posts`, `cluster_themes`, and the subreddit selector) saves a summary file to the output directory. A markdown workflow report is auto-generated when the hypothesis artifact is saved.

**Phase 2 (2026-04-15):** Added granular substep timing to every pipeline stage. Each LLM call, embedding generation, and algorithmic step is now individually timed. The timing data flows through Pydantic models into the log files and workflow report.

### Output Files Per Run

```
output/
  |-- subreddit_selection.json     # LLM reasoning + selected subreddits
  |-- fetch_stats.json             # Posts fetched, subreddits queried, timing
  |-- classification_eda.json      # Theme/intensity distributions + substep timing
  |-- clustering_eda.json          # Cluster details + substep timing breakdown
  |-- hypothesis.json              # (existing) Final hypotheses + substep timing
  |-- clustering.json              # (existing) Full clustering data
  |-- classified.json              # (existing) Full classified posts
  |-- workflow_report.md           # Markdown summary with timing tables
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
| `save_classification_eda()` | `classification_eda.json` | success/fail counts, rate, model, theme/intensity distributions, top 20 themes, error samples, **substep timing** |
| `save_clustering_eda()` | `clustering_eda.json` | dedup ratio, cluster details, size stats, **substep timing** |
| `save_workflow_report()` | `workflow_report.md` | Reads all JSON logs and assembles markdown report with timing tables |

### Modified: `app/analyst/models.py` -- New Timing Fields

Added substep timing fields to four Pydantic models:

```python
class ClassificationResult(BaseModel):
    # ... existing ...
    substep_timing: dict[str, float] = Field(default_factory=dict)

class BatchExpansionResult(BaseModel):
    # ... existing ...
    llm_time_seconds: float = 0.0  # total LLM expansion time

class ClusteringResult(BaseModel):
    # ... existing ...
    substep_timing: dict[str, float] = Field(default_factory=dict)

class HypothesisOutput(BaseModel):
    # ... existing ...
    llm_time_seconds: float = 0.0
    table_preparation_time_seconds: float = 0.0
```

All fields have defaults so they're backward-compatible with existing code.

### Modified: `app/analyst/classifier.py` -- Per-Call LLM Timing

Tracks cumulative LLM time across all classification calls:

```python
llm_time = 0.0
for i, post_item in enumerate(posts, 1):
    call_start = time.time()
    enriched = self.classify_post(...)
    llm_time += time.time() - call_start
```

Result includes:
```python
substep_timing={
    "llm_calls": round(llm_time, 2),
    "serialization_overhead": round(elapsed - llm_time, 2),
    "total_calls": total,
    "avg_time_per_call": round(llm_time / total, 3) if total > 0 else 0,
}
```

### Modified: `app/analyst/expansion.py` -- Batch LLM Timing

Tracks LLM time per expansion batch:

```python
total_llm_time = 0.0
for batch in batches:
    batch_start = time.time()
    llm_results = self._expand_batch(uncached)
    total_llm_time += time.time() - batch_start
```

Flows into `BatchExpansionResult.llm_time_seconds`, which the clustering pipeline reads.

### Modified: `app/analyst/clustering.py` -- Per-Substep Timing

Wraps each major substep with timing:

```python
substeps = {}

# Theme expansion (LLM)
t0 = time.time()
expanded_descriptions = self._expand_themes_for_embeddings(...)
substeps["theme_expansion"] = round(time.time() - t0, 2)
substeps["theme_expansion_llm"] = round(expanded_descriptions.llm_time_seconds, 2)

# Embedding generation (API)
t0 = time.time()
embeddings = self.provider.get_embeddings(texts_to_embed)
substeps["embedding_generation"] = round(time.time() - t0, 2)

# KMeans (sklearn)
t0 = time.time()
labels = KMeans(...).fit_predict(embeddings)
substeps["kmeans_clustering"] = round(time.time() - t0, 2)

# Cluster naming (LLM, one call per cluster)
t0 = time.time()
cluster_names = self._name_clusters(cluster_themes)
substeps["cluster_naming"] = round(time.time() - t0, 2)
```

Console log now shows the breakdown:
```
Clustering complete: 8 clusters in 15.3s (expansion=8.5s, embeddings=2.1s, kmeans=0.2s, naming=4.5s)
```

### Modified: `app/analyst/hypothesis.py` -- LLM + Table Prep Timing

```python
t0 = time.time()
cluster_table = self._prepare_cluster_table(clustering_result)
table_time = time.time() - t0

t0 = time.time()
raw = self._call_llm(cluster_table)
llm_time = time.time() - t0

result.llm_time_seconds = round(llm_time, 2)
result.table_preparation_time_seconds = round(table_time, 2)
```

### Modified: `app/agents/tools/classify.py` -- Passes Timing to Logger

Added `substep_timing=result.substep_timing` to the `save_classification_eda()` call.

### Modified: `app/agents/tools/cluster.py` -- Passes Timing to Logger

Added `substep_timing=result.substep_timing` to the `save_clustering_eda()` call.

### Modified: `app/collector/subreddit_selector.py` -- Saves Selection Log

Two insertion points:
1. **LLM success path:** saves reasoning, selected list, prompt, available count
2. **Fallback path:** saves with `fallback_used=True`

### Modified: `app/agents/tools/fetch.py` -- Saves Fetch Stats

Single insertion after fetch completes.

### Modified: `app/agents/tools/artifacts.py` -- Auto-Generates Report

When `artifact_type == "hypothesis"`, calls `save_workflow_report()`.

---

## Data Structures

### `classification_eda.json`

```json
{
  "timestamp": "2026-04-15T18:50:48Z",
  "summary": {
    "total_posts": 150,
    "successful_classifications": 145,
    "failed_classifications": 5,
    "success_rate": 96.7,
    "model_used": "gcloud:gemini-3.1-pro-001",
    "processing_time_seconds": 120.5,
    "posts_per_second": 1.24,
    "substep_timing": {
      "llm_calls": 115.2,
      "serialization_overhead": 5.3,
      "total_calls": 150,
      "avg_time_per_call": 0.768
    }
  },
  "unique_themes": 42,
  "theme_distribution": { "microtransactions": 25, "bugs": 20, ... },
  "top_20_themes": [ {"theme": "microtransactions", "count": 25}, ... ],
  "intensity_distribution": { "high": 45, "medium": 60, "low": 40 },
  "complaint_vs_noncomplaint": { "complaint": 110, "non_complaint": 35 },
  "errors_sample": ["JSON parse error: ..."]
}
```

### `clustering_eda.json`

```json
{
  "timestamp": "2026-04-15T18:50:48Z",
  "summary": {
    "original_theme_count": 120,
    "canonical_theme_count": 45,
    "deduplication_ratio": 0.375,
    "final_cluster_count": 8,
    "processing_time_seconds": 15.3,
    "embedding_model": "text-embedding-004",
    "provider_used": "gcloud",
    "total_posts_in_clusters": 145,
    "total_upvotes_in_clusters": 12500,
    "substep_timing": {
      "theme_expansion": 8.5,
      "theme_expansion_llm": 8.2,
      "embedding_generation": 2.1,
      "kmeans_clustering": 0.2,
      "cluster_naming": 4.5
    }
  },
  "cluster_details": [
    { "id": 0, "name": "Monetization complaints", "themes": [...], "post_count": 35, "total_upvotes": 2500, "avg_upvotes": 71.4 }
  ],
  "cluster_size_stats": { "min": 5, "max": 35, "mean": 18.1 }
}
```

### `workflow_report.md` -- Timing Tables

Classification section includes:
```markdown
### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 115.2 | 150 calls, avg 0.768s/call |
| Serialization/overhead | 5.3 | Rate limiting delays + serialization |
```

Clustering section includes:
```markdown
### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 8.5 | 55.6% |
| Theme Expansion Llm | 8.2 | 53.6% |
| Embedding Generation | 2.1 | 13.7% |
| Kmeans Clustering | 0.2 | 1.3% |
| Cluster Naming | 4.5 | 29.4% |
```

Hypothesis section includes:
```markdown
### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.1 |
| LLM generation | 8.2 |
| Parse + validation | 0.2 |
| **Total** | **8.5** |
```

---

## Timing Data Flow

```
classifier.py: classify_batch()
    |  tracks llm_time per call
    |  -> ClassificationResult.substep_timing
         |
         v
classify.py (tool): reads result.substep_timing
    |  -> run_logger.save_classification_eda(substep_timing=...)
         |
         v
classification_eda.json -> workflow_report.md

clustering.py: cluster_posts()
    |  times each substep (expansion, embeddings, kmeans, naming)
    |  reads BatchExpansionResult.llm_time_seconds for expansion LLM time
    |  -> ClusteringResult.substep_timing
         |
         v
cluster.py (tool): reads result.substep_timing
    |  -> run_logger.save_clustering_eda(substep_timing=...)
         |
         v
clustering_eda.json -> workflow_report.md

hypothesis.py: generate_hypotheses()
    |  times table prep and LLM call
    |  -> HypothesisOutput.llm_time_seconds + table_preparation_time_seconds
         |
         v
hypothesis.json -> workflow_report.md
```

---

## Error Handling

Every logging call is wrapped in try/except at the call site so logging failures never break the pipeline:

```python
try:
    from app.agents.tools.run_logger import save_classification_eda
    save_classification_eda(...)
except Exception as log_err:
    logger.warning(f"Failed to save classification EDA log: {log_err}")
```

---

## Complete File List

| File | Change Type |
|------|-------------|
| `app/agents/tools/run_logger.py` | **New** - centralized logging utility |
| `app/analyst/models.py` | Modified - added substep timing fields |
| `app/analyst/classifier.py` | Modified - per-call LLM timing |
| `app/analyst/expansion.py` | Modified - batch LLM timing |
| `app/analyst/clustering.py` | Modified - per-substep timing |
| `app/analyst/hypothesis.py` | Modified - LLM + table prep timing |
| `app/agents/tools/classify.py` | Modified - passes timing to logger |
| `app/agents/tools/cluster.py` | Modified - passes timing to logger |
| `app/agents/tools/fetch.py` | Modified - saves fetch stats |
| `app/agents/tools/artifacts.py` | Modified - auto-generates workflow report |
| `app/collector/subreddit_selector.py` | Modified - saves selection reasoning |

---

## Verification

Integration test confirmed:
1. All log files created with valid JSON
2. `substep_timing` fields populated with breakdowns
3. `workflow_report.md` includes timing tables with percentages
4. Total time approximately equals sum of substeps (within rounding)
5. All modified files compile without errors
