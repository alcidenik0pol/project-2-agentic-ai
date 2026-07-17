"""Thread-safe circuit breaker for Reddit API 429 rate-limit cascades.

Lives at the client singleton level so that all concurrent pipeline runs
(which share a single ``redditapiv2_client`` / ``reddit_client`` instance)
see the *aggregate* 429 rate and pause together. A per-fetcher breaker
cannot do this — three concurrent runs each seeing 2 local 429s would never
hit the threshold, even though the proxy IP is seeing 6.

Design
------
- **Consecutive-429 counter** (shared, lock-guarded). Any successful response
  resets both the counter and the cooldown budget — a success means the IP is
  alive, the burst was transient.
- **Cooldown gate** (``_cooldown_until`` timestamp). When the counter hits the
  threshold, every thread calling ``before_request`` blocks until the cooldown
  expires. This is what lets the proxy IP actually cool down — all callers
  pause simultaneously instead of one pausing while the rest keep hammering.
- **Trip state**. After ``MAX_COOLDOWNS`` cooldowns with no intervening
  success, the breaker trips permanently (for the process lifetime) and every
  subsequent request fails fast via ``CircuitBreakerOpen``.

Constants are intentionally hardcoded — this is a safety valve, not a tuning
knob.
"""

import logging
import threading
import time

from app.agents.tools.shared import PipelineCancelled, is_cancelled

logger = logging.getLogger(__name__)

# Thresholds — hardcoded per the module docstring.
_RATE_LIMIT_THRESHOLD = 3   # consecutive 429-exhausted errors before a cooldown
_COOLDOWN_SECONDS = 60      # how long to pause all callers
_MAX_COOLDOWNS = 2          # after this many cooldowns in a burst, trip permanently


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker has tripped — Reddit is blocking the IP.

    Fetchers catch this to ``break`` out of the subreddit loop cleanly instead
    of burning through remaining subreddits (each failing instantly).
    """


class CircuitBreaker:
    """Shared 429 circuit breaker for a Reddit client singleton.

    Thread-safe. Three entry points:

    - ``before_request()`` — call before ``session.request()``. Blocks during
      cooldown (cancellable via ``is_cancelled()``). Raises ``CircuitBreakerOpen``
      if the breaker has tripped.
    - ``on_success()`` — call after a successful response. Resets counters.
    - ``on_429()`` — call after a 429-exhausted ``RetryError``. May set a
      cooldown or trip the breaker.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._consecutive_429s: int = 0
        self._cooldowns_used: int = 0
        self._cooldown_until: float = 0.0
        self._tripped: bool = False

    @property
    def is_tripped(self) -> bool:
        """Whether the breaker has permanently tripped (fail-fast state)."""
        with self._lock:
            return self._tripped

    def before_request(self) -> None:
        """Gate that every request passes through.

        - If the breaker is tripped: raises ``CircuitBreakerOpen`` immediately.
        - If a cooldown is active: blocks (checking cancel every second) until
          the cooldown expires, THEN re-checks the trip state (another thread
          may have tripped it during our wait).
        - Otherwise: returns immediately, letting the caller proceed.
        """
        while True:
            with self._lock:
                remaining = self._cooldown_until - time.time()
                if remaining <= 0:
                    if self._tripped:
                        raise CircuitBreakerOpen(
                            f"Rate limit circuit breaker tripped after "
                            f"{_MAX_COOLDOWNS} cooldowns — Reddit is blocking "
                            f"the proxy IP. All Reddit requests will fail."
                        )
                    return  # coast is clear — proceed to the request

            # A cooldown is active but we're outside the lock. Wait in
            # 1-second slices so a cancel arrives within ~1s.
            if is_cancelled():
                raise PipelineCancelled()
            time.sleep(min(remaining, 1.0))

    def on_success(self) -> None:
        """Record a successful response. Resets the 429 streak and cooldown budget."""
        with self._lock:
            self._consecutive_429s = 0
            self._cooldowns_used = 0

    def on_429(self) -> None:
        """Record a 429-exhausted RetryError.

        After ``_RATE_LIMIT_THRESHOLD`` consecutive 429s, sets a cooldown gate
        that blocks all callers. After ``_MAX_COOLDOWNS`` cooldowns without an
        intervening success, trips the breaker permanently.
        """
        with self._lock:
            self._consecutive_429s += 1
            if self._consecutive_429s < _RATE_LIMIT_THRESHOLD:
                return  # not enough consecutive 429s yet

            # Threshold reached — either cooldown or trip.
            self._consecutive_429s = 0
            self._cooldowns_used += 1

            if self._cooldowns_used > _MAX_COOLDOWNS:
                self._tripped = True
                logger.error(
                    "Rate limit circuit breaker TRIPPED: %d cooldowns exhausted "
                    "with no success. Reddit is blocking the proxy IP — aborting.",
                    _MAX_COOLDOWNS,
                )
                return

            self._cooldown_until = time.time() + _COOLDOWN_SECONDS
            logger.warning(
                "Rate limit: %d consecutive 429s. Cooling down %ds "
                "(cooldown %d/%d) — pausing ALL Reddit requests.",
                _RATE_LIMIT_THRESHOLD,
                _COOLDOWN_SECONDS,
                self._cooldowns_used,
                _MAX_COOLDOWNS,
            )
