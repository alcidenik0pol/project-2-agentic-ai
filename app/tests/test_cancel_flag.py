# Unit tests for the cooperative cancel flag (Issue 2).
# Verifies the round-trip behavior of request_cancel/is_cancelled/clear_cancel
# and that execute_tool re-raises PipelineCancelled instead of swallowing it
# into a JSON tool-error string.
"""Offline unit tests for the cooperative cancel flag.

Run: ``pytest app/tests/test_cancel_flag.py -v``
"""

import json

import pytest

from app.agents.tools import execute_tool
from app.agents.tools.shared import (
    PipelineCancelled,
    clear_cancel,
    clear_shared_data,
    is_cancelled,
    request_cancel,
)


@pytest.fixture(autouse=True)
def _reset_flag():
    """Ensure a clean cancel state before and after every test."""
    clear_cancel()
    yield
    clear_cancel()


class TestFlagRoundTrip:
    def test_initially_not_cancelled(self):
        assert is_cancelled() is False

    def test_request_then_check(self):
        request_cancel()
        assert is_cancelled() is True

    def test_clear_after_request(self):
        request_cancel()
        assert is_cancelled() is True
        clear_cancel()
        assert is_cancelled() is False

    def test_clear_when_not_set_is_noop(self):
        # Clearing an unset flag must not error and must stay False.
        clear_cancel()
        assert is_cancelled() is False

    def test_request_is_idempotent(self):
        request_cancel()
        request_cancel()
        assert is_cancelled() is True

    def test_survives_shared_data_clear(self):
        # clear_shared_data() wipes the store then re-seeds a fresh event,
        # so the flag must read False immediately after (no stale cancel).
        request_cancel()
        assert is_cancelled() is True
        clear_shared_data()
        assert is_cancelled() is False


class TestExecuteToolPropagatesCancel:
    def test_execute_tool_reraises_pipeline_cancelled(self, monkeypatch):
        """execute_tool must NOT swallow PipelineCancelled into a JSON error."""
        def _raising_tool(**_kwargs):
            raise PipelineCancelled()

        # Inject a temporary tool into the registry and point the lookup at it.
        from app.agents.tools import _TOOL_REGISTRY

        _TOOL_REGISTRY["__test_cancel__"] = ({}, _raising_tool)
        monkeypatch.setattr(
            "app.agents.tools.get_tool_function",
            lambda name: _raising_tool if name == "__test_cancel__" else None,
        )

        with pytest.raises(PipelineCancelled):
            execute_tool("__test_cancel__", {})

        # Cleanup so the temp entry doesn't leak to other tests/runs.
        _TOOL_REGISTRY.pop("__test_cancel__", None)

    def test_execute_tool_returns_json_for_generic_error(self, monkeypatch):
        """Sanity: non-cancel exceptions are still turned into JSON errors."""
        def _failing_tool(**_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "app.agents.tools.get_tool_function",
            lambda name: _failing_tool,
        )

        result = execute_tool("__generic_fail__", {})
        assert isinstance(result, str)
        payload = json.loads(result)
        assert "error" in payload
        assert "boom" in payload["error"]
