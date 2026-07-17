"""Usage tracking API endpoint."""

import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from backend.app.models.api import UsageResponse

router = APIRouter(tags=["usage"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)


@router.get("/usage", response_model=UsageResponse)
async def get_usage() -> UsageResponse:
    """Get current Gemini API token usage and limits.

    Returns current usage stats, limits, and when the counter resets.
    The usage resets on the 1st of each month.

    In development mode, returns ``tracking_enabled=False`` and zeros —
    token counting and monthly limits are disabled in dev.
    """
    from app.config import config

    if config.is_development:
        return UsageResponse(
            tracking_enabled=False,
            used=0,
            limit=0,
            remaining=0,
            percent_remaining=0.0,
            resets_at="",
            month="",
            input_tokens=0,
            output_tokens=0,
            thinking_tokens=0,
        )

    from app.services.usage_tracker import get_usage_tracker

    tracker = get_usage_tracker()
    stats = tracker.get_usage()
    reset_date = tracker.get_next_reset_date()

    return UsageResponse(
        tracking_enabled=True,
        used=stats.total_tokens,
        limit=tracker.limit,
        remaining=tracker.limit - stats.total_tokens,
        percent_remaining=tracker.get_remaining_percent(),
        resets_at=reset_date.isoformat(),
        month=stats.month,
        input_tokens=stats.input_tokens,
        output_tokens=stats.output_tokens,
        thinking_tokens=stats.thinking_tokens,
    )
