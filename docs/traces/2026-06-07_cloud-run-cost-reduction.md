# Cloud Run Cost Reduction

**Date:** 2026-06-07
**Problem:** ~$20/month charges for an unused app
**Result:** Expected reduction to ~$3-5/month

---

## Root Cause Analysis

Cloud Run has `min-instances=0` (correct), so the app shouldn't cost anything when idle. However, costs were accumulating from:

| Source | Estimated Cost | Why It Happens | Fix |
|--------|---------------|----------------|-----|
| Cloud Run CPU (bot traffic) | ~$15-18/month | Crawlers wake instances, cold starts bill CPU | robots.txt + cpu-throttling |
| Artifact Registry storage | ~$1-2/month | Old Docker images accumulate with each deploy | Cleanup step in CI/CD |
| Network egress | ~$1-2/month | Response data leaving GCP | Can't easily reduce |

**The big cost is Cloud Run CPU, not storage.** Bots hit your site, cold start happens, you pay for CPU time. The changes we made (robots.txt, `--cpu=0.5`, `--cpu-throttling`) target this main cost driver.

---

## Solution Components

### 1. Block Crawlers with robots.txt

**File:** `frontend/public/robots.txt`

```
User-agent: *
Disallow: /
```

**Reasoning:** Well-behaved bots (Google, Bing) respect robots.txt and won't crawl the site. This reduces legitimate bot traffic that wakes instances. Malicious scanners ignore it, but they're a smaller portion of traffic.

**Limitation:** Won't stop all bots, but reduces the majority of crawler traffic.

---

### 2. Revision + Image Cleanup in CI/CD

**File:** `.github/workflows/deploy.yml`

**Critical prerequisite:** The service account needs delete permissions:

```bash
gcloud projects add-iam-policy-binding agenticaicolumbia --member="serviceAccount:painpan-sa@agenticaicolumbia.iam.gserviceaccount.com" --role="roles/artifactregistry.admin"
```

**Why two cleanup steps?** Cloud Run revisions hold references to Docker images. You can't delete an image while a revision points to it. Must delete revisions first, then images.

**Step 1: Delete old revisions**

```yaml
- name: Cleanup old Cloud Run revisions
  run: |
    # Delete all non-active backend revisions
    gcloud run revisions list --service=painpan-backend --region=${{ env.REGION }} --format="value(name)" | \
      grep -v "$(gcloud run services describe painpan-backend --region=${{ env.REGION }} --format='value(status.latestReadyRevisionName)')" | \
      xargs -I {} gcloud run revisions delete {} --region=${{ env.REGION }} --quiet || true

    # Delete all non-active frontend revisions
    gcloud run revisions list --service=painpan-frontend --region=${{ env.REGION }} --format="value(name)" | \
      grep -v "$(gcloud run services describe painpan-frontend --region=${{ env.REGION }} --format='value(status.latestReadyRevisionName)')" | \
      xargs -I {} gcloud run revisions delete {} --region=${{ env.REGION }} --quiet || true
```

**Step 2: Delete old images**

```yaml
- name: Cleanup old Artifact Registry images
  run: |
    # Delete all backend images except the one just deployed
    gcloud artifacts docker images list \
      ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPO }}/backend \
      --sort-by=~CREATE_TIME --format="get(version)" | tail -n +2 | \
      xargs -I {} gcloud artifacts docker images delete \
        ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPO }}/backend@{} --quiet --async || true

    # Delete all frontend images except the one just deployed
    gcloud artifacts docker images list \
      ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPO }}/frontend \
      --sort-by=~CREATE_TIME --format="get(version)" | tail -n +2 | \
      xargs -I {} gcloud artifacts docker images delete \
        ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPO }}/frontend@{} --quiet --async || true
```

**How it works:**
- Revision cleanup: Lists all revisions, filters out the active one, deletes the rest
- Image cleanup: `--sort-by=~CREATE_TIME` sorts newest first, `tail -n +2` skips the newest, deletes the rest
- `--async` makes deletion non-blocking so CI doesn't wait
- `|| true` ensures the step doesn't fail if there's nothing to delete

**Result:** Each deploy cleans up ALL old revisions and ALL old images, not just one.

---

### 3. Reduce Frontend CPU Allocation

**File:** `.github/workflows/deploy.yml`

Changed from `--cpu=1` to `--cpu=0.5` for frontend:

```yaml
--cpu=0.5
```

**Reasoning:** Next.js SSR doesn't need a full CPU for simple page renders. Halving CPU allocation halves compute costs when the frontend is serving requests.

**Tradeoff:** Slightly slower cold starts and request processing. Acceptable for a low-traffic app.

---

### 4. Explicit CPU Throttling

**File:** `.github/workflows/deploy.yml`

Added `--cpu-throttling` to both services:

```yaml
--cpu-throttling
```

**What it does:** Ensures CPU is **only billed during active request processing**, not during idle periods between requests within the same instance lifecycle.

**Note:** This is the default for Gen2 Cloud Run, but making it explicit:
1. Documents the intent
2. Prevents accidental changes
3. Ensures it works regardless of generation

---

## One-Time Cleanup Commands

### Prerequisites

You need Artifact Registry Admin permissions:

```bash
gcloud projects add-iam-policy-binding agenticaicolumbia --member="user:YOUR_EMAIL@gmail.com" --role="roles/artifactregistry.admin"
```

Then re-authenticate:

```bash
gcloud auth login
```

### Why Image Deletion Fails: Cloud Run Revisions

Cloud Run keeps "revisions" (snapshots of each deployment). Each revision references a specific Docker image digest. **GCP won't let you delete an image while a revision points to it.**

You must delete old revisions first, then delete the images.

### Step 1: List Revisions

```bash
gcloud run revisions list --service=painpan-backend --region=us-central1 --format="table(name,active)"
```

```bash
gcloud run revisions list --service=painpan-frontend --region=us-central1 --format="table(name,active)"
```

### Step 2: Delete Old Revisions (Keep Active One)

```bash
# Delete all non-active backend revisions
gcloud run revisions list --service=painpan-backend --region=us-central1 --format="value(name)" | grep -v "$(gcloud run services describe painpan-backend --region=us-central1 --format='value(status.latestReadyRevisionName)')" | xargs -I {} gcloud run revisions delete {} --region=us-central1 --quiet
```

```bash
# Delete all non-active frontend revisions
gcloud run revisions list --service=painpan-frontend --region=us-central1 --format="value(name)" | grep -v "$(gcloud run services describe painpan-frontend --region=us-central1 --format='value(status.latestReadyRevisionName)')" | xargs -I {} gcloud run revisions delete {} --region=us-central1 --quiet
```

### Step 3: Delete Old Images

After revisions are deleted, the images become deletable:

```bash
# List current images to see accumulation
gcloud artifacts docker images list us-central1-docker.pkg.dev/agenticaicolumbia/painpan --include-tags
```

```bash
# Delete all but latest backend image
gcloud artifacts docker images list us-central1-docker.pkg.dev/agenticaicolumbia/painpan/backend --sort-by=~CREATE_TIME --format="get(version)" | tail -n +2 | xargs -I {} gcloud artifacts docker images delete us-central1-docker.pkg.dev/agenticaicolumbia/painpan/backend@{} --quiet
```

```bash
# Delete all but latest frontend image
gcloud artifacts docker images list us-central1-docker.pkg.dev/agenticaicolumbia/painpan/frontend --sort-by=~CREATE_TIME --format="get(version)" | tail -n +2 | xargs -I {} gcloud artifacts docker images delete us-central1-docker.pkg.dev/agenticaicolumbia/painpan/frontend@{} --quiet
```

### Note on Storage Costs

This cleanup saves ~$1-2/month. The real savings (~$15/month) come from the bot-blocking and CPU changes which are already in the deploy workflow.

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/public/robots.txt` | Created - blocks all crawlers |
| `.github/workflows/deploy.yml:61` | Added `--cpu-throttling` to backend |
| `.github/workflows/deploy.yml:90` | Changed frontend CPU from `1` to `0.5` |
| `.github/workflows/deploy.yml:91` | Added `--cpu-throttling` to frontend |
| `.github/workflows/deploy.yml:103-113` | Added revision cleanup step |
| `.github/workflows/deploy.yml:115-129` | Added image cleanup step |

## IAM Changes Required

Run this once to enable CI/CD cleanup:

```bash
gcloud projects add-iam-policy-binding agenticaicolumbia --member="serviceAccount:painpan-sa@agenticaicolumbia.iam.gserviceaccount.com" --role="roles/artifactregistry.admin"
```

---

## Verification Checklist

After deployment, monitor for 1 week:

- [ ] Check GCP Billing Console for reduced charges
- [ ] Verify Cloud Run logs show fewer bot requests
- [ ] Confirm Artifact Registry has only 1 image per service
- [ ] Test that the app still works correctly with reduced CPU

---

## Cost Breakdown

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| Cloud Run CPU (bot traffic) | ~$15-18/mo | ~$2-3/mo | ~$13-15/mo |
| Artifact Registry storage | ~$1-2/mo | ~$0.10/mo | ~$1-2/mo |
| Network egress | ~$1-2/mo | ~$1-2/mo | $0 |
| **Total** | **~$20/mo** | **~$3-5/mo** | **~$15-17/mo** |

**Key insight:** Storage is cheap. CPU triggered by bot traffic is expensive. Focus on preventing instance wake-ups.
