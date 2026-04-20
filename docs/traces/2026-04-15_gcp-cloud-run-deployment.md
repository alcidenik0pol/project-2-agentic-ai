# Trace: GCP Cloud Run Deployment

**Date:** 2026-04-15
**Session:** Deploying the Based Instinct multi-agent Reddit analysis app (FastAPI backend + Next.js frontend) to Google Cloud Run. Encountered and resolved several GCP-specific issues around credentials, environment variables, and CLI syntax.

---

## Deployment Architecture

```
Internet → Cloud Run (Frontend, Next.js, port 3456)
                → Cloud Run (Backend, FastAPI, port 8901)
                    → Vertex AI API (Gemini 2.5 Pro/Flash)
                    → Reddit Public API
```

**Services deployed:**
- `painpan-backend` — `https://painpan-backend-953400329307.us-central1.run.app`
- `painpan-frontend` — `https://painpan-frontend-953400329307.us-central1.run.app`

**Region:** `us-central1`
**Project ID:** `agenticaicolumbia` (display name: `AgenticAIColumbia`)

---

## Files Created

| File | Purpose |
|------|---------|
| `cloudbuild-backend.yaml` | Cloud Build config to build & push backend Docker image to Artifact Registry |
| `cloudbuild-frontend.yaml` | Cloud Build config to build & push frontend Docker image to Artifact Registry |
| `deploy-env.yaml` | Backend env vars file for Cloud Run (used because commas in values break `--set-env-vars`) |
| `deploy.sh` | Manual deploy script (`./deploy.sh backend\|frontend\|all`) |
| `.github/workflows/deploy.yml` | GitHub Actions CI/CD: auto-deploy on push to main |

## Files Modified

| File | Change |
|------|--------|
| `backend/app/main.py` | CORS origins now read from `CORS_ORIGINS` env var (comma-separated), falls back to localhost defaults when unset |

---

## Infrastructure Created (One-Time)

| Resource | Name | Purpose |
|----------|------|---------|
| Artifact Registry repo | `painpan` (us-central1, docker format) | Stores versioned container images |
| Service Account | `painpan-sa@agenticaicolumbia.iam.gserviceaccount.com` | Identity for Cloud Run services |
| IAM binding | `roles/aiplatform.user` on `painpan-sa` | Vertex AI access for Gemini models |
| IAM binding | `roles/secretmanager.secretAccessor` on `painpan-sa` | Future secret access (not used yet) |
| IAM binding | `roles/storage.objectAdmin` on `painpan-sa` | Output artifact storage access |
| IAM binding | `roles/artifactregistry.writer` on `painpan-sa` | Push Docker images (CI/CD + manual deploy) |
| IAM binding | `roles/run.admin` on `painpan-sa` | Create/update Cloud Run services |
| IAM binding | `roles/iam.serviceAccountUser` on `painpan-sa` | Act as service account during deploy |

---

## Specificities & Adjustments

### 1. gcloud Account and Project Switch

**Problem:** Active gcloud config was pointed at a different project (`nychackathon2026`) with a personal account.

**Resolution:**
```bash
gcloud config set account vt2435@columbia.edu
gcloud config set project agenticaicolumbia
```

**Note:** The project ID is `agenticaicolumbia` (lowercase), while the display name is `AgenticAIColumbia`. The app's `config.py` uses `AgenticAIColumbia` as the default for `GCLOUD_PROJECT`, but the GCloudProvider lowercases it (`project_lower = self._project.lower()`) when building Vertex AI REST URLs, so it works correctly.

### 2. No Secret Manager Needed — Application Default Credentials

**Problem:** Initial plan assumed we'd need to store the service account key (`docs/credentials/credentials.json`) in Secret Manager and mount it into the container.

**Discovery:** The `GCloudProvider._initialize_credentials()` method in `app/analyst/providers/gcloud.py` already has a fallback chain:
```python
if cred_path.exists():
    # Use service account file (local dev)
    self._credentials = service_account.Credentials.from_service_account_file(...)
else:
    # Fallback to Application Default Credentials (Cloud Run)
    self._credentials, _ = google.auth.default(scopes=[...])
```

On Cloud Run, the credentials file doesn't exist (it's in `.gitignore` so it's not in the Docker image), so the code automatically uses `google.auth.default()` which picks up the Cloud Run service account's credentials. **No secrets to manage.**

**Resolution:** Skipped Secret Manager entirely. Attached `painpan-sa` service account directly to Cloud Run services via `--service-account` flag.

### 3. `gcloud builds submit` Has No `--dockerfile` Flag

**Problem:** Attempted to build with:
```bash
gcloud builds submit --tag IMAGE --dockerfile=backend/Dockerfile .
```
**Error:** `unrecognized arguments: --dockerfile=backend/Dockerfile`

**Resolution:** Created `cloudbuild-backend.yaml` and `cloudbuild-frontend.yaml` with explicit build steps that specify the Dockerfile path:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'IMAGE', '-f', 'backend/Dockerfile', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'IMAGE']
```

### 4. Cloud Run Rejects `PORT` Environment Variable

**Problem:** Attempted to deploy frontend with:
```bash
gcloud run deploy ... --set-env-vars=PORT=3456
```
**Error:** `The following reserved env names were provided: PORT. These values are automatically set by the system.`

**Root Cause:** Cloud Run automatically sets `PORT` (defaults to 8080) and does not allow overriding it. The container must listen on whatever port Cloud Run provides.

**Resolution:** Removed `PORT` from `--set-env-vars`. Used `--port=3456` on the `gcloud run deploy` command to tell Cloud Run which port the container listens on. The Next.js `npm start` command uses `next start --port 3456` (hardcoded in `package.json`), which matches.

**Potential Future Issue:** If Cloud Run ever overrides the `PORT` env var and Next.js reads it, there could be a mismatch. Currently safe because `next start --port 3456` ignores the `PORT` env var.

### 5. Comma-Separated Env Var Values Break `--set-env-vars`

**Problem:** Attempted to set CORS origins with:
```bash
gcloud run services update painpan-backend --set-env-vars="CORS_ORIGINS=https://...app,http://localhost:3456"
```
**Error:** `Bad syntax for dict arg: [http://localhost:3456]`

**Root Cause:** `gcloud` parses commas as separators between key=value pairs, not as literal characters within a value. The second URL was interpreted as a new key-value pair.

**Resolution:** Created a YAML file (`deploy-env.yaml`) and used `--env-vars-file`:
```yaml
CORS_ORIGINS: "https://painpan-frontend-...run.app,http://localhost:3456,http://127.0.0.1:3456"
```
```bash
gcloud run services update painpan-backend --region=us-central1 --env-vars-file=deploy-env.yaml
```

### 6. CORS Origins Made Dynamic

**Problem:** The backend had hardcoded CORS origins:
```python
allow_origins=[
    "http://localhost:3456",
    "http://127.0.0.1:3456",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

This wouldn't allow the Cloud Run frontend URL.

**Resolution:** Updated `backend/app/main.py` to read from environment variable:
```python
_cors_env = os.getenv("CORS_ORIGINS", "")
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    _cors_origins = [
        "http://localhost:3456",
        "http://127.0.0.1:3456",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
```

Keeps backward compatibility: local dev without `CORS_ORIGINS` set still works with the old defaults.

### 7. Two-Step Deployment Required (Frontend Needs Backend URL)

**Problem:** The frontend's `NEXT_PUBLIC_API_URL` is a build-time variable in Next.js (prefixed with `NEXT_PUBLIC_`). The frontend Docker image must be built with the backend URL baked in. But the backend URL isn't known until the backend is deployed.

**Resolution:** Deploy in order:
1. Deploy backend first → get backend URL
2. Build frontend image with `NEXT_PUBLIC_API_URL` pointing to backend URL
3. Deploy frontend

In our case, both images were pre-built (frontend with a placeholder URL), and the `NEXT_PUBLIC_API_URL` was set at runtime via Cloud Run env vars. This works because the Next.js app reads it from `process.env.NEXT_PUBLIC_API_URL` at runtime on the server side for API rewrites, and the client-side fetch calls use the same env var.

**Important:** If the app uses `NEXT_PUBLIC_API_URL` in client-side JavaScript (browser), it must be set at build time. If it's only used server-side (API routes, rewrites), it can be set at runtime. Our app uses it client-side in `frontend/lib/api.ts`, so it needs to be available at build time. We set it as a Cloud Run env var which makes it available to the Node.js server process.

### 8. Build Context for Frontend Docker Image

**Frontend cloudbuild.yaml** uses `frontend` as the build context (not `.`):
```yaml
args: ['build', '-t', 'IMAGE', '-f', 'frontend/Dockerfile', 'frontend']
```

This is because the frontend Dockerfile expects to be in the frontend directory (it copies `package.json` from the current directory). Using `frontend` as the build context puts the Docker build root inside the frontend directory.

---

## Deployment Commands Reference

```bash
# --- One-time infrastructure setup ---
gcloud config set account vt2435@columbia.edu
gcloud config set project agenticaicolumbia

gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com

gcloud artifacts repositories create painpan \
  --repository-format=docker --location=us-central1

gcloud iam service-accounts create painpan-sa --display-name="PainPan Application"
gcloud projects add-iam-policy-binding agenticaicolumbia \
  --member="serviceAccount:painpan-sa@agenticaicolumbia.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# --- Build & push images ---
gcloud builds submit --config=cloudbuild-backend.yaml .
gcloud builds submit --config=cloudbuild-frontend.yaml .

# --- Deploy backend ---
gcloud run deploy painpan-backend \
  --image=us-central1-docker.pkg.dev/agenticaicolumbia/painpan/backend:v1 \
  --platform=managed --region=us-central1 --allow-unauthenticated \
  --port=8901 --memory=512Mi --cpu=1 --timeout=3600 \
  --min-instances=0 --max-instances=2 --concurrency=10 \
  --service-account=painpan-sa@agenticaicolumbia.iam.gserviceaccount.com \
  --set-env-vars=LLM_PROVIDER=gcloud,GCLOUD_PROJECT=AgenticAIColumbia,GCLOUD_REGION=us-central1,AGENT_MODE=live

# --- Deploy frontend ---
gcloud run deploy painpan-frontend \
  --image=us-central1-docker.pkg.dev/agenticaicolumbia/painpan/frontend:v1 \
  --platform=managed --region=us-central1 --allow-unauthenticated \
  --port=3456 --memory=256Mi --cpu=1 --timeout=300 \
  --min-instances=0 --max-instances=2 --concurrency=1000 \
  --set-env-vars=NEXT_PUBLIC_API_URL=https://painpan-backend-953400329307.us-central1.run.app

# --- Update backend CORS ---
gcloud run services update painpan-backend --region=us-central1 \
  --env-vars-file=deploy-env.yaml
```

---

## Cloud Run Service Configuration

| Setting | Backend | Frontend |
|---------|---------|----------|
| Image | `painpan/backend:v1` | `painpan/frontend:v1` |
| Port | 8901 | 3456 |
| Memory | 512Mi | 256Mi |
| CPU | 1 | 1 |
| Timeout | 3600s | 300s |
| Min instances | 0 (scale to zero) | 0 (scale to zero) |
| Max instances | 2 | 2 |
| Concurrency | 10 | 1000 |
| Auth | Allow unauthenticated | Allow unauthenticated |
| Service account | `painpan-sa` | Default |

**Why these values:**
- Backend concurrency=10 because each analysis run is CPU/memory intensive (LLM calls, clustering, embeddings)
- Backend timeout=3600s because a full analysis pipeline can take several minutes
- Frontend concurrency=1000 because it's mostly static content serving
- Both scale to zero to minimize costs for low-traffic usage

---

## Estimated Monthly Cost

- Cloud Run: $0 (within free tier for < 500 analyses/month)
- Vertex AI: ~$3-8/month (Gemini Flash for classification, Pro for hypothesis)
- Secret Manager: $0 (not used)
- Artifact Registry: $0 (within free tier)
- **Total: ~$3-8/month**

---

## CI/CD: GitHub Actions Auto-Deploy

### 9. CI/CD Pipeline Setup

**Trigger:** Push to `main` branch → full build + deploy (~5-6 min)

**Workflow file:** `.github/workflows/deploy.yml`

**Pipeline steps:**
1. Checkout code
2. Authenticate to GCP via service account key (stored as `GCP_SA_KEY` GitHub secret)
3. Build backend Docker image → push to Artifact Registry
4. Deploy backend to Cloud Run
5. Build frontend Docker image → push to Artifact Registry
6. Deploy frontend to Cloud Run

**GitHub secret setup:**
```bash
# Create a service account key for CI/CD
gcloud iam service-accounts keys create /tmp/painpan-ci-key.json \
  --iam-account=painpan-sa@agenticaicolumbia.iam.gserviceaccount.com

# Add as GitHub secret
gh secret set GCP_SA_KEY < /tmp/painpan-ci-key.json

# Clean up local key file
rm /tmp/painpan-ci-key.json
```

### 9b. CI/CD IAM — First Deploy Failed (Permission Denied)

**Problem:** First CI/CD run failed with:
```
denied: Permission 'artifactregistry.repositories.uploadArtifacts' denied on resource
```

**Root Cause:** The `painpan-sa` service account only had roles for the *app* (Vertex AI, Secret Manager, Storage), not for *deployment operations*. CI/CD needs additional permissions to push images and manage Cloud Run services.

**Resolution:** Granted three additional IAM roles:
```bash
gcloud projects add-iam-policy-binding agenticaicolumbia \
  --member="serviceAccount:painpan-sa@agenticaicolumbia.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"    # Push Docker images

gcloud projects add-iam-policy-binding agenticaicolumbia \
  --member="serviceAccount:painpan-sa@agenticaicolumbia.iam.gserviceaccount.com" \
  --role="roles/run.admin"                   # Create/update Cloud Run services

gcloud projects add-iam-policy-binding agenticaicolumbia \
  --member="serviceAccount:painpan-sa@agenticaicolumbia.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"      # Deploy as painpan-sa
```

**Complete IAM roles for `painpan-sa`:**

| Role | Purpose |
|------|---------|
| `roles/aiplatform.user` | Vertex AI (Gemini models) |
| `roles/secretmanager.secretAccessor` | Secret Manager (future use) |
| `roles/storage.objectAdmin` | Cloud Storage (future use) |
| `roles/artifactregistry.writer` | Push Docker images to Artifact Registry |
| `roles/run.admin` | Create/update Cloud Run services |
| `roles/iam.serviceAccountUser` | Act as the service account during deploy |

**Lesson:** When setting up CI/CD with a dedicated service account, think about two permission categories: (1) what the *app* needs at runtime and (2) what the *CI/CD pipeline* needs to build and deploy. The initial setup only covered #1.
2. Authenticate to GCP via service account key (stored as `GCP_SA_KEY` GitHub secret)
3. Build backend Docker image → push to Artifact Registry
4. Deploy backend to Cloud Run
5. Build frontend Docker image → push to Artifact Registry
6. Deploy frontend to Cloud Run

**GitHub secret setup:**
```bash
# Create a service account key for CI/CD
gcloud iam service-accounts keys create /tmp/painpan-ci-key.json \
  --iam-account=painpan-sa@agenticaicolumbia.iam.gserviceaccount.com

# Add as GitHub secret
gh secret set GCP_SA_KEY < /tmp/painpan-ci-key.json

# Clean up local key file
rm /tmp/painpan-ci-key.json
```

**Specificity:** The `painpan-sa` service account needs additional IAM roles for CI/CD to work. The `roles/aiplatform.user` we already granted is sufficient for the app itself, but GitHub Actions also needs permission to push images and deploy Cloud Run services. These are covered by the project-level `roles/editor` on the default compute service account and the `roles/cloudbuild.builds.builder` on the Cloud Build service account.

### 10. Version Tagging Strategy

**Problem:** Hardcoded `:v1` tags get overwritten on each deploy, making rollbacks ambiguous.

**Resolution:** Version tags are generated from git SHA + timestamp:
```
v-<git-short-sha>-<YYYYMMDDHHMM>
```
Example: `v-415ca28-202604160230`

Each deploy creates a unique, traceable image tag. Cloud Run keeps all revisions, so rollback to any previous version is one command:
```bash
gcloud run revisions list --service=painpan-backend --region=us-central1
gcloud run services update-traffic painpan-backend --to-revisions=painpan-backend-00001-v4x=100 --region=us-central1
```

### 11. CI/CD Uses Local Docker Build (Not Cloud Build)

**Difference from manual deploy:** The manual `deploy.sh` uses `gcloud builds submit` (Cloud Build). The GitHub Actions workflow builds images directly on the GitHub Actions runner (`docker build` + `docker push`).

**Why:** Cloud Build in GitHub Actions requires the `google-github-actions/auth` step for authentication, and then `docker build` on the Actions runner is simpler than submitting to Cloud Build and waiting. The result is the same — images end up in Artifact Registry either way.

**Cloudbuild YAML files** (`cloudbuild-backend.yaml`, `cloudbuild-frontend.yaml`) are still used by `deploy.sh` for manual deployments. Both paths produce identical images.

### Files Created for CI/CD

| File | Purpose |
|------|---------|
| `.github/workflows/deploy.yml` | GitHub Actions workflow: build + deploy on push to main |
| `deploy.sh` | Manual deploy script (alternative to CI/CD) |

---

## Update Protocol Summary

| Method | When to use | Command |
|--------|-------------|---------|
| **CI/CD (automatic)** | Normal workflow | `git push origin main` |
| **Manual — both** | Quick fix, testing | `./deploy.sh all` |
| **Manual — backend only** | Backend-only change | `./deploy.sh backend` |
| **Manual — frontend only** | Frontend-only change | `./deploy.sh frontend` |
| **Rollback** | Deploy broke something | `gcloud run services update-traffic ...` |

---

## Lessons Learned

1. **Always check for Application Default Credentials fallback** — GCP SDKs handle this natively; no need to mount key files on Cloud Run/Cloud Functions/GKE.
2. **Test `gcloud` flag syntax before running** — `--dockerfile`, `--set-env-vars` with commas, and `PORT` env var all have non-obvious restrictions.
3. **Use `--env-vars-file` for complex env var values** — Any value with commas, equals signs, or special characters breaks `--set-env-vars`.
4. **Deploy backend first, then frontend** — Frontend needs the backend URL at build time (or at minimum, runtime).
5. **Keep localhost CORS defaults in code** — Production CORS is set via env var, but local dev still works without any configuration.
6. **CI/CD vs manual deploy both produce identical images** — Cloudbuild YAML for manual, `docker build` on Actions runner for CI/CD. Same Dockerfiles, same results.
7. **Version tag every deploy** — Unique tags per deploy (git SHA + timestamp) enable clean rollbacks. Never reuse tags.
