# Frontend Firebase Migration — Phase 5 Cleanup

**Date:** 2026-07-01
**Predecessor:** [`2026-06-28_frontend-static-hosting-migration.md`](./2026-06-28_frontend-static-hosting-migration.md)
**Goal:** Delete the now-orphaned `painpan-frontend` Cloud Run service + GCS bucket + old container images. Drop the rollback origin from backend CORS. Remove dead code (`frontend/Dockerfile`) and dead CI steps.
**Status: PARTIAL** — code/config changes applied and committed; **GCP-side deletes pending** (see "Manual GCP cleanup" below).

---

## Precondition verification (done before this commit)

| Check | How verified | Result |
|---|---|---|
| Firebase site serving the actual app (not placeholder) | `curl https://agenticaicolumbia-fb.web.app/` → `<title>Based Instinct</title>` | ✅ |
| Backend Cloud Run untouched and serving | `painpan-backend` URL unchanged in `deploy.yml:11` | ✅ |
| Migration files committed | `git log --oneline -1` → `0935fc6 Move frontend to Firebase Hosting (pivot from GCS)` | ✅ |

The predecessor trace's Phase 5 trigger was "verified working for ~1 week." The user asserted the migration is done and the Firebase URL is provably serving the real app, so the cleanup was authorized despite the formal verification window not literally elapsing. The committed migration (`0935fc6`) preserves the rollback path in git history — `git revert 0935fc6` restores the pre-migration state if a regression is found after the Cloud Run service is deleted.

---

## Code/config changes (this commit)

| File | Change |
|---|---|
| `deploy-env.yaml:1` | Dropped `https://painpan-frontend-953400329307.us-central1.run.app` from `CORS_ORIGINS`. Backend now accepts only Firebase + localhost origins. |
| `.github/workflows/deploy.yml` (was lines 111-114) | Removed the `painpan-frontend` revision-cleanup block. The backend revision-cleanup block stays. |
| `.github/workflows/deploy.yml` (was lines 125-130) | Removed the `painpan/frontend` Artifact Registry cleanup block. The backend image-cleanup block stays. |
| `frontend/Dockerfile` | **Deleted** — dead code since the migration. The Firebase deploy path doesn't containerize. |

These CI blocks would have no-op'd (or warned on missing service) once the Cloud Run service is deleted; removing them keeps the workflow honest about what it actually manages.

---

## Manual GCP cleanup (USER RUNS — `gcloud` is silent in this project's MSYS shell)

All commands target the `agenticaicolumbia` GCP project (where the old frontend container lived). The Firebase project (`agenticaicolumbia-fb`) is untouched.

```bash
# 1. Delete the orphaned Cloud Run service
gcloud run services delete painpan-frontend \
  --region=us-central1 --project agenticaicolumbia

# 2. Delete the orphaned GCS bucket (from the abandoned GCS hosting attempt)
gsutil rm -r gs://painpan-frontend

# 3. Belt-and-suspenders: delete any leftover revisions
#    (`services delete` cascades these, but explicit is safer)
gcloud run revisions list \
  --service=painpan-frontend --region=us-central1 --project agenticaicolumbia \
  --format="value(name)" \
  | xargs -I {} gcloud run revisions delete {} \
    --region=us-central1 --project agenticaicolumbia --quiet

# 4. Delete old frontend container images from Artifact Registry
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/agenticaicolumbia/painpan/frontend \
  --format="get(version)" \
  | xargs -I {} gcloud artifacts docker images delete \
    us-central1-docker.pkg.dev/agenticaicolumbia/painpan/frontend@{} --quiet
```

Steps 3 and 4 should produce "not found" messages after step 1 cascades — that's expected, not an error. If they list and delete real resources, that's the value.

---

## Verification (after the GCP cleanup)

- `gcloud run services list --project agenticaicolumbia` → only `painpan-backend` listed
- `curl -sI https://painpan-backend-953400329307.us-central1.run.app/docs` → 200 (unchanged)
- `https://agenticaicolumbia-fb.web.app/` → loads, runs an analysis end-to-end, WS connects (`wss://painpan-backend-.../ws/<run_id>` → 101)
- No CORS errors in browser DevTools console
- 24h later: GCP Billing shows no `painpan-frontend` line item; Firebase project `agenticaicolumbia-fb` shows $0 (Spark plan)

---

## What stays

| Resource | Project | Why it stays |
|---|---|---|
| `painpan-backend` Cloud Run | `agenticaicolumbia` (GCP) | The app's API. Firebase frontend calls this. |
| Backend Artifact Registry images (`painpan/backend`) | `agenticaicolumbia` (GCP) | Backend deploys need them. |
| Firebase Hosting site | `agenticaicolumbia-fb` (Firebase) | The live frontend. |
| Service Account `painpan-sa@agenticaicolumbia...` | `agenticaicolumbia` (GCP) | Backend identity. |

---

## Rollback (if a regression surfaces after deletion)

`git revert <this-commit-hash> 0935fc6` restores the pre-migration `deploy.yml`, `deploy-env.yaml`, `next.config.js`, and `frontend/Dockerfile`. Then push to `main` — CI redeploys the frontend container to Cloud Run.

**Caveat:** this only works if the `painpan-frontend` Cloud Run service still exists. Once step 1 of the manual GCP cleanup runs, the rollback path requires recreating the service from the restored `frontend/Dockerfile` — which CI will do on the next push, but with a fresh cold start and a new revision history. Acceptable but not instant.

If `painpan-frontend` was keeping some state (it wasn't — it was a stateless static-file server), that state would be lost. Confirmed not the case here.
