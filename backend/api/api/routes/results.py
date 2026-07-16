"""Results endpoint: retrieve completed analysis results."""

import io
import json
import logging
import re
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.models.api import ResultResponse
from app.services.analysis_service import analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{run_id}", response_model=ResultResponse)
async def get_results(run_id: str) -> ResultResponse:
    """Get results for a completed analysis run."""
    run = analysis_service.get_run(run_id)

    run_dir: Path | None = None
    status: str = "completed"
    error: str | None = None
    agent_results: dict | None = None

    if run is not None:
        run_dir = run.run_dir
        status = run.status
        error = run.error
        agent_results = run.result.get("agent_results") if run.result else None
    else:
        # Run was cleaned from memory — look it up on disk
        disk_result = _find_run_dir(run_id)
        if disk_result is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        run_dir, _, _ = disk_result

    # Load hypothesis
    hypothesis = None
    if run_dir:
        hypothesis_path = run_dir / "hypothesis.json"
        if hypothesis_path.exists():
            try:
                from app.models.api import HypothesisOutputAPI
                data = json.loads(hypothesis_path.read_text(encoding="utf-8"))
                hypothesis = HypothesisOutputAPI(**data)
            except Exception:
                pass

    # Load report
    report_content = None
    if run_dir:
        report_path = run_dir / "report.md"
        if report_path.exists():
            try:
                report_content = report_path.read_text(encoding="utf-8")
            except Exception:
                pass

    # Load EDA files
    classification_eda = None
    clustering_eda = None
    if run_dir:
        for filename, target in [
            ("classification_eda.json", "classification"),
            ("clustering_eda.json", "clustering"),
        ]:
            eda_path = run_dir / filename
            if eda_path.exists():
                try:
                    eda_data = json.loads(eda_path.read_text(encoding="utf-8"))
                    if target == "classification":
                        classification_eda = eda_data
                    else:
                        clustering_eda = eda_data
                except Exception:
                    pass

    return ResultResponse(
        run_id=run_id,
        status=status,
        hypothesis=hypothesis,
        report_content=report_content,
        agent_results=agent_results,
        classification_eda=classification_eda,
        clustering_eda=clustering_eda,
        error=error,
    )


@router.get("/{run_id}/file/{filename}")
async def get_result_file(run_id: str, filename: str) -> FileResponse:
    """Serve a file from the run's output directory."""
    run = analysis_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if run.run_dir is None:
        raise HTTPException(status_code=404, detail="Run has no output directory")

    file_path = Path(run.run_dir) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    # Only serve known file types
    allowed_extensions = {".json", ".md", ".jsonl"}
    if file_path.suffix not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not allowed")

    media_types = {
        ".json": "application/json",
        ".md": "text/markdown",
        ".jsonl": "application/x-ndjson",
    }

    return FileResponse(
        path=str(file_path),
        media_type=media_types.get(file_path.suffix, "application/octet-stream"),
        filename=filename,
    )


EXPECTED_OUTPUT_FILES = [
    "subreddit_selection.json",
    "fetch_stats.json",
    "classification_eda.json",
    "clustering_eda.json",
    "hypothesis.json",
    "report.md",
    "workflow_report.md",
]


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for safe use in a filename."""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    sanitized = re.sub(r'[\s\n\r]+', '_', sanitized)
    return sanitized[:50]


def _find_run_dir(run_id: str) -> tuple[Path, str | None, str | None] | None:
    """Find a run directory on disk by scanning for metadata.json.

    Returns (run_dir, query, mode) or None if not found.
    """
    reports_dir = Path(__file__).resolve().parents[4] / "output" / "reports"
    if not reports_dir.exists():
        return None

    # Scan date directories
    for date_dir in reports_dir.iterdir():
        if not date_dir.is_dir():
            continue
        # Scan time directories
        for run_dir in date_dir.iterdir():
            if not run_dir.is_dir():
                continue
            metadata_file = run_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                    if metadata.get("run_id") == run_id:
                        return (
                            run_dir,
                            metadata.get("query"),
                            metadata.get("mode"),
                        )
                except (json.JSONDecodeError, OSError):
                    continue
    return None


@router.get("/{run_id}/zip")
async def download_run_zip(run_id: str) -> StreamingResponse:
    """Create and serve a ZIP archive of all output files for a run."""
    # Try in-memory first
    run = analysis_service.get_run(run_id)

    # Fall back to disk lookup for old runs
    run_dir: Path | None = None
    query: str | None = None
    mode: str | None = None
    started_at: datetime | None = None

    if run is not None:
        if run.run_dir is None:
            raise HTTPException(status_code=404, detail="Run has no output directory")
        run_dir = Path(run.run_dir)
        query = run.query
        mode = run.mode
        started_at = run.started_at
    else:
        # Try to find on disk
        disk_result = _find_run_dir(run_id)
        if disk_result is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        run_dir, query, mode = disk_result

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run directory not found")

    zip_buffer = io.BytesIO()
    missing_files: list[str] = []

    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        agent_run_files = list(run_dir.glob("agent_run_*.jsonl"))
        if agent_run_files:
            zip_file.write(agent_run_files[0], "agent_run.jsonl")
        else:
            missing_files.append("agent_run.jsonl")

        for filename in EXPECTED_OUTPUT_FILES:
            file_path = run_dir / filename
            if file_path.exists():
                zip_file.write(file_path, filename)
            else:
                missing_files.append(filename)

        if missing_files:
            readme_content = (
                f"Analysis Run: {run_id}\n"
                f"Query: {query}\n"
                f"Mode: {mode}\n\n"
                f"Note: The following files were not available:\n" +
                "\n".join(f"  - {f}" for f in missing_files)
            )
            zip_file.writestr("README.txt", readme_content)

    zip_buffer.seek(0)

    timestamp = started_at.strftime("%Y%m%d_%H%M%S") if started_at else run_id[:8]
    query_safe = _sanitize_filename(query) if query else "analysis"
    zip_filename = f"{query_safe}_analysis_{timestamp}.zip"

    return StreamingResponse(
        io.BytesIO(zip_buffer.getvalue()),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )
