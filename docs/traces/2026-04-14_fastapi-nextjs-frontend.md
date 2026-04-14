# Trace: FastAPI + Next.js Frontend with WebSocket Real-Time Updates

**Date:** 2026-04-14
**Session:** Building a production-ready web frontend (Next.js + shadcn/ui) and backend (FastAPI) for the multi-agent Reddit analysis system, with WebSocket streaming, REST API, and Docker deployment.

---

## Files Created

### Backend (FastAPI)

| File | Purpose |
|------|---------|
| `backend/app/__init__.py` | Package marker |
| `backend/app/main.py` | FastAPI app entry: CORS, routers, WebSocket endpoint `/ws/{run_id}` |
| `backend/app/models/__init__.py` | Package marker |
| `backend/app/models/api.py` | Pydantic request/response models (AnalysisRequest, ResultResponse, WSMessage, etc.) |
| `backend/app/api/__init__.py` | Package marker |
| `backend/app/api/routes/__init__.py` | Package marker |
| `backend/app/api/routes/health.py` | `GET /api/v1/health` — returns provider, mode, version |
| `backend/app/api/routes/analysis.py` | `POST /api/v1/analysis` — creates run, returns 202 with run_id + WS URL |
| `backend/app/api/routes/results.py` | `GET /api/v1/results/{run_id}` + `GET .../file/{filename}` — serves results and artifacts |
| `backend/app/api/routes/rate_limit.py` | `GET /api/v1/rate-limit` — current Reddit API throttle status |
| `backend/app/api/websocket/__init__.py` | Package marker |
| `backend/app/api/websocket/manager.py` | `ConnectionManager` — typed WS message helpers (agent_started, log_entry, rate_limit_update, analysis_complete, error) |
| `backend/app/services/__init__.py` | Package marker |
| `backend/app/services/analysis_service.py` | `AnalysisService` — async wrapper running `AgentOrchestrator.run()` in thread pool with WebSocket log forwarding via custom logging handler |
| `backend/app/services/rate_limit_tracker.py` | `RateLimitTracker` — background task polling `reddit_client.get_rate_limit_status()` every 1s, broadcasting via WebSocket |
| `backend/requirements.txt` | Backend-specific dependencies (fastapi, uvicorn, websockets + inherited agent deps) |
| `backend/Dockerfile` | Python 3.11 slim image, installs deps, exposes port 8901 |

### Frontend (Next.js + shadcn/ui)

| File | Purpose |
|------|---------|
| `frontend/package.json` | Dependencies: next 15, react 19, radix primitives, lucide-react, tailwind |
| `frontend/tsconfig.json` | TypeScript config with `@/*` path alias |
| `frontend/tailwind.config.js` | Tailwind with shadcn CSS variable theme (dark mode) |
| `frontend/postcss.config.js` | PostCSS with tailwindcss + autoprefixer |
| `frontend/next.config.js` | Next.js config (empty, defaults) |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL=http://localhost:8901` |
| `frontend/app/globals.css` | CSS variables for dark theme, custom scrollbar, agent color classes |
| `frontend/app/layout.tsx` | Root layout with dark mode class on `<html>` |
| `frontend/app/page.tsx` | Main page — composes ChatInterface, AgentFlow, RateLimitMonitor, LogViewer, ResultsDisplay, ArchitectureDiagram |
| `frontend/lib/types.ts` | TypeScript types mirroring backend Pydantic models (WSMessage variants, AgentState, BusinessIdea, HypothesisOutput, etc.) |
| `frontend/lib/api.ts` | REST client: startAnalysis, getResults, getHealth, getRateLimit, getWebSocketUrl |
| `frontend/lib/websocket.ts` | WebSocketClient class with reconnect logic (5 retries, 2s delay) |
| `frontend/lib/utils.ts` | `cn()` helper (clsx + tailwind-merge) |
| `frontend/hooks/useWebSocket.ts` | React hook — manages WS connection, parses messages, maintains agents/logs/rateLimit/error state |
| `frontend/hooks/useAnalysis.ts` | React hook — submit analysis, fetch results, manage phase state |
| `frontend/components/ui/button.tsx` | shadcn Button (CVA variants: default, destructive, outline, secondary, ghost, link) |
| `frontend/components/ui/card.tsx` | shadcn Card (Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter) |
| `frontend/components/ui/tabs.tsx` | shadcn Tabs (Radix TabsPrimitive) |
| `frontend/components/ui/progress.tsx` | shadcn Progress (Radix ProgressPrimitive) |
| `frontend/components/ui/scroll-area.tsx` | shadcn ScrollArea (Radix ScrollAreaPrimitive) |
| `frontend/components/ui/badge.tsx` | shadcn Badge (CVA variants) |
| `frontend/components/ChatInterface.tsx` | Query textarea + test/live mode toggle + submit/cancel buttons |
| `frontend/components/AgentFlow.tsx` | Visual pipeline: Orchestrator → Analyst → Hypothesis with animated active/completed states |
| `frontend/components/RateLimitMonitor.tsx` | Progress bar + countdown timer + Throttled/OK badge |
| `frontend/components/LogViewer.tsx` | Auto-scrolling color-coded logs (blue=orchestrator, green=analyst, yellow=hypothesis) with level filter and copy button |
| `frontend/components/ResultsDisplay.tsx` | Tabbed results: Business Ideas (ranked cards with expandable evidence) + Report (markdown) |
| `frontend/components/ArchitectureDiagram.tsx` | Static SVG diagram showing 3-agent pipeline with tools listed |
| `frontend/Dockerfile` | Node 22 alpine, installs deps, builds, exposes port 3456 |

### Infrastructure

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Backend (8901) + Frontend (3456) services with shared output volume |
| `.gitignore` | Added `frontend/node_modules/`, `frontend/.next/`, `frontend/out/` |

---

## Files Modified

| File | Change |
|------|--------|
| `.gitignore` | Added frontend exclusions (node_modules, .next, out) |

No existing application code was modified. The backend wraps the existing `AgentOrchestrator` without changes to `app/agents/`, `app/analyst/`, `app/collector/`, or `scripts/`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Frontend (Next.js :3456)                  │
│                                                         │
│  ChatInterface ──submit()──▶ useAnalysis ──POST /api/v1 │
│       │                                    /analysis    │
│       │                                         │       │
│  AgentFlow ◀──useWebSocket──◀── WS :8901/ws/{id} ──────│
│  RateLimitMonitor           │                           │
│  LogViewer                  │  real-time messages:      │
│  ResultsDisplay             │  agent_started/completed  │
│                             │  log_entry                │
│                             │  rate_limit_update         │
│                             │  analysis_complete         │
└─────────────────────────────┼───────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────┐
│              Backend (FastAPI :8901)                     │
│                             │                           │
│  AnalysisService ──run_in_executor()──▶ AgentOrchestrator│
│       │                                (existing code)  │
│       │                                      │         │
│  WebSocketForwardingHandler ◀── logging ─────┘         │
│  RateLimitTracker ──poll(1s)──▶ reddit_client           │
│                                                         │
│  REST: /api/v1/health, /analysis, /results/{id}         │
└─────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Zero changes to existing agent code.** The `AnalysisService` runs `AgentOrchestrator.run()` in `asyncio.run_in_executor()`, keeping the synchronous pipeline untouched. A custom `logging.Handler` intercepts logs and forwards them to WebSocket.

2. **WebSocket-first with REST fallback.** Real-time updates (agent lifecycle, logs, rate limits) stream over WebSocket. The REST API provides entry points and result retrieval for when WebSocket isn't needed (e.g., programmatic access).

3. **Backend imports from project root.** `sys.path` manipulation ensures `from app.agents.runner import AgentOrchestrator` resolves correctly. The backend is a thin layer at `backend/` that imports the existing `app/` package.

4. **Stateful in-memory run tracking.** `AnalysisService._runs` maps `run_id -> AnalysisRun`. Results are loaded from disk (the run directory where `AgentOrchestrator` already writes `hypothesis.json` and `report.md`). No database needed for MVP.

---

## REST API Endpoints

| Method | Path | Status | Response |
|--------|------|--------|----------|
| `POST` | `/api/v1/analysis` | 202 | `{ run_id, websocket_url }` |
| `GET` | `/api/v1/results/{run_id}` | 200 | `{ run_id, status, hypothesis, report_content, agent_results, error }` |
| `GET` | `/api/v1/results/{run_id}/file/{filename}` | 200 | File content (json, md, jsonl) |
| `GET` | `/api/v1/rate-limit` | 200 | `{ requests_in_window, requests_remaining, seconds_until_reset, is_throttled, limit }` |
| `GET` | `/api/v1/health` | 200 | `{ status, version, llm_provider, agent_mode }` |

## WebSocket Protocol

**Server → Client messages:**

| type | data |
|------|------|
| `connected` | `{ run_id, server_time }` |
| `agent_started` | `{ agent_name, iteration, max_iterations }` |
| `agent_completed` | `{ agent_name, duration_seconds }` |
| `agent_progress` | `{ agent_name, tool_name, progress: { current, total, percentage } }` |
| `rate_limit_update` | `{ requests_in_window, requests_remaining, seconds_until_reset, is_throttled, limit, ... }` |
| `log_entry` | `{ level, logger, message, agent_name? }` |
| `analysis_complete` | `{ run_id, final_response, results: { hypothesis_path, report_path } }` |
| `error` | `{ message }` |

**Client → Server messages:**

| type | data |
|------|------|
| `start_analysis` | `{ query, mode }` (via REST, not WS) |
| `cancel_analysis` | `{ run_id }` |

---

## Verification Performed

### Backend
```
✓ FastAPI app imports cleanly: `from backend.app.main import app`
✓ Health endpoint: curl http://localhost:8901/api/v1/health → {"status":"healthy",...}
✓ Analysis endpoint: curl POST /api/v1/analysis → 202 {"run_id":"...","websocket_url":"/ws/..."}
✓ Results endpoint: curl GET /api/v1/results/{id} → {"status":"running",...}
✓ Rate limit endpoint: curl GET /api/v1/rate-limit → {requests_remaining: 10, ...}
```

### Frontend
```
✓ npm run build compiles successfully (25kB first load JS)
✓ npm run dev serves page at localhost:3456, returns 200
✓ TypeScript strict mode passes
✓ All components render without errors
```

### CLI Backward Compatibility
```
✓ Existing imports unchanged: from app.agents.runner import AgentOrchestrator → OK
✓ python scripts/run_agent.py "test" still works (no code changes to app/)
```

---

## Environment Variables

### Backend (.env, already exists)
```
REDDIT_USER_AGENT=complaint-analyzer:1.0
LLM_PROVIDER=gcloud
GEMINI_API_KEY=...
AGENT_MODE=test
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8901
```

### Docker Compose
```
Backend:  CORS_ORIGINS=http://localhost:3456
Frontend: NEXT_PUBLIC_API_URL=http://localhost:8901, PORT=3456
```

---

## What Was NOT Done (Out of Scope)

- No database — runs tracked in-memory (lost on server restart)
- No authentication — no user accounts, no API keys
- No WebSocket reconnection on the backend side — frontend client handles reconnect
- No file upload or configuration UI — settings come from env vars
- No concurrent run isolation — shared data store (`shared.py`) is global; only one analysis at a time

---

## Ports

| Service | Port |
|---------|------|
| Backend (FastAPI) | 8901 |
| Frontend (Next.js) | 3456 |
