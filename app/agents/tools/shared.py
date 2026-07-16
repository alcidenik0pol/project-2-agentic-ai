"""Shared data store for passing data between tools without going through LLM context.

This module is imported by individual tool files and by the tool registry,
so it must have no dependencies on other tool modules to avoid circular imports.
"""

import threading
from typing import Any

# Shared data store for inter-tool data passing.
# Keys: "fetched_posts", "classified_posts", "clustered_data"
_shared_data: dict[str, Any] = {}


class PipelineCancelled(Exception):
    """Raised to cooperatively interrupt the pipeline after a cancel request.

    Carries no payload; callers just need the type to break out of long loops
    (e.g. the per-subreddit fetch loop). Propagates up through the thread pool
    to the async wrapper, which translates it into a cancelled status.
    """


# Module-level cancel event. A single event suffices because the system runs one
# analysis at a time (Cloud Run max-instances=1). clear_shared_data() wipes it.
_shared_data["cancel_event"] = threading.Event()


def request_cancel() -> None:
    """Signal the running pipeline to stop at its next cooperative check."""
    event = _shared_data.get("cancel_event")
    if event is None:
        event = threading.Event()
        _shared_data["cancel_event"] = event
    event.set()


def is_cancelled() -> bool:
    """Return True if a cancel has been requested for the current run."""
    event = _shared_data.get("cancel_event")
    return bool(event is not None and event.is_set())


def clear_cancel() -> None:
    """Reset the cancel flag (call at the start of a new run)."""
    event = _shared_data.get("cancel_event")
    if event is not None:
        event.clear()


def set_shared_data(key: str, data: Any) -> None:
    """Store data in the shared store."""
    _shared_data[key] = data


def get_shared_data(key: str) -> Any | None:
    """Retrieve data from the shared store."""
    return _shared_data.get(key)


def clear_shared_data() -> None:
    """Clear all shared data (call at start of a new pipeline run)."""
    _shared_data.clear()
    # Re-seed a fresh cancel event so the flag is always reset for the new run.
    _shared_data["cancel_event"] = threading.Event()
