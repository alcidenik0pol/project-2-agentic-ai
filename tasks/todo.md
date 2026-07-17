# Phase 1: Vertex AI Cost Optimization — Measurement + Safe Reduction

## Context

- Current spend: ~$1.28/day avg on Vertex AI (95% of total bill), monthly ~$39
- Token tracker shows 416K tokens for July; at published pricing this is ~$0.30-1.22
- **28× gap** between tracked cost and actual bill — tracker is undercounting
- Three leaks: missing `thoughtsTokenCount`, missing embedding calls, no per-call visibility

## Goal

1. **Measurement**: Make the tracker reflect reality so we can target Phase 2
2. **Reduction**: Disable thinking on classification (safe — temp=0.1 JSON extraction)

## Out of Scope (deferred to Phase 2, after tracker data arrives)

- Pro → Flash switch for hypothesis (needs quality A/B)
- chat_with_tools thinking budget cap (needs per-agent eval)
- Classification Flash → Flash-Lite (different quality bar)
- Cross-run cache (rare-runs usage pattern = low hit rate, not worth it)

---

## Checklist

### A. Tracker schema extension (`app/services/usage_tracker.py`)
- [x] Add `thinking_tokens: int` field to `UsageStats` dataclass
- [x] Add `thinking_tokens` to `_empty_usage()` (default 0)
- [x] Extend `record_usage()` signature: `record_usage(input_tokens, output_tokens, thinking_tokens=0)`
- [x] Update `total_tokens` math: `input + output + thinking`
- [x] Verify old usage files (May, July) load cleanly via `.get(..., 0)` defaults

### B. Provider: count thinking tokens (`app/analyst/providers/gcloud.py`)
- [x] Extend `_record_usage` to read `usageMetadata.thoughtsTokenCount`
- [x] Refactor: extract `_record_raw` helper so callers without a response blob (embeddings) can record directly
- [x] Behavior applies to all four `_record_usage` call sites (unchanged): `generate_text`, `generate_structured`, `_chat_with_tools_internal`, `_classify_post_call`

### C. Provider: track embedding calls (`app/analyst/providers/gcloud.py`)
- [x] Add `_estimate_embedding_tokens` helper: word→token heuristic, documented as approximate
- [x] Call `_record_raw` inside `_get_embedding_batch` after success
- [x] Dev-mode bypass applies (via `_record_raw`)

### D. Provider: disable thinking on classification (the cost reduction)
- [x] In `_classify_post_call`, add `"thinkingConfig": {"thinkingBudget": 0}` to `generationConfig`
- [x] Drop `maxOutputTokens` from 1024 → 256
- [x] Document why thinking is disabled (inline comment)

### E. Backend API surface (`backend/app/models/api.py`, `backend/app/api/routes/usage.py`)
- [x] Add `thinking_tokens: int = 0` to `UsageResponse`
- [x] Update prod branch of `/api/v1/usage` to include thinking_tokens
- [x] Dev branch returns thinking_tokens=0

### F. Frontend display (`frontend/components/UsageIndicator.tsx`)
- [x] Added `input_tokens`, `output_tokens`, `thinking_tokens` to UsageData interface (optional)
- [x] Tooltip on the % badge now shows the breakdown: "in: X / out: Y / thinking: Z"

### G. Tests
- [x] Extended `app/tests/test_dev_mode.py`:
  - `_TrackerSpy` updated to 3-arg signature
  - `test_prod_mode_calls_tracker` now passes a `thoughtsTokenCount: 30` payload and asserts `(100, 50, 30)`
  - Added `test_prod_mode_records_zero_thinking_when_field_absent` (backward compat)
  - `_FakeStats` includes `thinking_tokens`
  - Endpoint tests assert thinking_tokens (dev=0, prod=50)
- [x] New `app/tests/test_usage_tracker_thinking.py` — 9 tests covering:
  - Tracker accumulation (with/without thinking, mixed calls, backward compat with old files)
  - `_estimate_embedding_tokens` heuristic
  - `_get_embedding_batch` records estimated input on success + skips in dev mode
  - Classification payload includes `thinkingConfig.thinkingBudget: 0`

### H. Verification
- [x] `pytest app/tests/test_usage_tracker_thinking.py -v` → **9/9 pass**
- [x] `pytest app/tests/test_dev_mode.py test_cancel_flag.py test_circuit_breaker.py test_redditapiv2_parser.py -v` → **45/45 pass** (no regressions)
- [x] Import smoke test: GCloudProvider, UsageTracker, UsageResponse all import cleanly
- [ ] Local end-to-end run with `LLM_PROVIDER=gcloud` (deferred to user — needs credentials + proxy)
- [ ] Deploy + observe tracker for 2-3 dev days (deferred)
- [x] Write `docs/traces/2026-07-17_vertex-cost-optimization-phase1.md` (this trace)

---

## Files Touched

| File | Section | Approx lines |
|---|---|---|
| `app/services/usage_tracker.py` | A | ~15 |
| `app/analyst/providers/gcloud.py` | B, C, D | ~30 |
| `backend/app/models/api.py` | E | ~2 |
| `backend/app/api/routes/usage.py` | E | ~3 |
| `frontend/components/UsageIndicator.tsx` | F | ~10 |
| `app/tests/test_dev_mode.py` | G | ~10 (extend existing) |
| `app/tests/test_usage_tracker_thinking.py` | G | ~80 (new) |
| `docs/traces/2026-07-17_vertex-cost-optimization-phase1.md` | H | ~80 (new) |
| **Total** | | **~230 lines** |

## Risks

1. **Classification quality regression** (Change D). Counter-argument: structured JSON at temp=0.1. If quality drops, revert is a one-line payload change.
2. **Token estimate for embeddings is approximate** (Change C). Documented; better than current zero visibility.
3. **Schema migration concerns**. Mitigated by `.get(..., 0)` defaults — old usage files load without error.

## Success Criteria

- All existing tests pass
- New tests pass
- After 2-3 days of dev activity post-deploy, tracker shows:
  - thinking_tokens > 0 (confirms fix is live)
  - Per-day total tokens should now reconcile with ~$1-2/day Vertex spend within 2-3× (still won't be exact due to retries, but vastly closer than current 28× gap)
- Classification call latency drops (thinking disabled = faster responses)
