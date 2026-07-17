"""Tests for thinking-token tracking and embedding usage tracking.

Run: ``pytest app/tests/test_usage_tracker_thinking.py -v``

Covers the Phase 1 cost-optimization changes:

- ``UsageTracker.record_usage`` accumulates thinking tokens into the monthly total
- ``UsageTracker.get_usage`` returns the ``thinking_tokens`` field
- Old usage files (pre-Phase-1) without ``thinking_tokens`` load as 0 — backward compat
- ``GCloudProvider._estimate_embedding_tokens`` produces sensible estimates
- ``GCloudProvider._get_embedding_batch`` records estimated input tokens on success
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


# ── UsageTracker: thinking-token accounting ───────────────────────────────────


class TestUsageTrackerThinking:
    def test_thinking_tokens_accumulate_into_total(self, tmp_path: Path):
        from app.services.usage_tracker import UsageTracker

        tracker = UsageTracker(bucket_name=None, local_path=tmp_path)
        tracker.record_usage(input_tokens=100, output_tokens=50, thinking_tokens=200)

        stats = tracker.get_usage()
        assert stats.input_tokens == 100
        assert stats.output_tokens == 50
        assert stats.thinking_tokens == 200
        assert stats.total_tokens == 350  # 100 + 50 + 200

    def test_thinking_tokens_default_zero(self, tmp_path: Path):
        """Old callers passing only (input, output) still work."""
        from app.services.usage_tracker import UsageTracker

        tracker = UsageTracker(bucket_name=None, local_path=tmp_path)
        tracker.record_usage(100, 50)

        stats = tracker.get_usage()
        assert stats.thinking_tokens == 0
        assert stats.total_tokens == 150

    def test_old_usage_file_loads_with_zero_thinking(self, tmp_path: Path):
        """An old usage file without thinking_tokens must load as 0, not crash."""
        from app.services.usage_tracker import UsageTracker

        # Write a legacy file (pre-Phase-1 schema: no thinking_tokens field)
        legacy = tmp_path / "usage-2026-07.json"
        legacy.write_text(
            '{"input_tokens": 300, "output_tokens": 200, "total_tokens": 500, '
            '"month": "2026-07", "updated_at": "2026-07-01T00:00:00"}'
        )

        tracker = UsageTracker(bucket_name=None, local_path=tmp_path)
        stats = tracker.get_usage()

        assert stats.input_tokens == 300
        assert stats.output_tokens == 200
        assert stats.thinking_tokens == 0  # default via .get(..., 0)
        assert stats.total_tokens == 500  # preserved from file

    def test_mixed_calls_accumulate_correctly(self, tmp_path: Path):
        """A run with both thinking and non-thinking calls sums correctly."""
        from app.services.usage_tracker import UsageTracker

        tracker = UsageTracker(bucket_name=None, local_path=tmp_path)
        # Classification call (Flash, thinking disabled via budget=0)
        tracker.record_usage(200, 30, thinking_tokens=0)
        # Hypothesis call (Pro, heavy thinking)
        tracker.record_usage(2000, 800, thinking_tokens=5000)
        # Embedding estimate
        tracker.record_usage(150, 0, thinking_tokens=0)

        stats = tracker.get_usage()
        assert stats.input_tokens == 2350
        assert stats.output_tokens == 830
        assert stats.thinking_tokens == 5000
        assert stats.total_tokens == 8180


# ── GCloudProvider: embedding token estimate helper ──────────────────────────


class TestEstimateEmbeddingTokens:
    def test_short_texts_produce_nonzero_estimate(self):
        from app.analyst.providers.gcloud import GCloudProvider

        texts = ["this is a short post title", "another post about gaming"]
        estimate = GCloudProvider._estimate_embedding_tokens(texts)
        # 5 words * 1.3 + 4 words * 1.3 = ~11 tokens
        assert estimate > 0
        assert estimate < 50  # sanity bound

    def test_empty_batch_returns_zero(self):
        from app.analyst.providers.gcloud import GCloudProvider

        assert GCloudProvider._estimate_embedding_tokens([]) == 0


# ── GCloudProvider: embedding tracker call ───────────────────────────────────


class _TrackerSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
    ) -> None:
        self.calls.append((input_tokens, output_tokens, thinking_tokens))


class _FakeResponse:
    """Minimal stand-in for requests.Response used by _get_embedding_batch."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        pass


class TestEmbeddingBatchRecordsUsage:
    # Import up front — see test_dev_mode.py for the decorator-timing reason.
    from app.analyst.providers.gcloud import GCloudProvider as _Provider

    def test_successful_batch_records_estimated_input(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=False)
        )
        spy = _TrackerSpy()
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.get_usage_tracker", lambda: spy
        )

        batch = ["post title one", "another post here", "third title"]
        fake_response = _FakeResponse(
            {"predictions": [{"embeddings": {"values": [0.1, 0.2, 0.3]}}] * len(batch)}
        )
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.requests.post",
            lambda *a, **kw: fake_response,
        )

        provider = self._Provider.__new__(self._Provider)
        # _get_embedding_batch reads config.clustering_embedding_model + self attrs
        provider._region = "us-central1"
        provider._project = "agenticaicolumbia"
        provider._timeout = 30
        provider._credentials = SimpleNamespace(
            valid=True, token="fake-token"
        )

        result = provider._get_embedding_batch(batch, batch_idx=0)

        assert len(result) == len(batch)
        assert len(spy.calls) == 1, "tracker must be called once on success"
        recorded_input = spy.calls[0][0]
        # 3 titles, ~3 words each * 1.3 ≈ 11 tokens
        assert recorded_input > 0
        assert spy.calls[0][1] == 0  # output
        assert spy.calls[0][2] == 0  # thinking

    def test_dev_mode_skips_tracker_for_embeddings(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Embedding tracking must respect the dev-mode bypass too."""
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=True)
        )
        spy = _TrackerSpy()
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.get_usage_tracker", lambda: spy
        )

        fake_response = _FakeResponse(
            {"predictions": [{"embeddings": {"values": [0.1, 0.2]}}]}
        )
        monkeypatch.setattr(
            "app.analyst.providers.gcloud.requests.post",
            lambda *a, **kw: fake_response,
        )

        provider = self._Provider.__new__(self._Provider)
        provider._region = "us-central1"
        provider._project = "agenticaicolumbia"
        provider._timeout = 30
        provider._credentials = SimpleNamespace(
            valid=True, token="fake-token"
        )

        provider._get_embedding_batch(["a single post"], batch_idx=0)

        assert spy.calls == [], "embeddings must not be tracked in dev mode"


# ── GCloudProvider: classification payload includes thinkingConfig ────────────


class TestClassifyPayloadDisablesThinking:
    """Confirms the cost-reduction payload is wired into _classify_post_call.

    We don't run the request — we inspect the payload that would be sent.
    The payload is built inline inside _classify_post_call, so we patch
    requests.post to capture it.
    """

    from app.analyst.providers.gcloud import GCloudProvider as _Provider

    def test_payload_contains_thinking_budget_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        captured: dict[str, Any] = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["url"] = url
            captured["payload"] = json
            return _FakeResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": '{"theme":"x"}'}]}}
                    ],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
                }
            )

        monkeypatch.setattr(
            "app.analyst.providers.gcloud.requests.post", fake_post
        )
        monkeypatch.setattr(
            "app.config.config", SimpleNamespace(is_development=True)
        )

        provider = self._Provider.__new__(self._Provider)
        provider._region = "us-central1"
        provider._project = "agenticaicolumbia"
        provider._timeout = 30
        provider._credentials = SimpleNamespace(
            valid=True, token="fake-token"
        )

        provider._classify_post_call(prompt="test", model="gemini-2.5-flash")

        gen_cfg = captured["payload"]["generationConfig"]
        assert gen_cfg["maxOutputTokens"] == 256, "maxOutputTokens must drop 1024→256"
        assert gen_cfg.get("thinkingConfig", {}).get("thinkingBudget") == 0, (
            "classification must disable thinking (Flash supports budget=0)"
        )
