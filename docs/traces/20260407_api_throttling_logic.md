# API Throttling Logic Trace

**Timestamp**: 2026-04-07
**Author**: Claude (trace documentation)

---

## Overview

The system implements rate limiting for Reddit's public JSON API at two levels:
1. **`app/reddit/client.py`** — `RedditPublicAPI` class (primary implementation)
2. **`app/collector/rate_limiter.py`** — `RedditRateLimiter` dataclass (standalone utility)

---

## Reddit API Rate Limits

| Authentication | Rate Limit |
|----------------|------------|
| Unauthenticated | 10 requests/minute per IP |
| Authenticated (OAuth) | 60 requests/minute |

Our implementation uses **unauthenticated** access, so we enforce the 10 req/min limit.

---

## Primary Implementation: `RedditPublicAPI`

**Location**: `app/reddit/client.py:21-269`

### Core Mechanism

```
_request_times: list[float]  # Timestamps of requests in current 60s window
_total_requests: int         # Lifetime request counter
```

### Throttling Flow

```
_make_request()
    │
    ▼
_wait_for_rate_limit()
    │
    ├── Clean old timestamps (>60s ago)
    │
    ├── Check: len(_request_times) >= 10 ?
    │   │
    │   ├── YES → Calculate wait time
    │   │          wait_time = 60 - (now - oldest) + 1  // +1s buffer
    │   │          time.sleep(wait_time)
    │   │          _request_times = []  // Reset after wait
    │   │
    │   └── NO  → Proceed immediately
    │
    ▼
Execute request
Record timestamp
Increment counter
```

### Key Properties

| Property | Returns |
|----------|---------|
| `requests_in_window` | Count of requests in last 60s |
| `requests_remaining` | `max(0, 10 - requests_in_window)` |
| `is_throttled` | `requests_in_window >= 10` |
| `seconds_until_reset` | Time until oldest request expires |
| `throttle_wait_time` | Seconds to wait if throttled, else `None` |

### Status Dict (for frontend)

```python
{
    "requests_in_window": int,
    "requests_remaining": int,
    "window_reset_time": float,      # Unix timestamp
    "seconds_until_reset": float,
    "is_throttled": bool,
    "throttle_wait_time": float | None,
    "limit": 10,
    "window_seconds": 60,
}
```

---

## Secondary Implementation: `RedditRateLimiter`

**Location**: `app/collector/rate_limiter.py:21-116`

A standalone dataclass that can be used independently of the API client.

### Differences from Primary

| Aspect | `RedditPublicAPI` | `RedditRateLimiter` |
|--------|-------------------|---------------------|
| Integration | Built into client | Standalone utility |
| Configurable limit | Hardcoded 10 | `requests_per_minute` param |
| ETA tracking | No | Yes (via `log_progress()`) |
| Request recording | Automatic | Manual (`record_request()`) |

### Usage Pattern

```python
limiter = RedditRateLimiter(requests_per_minute=10)

# Before each request
limiter.wait_if_needed()

# After request completes
limiter.record_request()

# Log progress
limiter.log_progress(current=50, total=100, description="Fetching posts")
```

---

## HTTP Retry Strategy

**Location**: `app/reddit/client.py:35-42`

The client also implements automatic retries via `urllib3`:

```python
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
```

- **Max retries**: 3
- **Backoff**: Exponential with factor 1 (1s, 2s, 4s)
- **Retry on**: 429 (rate limit), 5xx errors

---

## Tests

**Location**: `tests/test_rate_limit_metrics.py`

Validates:
- Initial state (0 requests, 10 remaining)
- Status dict structure and JSON serialization
- State transitions after simulated requests
- Throttle detection at 10 requests

---

## Flow Diagram

```
User Request
     │
     ▼
┌─────────────────────────────────────────┐
│           RedditPublicAPI               │
│  ┌─────────────────────────────────┐   │
│  │      _wait_for_rate_limit()     │   │
│  │                                 │   │
│  │   requests < 10?                │   │
│  │     │                           │   │
│  │     ├── YES → proceed           │   │
│  │     │                           │   │
│  │     └── NO  → sleep(wait_time)  │   │
│  │              reset timestamps   │   │
│  └─────────────────────────────────┘   │
│                                        │
│  Execute HTTP request (with retries)   │
│  Record timestamp                      │
└─────────────────────────────────────────┘
     │
     ▼
Response / Exception
```

---

## Notes

1. **Two implementations exist** but only `RedditPublicAPI` is actively used in production code (`RedditFetcher` uses it directly).

2. **The standalone `RedditRateLimiter`** appears unused — `fetcher.py` has its own `_log_progress()` method rather than using the limiter's.

3. **Buffer of +1 second** is added to wait times to avoid edge cases where requests arrive exactly at the boundary.

4. **No persistence** — rate limit state is in-memory only and resets on application restart.
