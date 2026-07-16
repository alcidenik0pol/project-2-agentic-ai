"""FastAPI application entry point.

Sets up CORS, includes API routers, and configures the WebSocket endpoint.
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import analysis, health, results
from backend.app.api.websocket.manager import manager as ws_manager
from backend.app.services.rate_limit_tracker import rate_limit_tracker

logger = logging.getLogger(__name__)

# Ensure project root is on sys.path so `app` module (agent code) resolves.
# backend/app/main.py → parents[2] = project root (parent.parent.parent).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)


def _log_dataset_status() -> None:
    """Log which dataset files are reachable from the data root.

    Probes only file paths and sizes — no credentials or network details.
    In production the data root is the read-only GCS bucket mounted at
    ``/app/data``; locally it is ``<project>/data``.
    """
    data_root = PROJECT_ROOT / "data"
    bucket = os.getenv("DATASETS_BUCKET") or "(unset)"

    probes = {
        "pushshift": data_root / "pushshift" / "RS_2018-01_00.parquet",
        "linanqiu": data_root / "linanqiu" / "linanqiu_dataset.json",
        "sample_default": data_root / "smallsample" / "sample_posts.json",
        "sample_gaming": data_root / "smallsample" / "gaming_test_20260416_105527.json",
    }

    def _size(path: Path) -> str:
        return f"{path.stat().st_size:,}B" if path.exists() else "MISSING"

    smallsample_dir = data_root / "smallsample"
    smallsample_n = len(list(smallsample_dir.glob("*.json"))) if smallsample_dir.exists() else 0
    desc_n = len(list(data_root.glob("**/subreddit_descriptions_*.json")))

    summary = " | ".join(
        [f"{name}={_size(p)}" for name, p in probes.items()]
        + [f"smallsample/*={smallsample_n}", f"subreddit_descriptions={desc_n}"]
    )
    logger.info("[DATASETS] root=%s bucket=%s | %s", data_root, bucket, summary)

    for name, path in probes.items():
        if not path.exists():
            logger.warning("[DATASETS] missing expected dataset file: %s -> %s", name, path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    from app.config import config, get_data_source

    print("=" * 60)
    print("  REDDIT PAIN POINT ANALYZER")
    print("=" * 60)
    print(f"  Provider: {config.llm_provider}")
    print(f"  Model:    {config.gcloud_model}")
    print(f"  Source:   {get_data_source()}")
    print(f"  API:      http://localhost:8901")
    print(f"  Docs:     http://localhost:8901/docs")
    print("=" * 60)

    logger.info("Starting Reddit Analysis API server")

    # Log which dataset files are reachable (bucket mount in prod, local data/ in dev)
    _log_dataset_status()

    # Restore previously completed runs from disk
    from backend.app.services.analysis_service import analysis_service
    restored = analysis_service.restore_runs_from_disk()
    if restored:
        print(f"  Restored {restored} previous run(s) from disk")

    yield

    print("\nShutting down...")
    logger.info("Shutting down Reddit Analysis API server")


app = FastAPI(
    title="Reddit Complaint Analysis API",
    version="1.0.0",
    description="Multi-agent Reddit analysis system with real-time WebSocket updates",
    lifespan=lifespan,
)

# CORS — allow the Next.js dev server and production origins
# CORS_ORIGINS env var: comma-separated list of allowed origins
# Falls back to common dev origins if not set
_cors_env = os.getenv("CORS_ORIGINS", "")
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    _cors_origins = [
        "http://localhost:3456",
        "http://127.0.0.1:3456",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Usage Limit Middleware ──

@app.middleware("http")
async def check_usage_limit(request: Request, call_next):
    """Block analysis requests if monthly token limit is exceeded.

    Skipped entirely in development mode — token limits are a production
    cost control. See ``app.config.Config.is_development``.
    """
    from app.config import config

    if config.is_development:
        return await call_next(request)

    # Only check for analysis endpoint
    if request.url.path == "/api/v1/analysis" and request.method == "POST":
        try:
            from app.services.usage_tracker import get_usage_tracker

            tracker = get_usage_tracker()
            if tracker.is_limit_exceeded():
                reset_date = tracker.get_next_reset_date()
                logger.warning(
                    "Usage limit exceeded: %d / %d tokens",
                    tracker.get_usage().total_tokens,
                    tracker.limit,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "usage_limit_exceeded",
                        "message": "Monthly token limit has been reached",
                        "resets_at": reset_date.isoformat(),
                        "used": tracker.get_usage().total_tokens,
                        "limit": tracker.limit,
                    },
                )
        except Exception as e:
            # Don't block requests if usage tracking fails
            logger.warning(f"Usage check failed (allowing request): {e}")

    return await call_next(request)


# Include REST routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(results.router, prefix="/api/v1")

# Rate limit endpoint
from backend.app.api.routes.rate_limit import router as rate_limit_router
app.include_router(rate_limit_router, prefix="/api/v1")

# Usage tracking endpoint
from backend.app.api.routes.usage import router as usage_router
app.include_router(usage_router, prefix="/api/v1")


# ── WebSocket endpoint ──

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for real-time analysis updates.

    The frontend connects to /ws/{run_id} after starting an analysis.
    The server pushes log entries, agent progress, rate limit updates,
    and completion messages.
    """
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"[WebSocket] Connection attempt: run_id={run_id} client={client_host}")

    # Reject dead runs BEFORE accepting/registering with ws_manager, so the
    # misleading "Connected to server, starting pipeline..." frame is never
    # sent for a run that can never produce updates. Self-heals stale
    # localStorage recovery on the frontend after a backend restart: the
    # client reconnects to a dead run_id, we tell it the run is gone, and it
    # returns to idle instead of freezing. "Actively running right now" is
    # the only state worth reconnecting to — this also covers runs restored
    # from disk by restore_runs_from_disk on startup (completed/failed runs
    # sitting in _runs but with no live task). We bypass ws_manager here and
    # send directly on the socket because _send() routes through
    # _connections, which isn't populated until ws_manager.connect().
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
        logger.info(f"[WebSocket] Connected: run_id={run_id} client={client_host}")
    except Exception as e:
        logger.error(f"[WebSocket] Failed to accept connection: run_id={run_id} error={e}")
        return

    try:
        while True:
            # Listen for client messages (e.g., cancel)
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "cancel_analysis":
                from backend.app.services.analysis_service import analysis_service
                analysis_service.cancel_run(run_id)
                await rate_limit_tracker.stop_tracking(run_id)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})

    except WebSocketDisconnect:
        ws_manager.disconnect(run_id)
        logger.info(f"[WebSocket] Client disconnected: run_id={run_id}")
    except Exception as e:
        logger.exception(f"[WebSocket] Error for run_id={run_id}: {e}")
        ws_manager.disconnect(run_id)
