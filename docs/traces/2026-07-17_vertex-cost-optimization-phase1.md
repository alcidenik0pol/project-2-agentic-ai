# Vertex AI Cost Optimization — Phase 1

**Date:** 2026-07-17
**Status:** **Phase 1 IMPLEMENTED. Phase 2 NOT STARTED.**

---

> ## ⚠️ Scope boundary — read this first
>
> **This trace documents Phase 1 ONLY.** Phase 1 ships:
> 1. A **measurement fix** (the token tracker was undercounting by ~28×)
> 2. **One** safe cost reduction (disable thinking on classification calls)
>
> **Phase 2 is explicitly NOT implemented in this trace.** Phase 2 candidates
> (Pro → Flash model swap, `chat_with_tools` thinking caps, Flash-Lite rollout,
> cross-run cache) are listed in [§ Out of Scope](#out-of-scope--phase-2-candidates)
> below. They wait for real tracker data to justify them.
>
> The reasoning: optimizing against a tracker that's off by 28× would be
> speculative. Measure first, then cut.

---

## Motivation: the 28× gap

User reported **~$2/day** Vertex AI cost. The token tracker (`gs://painpan-usage/usage-2026-07.json`) showed:

```json
{"input_tokens": 336290, "output_tokens": 80189, "total_tokens": 416479}
```

At published Gemini pricing (us-central1, ≤128K context):
- If every token were Flash: 336K × $0.30 + 80K × $2.50 = **~$0.30 for July**
- If every token were Pro (worst case): ~$1.22 for July

Actual July spend: **~$34** (≈ $2/day × 17 days). **Gap: 28× even in the worst-case model assumption.**

### Root cause — three leaks in `_record_usage`

1. **`thoughtsTokenCount` was not counted.** `app/analyst/providers/gcloud.py:_record_usage` read only `promptTokenCount` and `candidatesTokenCount`. Gemini 2.5 models run in thinking mode by default, and reasoning tokens are billed at output rate. For reasoning-heavy calls (hypothesis Pro call, agent tool-calling), thinking tokens can be 5-20× visible output. **This was the dominant missing cost.**

2. **Embedding API calls were never tracked.** `_get_embedding_batch` called Vertex AI but never invoked `_record_usage`. Every clustering run was invisible to the tracker. (Flagged as a known issue in `2026-07-15_dev-mode-token-tracking-bypass.md` but deferred.)

3. **Per-attempt retry accounting.** `@retry_with_exponential_backoff()` may make multiple API calls per logical call. The first attempt may error after generating tokens (still billed); only the successful response hits `_record_usage`. Pre-existing; **not fixed in Phase 1**.

---

## Daily cost pattern

User-pulled billing breakdown (95% Vertex AI):

| Date | Cost | Likely activity |
|------|------|-----------------|
| Jul 13 | $1.60 | Dev/test day |
| Jul 14 | $0.54 | Quiet day |
| Jul 15 | $0.86 | Dev day |
| Jul 16 | $2.13 | Heavy dev (429 breaker + CORS debug) |

Average ~$1.28/day, monthly run-rate ~$39. Cost scales with **own dev activity**, not recruiter traffic. Steady-state for a real rare-run demo would be ~$0.50/day.

---

## What Phase 1 implements

Two categories only: **measurement** and **one safe reduction**. Nothing else.

### A. Tracker schema extension — `app/services/usage_tracker.py`

Added `thinking_tokens: int` to `UsageStats` dataclass. Updated `_empty_usage()`, `record_usage()`, and `get_usage()` to thread it through. `total_tokens` now equals `input + output + thinking`.

```python
def record_usage(
    self,
    input_tokens: int,
    output_tokens: int,
    thinking_tokens: int = 0,
) -> None:
    ...
    data["total_tokens"] = (
        data["input_tokens"] + data["output_tokens"] + data["thinking_tokens"]
    )
```

**Backward compat:** `thinking_tokens=0` default. Old usage files (May, July 2026 — pre-Phase-1) load cleanly via `data.get("thinking_tokens", 0)`. No migration needed. Test: `test_old_usage_file_loads_with_zero_thinking`.

### B. Provider: count thinking tokens — `app/analyst/providers/gcloud.py`

`_record_usage` now reads three fields from `usageMetadata`:
```python
input_tokens = usage.get("promptTokenCount", 0)
output_tokens = usage.get("candidatesTokenCount", 0)
thinking_tokens = usage.get("thoughtsTokenCount", 0)
```

Refactored: extracted `_record_raw(input, output, thinking=0)` helper that does the dev-mode check and tracker call. `_record_usage` parses the response then calls `_record_raw`. Callers without a response blob (embeddings) call `_record_raw` directly. **Avoids DRY violation** — dev-mode check lives in one place.

### C. Provider: track embedding calls — `app/analyst/providers/gcloud.py`

`text-embedding-004` endpoint returns no `usageMetadata`. Added `_estimate_embedding_tokens(texts)` heuristic (1.3 tokens/word, documented as approximate). Called inside `_get_embedding_batch` after successful response:

```python
estimated_input = self._estimate_embedding_tokens(batch)
self._record_raw(estimated_input, 0, 0)
```

**Why approximate is acceptable:** the tracker is for visibility, not billing reconciliation. We need to know *roughly* how much of the bill is embeddings vs generation. Vertex AI bills on actual tokens regardless of what we record.

### D. Disable thinking on classification — the one cost reduction in Phase 1

Classification asks for `{theme, is_complaint, intensity}` JSON at `temperature: 0.1`. Pure structured extraction — reasoning is wasted budget.

```python
"generationConfig": {
    "temperature": 0.1,
    "maxOutputTokens": 256,  # was 1024 — JSON is ~50 tokens
    "thinkingConfig": {"thinkingBudget": 0},  # NEW
},
```

**Verified via [Google docs](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/thinking):**
- Gemini 2.5 Flash: supports `thinkingBudget: 0` (fully disables thinking) ✅
- Gemini 2.5 Pro: minimum is 128 (cannot disable)
- Gemini 2.5 Flash-Lite: disabled by default

Classification uses Flash via `use_fast=True`, so budget=0 works.

**Why this is the only reduction in Phase 1:** classification is the only call where we can confidently say thinking adds no value (structured JSON extraction at temp=0.1). Every other call site has a real reasoning component that needs A/B evaluation before touching.

Also dropped `maxOutputTokens` 1024→256. Doesn't directly save $ (billed on actual, not budget) but stops the model rambling on malformed responses that then get retried.

### E. Backend API surface

- `backend/app/models/api.py:UsageResponse` — added `thinking_tokens: int = Field(0, ...)`
- `backend/app/api/routes/usage.py` — both dev and prod branches include thinking_tokens

### F. Frontend display — `frontend/components/UsageIndicator.tsx`

Added `input_tokens?`, `output_tokens?`, `thinking_tokens?` to the local `UsageData` interface (optional — old clients keep working). The `%` badge's tooltip now reads:

```
X tokens remaining (Y%) — in: A / out: B / thinking: C
```

Existing UI (color, badge, dev mode amber DEV chip) unchanged.

**Note on prior tech debt:** `2026-07-15_dev-mode-token-tracking-bypass.md` flagged a DRY violation between `UsageIndicator`, `lib/api.ts`, and `limit-exceeded/page.tsx`. This change preserves the status quo (still uses inline fetch) rather than consolidating — out of Phase 1 scope.

---

## Out of scope — Phase 2 candidates

**Each of these was considered for Phase 1 and deliberately deferred.** They will be revisited after 2-3 dev days of tracker data arrives from the Phase 1 measurement fix.

| Item | Why deferred | Trigger to revisit |
|------|--------------|---------------------|
| **Pro → Flash for hypothesis** (`GCLOUD_MODEL`) | Single env-line change but the hypothesis paragraph is the project's flagship output. Quality regression would be visible to recruiters. Needs A/B. | If tracker shows Pro calls are >30% of total cost |
| **Cap `chat_with_tools` thinking budget** | Agent tool-selection genuinely benefits from thinking. Capping needs per-agent evaluation — different agents have different reasoning needs. | If tracker shows agent calls have outsized thinking-token volume |
| **Classification Flash → Flash-Lite** | Flash-Lite has thinking off by default (cheaper still), but it's a different quality bar for nuanced complaint classification. | If tracker shows Flash classification remains a top cost driver after Phase 1 |
| **Cross-run post→classification cache** | User confirmed rare-runs usage pattern (recruiter demo). Cache hit rate would be too low to justify ~50 lines + GCS bucket. | Not worth pursuing for this usage pattern |
| **Consolidate frontend DRY violation** (`UsageIndicator` / `lib/api.ts` / `limit-exceeded/page.tsx`) | Pre-existing tech debt flagged in prior trace. Not a cost optimization. | Separate cleanup pass, not Phase 2 |
| **Per-attempt retry accounting** | `@retry_with_exponential_backoff()` may make multiple billed attempts per logical call; only the successful one is tracked. Pre-existing. | If gap between tracker and billing remains >3× after Phase 1 ships |

---

## Files changed

| File | Change | Lines |
|------|--------|-------|
| `app/services/usage_tracker.py` | +`thinking_tokens` field, `_empty_usage`, `record_usage`, `get_usage` | +12 |
| `app/analyst/providers/gcloud.py` | `_record_usage` reads thoughtsTokenCount; `_record_raw` helper; `_estimate_embedding_tokens` helper; tracker call in `_get_embedding_batch`; `thinkingConfig: {thinkingBudget: 0}` + maxOutputTokens 256 in `_classify_post_call` | +50 |
| `backend/app/models/api.py` | +`thinking_tokens` field on `UsageResponse` | +1 |
| `backend/app/api/routes/usage.py` | thinking_tokens in dev and prod branches | +2 |
| `frontend/components/UsageIndicator.tsx` | 3 optional fields on `UsageData`, tooltip breakdown | +12 |
| `app/tests/test_dev_mode.py` | 3-arg `_TrackerSpy`, thinking assertions, backward-compat test | +25 |
| `app/tests/test_usage_tracker_thinking.py` | **NEW** — 9 tests | +190 |

Total: ~290 lines across 6 files + 1 new test file.

---

## Verification

```
pytest app/tests/test_usage_tracker_thinking.py -v         → 9/9 pass
pytest app/tests/test_dev_mode.py + 3 other suites -v      → 45/45 pass
```

No regressions. Import smoke test confirms schema fields landed:
- `UsageStats`: `['input_tokens', 'output_tokens', 'thinking_tokens', 'total_tokens', 'month']`
- `UsageResponse.model_fields`: includes `thinking_tokens`

**Deferred to user:**
- Local end-to-end run with `LLM_PROVIDER=gcloud` (needs credentials + proxy)
- Deploy + observe tracker for 2-3 dev days

---

## Expected outcomes after deploy (Phase 1 only)

**Realistic expectation: $10-15/mo reduction, not dramatic.** Classification thinking was one piece; hypothesis Pro thinking and agent `chat_with_tools` thinking remain uncapped (deferred to Phase 2). The bigger value of Phase 1 is **visibility** — the tracker will finally show where the money goes.

After 2-3 days of dev activity, the tracker should show:

1. **`thinking_tokens > 0`** — confirms the fix is live and Gemini is producing thinking tokens (proves the leak was real).
2. **Per-day total reconciles with billing within 2-3×** — down from the current 28× gap. Remaining gap is retry-attempt accounting and rate-card differences.
3. **Classification call latency drops** — thinking disabled = faster responses (Flash classification should drop from ~3-5s to ~1-2s).

### Phase 2 decision matrix — NOT for this trace

When tracker data arrives, Phase 2 picks from this menu:

| If tracker shows... | Phase 2 action |
|---|---|
| Thinking >60% of total | Cap `chat_with_tools` thinking budget too |
| Pro hypothesis call dominates | Switch `GCLOUD_MODEL` Pro→Flash, OR cap Pro thinking to ~2K |
| Embeddings surprisingly costly | Reconsider clustering cadence |
| Flash classification still expensive | Flash → Flash-Lite |

This matrix is forward-looking. **None of it is implemented here.**

---

## Pattern: measure twice, cut once

The temptation was to ship all the optimizations at once (Pro→Flash, thinking caps everywhere, flash-lite). Pushed back: the tracker was so broken that any "optimization" would have been speculative. Phase 1 ships the measurement fix + one safe change (classification thinking=0 — temp=0.1 JSON extraction, no quality risk). **Phase 2 decisions wait for real per-SKU data.**

This mirrors the lesson from `2026-07-16_client-level-429-circuit-breaker.md`: "verify a plan's failure-mode premise before building the fix." Here the premise was "thinking tokens are the missing cost" — verifiable only after shipping the tracker fix.

---

## Related traces

- `2026-07-15_dev-mode-token-tracking-bypass.md` — added the `is_development` gate that Phase 1 extends with thinking tokens.
- `2026-06-28_cloud-run-cost-optimization-v2.md` — prior cost trace; Cloud Run side is fully tuned, this trace picks up where that left off (Vertex AI was out of scope there).
- `2026-04-15_dual-model-fast-tier.md` — established the Pro/Flash split that Phase 1 preserves (Pro for hypothesis, Flash for everything else).
