# Trace: ZIP Download for All Output Files

**Date:** 2026-04-17
**Trigger:** User requested the "Download Report" button download a ZIP archive of ALL output files (8 files) instead of just report.md. After initial implementation, user reported 404 error — runs were lost from in-memory store after backend restart.

---

## Problem

### 1. Download only gave a single file

The existing download button served only `report.md`. Users needed all pipeline artifacts: agent traces, EDA data, hypothesis, reports, and metadata.

### 2. 404 on download after backend restart

Runs are stored in-memory via `analysis_service._runs` dict. Backend restart = all runs gone. The download endpoint called `analysis_service.get_run(run_id)` which returned `None` for any run not in the current process's memory.

Old runs (before metadata.json persistence was added) had no on-disk mapping from `run_id` to directory, making them unrecoverable.

---

## Fix

### Part A: ZIP endpoint

**File: `backend/app/api/routes/results.py`**

Added `GET /{run_id}/zip` endpoint that:

1. Tries in-memory lookup first (fast path for active runs)
2. Falls back to disk scan via `_find_run_dir()` — searches `output/reports/*/*/metadata.json` files for matching `run_id`
3. Creates in-memory ZIP with all 8 expected output files
4. Includes a `README.txt` listing any missing files
5. Returns `StreamingResponse` with sanitized filename: `{query}_analysis_{timestamp}.zip`

Also added:
- `_sanitize_filename()` — replaces unsafe chars, limits length to 50 chars
- `_find_run_dir()` — scans output directories for metadata.json matching run_id
- `EXPECTED_OUTPUT_FILES` constant listing the 7 named files (+ agent_run_*.jsonl via glob)

### Part B: Frontend button update

**File: `frontend/lib/api.ts`**

- Added `getZipUrl(runId)` export function

**File: `frontend/components/TabbedResultsDisplay.tsx`**

- Changed import from `getFileUrl` to `getZipUrl`
- Changed `onClick` to call `window.open(getZipUrl(runId), "_blank")`
- Updated button label from "Download Report" to "Download ZIP"

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/api/routes/results.py` | Added ZIP endpoint, `_find_run_dir()`, `_sanitize_filename()`, new imports |
| `frontend/lib/api.ts` | Added `getZipUrl()` export |
| `frontend/components/TabbedResultsDisplay.tsx` | Changed button to download ZIP instead of report.md |

---

## Files Included in ZIP

| File | Source |
|------|--------|
| `agent_run.jsonl` | Glob for `agent_run_*.jsonl` in run dir |
| `subreddit_selection.json` | Expected output file |
| `fetch_stats.json` | Expected output file |
| `classification_eda.json` | Expected output file |
| `clustering_eda.json` | Expected output file |
| `hypothesis.json` | Expected output file |
| `report.md` | Expected output file |
| `workflow_report.md` | Expected output file |
| `README.txt` | Generated if any files are missing |

---

## Limitations

- **Old runs without metadata.json**: Cannot be downloaded after backend restart. The `_find_run_dir()` scan requires `metadata.json` to map `run_id` to directory. Runs created before the metadata persistence feature (pre 2026-04-16) are affected.
- **New runs** (with metadata.json written on creation) survive backend restarts.

---

## Why This Matters

Users get a complete archive of all pipeline artifacts in one click. The disk-based fallback ensures downloads work even after backend restarts, as long as the run directory and metadata.json exist on disk.
