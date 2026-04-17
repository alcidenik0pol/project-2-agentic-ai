# Trace: Opportunities Tab Persistence Fix

**Date:** 2026-04-17
**Trigger:** After report completion, Classification EDA and Clustering Results tabs persisted correctly, but the Opportunities tab showed "No gold spotted. Try panning a different industry."

---

## Problem

Architectural asymmetry in how the three result tabs received their data:

| Tab | Data Source | Storage | Cleared on Submit | Restored After Complete |
|-----|-------------|---------|-------------------|------------------------|
| Classification EDA | WebSocket `intermediary_result` | `WebSocketContext` | Yes | **Yes** (auto-streamed) |
| Clustering Results | WebSocket `intermediary_result` | `WebSocketContext` | Yes | **Yes** (auto-streamed) |
| Opportunities | REST API `/api/v1/results/{run_id}` | `AnalysisContext` | Yes | **No** (required manual fetch) |

### The race condition

1. User submits query → `handleSubmit()` calls `resetWs()` and `submit()` → both contexts clear hypothesis
2. Pipeline runs → analyst completes → EDA data streamed via WebSocket → EDA tabs populate
3. Pipeline completes → `wsPhase` becomes `"completed"` → `fetchResults()` called via REST API
4. REST endpoint reads `hypothesis.json` from disk → but if timing is off or file doesn't exist yet → returns `null`
5. `AnalysisContext.hypothesis` stays `null` → Opportunities tab shows "No gold spotted"

The EDA tabs worked because the backend proactively pushes data through the WebSocket. The Opportunities tab relied on a pull (REST fetch) that could fail or race.

---

## Fix

Made all three tabs architecturally consistent by streaming hypothesis data via WebSocket, same as EDA results.

### Backend: Stream hypothesis after hypothesis agent completes

In `on_agent_completed` callback (`analysis_service.py`), added a new block for `agent_name == "hypothesis"`:

```python
if agent_name == "hypothesis" and run.run_dir:
    hypothesis_path = run.run_dir / "hypothesis.json"
    if hypothesis_path.exists():
        hypothesis_data = json.loads(hypothesis_path.read_text(encoding="utf-8"))
        asyncio.run_coroutine_threadsafe(
            ws_manager.send_intermediary_result(
                run_id=run.run_id,
                result_type="hypothesis",
                data=hypothesis_data,
            ),
            run._loop,
        )
```

This mirrors the existing EDA streaming block for the analyst agent (lines 253-273).

### Frontend: Receive hypothesis via WebSocket

Extended the existing `intermediary_result` handler in `WebSocketContext` to handle a third `result_type`:

```typescript
result_type: "classification_eda" | "clustering_eda" | "hypothesis"
```

Added `hypothesis` state to `WebSocketContext`, cleared on `connect()` and `reset()`.

### Frontend: Switch page.tsx data source

Moved `hypothesis` from `useAnalysis()` (REST-based) to `useGlobalWebSocket()` (WebSocket-based). The `fetchResults()` call in `AnalysisContext` still runs for `reportContent`, but hypothesis data now comes through the same streaming channel as EDA.

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/services/analysis_service.py:275-291` | Added hypothesis streaming in `on_agent_completed` callback |
| `frontend/contexts/WebSocketContext.tsx` | Added `hypothesis` state, interface field, handler branch, reset/clear, provider value |
| `frontend/app/page.tsx` | Moved `hypothesis` from `useAnalysis()` to `useGlobalWebSocket()` |

---

## Architecture (After Fix)

```
Pipeline runs in thread pool:
  orchestrator → analyst → hypothesis
                    │          │
                    ▼          ▼
      on_agent_completed     on_agent_completed
        ("analyst")            ("hypothesis")
          │                        │
          ├── classification_eda   ├── hypothesis.json
          ├── clustering_eda       │
          └── stream via WS ───────┤
                                  └── stream via WS
                                        │
                                        ▼
                                WebSocketContext
                                  ├── classificationEDA
                                  ├── clusteringEDA
                                  └── hypothesis  ← NEW
                                        │
                                TabbedResultsDisplay
                                  ├── Tab: Classification EDA
                                  ├── Tab: Clustering Results
                                  └── Tab: Opportunities  ← now works
```

---

## What Was Not Changed

- `AnalysisContext.tsx` — kept its `hypothesis` state and `fetchResults()` for backward compatibility (report content still needs REST fetch)
- `TabbedResultsDisplay.tsx` — no changes; already accepts `hypothesis` as a prop
- `useGlobalWebSocket.ts` — no changes; simple passthrough hook that now automatically exposes the new `hypothesis` field
- No new REST endpoints, no new npm dependencies
