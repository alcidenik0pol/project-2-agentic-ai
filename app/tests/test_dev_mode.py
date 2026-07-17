"""Tests for the dev-mode token-tracking bypass.

Run: ``pytest app/tests/test_dev_mode.py -v``

Covers:
- ``Config.is_development`` reflects ``APP_ENV``
- ``gcloud._record_usage`` is a no-op in dev mode
- ``/api/v1/usage`` returns ``tracking_enabled=False`` and zeros in dev

The dev-mode bypass is a single boolean on the module-level ``config`` singleton,
read via late ``from app.config import config`` imports inside each function
body. We therefore exercise behavior by patching ``app.config.config`` directly,
not by reloading modules.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest


# ── Config field ──────────────────────────────────────────────────────────────


class TestConfigIsDevelopment:
    def test_default_is_development(self):
        from app.config import Config

        c = Config(reddit_user_agent="test")
        assert c.environment == "development"
        assert c.is_development is True

    def test_app_env_production(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "production")
        from app.config import Config

        c = Config.from_env()
        assert c.environment == "production"
        assert c.is_development is False

    def test_app_env_development(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "development")
        from app.config import Config

        c = Config.from_env()
        assert c.is_development is True

    def test_unknown_value_treated_as_not_dev(self, monkeypatch: pytest.MonkeyPatch):
        # Anything other than "development" should fail closed (treat as prod).
        monkeypatch.setenv("APP_ENV", "staging")
        from app.config import Config

        c = Config.from_env()
        assert c.is_development is False


# ── GCloudProvider._record_usage ─────────────────────────────────────────────


class _TrackerSpy:
    """Records calls to ``record_usage`` so we can assert it was/wasn't hit."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
    ) -> None:
        self.calls.append((input_tokens, output_tokens, thinking_tokens))


class TestRecordUsageDevBypass:
    # Import up front so the @retry_with_exponential_backoff decorator (which
    # reads config attributes at class-definition time) runs against the real
    # config. Subsequent monkeypatching of app.config.config then only affects
    # late-binding reads inside method bodies.
    from app.analyst.providers.gcloud import GCloudProvider as _Provider

    def test_dev_mode_does_not_call_tracker(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=True)
        )
        spy = _TrackerSpy()
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.get_usage_tracker", lambda: spy
        )

        provider = self._Provider.__new__(self._Provider)
        provider._record_usage({"usageMetadata": {"promptTokenCount": 100}})

        assert spy.calls == [], "tracker must not be called in dev mode"

    def test_prod_mode_calls_tracker(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=False)
        )
        spy = _TrackerSpy()
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.get_usage_tracker", lambda: spy
        )

        provider = self._Provider.__new__(self._Provider)
        provider._record_usage(
            {
                "usageMetadata": {
                    "promptTokenCount": 100,
                    "candidatesTokenCount": 50,
                    "thoughtsTokenCount": 30,
                }
            }
        )

        assert spy.calls == [(100, 50, 30)]

    def test_prod_mode_records_zero_thinking_when_field_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Older / non-thinking responses omit thoughtsTokenCount → record 0."""
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=False)
        )
        spy = _TrackerSpy()
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.get_usage_tracker", lambda: spy
        )

        provider = self._Provider.__new__(self._Provider)
        provider._record_usage(
            {"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50}}
        )

        assert spy.calls == [(100, 50, 0)]

    def test_dev_mode_noop_even_with_full_usage_metadata(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Sanity: a realistic response payload still produces no call in dev."""
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=True)
        )
        spy = _TrackerSpy()
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.get_usage_tracker", lambda: spy
        )

        provider = self._Provider.__new__(self._Provider)
        provider._record_usage(
            {
                "candidates": [{"content": {"parts": [{"text": "hi"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 9999,
                    "candidatesTokenCount": 9999,
                    "totalTokenCount": 19998,
                },
            }
        )

        assert spy.calls == []


# ── /api/v1/usage endpoint ────────────────────────────────────────────────────


class _FakeStats:
    total_tokens = 500
    input_tokens = 300
    output_tokens = 150
    thinking_tokens = 50
    month = "2026-07"


class _FakeTracker:
    limit = 1_000_000

    def get_usage(self) -> _FakeStats:
        return _FakeStats()

    def get_next_reset_date(self):  # pragma: no cover - only called in prod path
        from datetime import datetime

        return datetime(2026, 8, 1)

    def get_remaining_percent(self) -> float:
        return 50.0


class TestUsageEndpointDevBypass:
    def test_dev_returns_tracking_disabled(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=True)
        )

        from backend.app.api.routes.usage import get_usage

        response = asyncio.run(get_usage())

        assert response.tracking_enabled is False
        assert response.used == 0
        assert response.limit == 0
        assert response.remaining == 0
        assert response.percent_remaining == 0.0
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.thinking_tokens == 0

    def test_prod_returns_tracking_enabled(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=False)
        )
        # NOTE: ``app/services/__init__.py`` re-exports the module-level
        # ``usage_tracker`` (a ``property`` object — see usage_tracker.py:284),
        # which shadows ``app.services.usage_tracker`` (the submodule) at the
        # package level. Use sys.modules to grab the real module.
        import sys

        usage_tracker_module = sys.modules["app.services.usage_tracker"]
        monkeypatch.setattr(
            usage_tracker_module, "get_usage_tracker", lambda: _FakeTracker()
        )

        from backend.app.api.routes.usage import get_usage

        response = asyncio.run(get_usage())

        assert response.tracking_enabled is True
        assert response.used == 500
        assert response.limit == 1_000_000
        assert response.remaining == 999_500
        assert response.month == "2026-07"
        assert response.input_tokens == 300
        assert response.output_tokens == 150
        assert response.thinking_tokens == 50

    def test_dev_does_not_instantiate_tracker(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """The dev branch must not import or call the tracker at all."""
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=True)
        )
        import sys

        usage_tracker_module = sys.modules["app.services.usage_tracker"]

        def _fail_if_called(*_a: Any, **_kw: Any) -> None:
            raise AssertionError("tracker must not be reached in dev mode")

        monkeypatch.setattr(
            usage_tracker_module, "get_usage_tracker", _fail_if_called
        )

        from backend.app.api.routes.usage import get_usage

        # Should not raise.
        asyncio.run(get_usage())
