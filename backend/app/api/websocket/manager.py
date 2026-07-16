"""WebSocket connection manager for real-time communication with the frontend."""

import asyncio
import copy
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


def _truncate_for_ws(payload: Any, max_text_chars: int = 2000) -> Any:
    """Deep-copy a payload and truncate long text fields to cap WS frame size.

    Orchestrator tool results (post data) can be 50KB+, which would blow up
    the WebSocket frame. We trim each Gemini ``contents[].parts[].text`` and
    OpenAI ``messages[].content`` string to a sane length with a marker so the
    shape is preserved for the frontend modal.
    """
    try:
        cloned = copy.deepcopy(payload)
    except Exception:
        # If the payload isn't deep-copyable, fall back to a shallow repr.
        return repr(payload)

    def _clip(text: Any) -> Any:
        if isinstance(text, str) and len(text) > max_text_chars:
            return text[:max_text_chars] + "...[truncated]"
        return text

    if isinstance(cloned, dict):
        # Gemini format: contents[].parts[].text
        for content in cloned.get("contents", []) or []:
            if isinstance(content, dict):
                for part in content.get("parts", []) or []:
                    if isinstance(part, dict) and "text" in part:
                        part["text"] = _clip(part["text"])
        # OpenAI format: messages[].content
        for message in cloned.get("messages", []) or []:
            if isinstance(message, dict):
                message["content"] = _clip(message.get("content"))

    return cloned


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting.

    Each analysis run gets its own WebSocket connection identified by run_id.
    """

    def __init__(self):
        # run_id -> WebSocket
        self._connections: dict[str, WebSocket] = {}
        # run_id -> list of buffered messages (replayed on connect)
        self._buffers: dict[str, list[dict[str, Any]]] = {}
        # Max buffered messages per run_id before dropping oldest
        self._max_buffer_size = 500
        # run_id -> timestamp when buffer should be expired
        self._buffer_expiry: dict[str, float] = {}
        # run_id -> pending auto-close task scheduled on analysis_complete
        self._auto_close_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._connections[run_id] = websocket
        logger.info(f"WebSocket connected for run_id={run_id}")

        # Send connected confirmation
        await self._send(run_id, {
            "type": "connected",
            "data": {
                "run_id": run_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
            },
        })

        # Flush any buffered messages that arrived before the client connected
        buffered = self._buffers.pop(run_id, None)
        if buffered:
            logger.info(f"Flushing {len(buffered)} buffered messages for run_id={run_id}")
            for msg in buffered:
                try:
                    await websocket.send_json(msg)
                except Exception as e:
                    logger.warning(f"Failed to flush buffered message: {e}")
                    break

    def disconnect(self, run_id: str) -> None:
        """Remove a WebSocket connection."""
        self._connections.pop(run_id, None)
        self._buffers.pop(run_id, None)
        self._buffer_expiry.pop(run_id, None)
        # Cancel any pending auto-close task; the connection is gone.
        task = self._auto_close_tasks.pop(run_id, None)
        if task and not task.done():
            task.cancel()
        logger.info(f"WebSocket disconnected for run_id={run_id}")

    async def _schedule_auto_close(self, run_id: str, delay: int = 900) -> None:
        """Close the WS connection after a grace period post-completion.

        Caps idle billing from abandoned tabs: once analysis_complete has been
        sent, the frontend no longer needs the WS for streaming. The 15-minute
        grace gives a reviewer time to scroll results before we close with code
        1000 (normal closure), which the frontend handles gracefully.
        """
        await asyncio.sleep(delay)
        ws = self._connections.get(run_id)
        if ws is None:
            return
        try:
            await ws.close(code=1000, reason="analysis_complete auto-close")
        except Exception as e:
            logger.warning(f"Auto-close failed for run_id={run_id}: {e}")
        self.disconnect(run_id)

    async def mark_run_complete(self, run_id: str) -> None:
        """Mark a run as complete. Keeps the buffer for 5 minutes for late connections."""
        import time
        self._buffer_expiry[run_id] = time.time() + 300
        # Schedule WS auto-close 15 min after completion to cap idle billing.
        task = asyncio.create_task(self._schedule_auto_close(run_id, delay=900))
        self._auto_close_tasks[run_id] = task
        logger.info(f"Run {run_id} marked complete, buffer expires in 5 minutes")

    async def _send(self, run_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to the WebSocket for the given run_id.

        If no client is connected, buffers the message for replay on connect.
        """
        ws = self._connections.get(run_id)
        if ws is None:
            # Buffer the message so it can be replayed when a client connects
            buf = self._buffers.setdefault(run_id, [])
            buf.append(message)
            # Drop oldest if buffer is full
            if len(buf) > self._max_buffer_size:
                buf.pop(0)
            return
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message to run_id={run_id}: {e}")
            self.disconnect(run_id)

    # ── Typed message helpers ──

    async def send_agent_started(
        self, run_id: str, agent_name: str, iteration: int = 1, max_iterations: int = 20
    ) -> None:
        await self._send(run_id, {
            "type": "agent_started",
            "data": {
                "agent_name": agent_name,
                "iteration": iteration,
                "max_iterations": max_iterations,
            },
        })

    async def send_agent_completed(
        self, run_id: str, agent_name: str, duration_seconds: float = 0.0
    ) -> None:
        await self._send(run_id, {
            "type": "agent_completed",
            "data": {
                "agent_name": agent_name,
                "duration_seconds": round(duration_seconds, 2),
            },
        })

    async def send_agent_progress(
        self, run_id: str, agent_name: str, tool_name: str,
        current: int, total: int,
    ) -> None:
        percentage = round((current / total) * 100, 1) if total > 0 else 0
        await self._send(run_id, {
            "type": "agent_progress",
            "data": {
                "agent_name": agent_name,
                "tool_name": tool_name,
                "progress": {
                    "current": current,
                    "total": total,
                    "percentage": percentage,
                },
            },
        })

    async def send_rate_limit_update(self, run_id: str, status: dict) -> None:
        await self._send(run_id, {
            "type": "rate_limit_update",
            "data": status,
        })

    async def send_log_entry(
        self, run_id: str, level: str, message: str,
        logger_name: str = "", agent_name: str | None = None,
    ) -> None:
        data: dict[str, Any] = {
            "level": level,
            "logger": logger_name,
            "message": message,
        }
        if agent_name:
            data["agent_name"] = agent_name
        await self._send(run_id, {
            "type": "log_entry",
            "data": data,
        })

    async def send_llm_call(
        self, run_id: str, *, level: str, message: str,
        logger_name: str = "", agent_name: str | None = None,
        llm_call: dict[str, Any] | None = None,
    ) -> None:
        """Send a clickable LLM call entry to the frontend.

        Mirrors send_log_entry but carries an ``llm_call`` payload (request +
        response summary) so the frontend can render a single clickable row
        that opens the full request JSON in a modal.
        """
        data: dict[str, Any] = {
            "level": level,
            "logger": logger_name,
            "message": message,
        }
        if agent_name:
            data["agent_name"] = agent_name
        if llm_call is not None:
            data["llm_call"] = llm_call
        await self._send(run_id, {
            "type": "llm_call",
            "data": data,
        })

    async def send_analysis_complete(
        self, run_id: str, final_response: str,
        hypothesis_path: str = "", report_path: str = "",
    ) -> None:
        await self._send(run_id, {
            "type": "analysis_complete",
            "data": {
                "run_id": run_id,
                "final_response": final_response,
                "results": {
                    "hypothesis_path": hypothesis_path,
                    "report_path": report_path,
                },
            },
        })

    async def send_intermediary_result(
        self, run_id: str, result_type: str, data: dict[str, Any]
    ) -> None:
        """Send intermediary analysis results (classification/clustering EDA)."""
        await self._send(run_id, {
            "type": "intermediary_result",
            "data": {
                "result_type": result_type,
                "data": data,
            },
        })

    async def send_error(self, run_id: str, error_message: str) -> None:
        await self._send(run_id, {
            "type": "error",
            "data": {"message": error_message},
        })

    async def send_cancelled(self, run_id: str, message: str = "Analysis was cancelled") -> None:
        await self._send(run_id, {
            "type": "analysis_cancelled",
            "data": {"message": message},
        })

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# Singleton instance
manager = ConnectionManager()
