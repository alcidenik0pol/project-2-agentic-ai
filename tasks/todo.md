# Token Usage Limiting Implementation

## Completed Tasks

- [x] Create `app/services/usage_tracker.py` - GCS-backed token tracking with monthly reset
- [x] Create `backend/app/api/routes/usage.py` - GET /api/v1/usage endpoint
- [x] Modify `app/analyst/providers/gcloud.py` - Record usage after all Gemini API calls
- [x] Add middleware to `backend/app/main.py` - 429 response when limit exceeded
- [x] Update `app/config.py` - Add `usage_limit_tokens` and `usage_storage_bucket` config
- [x] Create `frontend/app/limit-exceeded/page.tsx` - Limit exceeded page
- [x] Create `frontend/components/UsageIndicator.tsx` - Navbar usage indicator
- [x] Update `frontend/lib/api.ts` - UsageLimitExceededError class
- [x] Update `frontend/contexts/AnalysisContext.tsx` - Handle 429 redirect
- [x] Update `frontend/components/Navbar.tsx` - Add UsageIndicator
- [x] Update `deploy-env.yaml` - Add usage env vars

---

## Manual Steps (User Must Complete)

### Step 1: GCloud Billing Switch

```bash
# 1. Add victor.tenneroni@gmail.com as owner to project
gcloud projects add-iam-policy-binding agenticaicolumbia \
  --member="user:victor.tenneroni@gmail.com" \
  --role="roles/owner"

# 2. Login as new account
gcloud auth login victor.tenneroni@gmail.com

# 3. Link new billing account
gcloud billing projects link agenticaicolumbia --billing-account=016E5B-E5F4E1-FE2ED4

# 4. Verify
gcloud billing projects describe agenticaicolumbia
```

### Step 2: Create GCS Bucket

```bash
# Create the usage tracking bucket
gsutil mb -p agenticaicolumbia -l us-central1 gs://painpan-usage

# Grant service account access
gsutil iam ch serviceAccount:painpan-sa@agenticaicolumbia.iam.gserviceaccount.com:objectAdmin gs://painpan-usage
```

### Step 3: Redeploy

```bash
# From project root
./deploy.sh all
```

---

## Verification Checklist

- [ ] Billing account linked successfully
- [ ] GCS bucket `painpan-usage` created
- [ ] Local test: usage tracking records tokens
- [ ] Local test: limit enforcement returns 429
- [ ] Deploy succeeds
- [ ] Frontend shows usage indicator in navbar
- [ ] Hitting limit redirects to /limit-exceeded
- [ ] New month creates fresh usage file (auto-reset)

---

## Architecture Summary

### Backend Flow
1. All Gemini API calls in `gcloud.py` now call `self._record_usage(data)`
2. Usage tracker extracts `usageMetadata.promptTokenCount` and `candidatesTokenCount`
3. Data persists to GCS bucket (or local file in dev)
4. Middleware checks limit before `/api/v1/analyze` requests
5. Returns 429 with `usage_limit_exceeded` error if over limit

### Frontend Flow
1. `UsageIndicator` component polls `/api/v1/usage` every 30s
2. Shows colored badge: green (>50%), amber (20-50%), red (<20%)
3. `AnalysisContext` catches `UsageLimitExceededError` on submit
4. Redirects to `/limit-exceeded` page with countdown

### Configuration
- `USAGE_LIMIT_TOKENS`: Monthly limit (default 1,000,000)
- `USAGE_STORAGE_BUCKET`: GCS bucket name for persistence
