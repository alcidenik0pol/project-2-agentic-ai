"""save_artifact tool: persists output data to the run's output directory."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from app.agents.tools.shared import get_shared_data

logger = logging.getLogger(__name__)

SAVE_ARTIFACT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_artifact",
        "description": (
            "Save analysis output to a JSON file. "
            "Use this to persist final results like hypotheses, clustering results, "
            "or classified posts for later review."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "data_json": {
                    "type": "string",
                    "description": "JSON string of the data to save.",
                },
                "artifact_type": {
                    "type": "string",
                    "description": "Type of artifact: 'hypothesis', 'clustering', 'classified', or 'report'.",
                    "enum": ["hypothesis", "clustering", "classified", "report"],
                },
            },
            "required": ["data_json", "artifact_type"],
        },
    },
}


def _resolve_output_dir() -> Path:
    """Get the output directory for this run.

    Checks shared data for a run_dir set by the CLI.
    Falls back to output/ if not found.
    """
    run_dir = get_shared_data("run_dir")
    if run_dir:
        return Path(run_dir)

    # Fallback: output/ at project root
    output_dir = Path("output")
    if not output_dir.exists():
        project_root = Path(__file__).resolve().parents[3]
        output_dir = project_root / "output"
    return output_dir


def _resolve_full_data(data_json: str, artifact_type: str) -> str:
    """Detect truncation metadata and retrieve full data from shared store.

    When the LLM passes a truncation summary to save_artifact (instead of
    real data), this function intercepts it and retrieves the full data
    that was stored in shared memory by the upstream tool.

    Also handles the preemptive pattern where tools store data under
    known keys (e.g., hypotheses_full).

    Args:
        data_json: The data_json string passed by the LLM.
        artifact_type: The artifact type being saved.

    Returns:
        The full data as a JSON string, or the original data_json if no
        truncation was detected.
    """
    try:
        parsed = json.loads(data_json)
    except json.JSONDecodeError:
        return data_json

    if not isinstance(parsed, dict):
        return data_json

    # Case 1: base.py truncation metadata
    if parsed.get("status") == "truncated" and "shared_key" in parsed:
        shared_key = parsed["shared_key"]
        full_data = get_shared_data(shared_key)
        if full_data is not None:
            logger.info(
                f"Retrieved full data from shared key '{shared_key}' "
                f"(truncation detected for {artifact_type})"
            )
            return full_data if isinstance(full_data, str) else json.dumps(full_data, ensure_ascii=False, default=str)

    # Case 2: Preemptive pattern — tool stored data under a known key
    known_keys = {
        "hypothesis": "hypotheses_full",
        "clustering": "clustered_data",
    }
    shared_key = known_keys.get(artifact_type)
    if shared_key:
        full_data = get_shared_data(shared_key)
        if full_data is not None:
            # Use the full data from shared store — this is the authoritative source
            logger.info(f"Using full data from shared key '{shared_key}' for {artifact_type}")
            return full_data if isinstance(full_data, str) else json.dumps(full_data, ensure_ascii=False, default=str)

    return data_json


def save_artifact(data_json: str, artifact_type: str) -> str:
    """Save data to a JSON file in the run's output directory.

    Args:
        data_json: JSON string of the data to save.
        artifact_type: One of 'hypothesis', 'clustering', 'classified', 'report'.

    Returns:
        JSON string with the saved file path.
    """
    logger.info(f"  [ARTIFACT] Starting save_artifact: type={artifact_type}")
    t0 = time.time()
    output_dir = _resolve_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{artifact_type}.json"
    filepath = output_dir / filename

    # Resolve full data from shared store if truncation occurred
    data_json = _resolve_full_data(data_json, artifact_type)

    try:
        # Parse and re-serialize for pretty formatting
        parsed = json.loads(data_json)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"  [ARTIFACT] Completed: {artifact_type} saved to {filepath} in {time.time() - t0:.1f}s")

        # Generate workflow report after hypothesis artifact is saved (final step)
        if artifact_type == "hypothesis":
            try:
                from app.agents.tools.run_logger import save_workflow_report
                save_workflow_report()
            except Exception as report_err:
                logger.warning(f"Failed to generate workflow report: {report_err}")

        return json.dumps({
            "status": "saved",
            "path": str(filepath),
            "artifact_type": artifact_type,
            "size_bytes": filepath.stat().st_size,
        })
    except json.JSONDecodeError as e:
        # Save raw text if not valid JSON
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(data_json)
        logger.warning(f"Saved raw text (invalid JSON): {filepath}")
        return json.dumps({
            "status": "saved_raw",
            "path": str(filepath),
            "warning": f"Data was not valid JSON: {e}",
        })
    except Exception as e:
        logger.error(f"Failed to save artifact: {e}")
        return json.dumps({"error": f"Failed to save: {e}"})
