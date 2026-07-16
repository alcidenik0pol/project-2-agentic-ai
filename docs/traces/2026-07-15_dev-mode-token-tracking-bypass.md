# Trace: Dev-Mode Token Tracking Bypass

**Date:** 2026-07-15
**Status:** Done

---

## Problem

Token throttling fired identically in local dev and in production. The flow:

1. `gcloud.py` `_record_usage()` wrote to the tracker on every Gemini call → `app/services/usage_tracker.py:203-225` (GCS write, or local file fallback).
2. `backend/app/main.py` `check_usage_limit` middleware hit the tracker on every `POST /api/v1/analysis` and returned 429 once the monthly counter (default 1M tokens) was exceeded.

Both steps were unconditional. There was no concept of "dev mode" in the backend — only implicit signals (storage-writability probing, presence of `usage_storage_bucket`). The user asked for a way to disable counting **and** limiting locally, with "0 ambiguity, crystal clear implementation."

---

## Decision: Explicit Env Var over Host Detection

The user's phrasing ("reliable way to detect that we are in dev mode now i.e. localhost") initially suggested host/IP-based detection. Pushed back: auto-detection is implicit (surprising behavior), fragile (reverse proxies, Docker networks, preview URLs), and conflicts with the stated bar. An explicit env var is strictly more reliable and matches the existing `app/config.py` single-source-of-truth pattern.

The contract:

- `APP_ENV` env var, default `"development"`.
- `Config.environment` field + `Config.is_development` property.
- In dev: skip token counting, skip the limit gate, report `tracking_enabled: false` on `/usage`.
- In prod: behavior unchanged.
- Safe default: anything other than `"development"` (including typos like `"staging"`, `"prod"`, `"produciton"`) fails closed → treated as production.

Deploy sets `APP_ENV=production`; local dev relies on the default.

---

## Fix

### Backend

- **`app/config.py`** — added `environment: str = "development"` field and `is_development` property. Loaded from `APP_ENV`. The frozen dataclass accepts a property because `@property` is a class-level descriptor, not an instance attribute.
- **`backend/app/main.py`** — `check_usage_limit` middleware early-returns when `config.is_development`. The check is hoisted **above** the path/method branch so the entire middleware becomes a no-op (no tracker instantiation, no path matching).
- **`app/analyst/providers/gcloud.py`** — `_record_usage` early-returns when `config.is_development`, before reading `usageMetadata` or touching the tracker.
- **`backend/app/models/api.py`** — `UsageResponse` gained `tracking_enabled: bool` (defaults to `True`, so old clients keep working).
- **`backend/app/api/routes/usage.py`** — dev branch returns zeros with `tracking_enabled=False` without instantiating the tracker.

### Frontend

- **`frontend/components/UsageIndicator.tsx`** — when `tracking_enabled === false`, renders a small amber `DEV` badge with a `Wrench` icon and a `title=` tooltip: *"Local dev mode — token counting and monthly limits are disabled (APP_ENV=development)"*. Token-count rendering is unchanged for prod. Used the existing native `title=` convention rather than the installed-but-unused `@radix-ui/react-tooltip` to keep the diff minimal — there is no tooltip component anywhere else in the codebase to migrate to.

### Deploy / Docs

- **`deploy-env.yaml`** — added `APP_ENV: "production"`.
- **`.env.example`** — documented `APP_ENV`.

---

## Files Modified

| File | Change |
|------|--------|
| `app/config.py` | +`environment` field, +`is_development` property, +`APP_ENV` env loading |
| `backend/app/main.py` | `check_usage_limit` short-circuits in dev (3 lines) |
| `app/analyst/providers/gcloud.py` | `_record_usage` short-circuits in dev (3 lines) |
| `backend/app/models/api.py` | `UsageResponse.tracking_enabled: bool = True` |
| `backend/app/api/routes/usage.py` | Dev branch returns zeros without touching tracker |
| `frontend/components/UsageIndicator.tsx` | New dev-mode branch renders `DEV` badge w/ tooltip |
| `deploy-env.yaml` | +`APP_ENV: "production"` |
| `.env.example` | Documented `APP_ENV` |
| `app/tests/test_dev_mode.py` | New file — 10 tests (all passing) |

Total diff: ~80 lines across 9 files. Backend changes are ~15 lines of logic, the rest is tests + docs.

---

## Pattern: The Boolean Gate Beats the Auto-Detected Signal

The recurring temptation in dev/prod forks is to detect the environment from circumstantial evidence (hostnames, IP ranges, file paths, credential presence). Every one of these is a heuristic that eventually misfires:

- Hostname checks break under reverse proxies, Docker bridge networks, and preview deployments.
- "Bucket is configured → production" breaks the moment someone sets the bucket locally to test GCS writes.
- "Writability of `data/usage/`" breaks under any container with a read-only mount, regardless of environment.

An explicit env var has none of these failure modes. The cost is one line in the deploy manifest — trivial compared to the debugging time saved. **Default to the safe value** (here, `"development"`) so forgetting to set it in prod is the obviously-wrong failure rather than a silent over-permissive one. The fail-closed behavior on unknown values (`"staging"` → treated as prod) is a deliberate choice: typos shouldn't disable rate limits.

---

## Test Gotcha: Module Attribute Shadowing

Three of the ten tests failed initially due to a non-obvious interaction in `app/services/`:

```python
# app/services/__init__.py
from app.services.usage_tracker import usage_tracker, UsageStats
```

```python
# app/services/usage_tracker.py:284
usage_tracker = property(lambda _: get_usage_tracker())
```

The `__init__.py` re-exports `usage_tracker` — which is a module-level **`property` object**, not the submodule. After import, attribute access `app.services.usage_tracker` resolves to the property descriptor, not the module. `import app.services.usage_tracker as m` returns the property. `monkeypatch.setattr("app.services.usage_tracker.get_usage_tracker", ...)` fails with `AttributeError: 'property' object has no attribute 'get_usage_tracker'`.

Fix in tests: bypass attribute resolution entirely with `sys.modules["app.services.usage_tracker"]`, and use object-based monkeypatch (`monkeypatch.setattr(module_obj, "name", value)`) instead of string-based paths.

A related gotcha: replacing `app.config.config` with a `SimpleNamespace` stub broke `@retry_with_exponential_backoff()`, which reads `config.retry_max_attempts` at **class definition time**. The decorator runs once when `GCloudProvider` is first imported, so any stub must come **after** the class is defined. Solution: import the provider class at class scope in the test (outside the test method), then patch config inside the test body.

---

## Out of Scope / Known Caveats

Three pre-existing issues discovered during this work, all flagged but **not fixed** (outside the task scope):

1. **`openai_gemini` provider never records tokens.** Only `gcloud.py` calls `_record_usage`. If `LLM_PROVIDER=openai_gemini` is set in prod, the usage gate is silently a no-op — users can blow through the limit with no accounting. Pre-existing; needs a separate decision (mirror the call in openai_gemini, or document the limitation).

2. **Frontend DRY violation.** `UsageIndicator.tsx`, `app/limit-exceeded/page.tsx`, and `UsageLimitExceededError` in `lib/api.ts` each reconstruct the usage-fetch logic independently. `UsageIndicator` bypasses the typed `request<T>()` helper in `lib/api.ts`. There's no `UsageResponse` type in `lib/types.ts`. Worth a follow-up consolidation — but didn't touch it here.

3. **Dead `property` in `usage_tracker.py:284`.** `usage_tracker = property(lambda _: get_usage_tracker())` is a module-level property descriptor that nothing ever uses as an actual property (modules aren't classes). It's exported via `__init__.py` and shadows the submodule, which caused the test friction above. Candidate for removal in a cleanup pass.

---

## Verification

1. **New tests:** `pytest app/tests/test_dev_mode.py -v` → **10/10 passed**.
   - 4 config tests: default, production, development, unknown-value-fails-closed.
   - 3 `_record_usage` tests: dev skips tracker, prod calls tracker, dev no-op with realistic payload.
   - 3 endpoint tests: dev returns zeros, prod returns real numbers, dev doesn't instantiate tracker.

2. **Regression:** `pytest app/tests/` → **37/37 passed** (10 new + 27 existing, minus network-dependent `test_reddit_api.py`).

3. **Local manual check** (not run, requires running server):
   ```bash
   # Dev (default): tracking_enabled: false, zeros
   curl http://localhost:8901/api/v1/usage

   # Prod verification:
   APP_ENV=production python -m uvicorn backend.app.main:app --port 8901 --reload
   curl http://localhost:8901/api/v1/usage  # tracking_enabled: true, real numbers
   ```

4. **Frontend:** not yet verified in browser — needs `npm run dev`. Expected: small amber `DEV` badge with wrench icon appears where the `%` indicator used to be, with tooltip on hover.

---

## Related Traces

- `2026-04-15_frozen-config-mode-override.md` — same `Config` dataclass, same `frozen=True` constraint, same pattern of late-binding reads inside function bodies.
- `2026-04-17_graceful-429-rate-limit-handling.md` — the 429 response contract this middleware emits; the dev bypass means dev clients never see it.
