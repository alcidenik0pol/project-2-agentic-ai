"""Usage tracking API endpoint."""

from fastapi import APIRouter

from app.models.api import UsageResponse
from app.project_imports import get_usage_tracker

router = APIRouter(tags=["usage"])


@router.get("/usage", response_model=UsageResponse)
async def get_usage() -> UsageResponse:
    """Get current Gemini API token usage and limits.

    Returns current usage stats, limits, and when the counter resets.
    The usage resets on the 1st of each month.
    """

    tracker = get_usage_tracker()
    stats = tracker.get_usage()
    reset_date = tracker.get_next_reset_date()

    return UsageResponse(
        used=stats.total_tokens,
        limit=tracker.limit,
        remaining=tracker.limit - stats.total_tokens,
        percent_remaining=tracker.get_remaining_percent(),
        resets_at=reset_date.isoformat(),
        month=stats.month,
        input_tokens=stats.input_tokens,
        output_tokens=stats.output_tokens,
    )
