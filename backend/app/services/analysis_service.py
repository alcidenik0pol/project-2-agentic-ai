"""Async analysis service wrapping the synchronous LangGraph pipeline.

Runs the multi-agent pipeline in a thread pool executor while forwarding
logs to the WebSocket for real-time frontend updates.
"""

import asyncio
import json
import logging
import re
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def sanitize_json_escapes(text: str) -> str:
    """Fix invalid JSON escape sequences from LLM output.

    LLMs sometimes produce Python-style escapes like \\' which are not valid JSON.
    This replaces common invalid escapes with their valid equivalents.
    """
    # Replace \' with ' (single quote doesn't need escaping in JSON)
    # Use regex to avoid replacing \\' (which is a valid escaped backslash + quote)
    return re.sub(r"(?<!\\)\\'", "'", text)

from backend.app.api.websocket.manager import manager as ws_manager
from backend.app.api.websocket.manager import _truncate_for_ws
from backend.app.models.api import HypothesisOutputAPI

# shared.py only depends on the stdlib, so this top-level import is safe and
# avoids repeating lazy imports in each method that touches the cancel flag.
from app.agents.tools.shared import PipelineCancelled, request_cancel

logger = logging.getLogger(__name__)

# Project root is one level up from backend/
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class WebSocketForwardingHandler(logging.Handler):
    """Logging handler that forwards log records to the WebSocket.

    Must be created from the async event loop so it can capture a loop
    reference. Uses run_coroutine_threadsafe because emit() is called
    from the thread pool executor where _execute_pipeline runs.
    """

    def __init__(self, run_id: str, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.run_id = run_id
        self._loop = loop
        self._error_count = 0
        self._last_error: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Detect agent name from logger path (app.agents.orchestrator, etc.)
            agent_name = None
            for name in ("orchestrator", "analyst", "hypothesis"):
                if name in record.name or name in msg.lower():
                    agent_name = name
                    break

            # If the record carries an `llm_call` extra, route it to
            # send_llm_call and return — this produces exactly one clickable
            # row instead of a duplicate log_entry.
            llm_call = getattr(record, "llm_call", None)
            if llm_call:
                asyncio.run_coroutine_threadsafe(
                    ws_manager.send_llm_call(
                        run_id=self.run_id,
                        level=record.levelname,
                        message=msg,
                        logger_name=record.name,
                        agent_name=agent_name,
                        llm_call=_truncate_for_ws(llm_call),
                    ),
                    self._loop,
                )
                return

            # Fire-and-forget: schedule the coroutine without blocking.
            # Previously this used future.result(timeout=5.0) which caused a
            # deadlock: emit() blocked waiting for a WebSocket that couldn't
            # connect until the API returned the run_id.
            asyncio.run_coroutine_threadsafe(
                ws_manager.send_log_entry(
                    run_id=self.run_id,
                    level=record.levelname,
                    message=msg,
                    logger_name=record.name,
                    agent_name=agent_name,
                ),
                self._loop,
            )
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            # Use print/stderr only — never logger.warning here, as it would
            # re-trigger emit() on the root logger (infinite recursion).
            print(f"[WebSocketHandler ERROR] {self._last_error} (run_id={self.run_id})", file=sys.stderr)


class AnalysisRun:
    """Tracks state for a single analysis run."""

    def __init__(self, run_id: str, query: str, data_source: str):
        self.run_id = run_id
        self.query = query
        self.data_source = data_source
        self.status: str = "running"  # running | completed | failed
        self.started_at = datetime.utcnow()
        self.completed_at: datetime | None = None
        self.run_dir: Path | None = None
        self.error: str | None = None
        self.result: dict[str, Any] | None = None
        self.ws_handler: WebSocketForwardingHandler | None = None
        self._loop: asyncio.AbstractEventLoop | None = None


class AnalysisService:
    """Service managing analysis runs.

    Wraps the LangGraph pipeline in a thread pool to keep the
    FastAPI event loop responsive, while forwarding logs via WebSocket.
    """

    def __init__(self):
        # run_id -> AnalysisRun
        self._runs: dict[str, AnalysisRun] = {}
        # run_id -> asyncio.Task
        self._tasks: dict[str, asyncio.Task] = {}

    def create_run(self, query: str, data_source: str) -> AnalysisRun:
        """Create a new analysis run and return it."""
        run_id = uuid.uuid4().hex[:12]
        run = AnalysisRun(run_id=run_id, query=query, data_source=data_source)
        self._runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> AnalysisRun | None:
        return self._runs.get(run_id)

    def cleanup_run(self, run_id: str) -> None:
        """Remove a run from memory after completion/cancellation.

        The run data is already persisted to disk, so removing from memory
        prevents state accumulation across multiple runs.
        """
        removed_run = self._runs.pop(run_id, None)
        removed_task = self._tasks.pop(run_id, None)
        if removed_run or removed_task:
            logger.info(f"[{run_id}] Cleaned up from analysis_service (run={removed_run is not None}, task={removed_task is not None})")

    async def start_analysis(self, run: AnalysisRun) -> None:
        """Start the analysis pipeline asynchronously.

        Sets up logging, creates the output directory, and runs
        the LangGraph pipeline in a thread pool.
        """
        # Override data source at runtime (frozen config can't be mutated)
        from app.config import set_data_source_override
        set_data_source_override(run.data_source)

        # Create run directory
        now = datetime.now()
        run_dir = PROJECT_ROOT / "output" / "reports" / now.strftime("%Y-%m-%d") / f"{now.strftime('%H%M%S')}_{run.data_source}"
        run_dir.mkdir(parents=True, exist_ok=True)
        run.run_dir = run_dir

        # Persist run metadata to disk so runs survive server restarts
        metadata = {
            "run_id": run.run_id,
            "query": run.query,
            "data_source": run.data_source,
            "created_at": now.isoformat(),
        }
        metadata_file = run_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Set up WebSocket log forwarding (capture loop now, while we're async)
        loop = asyncio.get_running_loop()
        run._loop = loop
        root_logger = logging.getLogger()

        # Defensive cleanup: remove any stale WebSocketForwardingHandler instances
        # left over from previous runs that may not have cleaned up properly.
        stale = [h for h in root_logger.handlers if isinstance(h, WebSocketForwardingHandler)]
        for h in stale:
            root_logger.removeHandler(h)

        ws_handler = WebSocketForwardingHandler(run.run_id, loop=loop)
        ws_handler.setLevel(logging.INFO)
        root_logger.addHandler(ws_handler)
        run.ws_handler = ws_handler

        try:
            # Launch in thread pool
            task = asyncio.create_task(self._run_in_thread(run))
            self._tasks[run.run_id] = task
        except Exception:
            # If task creation fails, remove the handler immediately to prevent
            # accumulation on the global root logger across multiple requests.
            root_logger.removeHandler(ws_handler)
            run.ws_handler = None
            raise

    async def _run_in_thread(self, run: AnalysisRun) -> None:
        """Execute the synchronous pipeline in a thread pool."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._execute_pipeline, run)
            run.result = result
            run.status = "completed"
            run.completed_at = datetime.utcnow()

            # Load hypothesis if saved
            hypothesis_path = str(run.run_dir / "hypothesis.json")
            report_path = str(run.run_dir / "report.md")

            await ws_manager.send_analysis_complete(
                run_id=run.run_id,
                final_response=result.get("final_response", ""),
                hypothesis_path=hypothesis_path,
                report_path=report_path,
            )

        except asyncio.CancelledError:
            run.status = "failed"
            run.error = "Analysis cancelled"

            # Clean up partial run directory
            if run.run_dir and run.run_dir.exists():
                shutil.rmtree(run.run_dir, ignore_errors=True)
                logger.info(f"[{run.run_id}] Cleaned up cancelled run directory: {run.run_dir}")

            await ws_manager.send_cancelled(run.run_id, "Analysis was cancelled")
        except PipelineCancelled:
            # Cooperative cancel raised by the fetcher loop. Same cleanup as
            # asyncio.CancelledError above (the cooperative path fires during
            # the sync fetch phase; CancelledError fires during the async phase).
            run.status = "failed"
            run.error = "Analysis cancelled"

            if run.run_dir and run.run_dir.exists():
                shutil.rmtree(run.run_dir, ignore_errors=True)
                logger.info(f"[{run.run_id}] Cleaned up cancelled run directory: {run.run_dir}")

            await ws_manager.send_cancelled(run.run_id, "Analysis was cancelled")
        except Exception as e:
            logger.exception(f"Analysis failed for run_id={run.run_id}")
            run.status = "failed"
            run.error = str(e)
            await ws_manager.send_error(run.run_id, f"Analysis failed: {e}")
        finally:
            # Clean up the WebSocket handler
            if run.ws_handler:
                root_logger = logging.getLogger()
                root_logger.removeHandler(run.ws_handler)
                run.ws_handler = None
            await ws_manager.mark_run_complete(run.run_id)
            # Remove run from memory to prevent state accumulation
            self.cleanup_run(run.run_id)

    def _execute_pipeline(self, run: AnalysisRun) -> dict[str, Any]:
        """Synchronous pipeline execution (runs in thread pool).

        This method must NOT be called from the async event loop directly.
        """
        rid = run.run_id
        logger.info(f"[{rid}] === PIPELINE STARTED === query='{run.query}' mode={run.data_source}")

        # Add project root to sys.path so `app` module resolves
        project_root_str = str(PROJECT_ROOT)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        logger.info(f"[{rid}] Loading LangGraph + provider modules (first run may take a few seconds)...")
        from app.agents.logging_setup import setup_agent_logging
        from app.agents.graph import run_pipeline
        from app.agents.tools.shared import set_shared_data
        from app.config import config
        logger.info(f"[{rid}] Modules loaded.")

        # Set run_dir in shared data for artifact tools
        set_shared_data("run_dir", str(run.run_dir))
        logger.info(f"[{rid}] Output dir: {run.run_dir}")

        # Set up file logging (preserves WebSocket handler)
        handlers_to_preserve = [run.ws_handler] if run.ws_handler else []
        setup_agent_logging(
            log_dir=str(run.run_dir),
            preserve_handlers=handlers_to_preserve,
        )
        logger.info(f"[{rid}] Agent logging configured; registering lifecycle callbacks.")

        # Callbacks to send agent lifecycle events via WebSocket
        def on_agent_started(agent_name, idx, total):
            logger.info(f"[{rid}] Step {idx}/{total}: {agent_name} starting")
            asyncio.run_coroutine_threadsafe(
                ws_manager.send_agent_started(
                    run_id=run.run_id,
                    agent_name=agent_name,
                    iteration=idx,
                    max_iterations=total,
                ),
                run._loop,
            )

        def on_agent_completed(agent_name, duration_seconds):
            logger.info(f"[{rid}] {agent_name} completed in {duration_seconds:.1f}s")
            asyncio.run_coroutine_threadsafe(
                ws_manager.send_agent_completed(
                    run_id=run.run_id,
                    agent_name=agent_name,
                    duration_seconds=duration_seconds,
                ),
                run._loop,
            )

            # Stream intermediary EDA results after analyst agent completes
            if agent_name == "analyst" and run.run_dir:
                for eda_file, result_type in [
                    ("classification_eda.json", "classification_eda"),
                    ("clustering_eda.json", "clustering_eda"),
                ]:
                    eda_path = run.run_dir / eda_file
                    if eda_path.exists():
                        try:
                            eda_data = json.loads(eda_path.read_text(encoding="utf-8"))
                            asyncio.run_coroutine_threadsafe(
                                ws_manager.send_intermediary_result(
                                    run_id=run.run_id,
                                    result_type=result_type,
                                    data=eda_data,
                                ),
                                run._loop,
                            )
                            logger.info(f"[{rid}] Streamed {result_type} via WebSocket")
                        except Exception as e:
                            logger.warning(f"[{rid}] Failed to stream {result_type}: {e}")

            # Stream hypothesis after hypothesis agent completes
            if agent_name == "hypothesis" and run.run_dir:
                hypothesis_path = run.run_dir / "hypothesis.json"
                if hypothesis_path.exists():
                    try:
                        raw_content = hypothesis_path.read_text(encoding="utf-8")
                        sanitized = sanitize_json_escapes(raw_content)
                        hypothesis_data = json.loads(sanitized)
                        asyncio.run_coroutine_threadsafe(
                            ws_manager.send_intermediary_result(
                                run_id=run.run_id,
                                result_type="hypothesis",
                                data=hypothesis_data,
                            ),
                            run._loop,
                        )
                        logger.info(f"[{rid}] Streamed hypothesis via WebSocket")
                    except Exception as e:
                        logger.warning(f"[{rid}] Failed to stream hypothesis: {e}")

        # Run the pipeline with lifecycle callbacks
        logger.info(f"[{rid}] Starting LangGraph pipeline")
        try:
            result = run_pipeline(
                user_query=run.query,
                run_dir=str(run.run_dir),
                on_agent_started=on_agent_started,
                on_agent_completed=on_agent_completed,
            )
        except PipelineCancelled:
            # Let the cooperative cancel propagate to _run_in_thread, which
            # owns the cleanup + WS notification. Must NOT be wrapped below.
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{rid}] Pipeline failed: {error_msg}")

            # Detect rate limit errors for user-friendly message
            if "429" in error_msg or "rate" in error_msg.lower() or "too many requests" in error_msg.lower():
                user_msg = (
                    "The AI service is currently experiencing high demand (rate limit). "
                    "Please wait a few minutes and try again."
                )
            else:
                user_msg = f"Analysis failed: {error_msg}"

            # Save error report
            report_file = run.run_dir / "report.md"
            report_file.write_text(
                f"# Reddit Complaint Analysis Report\n\n"
                f"**Query:** {run.query}\n"
                f"**Data source:** {run.data_source}\n"
                f"**Status:** FAILED\n"
                f"**Error:** {error_msg}\n"
                f"**Generated:** {datetime.now().isoformat()}\n",
                encoding="utf-8",
            )

            raise RuntimeError(user_msg) from e

        logger.info(f"[{rid}] LangGraph pipeline completed")

        # Save report
        report_file = run.run_dir / "report.md"
        report_file.write_text(
            f"# Reddit Complaint Analysis Report\n\n"
            f"**Query:** {run.query}\n"
            f"**Data source:** {run.data_source}\n"
            f"**Provider:** {config.llm_provider} ({config.gcloud_model})\n"
            f"**Agents:** {' -> '.join(result['agents_run'])}\n"
            f"**Tool calls:** {result['total_tool_calls']}\n"
            f"**Generated:** {datetime.now().isoformat()}\n\n"
            f"---\n\n"
            f"{result['final_response']}\n",
            encoding="utf-8",
        )

        logger.info(f"[{rid}] Report saved to {report_file}")
        logger.info(f"[{rid}] === PIPELINE COMPLETE === agents={result['agents_run']} tools={result['total_tool_calls']}")
        return result

    def cancel_run(self, run_id: str) -> bool:
        """Cancel a running analysis.

        Sets the cooperative cancel flag (stops the sync fetch loop within one
        subreddit iteration) AND cancels the asyncio task (interrupts the LLM/
        analyst phase between graph nodes). Both signals are benign if they
        target the same run; the cleanup path is idempotent.
        """
        request_cancel()
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def get_hypothesis(self, run: AnalysisRun) -> HypothesisOutputAPI | None:
        """Load hypothesis.json from the run directory."""
        if not run.run_dir:
            return None
        hypothesis_file = run.run_dir / "hypothesis.json"
        if not hypothesis_file.exists():
            return None
        try:
            raw_content = hypothesis_file.read_text(encoding="utf-8")
            sanitized = sanitize_json_escapes(raw_content)
            data = json.loads(sanitized)
            return HypothesisOutputAPI(**data)
        except Exception:
            return None

    def get_report(self, run: AnalysisRun) -> str | None:
        """Load report.md from the run directory."""
        if not run.run_dir:
            return None
        report_file = run.run_dir / "report.md"
        if not report_file.exists():
            return None
        return report_file.read_text(encoding="utf-8")

    def restore_runs_from_disk(self) -> int:
        """Scan output directory and restore runs from metadata.json files.

        Returns:
            Number of runs restored.
        """
        reports_dir = PROJECT_ROOT / "output" / "reports"
        if not reports_dir.exists():
            return 0

        restored = 0
        for date_dir in reports_dir.iterdir():
            if not date_dir.is_dir():
                continue
            for run_dir in date_dir.iterdir():
                if not run_dir.is_dir():
                    continue

                metadata_file = run_dir / "metadata.json"
                if not metadata_file.exists():
                    continue

                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                    run_id = metadata["run_id"]

                    # Skip if already in memory
                    if run_id in self._runs:
                        continue

                    run = AnalysisRun(
                        run_id=run_id,
                        query=metadata["query"],
                        data_source=metadata.get("data_source", metadata.get("mode", "sample_default")),
                    )
                    run.run_dir = run_dir
                    run.status = "completed"
                    self._runs[run_id] = run
                    restored += 1
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Failed to restore run from {run_dir}: {e}")
                    continue

        if restored:
            logger.info(f"Restored {restored} runs from disk")
        return restored


# Singleton instance
analysis_service = AnalysisService()
