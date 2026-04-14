"""Health check endpoint."""

from fastapi import APIRouter

from backend.app.models.api import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check returning provider and mode info."""
    import sys
    from pathlib import Path

    project_root_str = str(Path(__file__).resolve().parents[5])
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    from app.config import config

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        llm_provider=config.llm_provider,
        agent_mode=config.agent_mode,
    )
