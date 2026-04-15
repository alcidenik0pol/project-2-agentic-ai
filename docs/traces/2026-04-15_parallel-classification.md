# Parallel Classification with ThreadPoolExecutor

_Date: 2026-04-15_

_Problem: Sequential classification = 2+ hours for 500 posts (14.8s/post)._

_Solution: ThreadPoolExecutor to classify multiple posts concurrently._

---

## What Changed

### Files Modified

| File | Change |
|------|--------|
| `app/config.py` | Added 3 config fields: `classification_max_workers`, `classification_request_timeout`, `classification_enable_parallel` |
| `app/analyst/classifier.py` | Refactored `classify_batch()` to dispatch to parallel or sequential path |

### Architecture

```
classify_batch()  (dispatcher)
    |
    ├── _classify_parallel()      ← default (config.classification_enable_parallel=True)
    |   └── ThreadPoolExecutor(max_workers=10)
    |       └── _classify_post_timed() x N  (concurrent threads)
    |           └── provider.classify_post()  (unchanged)
    |
    └── _classify_sequential()   ← fallback (CLASSIFICATION_ENABLE_PARALLEL=false)
        └── classify_post() x N  (original loop, one at a time)
```

### Config Fields

| Field | Default | Env Var | Purpose |
|-------|---------|---------|---------|
| `classification_max_workers` | 10 | `CLASSIFICATION_MAX_WORKERS` | Max concurrent threads |
| `classification_request_timeout` | 30s | `CLASSIFICATION_REQUEST_TIMEOUT` | Per-future timeout |
| `classification_enable_parallel` | true | `CLASSIFICATION_ENABLE_PARALLEL` | Master switch |

### Key Design Decisions

1. **Thread-safe state via `threading.Lock`** — shared `results` dict and failure counter are protected
2. **Index mapping preserves order** — `future_to_index` maps futures to original post positions, results sorted by index at the end
3. **Graceful early stopping** — cancels remaining futures on consecutive failure threshold
4. **`_classify_post_timed()` wrapper** — returns `(EnrichedPost, call_duration)` tuple for accurate per-thread timing
5. **Telemetry: `concurrency_savings`** — in parallel mode, reports `llm_time - wall_time` instead of negative `serialization_overhead`

---

## What Was Removed

- `time.sleep(self.request_delay)` between posts in parallel mode — rate limiting delay no longer needed with thread pool

---

## What Was NOT Changed

- Provider interface (`classify_post()` signature unchanged)
- Agent tools (`classify_posts` tool unchanged)
- Retry logic (still handled inside each provider's `classify_post()`)
- Early stopping logic (consecutive failure threshold still enforced)

---

## Test Results

5 posts via gcloud/gemini-2.5-pro:

| Metric | Before (sequential) | After (parallel) |
|--------|---------------------|-------------------|
| Wall time | ~74s (14.8s x 5) | 12.7s |
| Total LLM time | ~74s | 56.69s |
| Concurrency savings | N/A | 43.97s |
| Speedup | baseline | ~4.4x |

Projected for 500 posts:
- Sequential: ~2 hours
- Parallel (10 workers): ~25 minutes

---

## Rollback

Set `CLASSIFICATION_ENABLE_PARALLEL=false` in `.env` to revert to sequential mode instantly.
