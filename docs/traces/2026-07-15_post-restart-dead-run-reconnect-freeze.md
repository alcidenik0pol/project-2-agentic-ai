# Trace: Post-Restart Dead-Run Reconnect Freeze

**Date:** 2026-07-15
**Status:** Done (automated); live end-to-end verification pending

---

## Problem

Restart the backend → reload the page → the app freezes at **"Connected to server, starting pipeline..."**. Stop does nothing. Reset is disabled. App is bricked until the user manually clears localStorage.

The two buttons looked like suspects but were innocent:

- **Stop** = mid-run safeword. Shows only while `phase === "running"`. Already verified working: fetch loop halts in ~3s, `analysis_cancelled` sent, UI → idle.
- **Reset** = post-run cleanup so you can run again. Shows only when NOT running. `disabled={isRunning}` is correct — you don't clean up while it's still going.

Neither was broken. Both were **held hostage by a dead run the frontend believed was still live.**

### Root cause — two pieces, both required

1. **`WebSocketContext.tsx:392-409`** recovers `run_id` + `phase="running"` from localStorage on mount (15-min window) and reconnects to that `run_id`.
2. **`backend/app/main.py`** WS endpoint called `ws_manager.connect()` (`manager.py:67`), which accepts the socket and sends a `"connected"` frame — **even when the run no longer exists** (server restarted → run gone from `analysis_service._runs`). The frontend then set `phase="running"` + `activity="Connected to server, starting pipeline..."` and waited. Nothing ever came. Stop sent `cancel_analysis` for a dead run → `cancel_run` found no task → returned False → **no `analysis_cancelled` ever sent** → permanent freeze. Reset stayed disabled because `isRunning` was true.

A previous session had already applied a version of the dead-run check **after** `ws_manager.connect()`. It worked, but the "connected" frame had already gone out, so the user saw one frame of frozen text before the cancel arrived.

---

## Fix

### Fix A — backend rejects dead runs BEFORE sending "connected"

**`backend/app/main.py:160-188`** — reordered the dead-run check to run **before** `ws_manager.connect(run_id, websocket)`:

```python
from backend.app.services.analysis_service import analysis_service
run = analysis_service.get_run(run_id)
if run is None or run.status != "running":
    logger.info(
        f"[WebSocket] run_id={run_id} not active "
        f"(found={run is not None}, status={getattr(run, 'status', None)}); "
        f"notifying client to reset"
    )
    await websocket.accept()
    await websocket.send_json({
        "type": "analysis_cancelled",
        "data": {
            "message": "This run is no longer active (the server may have "
                       "restarted). Please submit again.",
        },
    })
    await websocket.close()
    return

try:
    await ws_manager.connect(run_id, websocket)
    ...
```

Two subtleties:

- **`run.status != "running"` (not just `run is None`).** `restore_runs_from_disk` repopulates completed/failed runs into `_runs` on startup. Those have no live task either, so they'd freeze the same way. "Actively running right now" is the only state worth reconnecting to.
- **Bypass `ws_manager` on the dead path.** `manager._send()` routes through `self._connections[run_id]`, which is only populated by `ws_manager.connect()`. If we called `ws_manager.send_cancelled()` before `connect()`, the message would be **buffered** (manager.py:138-144), not delivered — and then we'd close the socket without ever flushing the buffer. So we `accept()` + `send_json()` directly on the websocket, then `close()`. No `disconnect()` needed because we never registered.

### Fix B — frontend clears stale recovery state on cancel (DEVIATION from plan)

**`frontend/contexts/WebSocketContext.tsx:198-216`** — added localStorage cleanup inline in the `analysis_cancelled` handler:

```typescript
case "analysis_cancelled": {
    ...
    updatePhase("idle");
    setProgressPercent(0);
    setCurrentActivity("Cancelled");
    // Clear persisted run so a page reload doesn't try to recover this
    // dead/cancelled run and dead-reconnect again. Mirrors the cleanup
    // in reset(). Done inline (rather than in the persistence effect)
    // because that effect fires on mount with phase="idle" and would
    // wipe a legitimately recoverable run before the recovery effect
    // gets to read it.
    localStorage.removeItem("analysis_run_id");
    localStorage.removeItem("analysis_phase");
    localStorage.removeItem("analysis_timestamp");
    break;
}
```

**The plan said to add `"idle"` to the removal branch of the persistence `useEffect` (`WebSocketContext.tsx:379-389`). I did not do that — it has a mount-order race that would break recovery entirely.** Details in the next section.

The persistence `useEffect` itself is **unchanged**. It still persists on `running` and clears on `completed`/`failed`.

---

## Pattern: Cleanup Effects That Match the Initial State Will Wipe Boot Data

The plan's Fix B ("add `idle` to the removal branch") looked safe — its own note argued "the only time we set `phase="running"` is when we want to persist... `prepareNewRun`'s transient idle flip has nothing meaningful to clear." That covers post-mount transitions but **misses the initial mount fire**.

React runs `useEffect` callbacks top-to-bottom after commit. In `WebSocketContext`:

```
useEffect(persistence)   // line 379  — declares write/clear logic
useEffect(recovery)      // line 392  — reads localStorage on mount
```

On initial mount, `phase="idle"` and `runId=null`. With the plan's literal edit, the persistence effect would match the new `"idle"` branch on its very first run and **wipe `analysis_run_id` before the recovery effect below it got to read it**. Result: not just the dead-run edge case, but **every** legitimate reload-mid-run would silently fail to recover.

The rule: **a cleanup effect whose predicate matches the component's initial state is a footgun.** It will fire on mount and clobber anything a later-reading effect expected to find. Two safe formulations:

1. **Inline the cleanup in the handler** that transitions *to* the clearing state (what I did here — mirrors the existing `reset()` pattern at `WebSocketContext.tsx:463-465`).
2. **Guard the effect with a `hasMountedRef`** that skips the first invocation.

(1) was the smaller diff and matched an existing pattern, so I took it. The cost is a three-line DRY echo of `reset()`'s cleanup — acceptable because the trigger contexts differ (one is a WS message, one is a button click) and extracting a helper would be over-engineering for three one-liners.

---

## Rejected Alternatives

- **Make Reset always clickable (drop `disabled={isRunning}`).** Rejected: turns Reset into a second Stop and breaks the clean two-button model (Stop = mid-run halt, Reset = post-run cleanup). The original "make Reset always clickable" idea was reverted before commit.
- **Frontend "no `agent_started` in N seconds → bail" watchdog.** Rejected: the backend dead-run check is deterministic and runs on the first frame. A timeout adds false-positive risk during legitimately slow LLM starts — this session saw 44–65s Gemini calls, well within plausible start latency. A watchdog tuned to avoid those would have to be ~90s+, which is a worse UX than the deterministic fix.

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/main.py` | Reordered dead-run check to before `ws_manager.connect()`; dead path now `accept()` → `send_json()` directly on socket → `close()` (~12 lines net) |
| `frontend/contexts/WebSocketContext.tsx` | `analysis_cancelled` handler clears localStorage inline (3 `removeItem` calls + comment) |

**Explicitly NOT touched:** `frontend/components/ChatInterface.tsx` (Stop + Reset enablement is correct per the two-button model).

---

## Verification

1. **`pytest app/tests/test_cancel_flag.py -q`** → **8/8 passed** (0.65s). No regressions in the cancel-flag suite.
2. **`npx tsc --noEmit`** (frontend) → clean, no type errors.
3. **Live end-to-end (pending — needs running backend + browser):**
   1. Restart backend. **Do not clear localStorage** — reproduce the user's exact scenario.
   2. Reload `http://localhost:3456`. Expect: ≤1s flash → returns to idle, no permanent freeze, no stuck "Connected to server, starting pipeline...". Backend log shows `run_id=... not active (...); notifying client to reset`.
   3. Reload again → should go straight to idle (Fix B cleared localStorage on the first cancel), no reconnect flicker.
   4. Submit a fresh `reddit_v2` run → works normally; mid-run Stop halts in ~3s (already verified earlier this session).
   5. After complete/cancel → Reset is enabled and clears state → can run again.

---

## Related Traces

- **`2026-04-19_websocket-lifecycle-fixes.md`** — same `WebSocketContext.tsx`, same `analysis_cancelled` handler, same "prepareNewRun / atomic WS transition" machinery. That trace established the two-button model and the no-close-on-cancel rule this fix builds on.
- **`2026-04-16_ui-freeze-after-completion-fix.md`** — earlier UI freeze with a different root cause (post-completion state); useful contrast for "freeze" symptoms that trace to different layers.
