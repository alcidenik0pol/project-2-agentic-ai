# Trace: Reddit Pacing Visual Tracker

**Date:** 2026-04-16
**Trigger:** Frontend rate limit monitor showed 10-minute window stats but not the actual 6-second pacing countdown that governs each request.

---

## Problem

The existing `RateLimitMonitor` component displayed:

- Requests used / remaining (100 per 10-minute window)
- Window reset countdown (minutes:seconds)
- A budget progress bar

What it did **not** show:

1. **The 6-second pacing countdown** — the real constraint users see during analysis. Each request must wait 6 seconds after the previous one (600s / 100 requests = 6s interval).
2. **Queue progress** tied to the pacing — how many requests are done vs pending for the current agent.
3. **Proxy context** — why requests are slow (SOCKS5 proxy routing to avoid WAF blocks).

Users saw "Remaining: 95" and a long countdown timer, which didn't explain why each individual request took ~6 seconds.

---

## Solution

Created a new `RedditPacingTracker` component that replaces `RateLimitMonitor`, with four focused sub-components:

### 1. PacingTimer
- Counts down from ~6.0s to 0.0s between requests
- Updates every 100ms for smooth animation
- Color-coded: green (>3s), amber (1-3s), red (<1s)
- Progress bar fills as the wait elapses

### 2. QueueInformation
- Shows `requests_in_window / limit` with budget bar
- Lists live queue items with status (waiting / sent / error)
- Warning banners at 80% and 100% of budget

### 3. PacingExplanation
- Static text explaining: "100 requests per 10 min = 1 request every 6s"
- Notes proxy usage and no-burst policy

### 4. ProxyReference
- Points to `docs/traces/2026-04-16_socks5-proxy-reddit-waf-fix.md`

---

## Implementation

### Backend: New `seconds_until_next_request` field

Added a property to `RedditPublicAPI` that computes the time remaining until the next request can fire:

```python
# app/reddit/client.py
@property
def seconds_until_next_request(self) -> float:
    """Seconds until next request can be made (6-second pacing)."""
    if not self._request_times:
        return 0.0
    now = time.time()
    last_request = self._request_times[-1]
    elapsed = now - last_request
    min_interval = config.reddit_min_request_interval_seconds
    return max(0.0, min_interval - elapsed)
```

This value flows through:
- `get_rate_limit_status()` dict -> `RateLimitStatus` Pydantic model -> REST API response -> frontend TypeScript type

### Frontend: Self-contained hook

The new component uses its own `usePacingRateLimit()` hook instead of the shared `useRateLimit`. This hook:
- Polls the REST API every 2 seconds for the authoritative `seconds_until_next_request`
- The `PacingTimer` sub-component does local interpolation (100ms ticks) between API responses for smooth animation

### Deprecation

The old `RateLimitMonitor.tsx` is preserved with a deprecation doc comment at the top. Only the import site (`rate-limit/page.tsx`) was switched to the new component.

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/models/api.py` | Added `seconds_until_next_request: float = 0.0` to `RateLimitStatus` |
| `app/reddit/client.py` | Added `seconds_until_next_request` property; updated `get_rate_limit_status()` dict |
| `backend/app/api/routes/rate_limit.py` | Pass `seconds_until_next_request` to response model |
| `frontend/lib/types.ts` | Added `seconds_until_next_request: number` to `RateLimitStatus` interface |
| `frontend/components/RateLimitMonitor.tsx` | Added deprecation notice (file preserved) |
| `frontend/components/RedditPacingTracker.tsx` | **NEW**: Pacing timer, queue info, explanation, proxy reference |
| `frontend/app/rate-limit/page.tsx` | Switched import to `RedditPacingTracker`; updated page copy |

---

## Design Decisions

- **Local 100ms tick vs polling faster**: Polling every 100ms would hammer the backend. Instead, we poll every 2s and interpolate locally. The timer resets to the authoritative value on each API response.
- **Color thresholds (>3s green, 1-3s amber, <1s red)**: Matches the existing palette used in `RateLimitMonitor` for consistency.
- **Self-contained hook (`usePacingRateLimit`)**: The old `useRateLimit` hook maintains a `countdown` state for the 10-minute window reset, which the new component doesn't need. A dedicated hook keeps things clean.
- **Old file kept, not renamed**: Adding a deprecation comment is simpler than a rename (which would require git `mv` and could break any external references). The import site is the only consumer and was already switched.

---

## Related Traces

- `2026-04-16_rate-limiter-burst-fix.md` — Fixed the burst bug that made pacing necessary
- `2026-04-16_socks5-proxy-reddit-waf-fix.md` — SOCKS5 proxy setup that the ProxyReference points to
