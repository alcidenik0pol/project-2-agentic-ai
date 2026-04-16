# Trace: UI Freeze After Report Completion

**Date:** 2026-04-16
**Trigger:** Input field and button disabled for a noticeable period after analysis completed successfully.

---

## Problem

In `frontend/app/page.tsx:39-43`, the combined phase logic checked `analysisPhase === "running"` before `wsPhase === "completed"`:

```tsx
// Before (buggy order)
const phase: AnalysisPhase =
  wsPhase === "running" || analysisPhase === "running" ? "running" :
  wsPhase === "completed" ? "completed" :
  wsPhase === "failed" ? "failed" :
  analysisPhase;
```

This created a race condition:

1. WebSocket completes → `wsPhase` becomes `"completed"` → `fetchResults()` is called (async)
2. During the fetch: `analysisPhase` is still `"running"` → combined phase = `"running"` → **input disabled**
3. After fetch completes: `analysisPhase` becomes `"completed"` → combined phase = `"completed"` → **input enabled**

The `|| analysisPhase === "running"` check in the first condition caused the combined phase to stay `"running"` even when `wsPhase === "completed"`, until `fetchResults()` finished and updated `analysisPhase`.

---

## Fix

Reordered the ternary chain so `wsPhase` completion/failure states take priority over `analysisPhase` running:

```tsx
// After (fixed order)
const phase: AnalysisPhase =
  wsPhase === "completed" ? "completed" :
  wsPhase === "failed" ? "failed" :
  wsPhase === "running" || analysisPhase === "running" ? "running" :
  analysisPhase;
```

Priority is now:
1. **`wsPhase === "completed"`** → input enabled immediately when WebSocket reports done
2. **`wsPhase === "failed"`** → input enabled on error too
3. **`wsPhase || analysisPhase === "running"`** → input disabled during active analysis
4. Falls back to `analysisPhase` for initial/idle states

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/app/page.tsx:40-44` | Reordered combined phase ternary to prioritize wsPhase completion |

---

## Why This Matters

When `fetchResults()` is slow (large report, network latency), the old code kept the UI frozen for the entire duration of the fetch. Users couldn't type a new query or interact with the input during that window. The fix decouples UI responsiveness from the async fetch timing.
