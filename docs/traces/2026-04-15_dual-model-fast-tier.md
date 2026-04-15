# Dual-Model Fast Tier: gemini-2.5-flash for Simple Tasks

_Date: 2026-04-15_

_Problem: All 8 LLM calls used gemini-2.5-pro, making classification 14.8s/post (445s for 30 posts, 2+ hours for 500)._

_Solution: Route simple tasks (classification, expansion, clustering, agent routing, subreddit selection) to a faster model via env var._

---

## What Changed

### Files Modified

| File | Change |
|------|--------|
| `app/config.py` | Added `gcloud_model_fast` field (env: `GCLOUD_MODEL_FAST`, default: `gemini-2.5-flash`) |
| `app/analyst/providers/base.py` | Added `use_fast: bool = False` to `classify_post`, `generate_text`, `generate_structured`, `chat_with_tools` |
| `app/analyst/providers/gcloud.py` | Added `_url_for_model(model)` method; each method reads config directly based on `use_fast` |
| `app/analyst/providers/openai_gemini.py` | Same pattern — reads `config.gcloud_model_fast` when `use_fast=True` |
| `app/analyst/providers/lm_studio.py` | Accepts `use_fast` (ignored — single local model) |
| `app/analyst/classifier.py` | Passes `use_fast=True` to `classify_post` (Call 4) |
| `app/analyst/expansion.py` | Passes `use_fast=True` to `generate_text` (Call 5) |
| `app/analyst/clustering.py` | Passes `use_fast=True` to `generate_text` (Call 6) |
| `app/agents/base.py` | Passes `use_fast=True` to `chat_with_tools` (Calls 1-3) |
| `app/collector/subreddit_selector.py` | Passes `use_fast=True` to `generate_structured` (Call 8) |
| `.env.example` | Documents `GCLOUD_MODEL_FAST` |

### Architecture

```
config.py
  gcloud_model       = env(GCLOUD_MODEL, "gemini-2.5-pro")       # thinking model
  gcloud_model_fast  = env(GCLOUD_MODEL_FAST, "gemini-2.5-flash") # fast model

gcloud.py
  _url_for_model(model) -> builds Vertex AI URL from model name string
  each method: picks config.gcloud_model or config.gcloud_model_fast based on use_fast
  no local variable cache — reads config directly
```

### Task-to-Model Mapping

| Call | Task | Model | Rationale |
|------|------|-------|-----------|
| 1 | Orchestrator Agent | FAST | Simple routing |
| 2 | Analyst Agent | FAST | Simple routing |
| 3 | Hypothesis Agent | FAST | Formatting only |
| 4 | Classification | FAST | Structured extraction, temp=0.1 |
| 5 | Theme Expansion | FAST | Simple text expansion |
| 6 | Cluster Naming | FAST | 3-5 word naming |
| 7 | Hypothesis Generation | **PRO** | Complex reasoning, final output |
| 8 | Subreddit Selection | FAST | Selection/sorting |

### Config Fields

| Field | Default | Env Var | Purpose |
|-------|---------|---------|---------|
| `gcloud_model` | `gemini-2.5-pro` | `GCLOUD_MODEL` | Primary model (complex reasoning) |
| `gcloud_model_fast` | `gemini-2.5-flash` | `GCLOUD_MODEL_FAST` | Fast model (simple tasks) |

---

## Design Decisions

### Why config-driven, not hard-coded
Two env vars (`GCLOUD_MODEL` + `GCLOUD_MODEL_FAST`) are the source of truth. No local variable forests. Each provider method reads config directly — one ternary: `config.gcloud_model_fast if use_fast else config.gcloud_model`.

### Why hypothesis stays on PRO
Call 7 (hypothesis generation) is the final output — 5 ranked business ideas with revenue models, evidence linkage, and confidence reasoning. Quality matters more than speed here (called once per run, 66s is acceptable). This is the only call where the model does real creative reasoning.

### Why classification can use FAST
Structured JSON extraction at temperature 0.1 is a "read and categorize" task. Flash models handle this well. The retry logic + parallel execution already handle edge cases. Expected: 14.8s/post -> 3-5s/post.

### Rollback path
Delete or comment out `GCLOUD_MODEL_FAST` in `.env` -> falls back to `gemini-2.5-flash` default, which is still a valid model. To fully revert to single-model, set `GCLOUD_MODEL_FAST=gemini-2.5-pro` (same as GCLOUD_MODEL).

---

## Expected Impact

| Metric | Before (pro-only) | After (dual-tier) | Change |
|--------|-------------------|--------------------|--------|
| Classification (30 posts) | 445s | ~90-150s | **3-5x faster** |
| Theme expansion | 72.6s | ~15-25s | **3x faster** |
| Cluster naming | 31.6s | ~6-10s | **3x faster** |
| Total LLM time (30 posts) | ~549s (~9 min) | ~113-188s (~2-3 min) | **3-5x faster** |
| Scaled to 500 posts | ~2 hours | ~25-40 min | **~80 min saved** |
| Hypothesis quality | Good | Unchanged | PRO model retained |

---

## Verification

- [x] `config.gcloud_model_fast` loads from env with default `gemini-2.5-flash`
- [x] `GCloudProvider._url_for_model()` builds correct URLs for both models
- [x] All 3 providers (gcloud, openai_gemini, lm_studio) import cleanly
- [x] All call sites (classifier, expansion, clustering, agents, subreddit_selector) import cleanly
- [x] Hypothesis generation defaults to `use_fast=False` (PRO model)
- [ ] End-to-end pipeline test with fast model (needs live run)
- [ ] Classification quality A/B test: PRO vs FAST on same 100 posts
