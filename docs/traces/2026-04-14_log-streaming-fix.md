# Trace: Real-Time Log Streaming from Backend to Frontend

**Date:** 2026-04-14
**Status:** Fixed and working

---

## The Bug

Logs from the multi-agent pipeline were invisible in the frontend LogViewer. The pipeline ran correctly, but the frontend showed zero log entries.

### Root Cause

`app/agents/logging_setup.py:107` called `root_logger.handlers.clear()`, which removed **all** handlers from the root logger -- including the `WebSocketForwardingHandler` that was added moments earlier by `AnalysisService.start_analysis()`.

### Buggy Flow

```
1. start_analysis() adds WebSocketForwardingHandler to root logger      <-- handler added
2. _run_in_thread() spawns thread pool executor
3. _execute_pipeline() calls setup_agent_logging()
4. setup_agent_logging() calls root_logger.handlers.clear()             <-- handler removed!
5. All subsequent logger.info() calls go to console + file only
6. WebSocketForwardingHandler is gone -> logs never reach frontend
```

---

## The Fix

### Three files changed

#### 1. `app/agents/logging_setup.py` -- Core fix

Added `preserve_handlers` parameter. Instead of `handlers.clear()`, we keep specified handlers.

```python
# BEFORE (broken):
def setup_agent_logging(log_dir: str | None = None) -> AgentEventLogger:
    root_logger.handlers.clear()  # kills WebSocket handler

# AFTER (fixed):
def setup_agent_logging(
    log_dir: str | None = None,
    preserve_handlers: list[logging.Handler] | None = None,
) -> AgentEventLogger:
    preserve = set(preserve_handlers or [])
    root_logger.handlers = [h for h in root_logger.handlers if h in preserve]
```

Backward compatible: CLI usage passes no `preserve_handlers`, so all handlers still get cleared (same behavior as before).

#### 2. `backend/app/services/analysis_service.py` -- Two changes

**a) Preserve the WebSocket handler when calling setup_agent_logging:**

```python
# _execute_pipeline() -- BEFORE:
setup_agent_logging(log_dir=str(run.run_dir))

# _execute_pipeline() -- AFTER:
handlers_to_preserve = [run.ws_handler] if run.ws_handler else []
setup_agent_logging(
    log_dir=str(run.run_dir),
    preserve_handlers=handlers_to_preserve,
)
```

**b) Error visibility in WebSocketForwardingHandler.emit():**

```python
# BEFORE:
except Exception:
    pass  # silent failure

# AFTER:
except Exception as e:
    self._error_count += 1
    self._last_error = str(e)
    print(f"[WebSocketHandler ERROR] {self._last_error} (run_id={self.run_id})", file=sys.stderr)
```

Also added `future.result(timeout=1.0)` to catch async exceptions synchronously instead of fire-and-forget.

**c) Call mark_run_complete in the finally block:**

```python
finally:
    if run.ws_handler:
        root_logger = logging.getLogger()
        root_logger.removeHandler(run.ws_handler)
        run.ws_handler = None
    await ws_manager.mark_run_complete(run.run_id)
```

#### 3. `backend/app/api/websocket/manager.py` -- Buffer expiry

Added `mark_run_complete()` to keep buffered messages alive for 5 minutes after a run finishes, so late-connecting clients can still see the logs.

```python
async def mark_run_complete(self, run_id: str) -> None:
    import time
    self._buffer_expiry[run_id] = time.time() + 300  # 5 minutes
```

---

## Full Architecture: How Log Streaming Works

### Port Map

| Component | Port | Protocol | URL |
|-----------|------|----------|-----|
| Backend (FastAPI/uvicorn) | **8901** | HTTP | `http://localhost:8901` |
| Backend WebSocket | **8901** | WS | `ws://127.0.0.1:8901/ws/{run_id}` |
| Frontend (Next.js dev) | **3456** | HTTP | `http://localhost:3456` |
| Next.js rewrite proxy | **3456** | HTTP | `/api/*` -> `http://127.0.0.1:8901/api/*` |

### Config Files & Where Ports Are Defined

**Backend port 8901:**
- Started via: `uvicorn backend.app.main:app --reload --port 8901`
- Dockerfile: `EXPOSE 8901`, CMD uses `--port 8901`
- docker-compose.yml: `ports: ["8901:8901"]`
- Startup banner in `backend/app/main.py`: prints `http://localhost:8901`

**Frontend port 3456:**
- `frontend/package.json`: `"dev": "next dev --port 3456"`
- `frontend/Dockerfile`: `EXPOSE 3456`
- docker-compose.yml: `ports: ["3456:3456"]`

**CORS (backend allows frontend):**
- `backend/app/main.py`:
  ```python
  allow_origins=[
      "http://localhost:3456",
      "http://127.0.0.1:3456",
      "http://localhost:3000",
      "http://127.0.0.1:3000",
  ]
  ```

**Frontend -> Backend URL:**
- `frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8901`
- `frontend/lib/api.ts`: `API_BASE = process.env.NEXT_PUBLIC_API_URL`
- `frontend/next.config.js`: rewrites `/api/:path*` -> `http://127.0.0.1:8901/api/:path*` (fallback proxy, not used when env var is set)

**WebSocket URL construction:**
- `frontend/lib/api.ts`:
  ```typescript
  export function getWebSocketUrl(runId: string): string {
    const base = API_BASE.replace(/^http/, "ws");
    return `${base}/ws/${runId}`;
  }
  ```
- Resolves to: `ws://127.0.0.1:8901/ws/{run_id}`

---

### End-to-End Data Flow (After Fix)

```
USER CLICKS "Analyze" on frontend (port 3456)
    |
    v
POST /api/v1/analysis  ->  http://127.0.0.1:8901/api/v1/analysis
    |                       (direct, via NEXT_PUBLIC_API_URL)
    v
Backend AnalysisService.create_run()
    |   generates run_id (12-char hex, e.g. "a3f2b8c1e904")
    |
    v
AnalysisService.start_analysis()
    |   1. Creates output directory: output/reports/YYYY-MM-DD/HHMMSS_{mode}/
    |   2. Captures asyncio event loop reference
    |   3. Creates WebSocketForwardingHandler(run_id, loop)
    |   4. Adds it to Python's root logger
    |   5. Launches _run_in_thread() as asyncio.Task
    |
    v
Returns HTTP response: { run_id: "a3f2b8c1e904", websocket_url: "/ws/a3f2b8c1e904" }
    |
    v
Frontend receives run_id, constructs WS URL:
    |   getWebSocketUrl("a3f2b8c1e904")
    |   -> "ws://127.0.0.1:8901/ws/a3f2b8c1e904"
    |
    v
WebSocketClient connects to ws://127.0.0.1:8901/ws/a3f2b8c1e904
    |
    v
Backend websocket_endpoint() accepts connection
    |   ws_manager.connect() sends {"type": "connected", ...}
    |   Flushes any pre-connection buffered messages
    |
    v
Meanwhile, _execute_pipeline() runs in thread pool:
    |
    |   setup_agent_logging(log_dir=..., preserve_handlers=[ws_handler])
    |       ^^^ THIS IS THE FIX: ws_handler survives the clear
    |
    |   logger.info("PIPELINE STARTED") etc.
    |       -> root logger has 3 handlers now:
    |          1. StreamHandler (console, pretty formatted)
    |          2. AgentEventLogger (JSONL file)
    |          3. WebSocketForwardingHandler (-> WebSocket)
    |
    |   Each logger.info() call:
    |       -> Python calls all 3 handlers
    |       -> WebSocketForwardingHandler.emit():
    |              asyncio.run_coroutine_threadsafe(
    |                  ws_manager.send_log_entry(run_id, level, message, ...),
    |                  self._loop   <-- main event loop, captured at creation
    |              )
    |       -> ws_manager._send():
    |              if WebSocket connected: ws.send_json(message)
    |              else: buffer message for replay
    |
    v
Frontend WebSocketClient.onmessage receives JSON:
    |   {"type": "log_entry", "data": {"level": "INFO", "message": "...", ...}}
    |
    v
useWebSocket hook dispatches by type:
    |   "log_entry" -> append to logs[] state
    |   "agent_started" -> mark agent as running
    |   "agent_completed" -> mark agent as completed
    |   "analysis_complete" -> set phase=completed, store final response
    |
    v
LogViewer component renders logs[] in scrollable area
    (auto-scrolls, filter by level, color-coded, copy button)
```

---

### Message Types (WebSocket -> Frontend)

| Type | Sent When | Data Fields |
|------|-----------|-------------|
| `connected` | WS connection established | `run_id`, `server_time` |
| `agent_started` | Before each agent runs | `agent_name`, `iteration`, `max_iterations` |
| `agent_completed` | After agent finishes | `agent_name`, `duration_seconds` |
| `agent_progress` | During agent execution | `agent_name`, `tool_name`, `progress` (current/total/percentage) |
| `log_entry` | Every logger.info/warning/error call | `level`, `logger`, `message`, optional `agent_name` |
| `rate_limit_update` | Reddit API rate limit changes | status dict |
| `analysis_complete` | Pipeline finishes | `run_id`, `final_response`, `results` (paths) |
| `error` | Pipeline fails | `message` |

### Message Types (Frontend -> WebSocket)

| Type | Sent When | Purpose |
|------|-----------|---------|
| `cancel_analysis` | User clicks cancel | Stops the running pipeline |

---

### Key Design Decisions

1. **Why `asyncio.run_coroutine_threadsafe`?** The pipeline runs in a thread pool (`run_in_executor`) but WebSocket sends must happen on the asyncio event loop. This function safely schedules a coroutine from a non-async thread.

2. **Why buffer messages?** There's a race between the WS connection being established (frontend side) and the pipeline starting (backend side). The buffer catches early logs and replays them on connect.

3. **Why `future.result(timeout=1.0)`?** The old code fire-and-forget the coroutine, silently swallowing errors. Now we wait (up to 1s) for the result, so WebSocket send failures are visible in stderr.

4. **Why preserve_handlers instead of a named logger?** Named loggers would require changing all agent code to use a specific logger instead of the root logger. The preserve approach fixes the bug with one parameter.

---

### Files Involved (Complete List)

| File | Role |
|------|------|
| `app/agents/logging_setup.py` | Sets up console + JSONL handlers; **the file with the bug** |
| `backend/app/main.py` | FastAPI app, CORS config, WS endpoint, port 8901 |
| `backend/app/services/analysis_service.py` | Pipeline orchestration, WebSocketForwardingHandler |
| `backend/app/api/websocket/manager.py` | ConnectionManager, message buffering, typed senders |
| `frontend/lib/api.ts` | REST client + WS URL construction |
| `frontend/lib/websocket.ts` | WebSocketClient with reconnection |
| `frontend/hooks/useWebSocket.ts` | React hook, WS state management, message dispatch |
| `frontend/components/LogViewer.tsx` | Log display component |
| `frontend/lib/types.ts` | TypeScript types for WS messages |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL=http://127.0.0.1:8901` |
| `frontend/next.config.js` | Rewrite proxy `/api/*` -> backend |
| `frontend/package.json` | Dev port 3456 |
| `docker-compose.yml` | Port mappings 8901 + 3456 |
| `backend/Dockerfile` | EXPOSE 8901 |

### How to Run (Local Dev)

```bash
# Terminal 1: Backend
conda activate agentic-ai-p2
uvicorn backend.app.main:app --reload --port 8901

# Terminal 2: Frontend
cd frontend
npm run dev   # starts on port 3456 (defined in package.json)

# Open browser
http://localhost:3456
```
