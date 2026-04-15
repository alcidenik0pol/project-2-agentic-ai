# Trace: Cluster Name Truncation Fix

**Date:** 2026-04-15
**Status:** Done

---

## The Problem

Cluster names were being truncated at 64 tokens despite the prompt explicitly warning the model against truncation. Examples from assessment of run `195637_live`:

- "Concerns about" — cut off mid-phrase
- "Difficulty managing" — incomplete
- "Uncertainty" — over-shortened fallback

The prompt (`app/analyst/cluster_prompts.py`) includes: *"IMPORTANT: Do not truncate your response... If your response ends with '&', 'and', 'or', a comma... you have failed."* But `max_tokens=64` in the LLM call was cutting off the response before the model could finish, making the prompt warning irrelevant.

Identified in pipeline assessment `output/reports/2026-04-15/195637_live/assessment.md`:
> "Cluster names are TRUNCATED: 'Concerns about', 'Difficulty managing', 'Uncertainty'. The prompt explicitly warns against this but max_tokens=64 is still cutting off responses."

---

## Root Cause

**File:** `app/analyst/clustering.py:287` (was line 285 pre-edit)

```python
raw = self.provider.generate_text(prompt, temperature=0.3, max_tokens=64)
```

64 tokens should theoretically be enough for 3-5 words (~6.5-10 tokens), but in practice the model was hitting the ceiling. The code had retry logic to detect truncated names and retry with a strengthened prompt, but this was treating the symptom — the real fix is giving the model enough room to complete its output.

---

## Solution

Increase `max_tokens` from 64 to 256. This provides generous headroom for 3-5 word phrases while remaining negligible in cost relative to other LLM calls in the pipeline (expansion=2048, hypothesis=16384).

### Modified: `app/analyst/clustering.py` — Line 287

```python
# BEFORE:
raw = self.provider.generate_text(prompt, temperature=0.3, max_tokens=64)

# AFTER:
raw = self.provider.generate_text(prompt, temperature=0.3, max_tokens=256)
```

The existing retry logic (lines 292-305) remains as a safety net — it detects truncated names and retries with a stronger prompt, falling back to the first theme name if both attempts fail.

---

## Why 256 (not 128 or 512)

| Value | Pros | Cons |
|-------|------|------|
| 128 | 2x current, likely sufficient | Still somewhat close to edge for verbose models |
| **256** | **4x current, generous headroom, negligible cost** | — |
| 512 | Maximum safety | Unnecessarily generous for 3-5 word output |

Chose 256 as the conservative option: eliminates truncation risk entirely while adding ~192 unused tokens per call — a rounding error compared to the 16384-token hypothesis generation call.

---

## Complete File List

| File | Change Type |
|------|-------------|
| `app/analyst/clustering.py` | Modified — `max_tokens=64` → `max_tokens=256` |

---

## Verification

Run a test pipeline and confirm:
- Cluster names are complete phrases (3-5 words, not cut off)
- No names end with "&", ",", "and", "or" (truncation indicators)
- Retry logic is not triggered (no "Cluster name truncated/short" warnings in logs)
