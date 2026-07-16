"""Analysis endpoint: start a new analysis run."""

import logging

from fastapi import APIRouter, HTTPException

from app.models.api import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import analysis_service
from app.services.rate_limit_tracker import rate_limit_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisResponse, status_code=202)
async def start_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """Start a new analysis run.

    Returns a run_id and WebSocket URL for real-time updates.
    """
    logger.info(f"ANALYSIS REQUEST | query='{request.query}' data_source={request.data_source}")

    # Create the run
    logger.info("Creating analysis run")
    run = analysis_service.create_run(
        query=request.query,
        data_source=request.data_source,
    )
    logger.info(f"[{run.run_id}] Run created")

    # Build WebSocket URL (relative — the frontend constructs the full URL)
    websocket_url = f"/ws/{run.run_id}"

    # Start the pipeline in the background
    logger.info(f"[{run.run_id}] Starting async pipeline execution")
    await analysis_service.start_analysis(run)

    # Start rate limit tracking for live Reddit API calls
    if request.data_source == "reddit_live":
        await rate_limit_tracker.start_tracking(run.run_id)

    logger.info(f"[{run.run_id}] Returning run_id to client")
    return AnalysisResponse(
        run_id=run.run_id,
        websocket_url=websocket_url,
    )
