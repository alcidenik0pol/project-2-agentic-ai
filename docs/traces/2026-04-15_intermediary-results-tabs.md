# Trace: Intermediary Results — Tab System with WebSocket Streaming

**Date:** 2026-04-15
**Status:** Implemented, TypeScript + Python compile clean

---

## The Problem

The frontend only displayed the final business ideas (hypothesis). The pipeline generates rich intermediary data — classification EDA (theme distributions, intensity levels, complaint breakdown) and clustering EDA (cluster details, theme groupings, upvote metrics) — but this data was only available by inspecting JSON files on disk. Users had no visibility into how the analysis progressed or what patterns were found along the way.

---

## Solution Overview

Added a 3-tab results display that streams intermediary results via WebSocket as they're generated:

1. **Business Ideas** — existing hypothesis display (unchanged)
2. **Classification EDA** — summary stats, complaint analysis, intensity distribution, top 20 themes
3. **Clustering Results** — cluster details table, theme breakdown by cluster

The key design decision: stream EDA data through the existing WebSocket connection right after the analyst agent completes, rather than adding new REST endpoints. This reuses the real-time infrastructure already in place and shows results progressively.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/websocket/manager.py` | Added `send_intermediary_result()` method for new `intermediary_result` message type |
| `backend/app/services/analysis_service.py` | In `on_agent_completed` callback: when analyst finishes, reads `classification_eda.json` and `clustering_eda.json` from run dir, streams via WebSocket |
| `frontend/lib/types.ts` | Added `IntermediaryResultMessage`, `ClassificationEDAResult`, `ClusterDetail`, `ClusteringEDAResult` types |
| `frontend/contexts/WebSocketContext.tsx` | Added `classificationEDA`/`clusteringEDA` state; handles `intermediary_result` messages; resets on connect/reset |
| `frontend/components/ClassificationEDATable.tsx` | **New** — 4 cards: summary stats, complaint analysis, intensity distribution, top 20 themes table |
| `frontend/components/ClusteringEDATable.tsx` | **New** — 3 cards: clustering summary, cluster details table (sorted by upvotes), theme breakdown with badges |
| `frontend/components/TabbedResultsDisplay.tsx` | **New** — Radix UI tabs wrapping all 3 result views; tabs disabled until data arrives |
| `frontend/app/page.tsx` | Swapped `ResultsDisplay` → `TabbedResultsDisplay`; pulls EDA state from WebSocket context |

---

## Architecture

```
Pipeline runs in thread pool:
  orchestrator → analyst → hypothesis
                      │
                      ▼
           on_agent_completed("analyst")
             ├── read classification_eda.json
             ├── stream via WebSocket ──────────► Frontend
             ├── read clustering_eda.json         │
             └── stream via WebSocket ──────────► │
                                                  │
                                        WebSocketContext
                                          ├── classificationEDA state
                                          └── clusteringEDA state
                                                  │
                                          TabbedResultsDisplay
                                            ├── Tab: Business Ideas (existing)
                                            ├── Tab: Classification EDA (enables on data)
                                            └── Tab: Clustering Results (enables on data)
```

### Why stream after analyst completes?

The analyst agent runs both `classify_posts` and `cluster_themes` tools. Both JSON files are written to disk by the time `on_agent_completed("analyst")` fires. This avoids async/sync complications — we read the files synchronously from the thread pool and use `asyncio.run_coroutine_threadsafe` (already the pattern for WebSocket calls in this callback) to send them.

---

## Key Design Decisions

1. **WebSocket over REST**: Reused existing real-time infrastructure instead of adding new endpoints. The data is small (~3KB per EDA file) so WebSocket payload size is a non-issue.

2. **Read-from-disk over inline construction**: The EDA JSON files are already written by `run_logger.py`. Rather than duplicating data assembly in the callback, we simply read the files. This guarantees the frontend sees exactly what's on disk.

3. **Tab disable pattern**: Tabs start disabled and enable as data streams in. The Business Ideas tab is always visible (it's the primary output). Classification and Clustering tabs light up as soon as the analyst agent finishes.

4. **Data tables over charts**: Clean tables with badges for status indicators. No chart library dependency needed.

---

## Type Contract (Backend → Frontend)

```typescript
// WebSocket message received
{
  type: "intermediary_result",
  data: {
    result_type: "classification_eda" | "clustering_eda",
    data: ClassificationEDAResult | ClusteringEDAResult
  }
}

// ClassificationEDAResult
{
  summary: { total_posts, successful_classifications, success_rate, model_used, processing_time_seconds, posts_per_second },
  unique_themes: number,
  top_20_themes: Array<{ theme: string, count: number }>,
  intensity_distribution: { high, medium, low },
  complaint_vs_noncomplaint: { complaint, non_complaint }
}

// ClusteringEDAResult
{
  summary: { original_theme_count, canonical_theme_count, deduplication_ratio, final_cluster_count, embedding_model, total_upvotes_in_clusters },
  cluster_details: Array<{ id, name, themes[], theme_count, post_count, total_upvotes, avg_upvotes }>,
  cluster_size_stats: { min, max, mean }
}
```

Types match the JSON structure produced by `app/agents/tools/run_logger.py`.

---

## What Was Not Changed

- `app/agents/tools/run_logger.py` — no changes; existing log structure is the data source
- `app/agents/tools/classify.py` — no changes; EDA data already saved to disk
- `app/agents/tools/cluster.py` — no changes; EDA data already saved to disk
- `frontend/components/ResultsDisplay.tsx` — kept as-is; not deleted in case it's needed for fallback
- No new REST endpoints added
- No new npm dependencies added
