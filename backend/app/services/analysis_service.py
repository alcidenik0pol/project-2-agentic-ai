"""Async analysis service wrapping the synchronous AgentOrchestrator.

Runs the multi-agent pipeline in a thread pool executor while forwarding
logs to the WebSocket for real-time frontend updates.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.api.websocket.manager import manager as ws_manager
from backend.app.models.api import HypothesisOutputAPI

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

            # Thread-safe: schedule the coroutine on the main event loop
            future = asyncio.run_coroutine_threadsafe(
                ws_manager.send_log_entry(
                    run_id=self.run_id,
                    level=record.levelname,
                    message=msg,
                    logger_name=record.name,
                    agent_name=agent_name,
                ),
                self._loop,
            )
            future.result(timeout=1.0)
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            print(f"[WebSocketHandler ERROR] {self._last_error} (run_id={self.run_id})", file=sys.stderr)


class AnalysisRun:
    """Tracks state for a single analysis run."""

    def __init__(self, run_id: str, query: str, mode: str):
        self.run_id = run_id
        self.query = query
        self.mode = mode
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

    Wraps AgentOrchestrator.run() in a thread pool to keep the
    FastAPI event loop responsive, while forwarding logs via WebSocket.
    """

    def __init__(self):
        # run_id -> AnalysisRun
        self._runs: dict[str, AnalysisRun] = {}
        # run_id -> asyncio.Task
        self._tasks: dict[str, asyncio.Task] = {}

    def create_run(self, query: str, mode: str) -> AnalysisRun:
        """Create a new analysis run and return it."""
        run_id = uuid.uuid4().hex[:12]
        run = AnalysisRun(run_id=run_id, query=query, mode=mode)
        self._runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> AnalysisRun | None:
        return self._runs.get(run_id)

    async def start_analysis(self, run: AnalysisRun) -> None:
        """Start the analysis pipeline asynchronously.

        Sets up logging, creates the output directory, and runs
        AgentOrchestrator.run() in a thread pool.
        """
        # Override AGENT_MODE env var
        os.environ["AGENT_MODE"] = run.mode

        # Create run directory
        now = datetime.now()
        run_dir = PROJECT_ROOT / "output" / "reports" / now.strftime("%Y-%m-%d") / f"{now.strftime('%H%M%S')}_{run.mode}"
        run_dir.mkdir(parents=True, exist_ok=True)
        run.run_dir = run_dir

        # Set up WebSocket log forwarding (capture loop now, while we're async)
        loop = asyncio.get_running_loop()
        run._loop = loop
        ws_handler = WebSocketForwardingHandler(run.run_id, loop=loop)
        ws_handler.setLevel(logging.INFO)
        root_logger = logging.getLogger()
        root_logger.addHandler(ws_handler)
        run.ws_handler = ws_handler

        # Launch in thread pool
        task = asyncio.create_task(self._run_in_thread(run))
        self._tasks[run.run_id] = task

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

            await ws_manager.send_error(run.run_id, "Analysis was cancelled")
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

    def _execute_pipeline(self, run: AnalysisRun) -> dict[str, Any]:
        """Synchronous pipeline execution (runs in thread pool).

        This method must NOT be called from the async event loop directly.
        """
        rid = run.run_id
        logger.info(f"[{rid}] === PIPELINE STARTED === query='{run.query}' mode={run.mode}")

        # Import here so it picks up the AGENT_MODE env var we just set
        # Add project root to sys.path so `app` module resolves
        project_root_str = str(PROJECT_ROOT)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        from app.agents.logging_setup import setup_agent_logging
        from app.agents.runner import AgentOrchestrator
        from app.agents.tools.shared import set_shared_data
        from app.config import config

        # Set run_dir in shared data for artifact tools
        set_shared_data("run_dir", str(run.run_dir))
        logger.info(f"[{rid}] Output dir: {run.run_dir}")

        # Set up file logging (preserves WebSocket handler)
        handlers_to_preserve = [run.ws_handler] if run.ws_handler else []
        setup_agent_logging(
            log_dir=str(run.run_dir),
            preserve_handlers=handlers_to_preserve,
        )

        # Send agent started messages (use run_coroutine_threadsafe since
        # we're in a thread pool, not on the main event loop)
        agents = ["orchestrator", "analyst", "hypothesis"]
        logger.info(f"[{rid}] Step 1/3: Orchestrator Agent (fetch_posts)")
        logger.info(f"[{rid}] Step 2/3: Analyst Agent (classify_posts, cluster_themes)")
        logger.info(f"[{rid}] Step 3/3: Hypothesis Agent (generate_hypotheses, save_artifact)")
        for i, agent_name in enumerate(agents):
            asyncio.run_coroutine_threadsafe(
                ws_manager.send_agent_started(
                    run_id=run.run_id,
                    agent_name=agent_name,
                    iteration=i + 1,
                    max_iterations=len(agents),
                ),
                run._loop,
            )

        # Run the pipeline
        logger.info(f"[{rid}] Starting AgentOrchestrator.run()")
        orchestrator = AgentOrchestrator()
        result = orchestrator.run(run.query)
        logger.info(f"[{rid}] AgentOrchestrator.run() completed")

        # Save report
        report_file = run.run_dir / "report.md"
        report_file.write_text(
            f"# Reddit Complaint Analysis Report\n\n"
            f"**Query:** {run.query}\n"
            f"**Mode:** {config.agent_mode}\n"
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
        """Cancel a running analysis."""
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
            data = json.loads(hypothesis_file.read_text(encoding="utf-8"))
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


# Singleton instance
analysis_service = AnalysisService()
