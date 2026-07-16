"""Rate limit status endpoint."""

import sys
from pathlib import Path

from fastapi import APIRouter

from app.models.api import RateLimitStatus

router = APIRouter(tags=["rate-limit"])

PROJECT_ROOT = Path(__file__).resolve().parents[5]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)


@router.get("/rate-limit", response_model=RateLimitStatus)
async def get_rate_limit() -> RateLimitStatus:
    """Current Reddit API rate limit status."""
    from app.reddit.client import reddit_client

    status = reddit_client.get_rate_limit_status()
    return RateLimitStatus(
        requests_in_window=status["requests_in_window"],
        requests_remaining=status["requests_remaining"],
        seconds_until_reset=status["seconds_until_reset"],
        is_throttled=status["is_throttled"],
        limit=status["limit"],
        seconds_until_next_request=status["seconds_until_next_request"],
    )
