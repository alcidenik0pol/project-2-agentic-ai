"""Results endpoint: retrieve completed analysis results."""

import io
import logging
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from backend.app.models.api import ResultResponse
from backend.app.services.analysis_service import analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{run_id}", response_model=ResultResponse)
async def get_results(run_id: str) -> ResultResponse:
    """Get results for a completed analysis run."""
    run = analysis_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    hypothesis = analysis_service.get_hypothesis(run)
    report_content = analysis_service.get_report(run)

    return ResultResponse(
        run_id=run.run_id,
        status=run.status,
        hypothesis=hypothesis,
        report_content=report_content,
        agent_results=run.result.get("agent_results") if run.result else None,
        error=run.error,
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


@router.get("/{run_id}/zip")
async def download_run_zip(run_id: str) -> StreamingResponse:
    """Create and serve a ZIP archive of all output files for a run."""
    run = analysis_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if run.run_dir is None:
        raise HTTPException(status_code=404, detail="Run has no output directory")

    run_dir = Path(run.run_dir)
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
                f"Query: {run.query}\n"
                f"Mode: {run.mode}\n"
                f"Generated: {run.started_at}\n\n"
                f"Note: The following files were not available:\n" +
                "\n".join(f"  - {f}" for f in missing_files)
            )
            zip_file.writestr("README.txt", readme_content)

    zip_buffer.seek(0)

    timestamp = run.started_at.strftime("%Y%m%d_%H%M%S") if run.started_at else run_id[:8]
    query_safe = _sanitize_filename(run.query) if run.query else "analysis"
    zip_filename = f"{query_safe}_analysis_{timestamp}.zip"

    return StreamingResponse(
        io.BytesIO(zip_buffer.getvalue()),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )
