# Trace: Rate Limiter Burst Bug Fix

**Date:** 2026-04-16
**Trigger:** Reddit WAF blocking requests due to burst patterns after rate limit waits.

---

## Problem

In `app/reddit/client.py:69`, after the rate limiter waited for the 60-second window to expire, it **cleared the entire request history**:

```python
# _wait_for_rate_limit()
time.sleep(wait_time)
self._request_times = []  # BUG: wipes all history
```

This caused a burst pattern:

1. Pipeline makes 10 requests in quick succession (fills the window)
2. Rate limiter waits ~60s for the window to expire
3. **Nukes all timestamps** → now 0 requests recorded
4. Next loop iteration fires another 10 requests as fast as possible (< 1 second)
5. Reddit's WAF sees 10 requests in <1s and blocks the IP

The standalone `app/collector/rate_limiter.py:64` did NOT have this bug — it correctly filtered expired entries only:

```python
# rate_limiter.py (already correct)
self.request_times = [t for t in self.request_times if time.time() - t < 60]
```

---

## Fix

Changed `client.py` to filter expired entries instead of clearing the list:

```python
# Before
time.sleep(wait_time)
self._request_times = []

# After
time.sleep(wait_time)
now_after = time.time()
self._request_times = [t for t in self._request_times if now_after - t < 60]
```

This preserves any requests that happened recently before the wait. They still count against the window, preventing the burst.

---

## Files Modified

| File | Change |
|------|--------|
| `app/reddit/client.py:69` | Replaced `self._request_times = []` with filtered cleanup |

---

## Why This Matters

With the hot-post fetching approach (see companion trace), the pipeline now fetches one page per subreddit instead of searching. Each page is a single request. But with 5-10 subreddits, the burst pattern would still trigger if all requests fire at once after a rate limit wait.

The fix ensures requests are always paced correctly, even across rate limit boundaries.
