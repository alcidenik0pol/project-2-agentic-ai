# Trace: Subreddit Selection Token Limit Increase

**Date:** 2026-04-16
**Trigger:** Logs showed `MAX_TOKENS` warning and fallback to keyword selection for subreddit selection.

---

## Problem

In `app/collector/subreddit_selector.py:119-124`, the LLM-based subreddit selection was failing:

```python
response = provider.generate_structured(
    prompt=prompt,
    temperature=0.3,
    max_tokens=4096,  # Too small
    use_fast=True,
)
```

The logs revealed:
```
INFO     Built description list with 60 subreddits
WARNING  generate_structured hit MAX_TOKENS limit (2048). Response may be truncated.
INFO     Using fallback keyword-based subreddit selection for topic 'game ideas'
INFO     Fallback selection returned 9 subreddits
```

### Why 60 Subreddits?

The `_build_description_list()` function (line 69-70) hardcodes a slice:
```python
# Sort by subscriber count, limit to 60
formatted = []
for name, metadata in sorted(
    descriptions.items(),
    key=lambda x: -x[1].get("subscribers", 0),
):
    formatted.append(format_subreddit_for_prompt(name, metadata))

logger.info("Built description list with %d subreddits", len(formatted[:60]))
return "\n".join(formatted[:60])  # ← Top 60 by subscribers
```

With ~87 subreddits loaded from JSON, the system:
1. Sorts by subscriber count
2. Takes top 60
3. Sends all 60 descriptions to LLM
4. LLM selects relevant ones from that list

### The Token Math

- 60 subreddits × ~50-100 tokens/description = **3000-6000 input tokens**
- Prompt template overhead = ~200 tokens
- **Total: ~3200-6200 tokens** for the full prompt

With `max_tokens=4096`, the response was getting truncated, causing invalid JSON and triggering the keyword fallback.

---

## Fix

Increased `max_tokens` from 4096 to 8192 in the subreddit selection call only:

```python
# Before
response = provider.generate_structured(
    prompt=prompt,
    temperature=0.3,
    max_tokens=4096,
    use_fast=True,
)

# After
response = provider.generate_structured(
    prompt=prompt,
    temperature=0.3,
    max_tokens=8192,
    use_fast=True,
)
```

### Why Not Change Defaults?

The abstract base class (`app/analyst/providers/base.py:106`) and concrete implementations (`gcloud.py`, `lm_studio.py`) all default to 2048 tokens. Changing those would affect **all** LLM calls across the app. This was a targeted fix for the subreddit selection specifically.

---

## Files Modified

| File | Change |
|------|--------|
| `app/collector/subreddit_selector.py:122` | `max_tokens: 4096 → 8192` |

---

## Why This Matters

The LLM-based subreddit selection is a key differentiator — it dynamically picks relevant subreddits based on topic understanding, not just keyword matching. When it falls back to keyword selection, the results are lower quality.

The 8192 token limit ensures the full response (selected subreddit list + reasoning) fits without truncation, allowing the LLM to properly select from all 60 candidate subreddits.

---

## Related

- The 60-subreddit limit itself is hardcoded and could be revisited (currently sends top 60 by subscribers)
- Fallback keyword selection exists in `_fallback_selection()` as a safety net
