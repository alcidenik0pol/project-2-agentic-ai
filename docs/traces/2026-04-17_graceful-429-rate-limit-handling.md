# Trace: Graceful 429 Rate Limit Handling

**Date:** 2026-04-17
**Trigger:** Deployed Docker app crashes entirely on Gemini API 429 rate limit errors. No retry, no error message to user, just crash.

---

## Problem

When Google's Gemini API returns 429 "Too Many Requests", the entire application crashes:

```
ERROR [TIMING] agent_run failed after 80.83s: 429 Client Error: Too Many Requests
ERROR [TIMING] agent_orchestrator_run failed after 614.82s: 429 Client Error
```

Three root causes:

1. **No exponential backoff** — both providers used fixed 1-second delays between retries
2. **Uncaught `HTTPError`** — `response.raise_for_status()` throws `HTTPError` for 429, never caught at the right level
3. **No error boundary** — agent orchestrator has no try/except between agents, one failure kills the whole pipeline

The manual retry loops in providers were inadequate:

```python
# openai_gemini.py — fixed 1s delay, no backoff
for attempt in range(1, self._max_retries + 1):
    try:
        response = self._client.embeddings.create(...)
        break
    except Exception as e:
        if attempt < self._max_retries:
            time.sleep(1)  # Always 1s, even for rate limits
        else:
            raise
```

---

## Solution

### 1. Reusable Retry Decorator

Created `app/utils/retry.py` with `@retry_with_exponential_backoff()` decorator:

- Exponential backoff: 1s → 2s → 4s → 8s → 16s (capped at 60s)
- ±10% jitter to prevent thundering herd when multiple requests retry simultaneously
- Detects retriable errors from OpenAI SDK (`RateLimitError`), requests (`HTTPError`), and generic `status_code` attributes
- Only retries on 429, 500, 502, 503, 504 — non-transient errors pass through immediately
- Clear logging: `"Retryable error in generate_text (attempt 2/5): HTTPError. Retrying in 2.1s..."`

### 2. Applied to All Provider Methods

Each provider now has the decorator on every API-call method:

**OpenAI Gemini (`openai_gemini.py`):**
- `generate_text()`, `generate_structured()`, `_chat_with_tools_internal()`
- Extracted `_get_embedding_batch()` and `_classify_post_call()` as decorated single-call helpers
- Removed manual `time.sleep(1)` retry loops

**GCloud (`gcloud.py`):**
- `generate_text()`, `generate_structured()`, `_chat_with_tools_internal()`
- Extracted `_get_embedding_batch()` and `_classify_post_call()` as decorated single-call helpers
- Removed manual `time.sleep(1.0)` retry loops

The `classify_post` methods kept their outer loop for parse-level retries (when LLM returns unparseable output, it retries with `RETRY_PROMPT`), but the actual API call is now in a decorated helper.

### 3. Agent-Level Error Boundary

Added try/except in `app/agents/base.py` around `provider.chat_with_tools()`:

```python
try:
    response = self.provider.chat_with_tools(...)
except Exception as e:
    logger.error(f"[{self.name}] LLM failed after retries: {e}")
    return {"response": f"Error: LLM call failed after retries - {e}", ...}
```

If the decorator exhausts all retries, the agent returns an error response instead of crashing.

### 4. Orchestrator-Level Error Boundary

Enhanced `_execute_pipeline()` in `analysis_service.py`:

- Catches orchestrator failures with user-friendly rate limit messages
- Saves error report to disk before raising
- Existing `_run_in_thread` already catches and sends errors via WebSocket

---

## Files Changed

| File | Change |
|------|--------|
| `app/utils/retry.py` | **NEW** — `@retry_with_exponential_backoff()` decorator with backoff, jitter, retriable detection |
| `app/config.py` | Added 5 retry config fields: `retry_max_attempts`, `retry_initial_backoff_seconds`, `retry_max_backoff_seconds`, `retry_backoff_multiplier`, `retry_enable_jitter` |
| `app/analyst/providers/openai_gemini.py` | Applied decorator to all API methods, extracted `_get_embedding_batch()` and `_classify_post_call()`, removed manual retry loops |
| `app/analyst/providers/gcloud.py` | Applied decorator to all API methods, extracted `_get_embedding_batch()` and `_classify_post_call()`, removed manual retry loops |
| `app/agents/base.py` | Added try/except around `chat_with_tools()` call, returns error response instead of crashing |
| `backend/app/services/analysis_service.py` | Added try/except around orchestrator.run(), user-friendly rate limit messages, error report saved to disk |

---

## Retry Behavior Example

```
Attempt 1: Immediate → 429 received
WARNING - Retryable error in generate_text (attempt 1/5): HTTPError. Retrying in 1.0s...
Attempt 2: Wait ~1.0s → 429 received
WARNING - Retryable error in generate_text (attempt 2/5): HTTPError. Retrying in 2.0s...
Attempt 3: Wait ~2.0s → 429 received
WARNING - Retryable error in generate_text (attempt 3/5): HTTPError. Retrying in 4.1s...
Attempt 4: Wait ~4.1s → Success ✓
```

Total wait: ~7 seconds. Current system would have crashed after 3 seconds of fixed 1s retries.

---

## Configuration

Environment variables (all optional, sensible defaults):

```bash
RETRY_MAX_ATTEMPTS=5
RETRY_INITIAL_BACKOFF_SECONDS=1.0
RETRY_MAX_BACKOFF_SECONDS=60.0
RETRY_BACKOFF_MULTIPLIER=2.0
RETRY_ENABLE_JITTER=true
```

---

## Graceful Degradation Chain

```
429 Error
  ↓
@retry_with_exponential_backoff retries 5x with backoff
  ↓ (still failing after 5 attempts)
Agent catches exception → returns error response
  ↓
Orchestrator catches → marks run as "failed"
  ↓
WebSocket sends user-friendly error to frontend
  ↓
App stays alive, ready for next request ✓
```

Previous behavior: uncaught exception → thread dies → frontend hangs → app unusable.
