# Trace: State Synchronization & WebSocket Lifecycle Fixes

**Date:** 2026-04-19
**Context:** Multi-agent Reddit analysis app with real-time WebSocket updates

---

## Original Problem Statement

User reported multiple bugs after initial implementation:
1. "Analysis complete" banner disappears
2. "Pan It" button shows "Stop" after completion
3. UI freezes on second run after page refresh
4. Page refresh persistence causes state conflicts
5. WebSocket disconnects on second run

Console showed: `"[WebSocket] Connection closed — replaced by new connection, ignoring"`

---

## Phase 1: Initial State Synchronization Fixes

### Fix 1.1: Removed sessionStorage Restoration from AnalysisContext

**Problem:** `AnalysisContext.tsx` had sessionStorage restoration on mount that would set `phase="completed"` for old runs, conflicting with new submissions.

**Change:** Removed the entire `useEffect` restoration block (lines 84-111), kept only cleanup on mount.

**File:** `frontend/contexts/AnalysisContext.tsx`

```typescript
// REMOVED: sessionStorage restoration useEffect
// KEPT: Cleanup on mount
useEffect(() => {
    sessionStorage.removeItem(RUN_ID_STORAGE_KEY);
    sessionStorage.removeItem(REPORT_CONTENT_STORAGE_KEY);
}, []);
```

### Fix 1.2: Simplified Phase Combination Logic

**Problem:** Combined phase logic prioritized `wsPhase === "completed"` which prevented proper state transitions during second runs.

**Change:** Reordered priority to give `wsPhase === "running"` first priority.

**File:** `frontend/app/page.tsx`

```typescript
const phase: AnalysisPhase =
  wsPhase === "running" ? "running" :
  wsPhase === "completed" ? "completed" :
  wsPhase === "failed" ? "failed" :
  wsPhase === "idle" ? analysisPhase :
  analysisPhase;
```

### Fix 1.3: Fixed hasFetched Reset Logic

**Problem:** `hasFetched` only reset when `wsPhase === "idle"`, but `wsPhase` stays "completed" forever after completion.

**Change:** Added reset when `wsPhase === "running"` to handle new runs.

**File:** `frontend/app/page.tsx`

```typescript
if (wsPhase === "completed" && !hasFetched && runId) {
    setHasFetched(true);
    fetchResults();
}
// Reset hasFetched when starting a new run
if (wsPhase === "running" && hasFetched) {
    setHasFetched(false);
}
// Also reset when wsPhase becomes "idle" (cancelled)
if (wsPhase === "idle" && hasFetched) {
    setHasFetched(false);
}
```

### Fix 1.4: Removed WebSocket Close from analysis_cancelled Handler

**Problem:** `analysis_cancelled` handler was closing the WS immediately, causing race conditions.

**Change:** Removed WS close logic, let lifecycle handle cleanup on next run.

**File:** `frontend/contexts/WebSocketContext.tsx`

```typescript
case "analysis_cancelled": {
    const data = message.data as { message: string };
    setConnectionStatus("disconnected");
    setError(data.message);
    setPhase("idle");
    setProgressPercent(0);
    setCurrentActivity("Cancelled");
    // Don't close WS here - let the natural lifecycle handle it
    // The WS will be closed/reset when user starts a new run
    break;
}
```

---

## Phase 2: Second Run Failure Fix

### Problem: "No new analysis happens" on second run

**Symptoms:**
- Button not frozen (improvement from first fix)
- But no progress bar, no analysis, no updates
- Console only shows: `"[WebSocket] Connection closed — replaced by new connection, ignoring"`

### Root Cause Analysis

The old flow was:
```
handleSubmit:
  1. resetWs() → closes WS, sets clientRef = null
  2. resetAnalysis() → resets analysis state
  3. await 100ms delay → React processes batch, phase = "idle"
  4. submit() → POST request
  5. connect(id) → create new WS
```

**The issue:** `resetWs()` destroyed the old WebSocket connection in a separate step, creating a gap where no WS existed. The 100ms delay made it worse by forcing React to process the intermediate "idle" state, causing:
- Stale auto-fetch effects to trigger
- Race conditions with backend's disconnect handling
- The old WS close handshake to overlap with new WS creation

### Solution: Atomic WebSocket Transition

**Key insight:** `connect()` already had logic to atomically close old connection and create new one. The fix was to avoid prematurely destroying the old connection.

#### Added `prepareNewRun()` to WebSocketContext

**File:** `frontend/contexts/WebSocketContext.tsx`

```typescript
const prepareNewRun = useCallback(() => {
    // Reset all WS UI state for a new run WITHOUT closing the connection.
    // connect() will atomically close the old WS and create a new one.
    setRunId(null);
    setPhase("idle");
    setAgents(INITIAL_AGENTS);
    setLogs([]);
    setRateLimit(null);
    setError(null);
    setFinalResponse(null);
    setCurrentActivity(null);
    setProgressPercent(0);
    setClassificationEDA(null);
    setClusteringEDA(null);
    setHypothesis(null);
    setAgentProgress(null);
    setElapsed(0);
    setElapsedStartTime(null);
}, []);
```

#### Updated handleSubmit in page.tsx

**File:** `frontend/app/page.tsx`

```typescript
const handleSubmit = useCallback(async (query: string, mode: "test" | "live") => {
    setHasFetched(false);
    setLastQuery(query);
    setHasFlashed({});

    // Reset UI state for a new run without closing the WS.
    // connect() will atomically close old WS and create new one.
    prepareNewRun();
    resetAnalysis();

    const id = await submit(query, mode);
    if (!id) return;
    connect(id);
}, [submit, connect, prepareNewRun, resetAnalysis]);
```

#### Updated Combined Phase Logic

**File:** `frontend/app/page.tsx`

```typescript
// Combined phase: wsPhase is the real-time source of truth for running/completed/failed.
// analysisPhase "submitting" takes priority over stale wsPhase "completed" so the
// UI immediately reflects a new submission even before the WS reconnects.
const phase: AnalysisPhase =
    wsPhase === "running" ? "running" :
    wsPhase === "failed" ? "failed" :
    analysisPhase === "submitting" ? "submitting" :
    wsPhase === "completed" ? "completed" :
    analysisPhase;
```

**Why this matters:** When starting a second run, `wsPhase` is still "completed" from the first run. Without the `analysisPhase === "submitting"` check, the phase would stay "completed" until the new WS connects, causing poor UX.

---

## Phase 3: WebSocket Lifecycle Exploration

User suggested implementing a ping/pong keep-alive system, concerned that "the websocket disconnecting because the button Stop closes it right?"

### Findings from Exploration

**The Stop button does NOT close the WebSocket.** Current flow:

1. User clicks Stop
2. Frontend sends `cancel_analysis` message via WS
3. Backend cancels the running task
4. Backend sends `analysis_cancelled` message back
5. Frontend transitions to "idle" state but **WS stays alive**
6. WS only closes when starting a new run (via `connect()` which marks old as replaced)

### Current Reconnection Logic

**File:** `frontend/lib/websocket.ts`

- Reconnects automatically if: unintentional close AND attempts < 5
- Reconnect delay: 2000ms
- Max attempts: 5
- Does NOT reconnect if: `intentionalClose = true` OR connection was replaced

**No existing ping/pong mechanism.** The implementation relies solely on application-level messages.

### Potential Issues Identified

1. **No keep-alive:** Long-running connections might be dropped by intermediaries (proxies, load balancers, NATs)
2. **No dead connection detection:** If the socket is "zombie" (connected but not working), no automatic recovery
3. **No heartbeat:** No way to detect if the backend is still alive during idle periods

---

## Discussion: Ping/Pong Proposal

**User's idea:** Implement a ping system to keep WebSocket alive, plus a state reset mechanism on top.

**Potential benefits:**
- Keep connections alive through proxies/load balancers
- Detect zombie connections early
- Automatic recovery from transient network issues

**Considerations:**
- Adds complexity to both frontend and backend
- Backend needs to handle ping messages and send pongs
- Frontend needs to track last pong time and trigger reconnect if no response
- Interval selection: too frequent = unnecessary load, too sparse = slow detection
- Common practice: 30-60 second heartbeat interval

**Not implemented yet** - awaiting user confirmation on requirements and priority.

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/contexts/AnalysisContext.tsx` | Removed sessionStorage restoration, simplified to cleanup-only |
| `frontend/contexts/WebSocketContext.tsx` | Removed WS close from analysis_cancelled handler, added prepareNewRun() |
| `frontend/app/page.tsx` | Fixed phase combination logic, fixed hasFetched reset, updated handleSubmit to use prepareNewRun(), removed 100ms delay |

---

## Verification Status

**Implemented:** All Phase 1 and Phase 2 fixes completed and type-checked.

**Pending:** Ping/pong system implementation (Phase 3) - awaiting user decision on whether to proceed.

**Testing needed:**
1. Full completion flow (first run)
2. STOP button test (mid-run cancellation)
3. New run after cancel
4. Page refresh test
5. Second run after page refresh
6. Multiple sequential runs
7. Multiple cancel cycles
