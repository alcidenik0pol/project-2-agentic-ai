# Trace: Client-Level 429 Circuit Breaker

**Date:** 2026-07-16
**Status:** Done (unit-tested); live end-to-end verification pending

---

## Problem

Production runs against `old.reddit.com` via the IPVanish SOCKS5 proxy
degrade silently when Reddit rate-limits the proxy IP. The production log
(run `ee612ece0a71`, 2026-07-16 17:45–17:55) shows the cascade:

```
[17:47:12] Error fetching comments for 1uxcs6e: SOCKSHTTPSConnectionPool(
  host='old.reddit.com', port=443): Max retries exceeded with url: ...
  (Caused by ResponseError('too many 429 error responses'))
[17:48:02] Error fetching from r/mildlyinfuriating: ... too many 429 ...
[17:48:08] Error fetching from r/talesfromtechsupport: ... too many 429 ...
```

The first fetch (17:45:51–17:46:51) succeeded with **zero** 429s — 100
posts, 551 comments, 70 requests. The 429s only started ~90 seconds later
when **three concurrent pipeline runs** (`ee612ece0a71`, `409877cd582f`,
`6fa9489edf6d`) shared the singleton `redditapiv2_client` and collectively
overwhelmed the proxy IP.

### What the original plan got wrong

The approved plan proposed a per-fetcher circuit breaker in
`fetch_posts_for_topic`'s subreddit loop, keyed on `"429" in str(e)`. Two
flaws:

1. **Dead code:** `_fetch_from_subreddit` catches `Exception` internally and
   returns an empty list. The outer loop's `except` block never sees the 429.
2. **Wrong scope:** Even if the 429 escaped, a per-fetcher breaker only sees
   ONE run's 429s. With 3 concurrent runs each seeing 2 local 429s, none
   hits the threshold — but the proxy IP sees 6 simultaneously.

---

## Root Cause

The `redditapiv2_client` / `reddit_client` is a **module-level singleton**.
All concurrent pipeline runs (Cloud Run serves concurrent requests via
`loop.run_in_executor` threads) funnel through it. The existing pacing
tracker (`_request_times`) was already shared, but there was no shared 429
tracking — so no single place saw the aggregate rate that was tripping the
proxy IP.

---

## Solution

Circuit breaker at the **client singleton level**, not the fetcher level.

### New module: `app/reddit/circuit_breaker.py`

Thread-safe `CircuitBreaker` class with three entry points:

- **`before_request()`** — gate that every `session.request()` call passes
  through. Blocks during cooldown (all threads pause together — this is the
  key property that lets the proxy IP actually cool down). Raises
  `CircuitBreakerOpen` if the breaker has tripped.
- **`on_success()`** — resets both the consecutive-429 counter and the
  cooldown budget. A success means the IP is alive; the burst was transient.
- **`on_429()`** — counts consecutive 429s. After `_RATE_LIMIT_THRESHOLD` (3),
  sets a `_cooldown_until` timestamp. After `_MAX_COOLDOWNS` (2) cooldowns
  without an intervening success, trips permanently.

### Detection

urllib3's `Retry(total=3, status_forcelist=[429])` exhausts on 429 and
raises `requests.exceptions.RetryError` with `ResponseError('too many 429
error responses')` in the message. The client catches
`requests.exceptions.RequestException` and checks `"429" in str(e)` —
robust across `RetryError` / `ConnectionError` wrappers.

### Why `before_request()` blocks all threads

The cooldown is a **timestamp gate** (`_cooldown_until`), not a per-thread
sleep. When thread A detects the 3rd consecutive 429 and sets the gate,
threads B, C, D all hit `before_request()` and block on the same timestamp.
This is what makes the cooldown effective — all callers pause together.

### Fetcher changes (minimal)

Both fetchers add two one-liners:

1. `_fetch_from_subreddit`: `except CircuitBreakerOpen: raise` (alongside
   the existing `PipelineCancelled: raise`) — so the exception escapes the
   inner `except Exception` that would otherwise swallow it.
2. `fetch_posts_for_topic`: `except CircuitBreakerOpen: break` (before the
   generic `except Exception: continue`) — so the fetch aborts cleanly
   instead of burning through remaining subreddits, each failing instantly.

---

## Files Changed

| File | Change |
|------|--------|
| `app/reddit/circuit_breaker.py` | **NEW** — `CircuitBreaker` class + `CircuitBreakerOpen` exception |
| `app/reddit/client.py` | Instantiate breaker; route `_make_request` through it |
| `app/reddit_v2/redditapiv2_client.py` | Same changes as v1 |
| `app/collector/fetcher.py` | Re-raise + break on `CircuitBreakerOpen` |
| `app/reddit_v2/redditapiv2_fetcher.py` | Same fetcher changes |
| `app/tests/test_circuit_breaker.py` | **NEW** — 10 unit tests (all pass) |

---

## Behavior After Fix

| Scenario | Before | After |
|----------|--------|-------|
| 3 consecutive 429s (one run) | Continue immediately, next request also 429s | All concurrent runs pause 60s together |
| 6 total 429s across 2 cooldowns, no success | Keep hammering all remaining subreddits | Breaker trips — every request fails fast with clear log |
| Mixed 429 + success | N/A | Counters reset on each success |
| Concurrent runs sharing the singleton | Each sees local 429s only; aggregate invisible | Breaker sees the true aggregate rate |
| User clicks Stop during cooldown | Waits full cooldown | `is_cancelled()` checked every 1s → `PipelineCancelled` within ~1s |

---

## DRY Note

The circuit breaker state/logic lives in ONE place (`circuit_breaker.py`).
Both clients instantiate it and call the same three methods. The fetcher
handlers (`except CircuitBreakerOpen`) are 2-line additions that match the
existing `PipelineCancelled` pattern. No duplication of breaker logic.

---

## Verification

1. **Unit tests:** `pytest app/tests/test_circuit_breaker.py -v` → **10/10
   pass** (63s — includes a 1s real-cooldown blocking test).
2. **Import check:** both `reddit_client._breaker` and
   `redditapiv2_client._breaker` resolve to `CircuitBreaker` instances. No
   circular imports.
3. **Regression:** `pytest app/tests/test_cancel_flag.py` → **8/8 pass**.
4. **Live end-to-end (pending):** submit a `reddit_v2` analysis, watch logs
   for "Cooling down" or "circuit breaker TRIPPED". If Reddit isn't 429-ing,
   the breaker never fires and behavior is identical to before.

---

## Related Traces

- `2026-04-16_socks5-proxy-reddit-waf-fix.md` — Lesson #9 flagged the
  `except Exception: continue` design smell ("consecutive failures should
  abort early"). This change implements that recommendation at the right
  layer.
- `2026-04-17_graceful-429-rate-limit-handling.md` — Gemini LLM 429 retry
  decorator. Different concern (LLM, not Reddit) but same pattern
  (exponential backoff + abort after max retries).
