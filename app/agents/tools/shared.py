"""Shared data store for passing data between tools without going through LLM context.

This module is imported by individual tool files and by the tool registry,
so it must have no dependencies on other tool modules to avoid circular imports.
"""

from typing import Any

# Shared data store for inter-tool data passing.
# Keys: "fetched_posts", "classified_posts", "clustered_data"
_shared_data: dict[str, Any] = {}


def set_shared_data(key: str, data: Any) -> None:
    """Store data in the shared store."""
    _shared_data[key] = data


def get_shared_data(key: str) -> Any | None:
    """Retrieve data from the shared store."""
    return _shared_data.get(key)


def clear_shared_data() -> None:
    """Clear all shared data (call at start of a new pipeline run)."""
    _shared_data.clear()
