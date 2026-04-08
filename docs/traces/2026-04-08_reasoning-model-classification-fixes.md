# Trace: Reasoning Model Classification Fixes

**Date:** 2026-04-08
**Session:** Debugging and optimizing Reddit post classification with reasoning models
**Files Modified:**
- `app/analyst/classifier.py`
- `app/analyst/models.py`
- `scripts/analyze_output.py` (created)

---

## 2026-04-08 21:53 - Initial Problem Discovery

### Context
Running `classify_posts.py` with 600 posts using `qwen3.5-27b-claude-4.6-opus-reasoning-distilled` model.

### Issue #1: Empty Responses
**Symptom:** Classification returning 0/600 successful. Raw responses were empty or ellipsis-only.

**Root Cause:** `max_tokens=100` was too small for reasoning models that output thinking blocks before the actual response.

**Fix Applied:**
```python
# app/analyst/classifier.py:106
max_tokens=1024,  # Reasoning models need more tokens for thinking + output
```

---

## 2026-04-08 22:00 - Issue #2: Statistics Bug

### Symptom
Summary showed "0 successful" even when classifications were working.

**Root Cause:** Pydantic v2 doesn't support `__post_init__` like Pydantic v1. The computed fields were never being calculated.

**Fix Applied:**
```python
# app/analyst/models.py - Changed from __post_init__ to @property
class ClassificationResult(BaseModel):
    @property
    def successful_classifications(self) -> int:
        return sum(1 for p in self.posts if p.classification is not None)

    @property
    def failed_classifications(self) -> int:
        return sum(1 for p in self.posts if p.classification_error is not None)
```

---

## 2026-04-08 22:15 - Issue #3: Request Queuing (Critical)

### Symptom
- 50+ generations queued in LM Studio UI
- RAM usage approaching 64GB
- Sequential processing NOT working despite design

**Root Cause:** OpenAI client uses httpx with HTTP/2 and connection pooling, allowing request pipelining. Requests were being sent faster than LM Studio could process them.

**Fix Attempted #1 (Failed):**
```python
# This didn't work - http_version is not a valid parameter
http_client = httpx.Client(
    limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
    http_version="http1.1",  # ERROR: unexpected keyword argument
)
```

**Fix Applied #2 (Success):**
```python
# app/analyst/classifier.py:50-58
import httpx
http_client = httpx.Client(
    limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
)
self.client = OpenAI(
    base_url=self.base_url,
    api_key="lm-studio",
    timeout=self.timeout,
    http_client=http_client,
)
```

---

## 2026-04-08 22:30 - Issue #4: Retry Delay Too Short

### Symptom
Reasoning model needed more time between retries.

**Fix Applied:**
```python
# app/analyst/classifier.py:142-143
if attempt < self.max_retries:
    time.sleep(self.request_delay * 2)  # 5 seconds for reasoning models
```

---

## 2026-04-08 23:03 - Full Batch Execution

### Command Run
```bash
python scripts/classify_posts.py data/*.json --max-posts 600 --yes
```

### Results
- **Output:** `output/classified_posts_20260407_230341.json`
- **Total Posts:** 242 (stopped early, 358 remaining)
- **Success Rate:** 97.9% (237/242)
- **Failed:** 5 posts (all from r/ADHD)
- **Processing Time:** 62.6 minutes (~15.5 sec/post)
- **Model:** `qwen3.5-27b-claude-4.6-opus-reasoning-distilled`

---

## 2026-04-08 23:30 - Quality Assessment

### Classification Metrics

| Metric | Value |
|--------|-------|
| Total Posts | 242 |
| Successful | 237 (97.9%) |
| Failed | 5 (2.1%) |
| Complaints Found | 106 (44.7%) |
| Non-complaints | 131 (55.3%) |

### Intensity Distribution
- Low: 160 (67.5%)
- Medium: 51 (21.5%)
- High: 26 (11.0%)

### Unique Complaint Themes
**Total: 98 unique themes** across 106 complaint posts

Top themes by frequency:
1. Workplace frustration (4)
2. Workplace boundaries (2)
3. Executive dysfunction struggles (2)
4. Medication comparison (2)
5. Workplace dissatisfaction (2)
6. Job dissatisfaction (2)

---

## 2026-04-08 23:45 - Analysis Tool Created

### New Script: `scripts/analyze_output.py`

Purpose: Quick analysis of classification output files without reading full JSON.

Features:
- Summary statistics (total, success rate, processing time)
- Complaint vs non-complaint breakdown
- Intensity distribution
- All unique themes with frequency counts
- Failed posts listing
- High intensity complaint samples

---

## Lessons Learned

1. **Reasoning models need more tokens:** Set `max_tokens=1024` minimum for models that output thinking blocks.

2. **Pydantic v2 vs v1:** Use `@property` decorators for computed fields, not `__post_init__`.

3. **HTTP connection pooling can break sequential processing:** Even single-threaded code can queue requests if the HTTP client supports pipelining.

4. **OpenAI client defaults:** The OpenAI Python client uses httpx with aggressive connection pooling. Must override with custom `httpx.Client(limits=...)` for true sequential processing.

5. **Reasoning models need longer retry delays:** 5 seconds between retries vs 2.5 seconds for standard models.

---

## Remaining Work

- [ ] Process remaining 358 posts (to reach 600 total)
- [ ] Investigate why r/ADHD posts had higher failure rate
- [ ] Consider adding 4th retry with 10+ second delay for edge cases

---

## Files Changed Summary

### `app/analyst/classifier.py`
- Line 50-58: Added custom httpx client with connection limits
- Line 106: Increased max_tokens from 100 to 1024
- Line 142-143: Increased retry delay from `request_delay` to `request_delay * 2`

### `app/analyst/models.py`
- Lines 61-74: Changed from `__post_init__` to `@property` methods for Pydantic v2 compatibility

### `scripts/analyze_output.py` (NEW)
- Complete analysis tool for classification output files

---

## Verification Steps

1. Run classification on small batch (10 posts):
   ```bash
   python scripts/classify_posts.py data/*.json --max-posts 10 --yes
   ```

2. Verify LM Studio queue count stays at 0-1 (no buildup)

3. Analyze results:
   ```bash
   python scripts/analyze_output.py output/classified_posts_<timestamp>.json
   ```

4. Check success rate > 95% and themes are meaningful
