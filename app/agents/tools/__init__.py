"""Tool registry: maps tool names to their OpenAI schemas and Python functions."""

import json
import logging
from typing import Any, Callable

from app.agents.tools.artifacts import SAVE_ARTIFACT_SCHEMA, save_artifact
from app.agents.tools.classify import CLASSIFY_POSTS_SCHEMA, classify_posts
from app.agents.tools.cluster import CLUSTER_THEMES_SCHEMA, cluster_themes
from app.agents.tools.fetch import FETCH_POSTS_SCHEMA, fetch_posts
from app.agents.tools.hypothesis import GENERATE_HYPOTHESES_SCHEMA, generate_hypotheses
from app.agents.tools.shared import clear_shared_data, get_shared_data, set_shared_data
from app.utils.timing import timed

logger = logging.getLogger(__name__)

# Tool registry: name -> (schema, function)
_TOOL_REGISTRY: dict[str, tuple[dict, Callable]] = {
    "fetch_posts": (FETCH_POSTS_SCHEMA, fetch_posts),
    "classify_posts": (CLASSIFY_POSTS_SCHEMA, classify_posts),
    "cluster_themes": (CLUSTER_THEMES_SCHEMA, cluster_themes),
    "generate_hypotheses": (GENERATE_HYPOTHESES_SCHEMA, generate_hypotheses),
    "save_artifact": (SAVE_ARTIFACT_SCHEMA, save_artifact),
}

# Agent -> allowed tools mapping
AGENT_TOOLS: dict[str, list[str]] = {
    "orchestrator": ["fetch_posts"],
    "analyst": ["classify_posts", "cluster_themes"],
    "hypothesis": ["generate_hypotheses", "save_artifact"],
}


def get_tool_schemas(agent_name: str) -> list[dict]:
    """Get OpenAI function-calling schemas for an agent's tools."""
    tool_names = AGENT_TOOLS.get(agent_name, [])
    schemas = []
    for name in tool_names:
        if name in _TOOL_REGISTRY:
            schemas.append(_TOOL_REGISTRY[name][0])
    return schemas


def get_tool_function(tool_name: str) -> Callable | None:
    """Get the Python function for a tool by name."""
    entry = _TOOL_REGISTRY.get(tool_name)
    return entry[1] if entry else None


@timed("execute_tool")
def execute_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name with the given arguments.

    Returns the tool's output as a string.
    """
    func = get_tool_function(tool_name)
    if func is None:
        return f"Error: Unknown tool '{tool_name}'"

    logger.info(f"Executing tool: {tool_name}({list(arguments.keys())})")
    try:
        result = func(**arguments)
        logger.info(f"Tool {tool_name} completed successfully")
        return result
    except Exception as e:
        error_msg = f"Tool {tool_name} failed: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
