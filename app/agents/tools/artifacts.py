"""save_artifact tool: persists output data to the run's output directory."""

import json
import logging
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


def save_artifact(data_json: str, artifact_type: str) -> str:
    """Save data to a JSON file in the run's output directory.

    Args:
        data_json: JSON string of the data to save.
        artifact_type: One of 'hypothesis', 'clustering', 'classified', 'report'.

    Returns:
        JSON string with the saved file path.
    """
    output_dir = _resolve_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{artifact_type}.json"
    filepath = output_dir / filename

    try:
        # Parse and re-serialize for pretty formatting
        parsed = json.loads(data_json)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Artifact saved: {filepath}")
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
