"""Results endpoint: retrieve completed analysis results."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

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
