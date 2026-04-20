# Trace: Second Query Hang — WebSocketForwardingHandler Deadlock Fix

**Date:** 2026-04-19
**Branch:** `withagentframework`
**Status:** FIXED

---

## Symptom

After a page refresh or reset, the second analysis query hangs. The UI freezes at "submitting" phase. The API call never returns.

**Frontend logs showed:**
```
[Analysis] submit: calling startAnalysis API...
[Page] Phase resolution: {..., analysisPhase: 'submitting', resolved: 'submitting', ...}
```

Then nothing. No response, no WebSocket connection, no progress.

**First query always worked.** Second query always hung. Page refresh made it worse (stale handlers accumulated).

---

## Root Cause: Deadlock in `WebSocketForwardingHandler.emit()`

### The Deadlock Chain

```
Frontend.submit()
  → POST /analysis
    → analysis_service.start_analysis()
      → root_logger.addHandler(ws_handler)        ← Handler added to global root logger
      → Any logger.info() during setup
        → WebSocketForwardingHandler.emit()        ← Triggered by every log line
          → asyncio.run_coroutine_threadsafe(...)  ← Schedules coroutine on event loop
            → future.result(timeout=5.0)           ← BLOCKS HERE FOR 5 SECONDS
              → ws_manager tries to send to WebSocket
                → NO WebSocket yet! (connect() hasn't happened)
                  → Timeout or indefinite block
```

### Why This Deadlocked

**Timeline mismatch — a circular dependency:**

1. API endpoint calls `start_analysis()`
2. `start_analysis()` adds `ws_handler` to the global root logger
3. Any `logger.info()` during setup (directory creation, config, etc.) triggers `emit()`
4. `emit()` calls `future.result(timeout=5.0)` — blocks the calling thread waiting for the WebSocket send to complete
5. But the WebSocket doesn't exist yet — the frontend hasn't received the `run_id` because the API hasn't returned
6. The API can't return until `start_analysis()` completes
7. The frontend can't connect until the API returns the `run_id`
8. **Deadlock.**

### Why the First Query Worked (Sometimes)

On a cold start, there were no stale handlers on the root logger. The `future.result(timeout=5.0)` would timeout after 5 seconds, the log entry would be dropped, and execution would continue. The 5-second penalty per log line was absorbed but noticeable.

### Why the Second Query Hung Completely

After the first query completed, stale `WebSocketForwardingHandler` instances could remain on the root logger (the cleanup in `finally` blocks could be racy). Each stale handler's `emit()` would block for 5 seconds. With multiple stale handlers and multiple log lines during setup, the cumulative blocking could reach 30-60+ seconds, effectively freezing the request.

---

## The Fix

**File:** `backend/app/services/analysis_service.py` (lines 41-70)
**Change:** Made `emit()` non-blocking (fire-and-forget)

### Before (Deadlocking)

```python
def emit(self, record: logging.LogRecord) -> None:
    try:
        msg = self.format(record)
        agent_name = None
        for name in ("orchestrator", "analyst", "hypothesis"):
            if name in record.name or name in msg.lower():
                agent_name = name
                break

        # Thread-safe: schedule the coroutine on the main event loop
        future = asyncio.run_coroutine_threadsafe(
            ws_manager.send_log_entry(
                run_id=self.run_id,
                level=record.levelname,
                message=msg,
                logger_name=record.name,
                agent_name=agent_name,
            ),
            self._loop,
        )
        try:
            future.result(timeout=5.0)                    # ← BLOCKING! DEADLOCK!
        except asyncio.TimeoutError:
            self._error_count += 1
            self._last_error = "WebSocket log forwarding timeout"
            print(f"[WebSocketHandler ERROR] ...", file=sys.stderr)
            logger.warning(f"WebSocket log timeout ...")   # ← Recursive risk!
            return
    except Exception as e:
        self._error_count += 1
        self._last_error = str(e)
        print(f"[WebSocketHandler ERROR] ...", file=sys.stderr)
        logger.warning(f"WebSocket log error ...")         # ← Recursive risk!
```

### After (Fire-and-Forget)

```python
def emit(self, record: logging.LogRecord) -> None:
    try:
        msg = self.format(record)
        agent_name = None
        for name in ("orchestrator", "analyst", "hypothesis"):
            if name in record.name or name in msg.lower():
                agent_name = name
                break

        # Fire-and-forget: schedule the coroutine without blocking.
        # Previously this used future.result(timeout=5.0) which caused a
        # deadlock: emit() blocked waiting for a WebSocket that couldn't
        # connect until the API returned the run_id.
        asyncio.run_coroutine_threadsafe(
            ws_manager.send_log_entry(
                run_id=self.run_id,
                level=record.levelname,
                message=msg,
                logger_name=record.name,
                agent_name=agent_name,
            ),
            self._loop,
        )
        # No future.result() — returns immediately
    except Exception as e:
        self._error_count += 1
        self._last_error = str(e)
        # Use print/stderr only — never logger.warning here, as it would
        # re-trigger emit() on the root logger (infinite recursion).
        print(f"[WebSocketHandler ERROR] {self._last_error} (run_id={self.run_id})", file=sys.stderr)
```

### What Changed Specifically

1. **Removed `future.result(timeout=5.0)`** — the blocking call that caused the deadlock. `asyncio.run_coroutine_threadsafe()` now runs without waiting for the result.
2. **Removed the `try/except asyncio.TimeoutError` inner block** — no longer needed since we don't wait for the result.
3. **Removed `logger.warning()` from error handler** — this was a latent recursion bug. The handler is attached to the root logger; logging from within `emit()` would re-trigger `emit()` on the root logger. Replaced with `print(..., file=sys.stderr)` only.

---

## Why This Is Safe

- **Logging handlers should never block.** Python's logging docs explicitly warn against this. If log forwarding fails, the error is recorded to stderr and execution continues.
- **No loss of functionality.** The WebSocket manager (`ws_manager.send_log_entry`) has its own logic to handle missing connections (it simply drops the message if no WebSocket client is connected for that `run_id`).
- **Graceful degradation.** If the WebSocket is unavailable, log entries are silently dropped. This is acceptable — the real data lives in the pipeline output files on disk. The WebSocket log streaming is a UI convenience, not a data path.
- **The timeline now works correctly:**
  1. API calls `start_analysis()` → adds handler → returns immediately
  2. Frontend receives `run_id` from API response
  3. Frontend opens WebSocket connection with `run_id`
  4. Pipeline runs in thread pool, logs stream via fire-and-forget
  5. WebSocket manager delivers logs to the connected client

---

## Verification

Tested by user:
- First analysis: completes normally, confetti fires
- Reset → second analysis: **works immediately** (no hang)
- Multiple sequential runs (Run → Reset → Run → Reset): all succeed

---

## Lessons

1. **Never block in logging handlers.** `emit()` is called synchronously from whatever thread logs. If `emit()` blocks, it blocks the caller — which could be anything, including the async event loop.
2. **Circular dependencies hide in event-driven systems.** The deadlock wasn't obvious because it crossed the HTTP/WebSocket boundary: API blocked on a WebSocket send that couldn't happen until the API returned.
3. **`future.result()` in a logging handler is almost always wrong.** The `asyncio.run_coroutine_threadsafe()` call is the correct pattern for crossing thread boundaries; waiting on its result negates the benefit and introduces blocking.

---

# Trace: Reset Button Restarts YouTube Video

**Date:** 2026-04-19
**Branch:** `withagentframework`
**Status:** FIXED

---

## Symptom

After a first analysis run, user pauses the YouTube video. Clicking **Reset** starts the video playing again. Expected: reset should have no effect on the video (which is already paused after completion).

---

## Root Cause: React `key` Remounts Video Player on Reset

**File:** `frontend/components/layout/MainLayout.tsx:98`

```tsx
<PipelineVideoPlayer key={runId ?? "idle"} videoIds={PIPELINE_VIDEOS} active={showVideo} />
```

**The chain:**

1. First run starts → `runId` = `"abc123"` → component mounts with key `"abc123"` → video plays
2. Run completes → `active` becomes `false` → existing `useEffect` pauses the video (line 80-87 of PipelineVideoPlayer)
3. User pauses the video manually
4. User clicks **Reset** → `handleReset()` clears `runId` to `null`
5. Key changes from `"abc123"` to `"idle"` → **React destroys and remounts the component**
6. Fresh mount triggers shuffle effect → sets `selectedId` → creates new YouTube player with `autoplay: 1`
7. Video starts playing from scratch

**Why the key was there:** To get a fresh video on each new run. The intent was correct, but the implementation didn't distinguish between "new run started" and "old run cleared."

---

## The Fix

**File:** `frontend/components/layout/MainLayout.tsx`

Use a `useRef` that only updates when a new `runId` appears (truthy), but keeps the old value when `runId` goes to `null` on reset.

### Before

```tsx
<PipelineVideoPlayer key={runId ?? "idle"} videoIds={PIPELINE_VIDEOS} active={showVideo} />
```

### After

```tsx
const videoKeyRef = useRef<string>("idle");
if (runId) {
  videoKeyRef.current = runId;
}

// ...
<PipelineVideoPlayer key={videoKeyRef.current} videoIds={PIPELINE_VIDEOS} active={showVideo} />
```

### What Changed

1. **Added `useRef<string>("idle")`** — stores the last non-null `runId`
2. **Only updates on new run** — `if (runId) { videoKeyRef.current = runId }` only writes when a run is active
3. **On reset** — `runId` becomes `null`, ref stays at old value, key doesn't change, component survives

### Behavioral Matrix

| Action | `runId` | `videoKeyRef.current` | Key changes? | Player |
|--------|---------|----------------------|-------------|--------|
| First run | `null` → `"abc"` | `"idle"` → `"abc"` | Yes | Remounts, autoplays (correct) |
| Complete | `"abc"` | `"abc"` | No | `active=false` pauses it |
| Pause video | `"abc"` | `"abc"` | No | Stays paused |
| Reset | `"abc"` → `null` | stays `"abc"` | No | Stays paused |
| Second run | `null` → `"def"` | `"abc"` → `"def"` | Yes | Remounts, autoplays (correct) |

---

## Files Changed

1. `frontend/components/layout/MainLayout.tsx`
   - Added `useRef` import
   - Added `videoKeyRef` ref that only updates on new `runId`
   - Changed `key={runId ?? "idle"}` to `key={videoKeyRef.current}`

2. `frontend/components/ChatInterface.tsx` (related, same session)
   - Made reset button always visible (not just after completion)
   - Moved reset inline with submit button
   - Added `disabled={isRunning}` to prevent interrupting active pipeline

---

## Why This Is Safe

- **No change to reset logic** — only affects when the video player React key changes
- **No change to video pause/resume** — the existing `active` prop effect still works
- **One-directional ref update** — only writes on truthy `runId`, never resets back to `"idle"`
- **No race conditions** — `useRef` updates synchronously during render, before effects run

---

## Lessons

1. **React `key` is a remount trigger, not just an identifier.** Any value change destroys and recreates the component. Using a value that changes on *both* mount and unmount (like `runId ?? "idle"`) causes unintended remounts.
2. **Use refs to "latch" values** when you want one-directional transitions (null→value but not value→null). `useRef` preserves the last "interesting" value across renders without causing re-renders.
