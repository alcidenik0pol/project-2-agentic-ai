# Unit tests for the Reddit client circuit breaker.
# Verifies the state machine: consecutive-429 counting, cooldown gating,
# permanent trip after MAX_COOLDOWNS, and success-reset behavior.
"""Offline unit tests for :mod:`app.reddit.circuit_breaker`.

Run: ``pytest app/tests/test_circuit_breaker.py -v``
"""

import time

import pytest

from app.reddit import circuit_breaker as cb_module
from app.reddit.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


@pytest.fixture(autouse=True)
def _short_thresholds(monkeypatch):
    """Use tiny thresholds so tests don't wait 60s for a real cooldown."""
    monkeypatch.setattr(cb_module, "_RATE_LIMIT_THRESHOLD", 2)
    monkeypatch.setattr(cb_module, "_MAX_COOLDOWNS", 2)
    # Keep COOLDOWN_SECONDS real for the blocking test; individual tests
    # can override it.


class TestFreshBreaker:
    def test_before_request_returns_immediately(self):
        breaker = CircuitBreaker()
        breaker.before_request()  # must not block or raise

    def test_not_tripped(self):
        breaker = CircuitBreaker()
        assert breaker.is_tripped is False


class TestCountingAndCooldown:
    def test_below_threshold_does_not_set_cooldown(self):
        breaker = CircuitBreaker()
        breaker.on_429()  # 1 of 2
        breaker.before_request()  # must not block
        assert breaker.is_tripped is False

    def test_threshold_sets_cooldown(self):
        breaker = CircuitBreaker()
        breaker.on_429()
        breaker.on_429()  # hits threshold (2) → cooldown #1
        assert breaker.is_tripped is False

    def test_before_request_blocks_during_cooldown(self, monkeypatch):
        monkeypatch.setattr(cb_module, "_COOLDOWN_SECONDS", 1)
        breaker = CircuitBreaker()
        breaker.on_429()
        breaker.on_429()  # triggers cooldown

        start = time.monotonic()
        breaker.before_request()  # blocks ~1s
        elapsed = time.monotonic() - start
        assert elapsed >= 0.8, f"Expected ~1s cooldown, waited {elapsed:.2f}s"

    def test_before_request_does_not_block_after_cooldown_expires(self, monkeypatch):
        monkeypatch.setattr(cb_module, "_COOLDOWN_SECONDS", 0)
        breaker = CircuitBreaker()
        breaker.on_429()
        breaker.on_429()  # cooldown with 0s duration
        breaker.before_request()  # expires instantly, must not raise
        assert breaker.is_tripped is False


class TestTripBehavior:
    def test_trips_after_max_cooldowns(self):
        """Two cooldowns (threshold=2, max=2) → third burst trips."""
        breaker = CircuitBreaker()
        # Cooldown #1
        breaker.on_429()
        breaker.on_429()
        # Cooldown #2
        breaker.on_429()
        breaker.on_429()
        # Now the NEXT threshold-exceeding burst should trip (cooldown #3 > max)
        breaker.on_429()
        breaker.on_429()
        assert breaker.is_tripped is True

    def test_before_request_raises_when_tripped(self):
        breaker = CircuitBreaker()
        # Force-trip by exhausting all cooldowns.
        for _ in range(6):  # 3 bursts of 2 = 3 cooldowns, last one trips
            breaker.on_429()
        assert breaker.is_tripped is True
        with pytest.raises(CircuitBreakerOpen):
            breaker.before_request()


class TestSuccessResets:
    def test_success_resets_consecutive_counter(self):
        breaker = CircuitBreaker()
        breaker.on_429()
        breaker.on_success()  # reset
        breaker.on_429()  # now only 1 of 2 — must NOT trigger cooldown
        breaker.before_request()  # must not block
        assert breaker.is_tripped is False

    def test_success_resets_cooldown_budget(self):
        """A success between bursts resets the cooldown count."""
        breaker = CircuitBreaker()
        breaker.on_429()
        breaker.on_429()  # cooldown #1
        breaker.on_success()  # resets cooldowns_used
        breaker.on_429()
        breaker.on_429()  # cooldown #1 again (not #2)
        assert breaker.is_tripped is False
