"""Background service that polls Reddit rate limit status and broadcasts via WebSocket."""

import asyncio
import logging
import sys
from pathlib import Path

from app.api.websocket.manager import manager as ws_manager

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class RateLimitTracker:
    """Periodically polls the Reddit client's rate limit status and sends
    updates to connected WebSocket clients.
    """

    def __init__(self, poll_interval: float = 1.0):
        self._poll_interval = poll_interval
        self._task: asyncio.Task | None = None
        self._active_run_id: str | None = None

    async def start_tracking(self, run_id: str) -> None:
        """Start tracking rate limits for a specific run."""
        self._active_run_id = run_id
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_loop())

    async def stop_tracking(self, run_id: str) -> None:
        """Stop tracking for a run."""
        if self._active_run_id == run_id:
            self._active_run_id = None
            if self._task and not self._task.done():
                self._task.cancel()

    async def _poll_loop(self) -> None:
        """Poll rate limit status and broadcast updates."""
        project_root_str = str(PROJECT_ROOT)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        while self._active_run_id:
            try:
                from app.reddit.client import reddit_client

                status = reddit_client.get_rate_limit_status()
                await ws_manager.send_rate_limit_update(
                    run_id=self._active_run_id,
                    status=status,
                )
            except Exception as e:
                logger.debug(f"Rate limit poll failed: {e}")

            await asyncio.sleep(self._poll_interval)

    @property
    def is_tracking(self) -> bool:
        return self._active_run_id is not None


# Singleton
rate_limit_tracker = RateLimitTracker()
