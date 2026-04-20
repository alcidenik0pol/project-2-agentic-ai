"""FastAPI application entry point.

Sets up CORS, includes API routers, and configures the WebSocket endpoint.
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import analysis, health, results
from backend.app.api.websocket.manager import manager as ws_manager
from backend.app.services.rate_limit_tracker import rate_limit_tracker

logger = logging.getLogger(__name__)

# Ensure project root is on sys.path so `app` module (agent code) resolves
PROJECT_ROOT = Path(__file__).resolve().parents[3]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    from app.config import config

    print("=" * 60)
    print("  REDDIT PAIN POINT ANALYZER")
    print("=" * 60)
    print(f"  Provider: {config.llm_provider}")
    print(f"  Model:    {config.gcloud_model}")
    print(f"  Mode:     {config.agent_mode}")
    print(f"  API:      http://localhost:8901")
    print(f"  Docs:     http://localhost:8901/docs")
    print("=" * 60)

    logger.info("Starting Reddit Analysis API server")

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

# Include REST routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(results.router, prefix="/api/v1")

# Rate limit endpoint
from backend.app.api.routes.rate_limit import router as rate_limit_router
app.include_router(rate_limit_router, prefix="/api/v1")


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
