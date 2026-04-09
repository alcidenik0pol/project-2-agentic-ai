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
- `app/analyst/config.py`
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
- `model_name` (property) — e.g., `"gemini-2.5-flash"`
- `provider_name` (property) — e.g., `"gcloud"`

### 2. LM Studio Provider (`app/analyst/providers/lm_studio.py`)

Extracted verbatim from the original `classifier.py`. No logic changes. Retains:
- Custom httpx client with single-connection pool (prevents request queuing)
- Thinking-block stripping for reasoning models (`<think...>`, `🔏...🔏`, etc.)
- 3-tier JSON parse fallback (direct → code block → bare object)
- 2-second retry delay between attempts

### 3. Google Cloud Provider (`app/analyst/providers/gcloud.py`)

Uses direct REST API calls to Vertex AI (not the deprecated `vertexai` SDK). See "Debugging Saga" below for why.

```
Initialization:
  ├── Service account key from GCLOUD_SERVICE_ACCOUNT_KEY_PATH
  │   or Application Default Credentials (ADC)
  ├── Lowercase project ID for URL construction
  └── Build REST endpoint URL

classify_post():
  ├── Format prompt using existing CLASSIFICATION_PROMPT template
  ├── Refresh OAuth token if expired
  ├── POST to Vertex AI REST endpoint
  ├── Extract response text from candidates[0].content.parts[0].text
  └── Retry up to GCLOUD_MAX_RETRIES times on failure
```

### 4. Configuration (`app/config.py`)

New fields added to frozen dataclass:

| Field | Env Var | Default |
|-------|---------|---------|
| `llm_provider` | `LLM_PROVIDER` | `"gcloud"` |
| `gcloud_project` | `GCLOUD_PROJECT` | `"AgenticAIColumbia"` |
| `gcloud_region` | `GCLOUD_REGION` | `"us-central1"` |
| `gcloud_model` | `GCLOUD_MODEL` | `"gemini-2.5-flash"` |
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
# e.g., "gcloud:gemini-2.5-flash" or "lm_studio:qwen3.5-27b-..."
```

---

## Debugging Saga: Three Bugs That Caused the 403

### Timeline

```
14:52  First test → 403 PERMISSION_DENIED on all 3 attempts
       Error: "CONSUMER_INVALID" for project AgenticAIColumbia
       My incorrect diagnosis: "API not enabled" or "role not granted"
       User confirmed: API IS enabled, role IS granted

15:05  Re-test → same 403, still blaming Google Cloud setup

15:07  Wrote direct REST test script → STATUS 200 SUCCESS
       Same service account, same project, different code path

15:07  Re-test through vertexai SDK → still 403
       Re-test through REST → 200

       ROOT CAUSES FOUND:
       ┌──────────────────────────────────────────────────────────────┐
       │ Bug 1: Prompt template had unescaped { braces               │
       │ Bug 2: vertexai SDK passes project ID with original casing  │
       │ Bug 3: Project ID casing — API requires lowercase           │
       └──────────────────────────────────────────────────────────────┘

15:09  Fixed all three → 100% success, 6 seconds per post
```

### Bug 1: Prompt Template — Unescaped Braces

**File:** `app/analyst/prompts.py`

The `CLASSIFICATION_PROMPT` contained a JSON example with bare `{` braces:

```python
# BROKEN — Python's .format() tries to interpret "theme" as a variable
Return ONLY a JSON object in this exact format:
{
  "theme": "core complaint theme (3 words or less)",
  "is_complaint": true/false,
  "intensity": "low" | "medium" | "high"
}
```

When `.format(title=..., selftext=..., subreddit=...)` was called, Python saw `{\n  "theme"` and raised:
```
KeyError: '\n  "theme"'
```

This error was silently caught by the try/except in `classify_post()` and counted as a failed attempt.

**Fix:** Escape with double braces `{{` and `}}`:
```python
Return ONLY a JSON object in this exact format:
{{
  "theme": "core complaint theme (3 words or less)",
  "is_complaint": true/false,
  "intensity": "low" | "medium" | "high"
}}
```

**Note:** The `RETRY_PROMPT` already had this correct (used `{{}}` throughout).

### Bug 2: Deprecated `vertexai` SDK Passes Mixed-Case Project ID

**The `vertexai` Python SDK** (deprecated June 2025) was used in the initial implementation:

```python
vertexai.init(
    project="AgenticAIColumbia",  # mixed case from config
    location="us-central1",
    credentials=credentials,
)
```

The SDK passes the project ID to gRPC calls as-is, without lowercasing. This resulted in the API receiving `AgenticAIColumbia` instead of `agenticaicolumbia`, producing:
```
403 Permission denied on resource project AgenticAIColumbia.
[reason: "CONSUMER_INVALID"]
```

A direct REST call with the lowercase project ID worked immediately:
```python
url = ".../projects/agenticaicolumbia/..."  # lowercase → 200 OK
```

**Fix:** Replaced the `vertexai` SDK with direct REST API calls using `requests` + `google-auth`. The provider now constructs the URL with `.lower()`:

```python
project_lower = self._project.lower()
self._url = (
    f"https://{self._region}-aiplatform.googleapis.com/v1/"
    f"projects/{project_lower}/locations/{self._region}/"
    f"publishers/google/models/{self._model}:generateContent"
)
```

### Bug 3: Model ID Versioning

**Initial model ID:** `gemini-2.5-flash-001`
**Working model ID:** `gemini-2.5-flash`

The version-suffixed ID returned 404 NOT_FOUND. Google's Vertex AI publisher endpoint uses the model name without the version suffix for the latest stable version.

---

## The Correct Debugging Approach (What I Should Have Done)

When the user says "the API is enabled and the role is granted":

1. **Test with a direct REST call FIRST** — bypass the SDK entirely to isolate whether the issue is auth or code
2. **Compare the working request to the failing request** — the REST call succeeded while the SDK failed, proving the issue was in the SDK, not the infrastructure
3. **Check URL casing** — Google Cloud project IDs are always lowercase; the display name "AgenticAIColumbia" is NOT the project ID

What I did wrong: I kept asking the user to fix things in the Google Cloud Console for ~20 minutes when the problem was entirely in my code.

---

## Working Configuration Reference

### `.env`
```bash
LLM_PROVIDER=gcloud
GCLOUD_PROJECT=AgenticAIColumbia    # Display name (lowercased in code)
GCLOUD_REGION=us-central1
GCLOUD_MODEL=gemini-2.5-flash       # No version suffix
GCLOUD_SERVICE_ACCOUNT_KEY_PATH=/path/to/key.json
GCLOUD_TIMEOUT=30
GCLOUD_MAX_RETRIES=3
```

### Service Account Requirements
- Role: **Vertex AI User** (`roles/aiplatform.user`)
- API: **Vertex AI API** must be enabled on the project

### Key File Location
```
docs/credentials/agenticaicolumbia-72b6c0b1b975.json
```
- Listed in `.gitignore` under `docs/credentials/`
- SA email: `reddit-analyst@agenticaicolumbia.iam.gserviceaccount.com`

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
     │     ├── Build REST URL (project ID lowercased)
     │     └── Prepare credentials with cloud-platform scope
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
     │       ├── Refresh OAuth token if expired
     │       ├── POST to Vertex AI REST endpoint
     │       ├── Extract text from candidates[0].content.parts[0].text
     │       ├── parse_classification(raw_response)
     │       │     ├── Direct JSON parse
     │       │     ├── Extract from markdown code block
     │       │     └── Extract bare JSON object
     │       └── Return EnrichedPost
     │
     └── Return ClassificationResult
```

---

## First Successful Classification

```
Post: "X, Meta, and CCP-affiliated content is no longer permitted"
  Theme: Far-right content
  Is Complaint: True
  Intensity: high
  Processing time: 6.0 seconds
  Model: gcloud:gemini-2.5-flash
  Success rate: 100%
```

---

## Lessons Learned

1. **Bug your code first, not the user's infrastructure.** When a 403 comes back, write a minimal REST call to test auth before asking the user to change console settings. The direct REST test took 30 seconds to write and immediately proved auth was fine.

2. **Google Cloud project IDs are always lowercase.** The display name "AgenticAIColumbia" is NOT the project ID. The project ID is `agenticaicolumbia`. When constructing API URLs, always `.lower()` the project name.

3. **The `vertexai` Python SDK is deprecated (June 2025) and has bugs.** It does not lowercase project IDs before making gRPC calls, causing mysterious 403s. Use direct REST calls with `requests` + `google-auth` instead.

4. **Python `.format()` breaks on unescaped JSON.** Any literal `{` or `}` in a string passed to `.format()` must be escaped as `{{` and `}}`. This applies to prompt templates that contain JSON examples. The `RETRY_PROMPT` was correct; `CLASSIFICATION_PROMPT` was broken.

5. **Model IDs: use the short form.** `gemini-2.5-flash` works; `gemini-2.5-flash-001` returns 404 on the publisher endpoint. The short form resolves to the latest stable version automatically.

6. **Test the simplest possible thing first.** Instead of running the full pipeline through the provider abstraction, a 20-line script that calls the API directly with hardcoded values would have revealed the casing issue in 30 seconds instead of 20 minutes.
