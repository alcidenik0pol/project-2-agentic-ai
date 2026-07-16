"""Health check endpoint."""

from fastapi import APIRouter

from app.models.api import HealthResponse
from app.project_imports import config, get_data_source

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check returning provider and data source info."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        llm_provider=config.llm_provider,
        data_source=get_data_source(),
    )


@router.get("/readiness")
async def readiness_check() -> dict:
    """Cloud Run readiness probe - checks if service can accept traffic."""
    return {"ready": True}
