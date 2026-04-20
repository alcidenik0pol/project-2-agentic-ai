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
