# Trace: Download Button 404 Bug — Frontend + Backend Persistence

**Date:** 2026-04-16
**Trigger:** Download button returned `{"detail":"Run 2392ed736efa not found"}` after page refresh and after backend restart.

---

## Problem

Two distinct bugs caused the download button to 404:

### Bug 1: Frontend State Desync (immediate cause)

`page.tsx` passes `WebSocketContext.runId` to `TabbedResultsDisplay` for the download button. After a page refresh:

- **`AnalysisContext`** — restores `runId` from `sessionStorage` on mount (already implemented)
- **`WebSocketContext`** — does NOT restore `runId`; it stays `null`

The download button calls the API with a `null` runId, producing a 404.

### Bug 2: Backend In-Memory Storage (fundamental cause)

`AnalysisService._runs` is an in-memory dictionary (`analysis_service.py:103`). After a backend restart:

- Report files still exist on disk (`output/reports/YYYY-MM-DD/HHMMSS_mode/`)
- Run metadata (`run_id`, `query`, `mode`) is gone
- The `/api/v1/results/{run_id}/file/report.md` endpoint looks up the run in `_runs`, can't find it, returns 404

---

## Fix

### Part A: Frontend — sessionStorage persistence for WebSocketContext

Mirrored the existing `AnalysisContext` pattern in `WebSocketContext`.

**File: `frontend/contexts/WebSocketContext.tsx`**

- Added `WS_RUN_ID_STORAGE_KEY` constant (`"ws_run_id"`)
- New mount `useEffect` — reads `runId` from `sessionStorage`. If found, restores `runId`, sets `phase` to `"completed"`, sets `progressPercent` to `100`
- `connect()` — saves `runId` to `sessionStorage` when a new analysis starts
- `reset()` — removes `runId` from `sessionStorage` so stale data doesn't linger

### Part B: Backend — metadata.json + disk restoration

**File: `backend/app/services/analysis_service.py`**

- `start_analysis()` — writes `metadata.json` alongside the report in each run directory, containing `run_id`, `query`, `mode`, `created_at`
- New `restore_runs_from_disk()` method — scans `output/reports/` tree, reads `metadata.json` files, reconstructs `AnalysisRun` objects into `_runs` dict with status `"completed"`

**File: `backend/app/main.py`**

- `lifespan()` startup — calls `analysis_service.restore_runs_from_disk()`, prints count to console

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/contexts/WebSocketContext.tsx:88-98` | Added sessionStorage restore on mount |
| `frontend/contexts/WebSocketContext.tsx:224` | `connect()` saves runId to sessionStorage |
| `frontend/contexts/WebSocketContext.tsx:263` | `reset()` clears sessionStorage |
| `backend/app/services/analysis_service.py:133-141` | `start_analysis()` writes metadata.json |
| `backend/app/services/analysis_service.py:334-379` | New `restore_runs_from_disk()` method |
| `backend/app/main.py:45-49` | Startup hook calls restoration |

---

## Edge Cases

| Case | Behavior |
|------|----------|
| Missing `metadata.json` in run dir | Skipped silently |
| Corrupted `metadata.json` | Logged as warning, skipped |
| Run already in memory | Skipped (no overwrite) |
| Empty or missing `output/reports/` | Returns 0, no error |
| Old directories without metadata | Silently skipped |
| `reset()` called | Clears sessionStorage, no stale restore on next mount |

---

## Why This Matters

The download button was the only user-visible artifact export. Without these fixes, any page refresh or backend restart permanently broke the download for that run — even though the report file sat intact on disk. The fix ensures run metadata survives both frontend navigation and backend restarts with minimal overhead (one JSON file per run, one directory scan on startup).
