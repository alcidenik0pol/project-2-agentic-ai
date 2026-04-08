# Trace: LM Studio to Google Cloud Vertex AI Provider Migration

**Date:** 2026-04-08
**Session:** Migrating classification from local LM Studio to Google Cloud Vertex AI with provider abstraction layer
**Files Created:**
- `app/analyst/providers/__init__.py`
- `app/analyst/providers/base.py`
- `app/analyst/providers/lm_studio.py`
- `app/analyst/providers/gcloud.py`
- `scripts/test_providers.py`

**Files Modified:**
- `app/analyst/classifier.py`
- `app/config.py`
- `requirements.txt`
- `.env.example`
- `scripts/classify_posts.py`

---

## 2026-04-08 - Motivation

### Problem
Running 600 posts through local LM Studio with `qwen3.5-27b-claude-4.6-opus-reasoning-distilled` took ~62 minutes (~15.5 sec/post). For the project's multi-agent pipeline, we need faster classification to enable iterative refinement loops and real-time frontend feedback.

### Solution
Add Google Cloud Vertex AI (Gemini 2.5 Flash) as a provider, with a clean abstraction layer so either provider can be swapped via environment variable.

---

## Architecture: Provider Abstraction Layer

### Before (Single Provider)

```
PostClassifier
  ├── OpenAI client → LM Studio (localhost:1234/v1)
  ├── classify_post()     → calls LLM directly
  ├── _parse_classification() → JSON extraction
  └── classify_batch()    → loops over posts
```

All classification logic, LLM client setup, retry logic, and response parsing lived in a single 305-line `classifier.py`.

### After (Provider Pattern)

```
PostClassifier  (thin orchestration layer)
  ├── provider: LLMProvider (interface)
  │     ├── LMStudioProvider  (extracted from old classifier.py)
  │     └── GCloudProvider    (new, Vertex AI + Gemini)
  ├── classify_post()  → delegates to provider
  └── classify_batch() → loops + progress tracking

get_provider(name)  → factory function returning provider instance
```

### Class Hierarchy

```
LLMProvider (ABC)
  ├── classify_post(post_data, subreddit, category, comments_count) -> EnrichedPost
  ├── parse_classification(raw_response) -> ComplaintClassification | None
  ├── model_name: str (property)
  └── provider_name: str (property)
```

Each provider owns its own:
- Client initialization and authentication
- API call logic (with retries)
- Response parsing (reasoning-model quirks for LM Studio, clean JSON for Gemini)

---

## Implementation Details

### 1. Provider Base Class (`app/analyst/providers/base.py`)

Abstract base class defining the interface. Four abstract methods:
- `classify_post()` — main entry point
- `parse_classification()` — JSON extraction from raw LLM output
- `model_name` (property) — e.g., `"gemini-2.5-flash-001"`
- `provider_name` (property) — e.g., `"gcloud"`

### 2. LM Studio Provider (`app/analyst/providers/lm_studio.py`)

Extracted verbatim from the original `classifier.py`. No logic changes. Retains:
- Custom httpx client with single-connection pool (prevents request queuing)
- Thinking-block stripping for reasoning models (`<think...>`, `🔏...🔏`, etc.)
- 3-tier JSON parse fallback (direct → code block → bare object)
- 2-second retry delay between attempts

### 3. Google Cloud Provider (`app/analyst/providers/gcloud.py`)

New implementation using `vertexai` SDK:

```
Initialization:
  ├── Service account key from GCLOUD_SERVICE_ACCOUNT_KEY_PATH
  │   or Application Default Credentials (ADC)
  ├── vertexai.init(project, region, credentials)
  └── GenerativeModel(gemini-2.5-flash-001)

classify_post():
  ├── Format prompt using existing CLASSIFICATION_PROMPT template
  ├── model.generate_content(prompt, generation_config={temperature: 0.1})
  ├── response.text → parse_classification()
  └── Retry up to GCLOUD_MAX_RETRIES times on failure
```

Simpler JSON parsing than LM Studio — Gemini doesn't output thinking blocks, so no need for the regex stripping.

### 4. Configuration (`app/config.py`)

New fields added to frozen dataclass:

| Field | Env Var | Default |
|-------|---------|---------|
| `llm_provider` | `LLM_PROVIDER` | `"gcloud"` |
| `gcloud_project` | `GCLOUD_PROJECT` | `"AgenticAIColumbia"` |
| `gcloud_region` | `GCLOUD_REGION` | `"us-central1"` |
| `gcloud_model` | `GCLOUD_MODEL` | `"gemini-2.5-flash-001"` |
| `gcloud_service_account_key_path` | `GCLOUD_SERVICE_ACCOUNT_KEY_PATH` | `None` |
| `gcloud_timeout` | `GCLOUD_TIMEOUT` | `30` |
| `gcloud_max_retries` | `GCLOUD_MAX_RETRIES` | `3` |

### 5. Refactored Classifier (`app/analyst/classifier.py`)

Reduced from 305 lines to 169 lines. Now a thin orchestration layer:
- `__init__()` → `get_provider(name)` to instantiate the right provider
- `classify_post()` → delegates entirely to `self._provider.classify_post()`
- `classify_batch()` → retains loop, progress tracking, early stopping

The `model_used` field in `ClassificationResult` now includes the provider prefix:
```python
model_used=f"{self._provider_name}:{self._provider.model_name}"
# e.g., "gcloud:gemini-2.5-flash-001" or "lm_studio:qwen3.5-27b-..."
```

---

## Flow Diagram

```
User / .env
     │
     ▼
LLM_PROVIDER=gcloud
     │
     ▼
Config.from_env()
     │
     ▼
PostClassifier.__init__()
     │
     ▼
get_provider("gcloud")
     │
     ├── "gcloud"  → GCloudProvider()
     │     ├── Load service account key
     │     ├── vertexai.init(project, region, creds)
     │     └── GenerativeModel("gemini-2.5-flash-001")
     │
     └── "lm_studio" → LMStudioProvider()
           ├── httpx.Client(max_connections=1)
           └── OpenAI(base_url, api_key="lm-studio")
     │
     ▼
classify_batch(posts)
     │
     ├── for each post:
     │     provider.classify_post(post_data, ...)
     │       │
     │       ├── Format prompt (CLASSIFICATION_PROMPT / RETRY_PROMPT)
     │       ├── Call LLM API
     │       ├── parse_classification(raw_response)
     │       │     ├── Direct JSON parse
     │       │     ├── Extract from markdown code block
     │       │     └── Extract bare JSON object
     │       └── Return EnrichedPost
     │
     └── Return ClassificationResult
```

---

## Verification Results

### Provider Import Test

```
$ conda run -n agentic-ai-p2 python scripts/test_providers.py

Configuration loaded:
  LLM Provider: gcloud
  GCloud Project: AgenticAIColumbia
  GCloud Model: gemini-2.5-flash-001

1. LM Studio provider:
   SUCCESS: provider_name=lm_studio, model_name=qwen3.5-27b-claude-4.6-opus-reasoning-distilled

2. GCloud provider:
   FAILED (expected without service account key): RuntimeError

3. PostClassifier with LM Studio (explicit):
   SUCCESS: provider_name=lm_studio, model_name=qwen3.5-27b-claude-4.6-opus-reasoning-distilled
```

GCloud provider correctly raises `RuntimeError` when no service account key is configured. Once the user adds the key path to `.env`, it will initialize successfully.

### Existing Tests

```
tests/test_rate_limit_metrics.py — 4 tests PASSED (unaffected by provider changes)
```

---

## Switching Providers

### To use Google Cloud (default):
```bash
# In .env:
LLM_PROVIDER=gcloud
GCLOUD_SERVICE_ACCOUNT_KEY_PATH=/path/to/key.json
```

### To use LM Studio (fallback):
```bash
# In .env:
LLM_PROVIDER=lm_studio
# Then start LM Studio with your model loaded
```

### Override at code level:
```python
classifier = PostClassifier(provider_name="lm_studio")  # explicit override
```

---

## Rollback Plan

If Google Cloud provider fails in production:
1. Set `LLM_PROVIDER=lm_studio` in `.env`
2. Start LM Studio locally
3. No code changes needed

---

## Dependencies Added

```
google-cloud-aiplatform>=1.38.0
```

This pulls in `google-auth`, `google-cloud-core`, and the Vertex AI SDK. Total install size is significant but only imported when `GCloudProvider` is instantiated.

---

## Lessons Learned

1. **Extract early, not late.** The original `classifier.py` had all provider-specific logic inline. Extracting to a provider pattern after the fact was straightforward because the `classify_post()` / `classify_batch()` boundary was already clean.

2. **Provider factory pattern is simple and sufficient.** No need for a plugin system or dynamic imports — a dict mapping names to classes handles the two-provider case cleanly.

3. **Gemini response parsing is simpler than reasoning models.** The LM Studio provider needs 8 regex patterns to strip thinking blocks. The GCloud provider doesn't need any — Gemini returns clean text. Both share the same JSON extraction fallback, but the reasoning-model cruft stays isolated in `lm_studio.py`.

4. **Configuration-driven provider selection keeps it simple.** One env var (`LLM_PROVIDER`) switches the entire backend. No feature flags, no conditional imports in business logic.

---

## Remaining Work

- [ ] User sets up Google Cloud service account key
- [ ] Test GCloud provider with real classification
- [ ] Compare classification quality between LM Studio (Qwen) and Gemini
- [ ] Benchmark speed: Gemini Flash should be ~10-20x faster per post
- [ ] Consider adding `provider_name` to CLI script (`--provider` flag)
