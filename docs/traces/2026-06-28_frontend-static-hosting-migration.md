# Frontend Static Hosting Migration (Cost Optimization Follow-up #1)

**Date:** 2026-06-28
**Problem:** Cloud Run `painpan-frontend` costs ~$0.40/day to serve what is a fully static SPA — pure waste
**Result (target):** ~$0.40/day savings → combined run rate from v2's projected ~$0.65–0.75/day to ~$0.25–0.35/day (~$8–10/month)
**Status: PRE-DEPLOY** — code changes applied locally and build verified; **Phase 1 complete** (Firebase CLI installed, project `agenticaicolumbia-fb` created, `FIREBASE_TOKEN` GitHub Secret set, `firebase projects:list` confirms the project); first deploy + smoke test still pending (see banner)

---

> ## PRE-DEPLOY — CODE COMPLETE, NOT YET TESTED AGAINST FIREBASE HOSTING
>
> Eight files have been modified per the plan and the local `npm run build` produces the expected static export at `frontend/out/` (all 5 routes present). Phase 1 is complete: Firebase CLI installed, `agenticaicolumbia-fb` project created, `FIREBASE_TOKEN` GitHub Secret set, `firebase projects:list` confirms the project. Still pending the verification pipeline at the bottom of this doc:
>
> - First deploy (manual or via CI) to `https://agenticaicolumbia-fb.web.app`
> - End-to-end smoke test from the new URL — especially the deep-link refresh test that killed the GCS plan
> - Billing delta confirmation
>
> The deep-link refresh test is the highest-risk unverified assumption — see "Open Assumptions" below. Verification starts **before** pushing code precisely because that assumption is load-bearing.

---

## Intent

This is the direct follow-up to [`2026-06-28_cloud-run-cost-optimization-v2.md`](./2026-06-28_cloud-run-cost-optimization-v2.md) ("follow-up #1"). v2 took the cheap CPU/WS/concurrency wins and explicitly deferred this work as its own trace.

**Concrete goal:** eliminate the `painpan-frontend` Cloud Run service. The frontend is a Next.js 15.2 App Router SPA with no SSR, no `next/image`, no middleware, and no API routes — it compiles cleanly to static HTML+JS. Running a container just to serve static files is the wasted spend.

**Cost target:** ~$0.40/day elimination, taking the combined run rate from v2's projected ~$0.65–0.75/day to ~$0.25–0.35/day (~$8–10/month). Firebase Hosting's free tier (10 GB storage, 360 MB/day transfer) is far above this app's ~1 MB footprint; billing should be $0.

**Non-goals (deliberately scoped out, each flagged at the bottom):**
- WS origin enforcement (security gap, pre-existing)
- 3-way DRY violation in `NEXT_PUBLIC_API_URL` parsing (cleanup, separate concern)
- `main.py` bypassing `app/config.py` for `CORS_ORIGINS` (pre-existing)
- Custom domain setup (e.g. `painpan.app`) — default `agenticaicolumbia-fb.web.app` is fine for the recruiter-demo
- Phase 5 cleanup (deleting the old Cloud Run service + GCS bucket) — happens ~1 week post-verification

Backend stays on Cloud Run untouched. Only the frontend moves.

---

## What we tried first: GCS static hosting (and why it failed)

The first plan targeted GCS static hosting at `https://c.storage.googleapis.com/painpan-frontend/`. The bucket was created (`gs://painpan-frontend`), public-read granted, website config set (`gsutil web set -m index.html`), and 1.1 MiB of static assets uploaded. Then came the empirical probe — 10 URL forms tested against the live bucket:

| # | URL | Result |
|---|-----|--------|
| 1 | `https://c.storage.googleapis.com/painpan-frontend/` | **400 Bad Request** |
| 2 | `https://c.storage.googleapis.com/painpan-frontend/index.html` | **400 Bad Request** |
| 3 | `https://storage.googleapis.com/painpan-frontend/` | XML bucket listing (not HTML) |
| 4 | `https://storage.googleapis.com/painpan-frontend/index.html` | 200 ✓ (explicit file only) |
| 5 | `https://storage.googleapis.com/painpan-frontend/debug/` | **404** (dir index NOT served) |
| 6 | `https://storage.googleapis.com/painpan-frontend/debug/index.html` | 200 ✓ (explicit file only) |
| 7 | `https://painpan-frontend.storage.googleapis.com/` | XML bucket listing |
| 8 | `https://painpan-frontend.storage.googleapis.com/index.html` | 200 ✓ |
| 9 | `https://painpan-frontend.storage.googleapis.com/debug/` | **404** |
| 10 | `https://painpan-frontend.storage.googleapis.com/debug/index.html` | 200 ✓ |

**Verdict: GCS is unworkable for this app.** Three independent failure modes:

1. `c.storage.googleapis.com/<bucket>/` returns **400 Bad Request** — it's a CNAME target, not directly browsable
2. No GCS endpoint form honors `gsutil web set`'s `MainPageSuffix` for directory→`index.html` resolution. The "website config" feature only kicks in behind a Load Balancer / CDN front, not on direct API endpoints
3. Every trailing-slash URL (`/`, `/debug/`) returns either XML bucket listing or 404. Only explicit-file URLs (`/index.html`, `/debug/index.html`) serve HTML

For a recruiter-demo where deep-link refreshes must work, this is unusable. A Load Balancer / Cloud CDN front would fix it but adds complexity and cost beyond the original ~$0.40/day savings target.

**Pivot: Firebase Hosting.** Purpose-built for SPAs, part of GCP, free tier far above this app's footprint, handles trailing-slash routing and SPA fallbacks natively. The cost goal is preserved.

**Cleanup of the failed GCS attempt:**
- `gs://painpan-frontend` bucket stays in place (~$0/month for 1.1 MiB), removed in Phase 5
- `gcloud config set project agenticaicolumbia` (run during probing) reverts to `jobsearch2026-vt` when done
- The CORS entry for `https://c.storage.googleapis.com` (added in the prior commit attempt) is replaced by `https://agenticaicolumbia-fb.web.app` in this plan
- The `deploy.yml` frontend block with `gsutil rsync` is replaced by `firebase deploy` in this plan

---

## The pivot: Firebase Hosting

- **URL strategy:** `https://agenticaicolumbia-fb.web.app` (Firebase Hosting default, project-scoped). Old Cloud Run URL is abandoned (Cloud Run owns that hostname).
- **Rollback:** Keep the old `painpan-frontend` Cloud Run service running during the verification window — same shape as the original plan.
- **Auth:** Long-lived `FIREBASE_TOKEN` (from `firebase login:ci`) stored as a GitHub repo Secret. Chosen over Service Account auth because the existing `secrets.GCP_SA_KEY` SA is in the **backend** GCP project (`agenticaicolumbia`), which is now a different project from the Firebase project — it couldn't deploy to Firebase even with extra IAM grants. The token approach is essential, not just convenient.

### Why Firebase project is separate from the backend GCP project

The original plan was to "Add Firebase" to the existing GCP project `agenticaicolumbia` (one project, both Cloud Run and Firebase). During Phase 1 setup, `agenticaicolumbia` was not selectable in Firebase's "Add project" flow — likely because the project already had a Firebase binding from an earlier experiment, or because of an org-policy / role restriction on the user account.

Pragmatic resolution: **a new Firebase project `agenticaicolumbia-fb` was created.** This results in a clean two-project split:

| Resource | Project | Notes |
|----------|---------|-------|
| Backend Cloud Run (`painpan-backend`) | `agenticaicolumbia` (GCP) | Untouched |
| Old frontend Cloud Run (`painpan-frontend`, rollback) | `agenticaicolumbia` (GCP) | Untouched during rollback window |
| Artifact Registry (`painpan/backend`, `painpan/frontend`) | `agenticaicolumbia` (GCP) | Untouched |
| Backend SA (`painpan-sa@agenticaicolumbia...`) | `agenticaicolumbia` (GCP) | Untouched |
| Frontend hosting (Firebase) | `agenticaicolumbia-fb` (Firebase) | NEW |
| Frontend URL | `agenticaicolumbia-fb.web.app` | NEW |

**Implications:**
- Billing is split between two projects. Firebase Spark (free) plan covers this app's footprint (~1 MB static, ~0 egress in practice), so the Firebase project should incur $0. Worth confirming during Step 5 billing check.
- CI deploy uses `FIREBASE_TOKEN` (scoped to the user account, works across any project the user owns) — no IAM cross-project trust needed.
- Custom-domain setup later (if desired) happens on the Firebase project, not the main GCP project.
- Phase 5 cleanup commands that reference `us-central1-docker.pkg.dev/agenticaicolumbia/...` (Artifact Registry) stay pointing at the original GCP project. They target the old frontend container images, which are in `agenticaicolumbia`.

Investigating *why* `agenticaicolumbia` wasn't selectable in Firebase is its own follow-up (not in scope for this trace). Likely worth checking whether there's an orphan Firebase binding on that project.

---

## Preliminary Analysis (why this should work)

### Static export feasibility — CONFIRMED LOCALLY (unchanged)

| Check | Result |
|-------|--------|
| All pages are `"use client"` | yes |
| No `next/image` usage | yes (but `images.unoptimized: true` added defensively) |
| No middleware | yes |
| No API routes | yes |
| No `getServerSideProps` / server actions | yes |
| Next.js version | 15.2 (App Router) — supports `output: 'export'` cleanly |

**Verified post-change by running `npm run build` locally:** Next.js 15.5.15 produces `out/` with all 5 routes as `out/<route>/index.html`:

- `out/index.html`
- `out/debug/index.html`
- `out/how-it-works/index.html`
- `out/limit-exceeded/index.html`
- `out/rate-limit/index.html`

Plus `out/404.html`, `_next/static/*` hashed chunks, `favicon.ico`, `icon.svg`, `robots.txt`. This matches exactly what the CI step `test -f out/index.html` will sanity-check. **Re-verified after the firebase.json was added — build is unaffected by the new config file.**

### Cross-origin WS — already the production pattern (unchanged)

The frontend and backend already run on **separate Cloud Run origins** in production today. WS already crosses origins. FastAPI does not validate WS origin (a pre-existing security gap, flagged at the bottom — not introduced here). So moving the frontend origin from `painpan-frontend-...run.app` to `agenticaicolumbia-fb.web.app` does not change the WS connection path — only the HTTP CORS origin changes.

### `rewrites()` is dev-only, safe to keep (unchanged)

`frontend/next.config.js` has a `rewrites()` block proxying `/api/*` to `http://127.0.0.1:8901` (the local backend). Under `output: 'export'`, Next.js emits a build-time warning that rewrites are ignored, but does not fail. Kept in the config so local `npm run dev` still works without `.env.local`.

### Cache strategy is safe because Next.js content-hashes (unchanged)

`_next/static/*` filenames include content hashes. Same content → same filename → safe to cache for a year (`max-age=31536000, immutable`). When content changes, the filename changes, automatically busting the cache. Everything outside `_next/static/` (HTML files) uses Firebase default cache (~short), which is correct since `index.html` references the hashed chunk names and needs to update on each deploy. Configured via `headers` block in `firebase.json`.

### Firebase Hosting handles trailing-slash routing natively

This is the key property that GCS lacks. With `trailingSlash: true` in `firebase.json`, Firebase will:
- Serve `/debug/` directly from `out/debug/index.html` (no redirect needed)
- Redirect `/debug` → `/debug/` (301) so the bare-path form works too
- Serve `/` from `out/index.html`

Hard refresh on any route works because Firebase's CDN serves the actual file, not a bucket listing. This is the verification that catches the failure mode that killed the GCS plan.

---

## Changes Applied (8 files, uncommitted)

| File | Change |
|------|--------|
| `frontend/firebase.json` | NEW — hosting config (public dir, trailingSlash, headers, cleanUrls) |
| `frontend/.firebaserc` | NEW — pins default project to `agenticaicolumbia-fb` |
| `frontend/next.config.js` | UNCHANGED from prior commit attempt (already correct) |
| `.gitignore` | Add `frontend/.firebase/` to existing `# Frontend` block |
| `.github/workflows/deploy.yml:12` | Update `FRONTEND_URL` to Firebase URL |
| `.github/workflows/deploy.yml:68-99` | Replace GCS steps with Firebase CLI setup + deploy |
| `deploy-env.yaml:1` | Replace GCS origin with `https://agenticaicolumbia-fb.web.app` (keep old Cloud Run origin during rollback) |
| `docs/traces/2026-06-28_frontend-static-hosting-migration.md` | This file (renamed from `...gcs-static-hosting-migration.md`) |

`frontend/Dockerfile` becomes dead code but is deliberately **not** removed in this commit — it gets cleaned up in Phase 5 after the rollback window closes.

Frontend cleanup steps in `deploy.yml` (`Cleanup old Cloud Run revisions` and `Cleanup old Artifact Registry images`, lines 104-130) deliberately left untouched: during the rollback window they keep the old `painpan-frontend` Cloud Run service trimmed, which is exactly what we want for rollback safety.

### `frontend/firebase.json` — NEW

Lives in `frontend/` next to `next.config.js` — co-located with the frontend code, matches existing convention.

```json
{
  "hosting": {
    "public": "out",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "trailingSlash": true,
    "headers": [
      {
        "source": "_next/static/**",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      }
    ],
    "cleanUrls": false
  }
}
```

**Field rationale:**
- `public: "out"` — Next.js `output: 'export'` produces `frontend/out/`. The deploy command runs in `frontend/`, so this is the relative path.
- `trailingSlash: true` — matches `next.config.js` (which emits `out/debug/index.html`). Firebase will redirect `/debug` → `/debug/` and serve `debug/index.html`.
- `cleanUrls: false` — `cleanUrls: true` strips `.html` extensions, which would conflict with the trailing-slash regime. Explicit `false` for clarity.
- `headers` for `_next/static/**` — content-hashed assets; safe to cache for a year. Firebase's CDN honors this header on edge responses.

### `frontend/.firebaserc` — NEW

Pins the default project so `firebase deploy` doesn't need `--project` flag (CI still passes it explicitly for defense-in-depth).

```json
{
  "projects": {
    "default": "agenticaicolumbia-fb"
  }
}
```

### `frontend/next.config.js` — UNCHANGED

Already has the correct config from the prior commit attempt (`output: 'export'`, `trailingSlash: true`, `images.unoptimized: true`). All three are compatible with Firebase Hosting. No further changes needed.

### `.gitignore` — add `frontend/.firebase/`

Firebase CLI creates `frontend/.firebase/hosting.<site>.cache` during local deploys (CI is ephemeral, not affected). The existing root `.gitignore` covers `frontend/out/`, `frontend/.next/`, `frontend/node_modules/` but not `.firebase/`. One line added to the existing `# Frontend` block:

```gitignore
# Frontend
frontend/node_modules/
frontend/.next/
frontend/out/
frontend/.firebase/    # NEW — local Firebase CLI cache
```

The root `.gitignore` ends with `!*.json` to allow JSON files. `firebase.json` is allowed by this rule. `.firebaserc` ends in `.firebaserc` (not `.json`) but isn't matched by any ignore pattern, so it commits cleanly.

### `.github/workflows/deploy.yml` — Firebase deploy block

`FRONTEND_URL` env var (line 12):

```yaml
FRONTEND_URL: https://agenticaicolumbia-fb.web.app
```

`PROJECT_ID: agenticaicolumbia` (line 8) **stays unchanged** — that's the backend GCP project (Cloud Run, Artifact Registry, SA).

New frontend block (replaces the GCS block):

```yaml
      # ── Frontend (Firebase Hosting) ──

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Setup Firebase CLI
        run: npm install -g firebase-tools@13

      - name: Build frontend (static export)
        working-directory: frontend
        env:
          # Build-time inlined into the JS bundle — must match prod backend URL
          NEXT_PUBLIC_API_URL: ${{ env.BACKEND_URL }}
        run: |
          npm ci
          npm run build
          # Sanity: confirm static export produced output
          test -f out/index.html

      - name: Deploy frontend to Firebase Hosting
        working-directory: frontend
        env:
          FIREBASE_TOKEN: ${{ secrets.FIREBASE_TOKEN }}
        run: |
          firebase deploy --only hosting --project agenticaicolumbia-fb --message "Deploy ${GITHUB_SHA::7}"
```

**Why `npm install -g firebase-tools@13` over a third-party GitHub Action?** Explicit, transparent, reuses the Node setup we already have. Version pinned via `@13`. The install adds ~5s to CI; acceptable.

**Why `FIREBASE_TOKEN` over Service Account auth?** Essential now that Firebase lives in a separate project (`agenticaicolumbia-fb`) from the backend SA (`agenticaicolumbia`). The SA in `secrets.GCP_SA_KEY` has no permissions on the Firebase project — cross-project IAM for Firebase Hosting isn't a thing. The token (scoped to the user account that owns `agenticaicolumbia-fb`) is the only viable auth path.

### `deploy-env.yaml` — CORS origins

```yaml
# During rollback window — Firebase + old Cloud Run origins both allowed
CORS_ORIGINS: "https://agenticaicolumbia-fb.web.app,https://painpan-frontend-953400329307.us-central1.run.app,http://localhost:3456,http://127.0.0.1:3456"
```

The Firebase origin is **scheme + host only**, no path. CORS spec requires this exact format. The old Cloud Run origin is kept during the rollback window so both URLs work while verifying. `https://c.storage.googleapis.com` (added in the prior commit attempt) is removed — unused since the GCS path is abandoned.

---

## Open Assumptions (what we are about to verify)

These are the assumptions embedded in the plan that **should** make this work. Some are now empirically confirmed (Phase 1 setup done); others pending.

### A1. Phase 1 Firebase setup works — CONFIRMED

Firebase CLI installed, `agenticaicolumbia-fb` project created, `FIREBASE_TOKEN` generated via `firebase login:ci` and added as a GitHub Secret, `firebase projects:list` confirms the project. Could not "Add Firebase" to the existing `agenticaicolumbia` GCP project (not selectable in the Console flow); created a new Firebase project instead. See "Why Firebase project is separate" above.

### A2. Deep-link refresh on `/debug/`, `/how-it-works/`, etc. serves the page — HIGHEST RISK (but low)

This is the failure mode that killed GCS. Firebase Hosting is *designed* for this, but we verify empirically. With `trailingSlash: true` in both `next.config.js` and `firebase.json`, Firebase's CDN should serve `out/debug/index.html` for any of `/debug`, `/debug/`, hard refresh on `/debug/`.

**How we'll find out:** Hard refresh on each route in the browser, expect HTML (not 404, not XML listing).

### A3. CORS update is sufficient

`https://agenticaicolumbia-fb.web.app` added to `CORS_ORIGINS`. The origin is scheme + host only (correct per CORS spec). Must match the actual origin browsers send — which it does, since that's the URL users visit.

**How we'll find out:** DevTools network tab during smoke test — no CORS errors on any HTTP or WS request.

### A4. WS continues to work cross-origin

Already the production pattern (frontend and backend are already separate origins). No WS protocol change. The only WS risk is if the new frontend origin triggers some pre-existing origin check that's currently dormant — the plan claims there is none (`manager.py:34` accepts WS without origin check; `main.py:140` doesn't validate). Flagged as a separate security concern, not in scope here.

### A5. `FIREBASE_TOKEN` GitHub Secret is set — CONFIRMED

Token generated via `firebase login:ci` and added as the `FIREBASE_TOKEN` GitHub Secret. CI deploy step will auth with this token.

**How we'll confirm:** First CI run after push succeeds the auth step.

### A6. `_next/static/**` cache header is honored by Firebase CDN

The `headers` block in `firebase.json` should set `Cache-Control: public, max-age=31536000, immutable` on edge responses for hashed assets. Firebase CDN honors this. Same strategy as the (now-abandoned) GCS plan's second `gsutil rsync`.

**How we'll find out:** DevTools network tab during smoke test — inspect response headers on a `_next/static/*` request.

### A7. Old Cloud Run service stays alive for rollback

We're not deleting `painpan-frontend` Cloud Run. The cleanup steps in CI (`deploy.yml:104-130`) still target it. If anything breaks, `git revert` + push redeploys the old frontend image and the old URL resumes serving. Verified by reading the diff — no line in this change touches the old service.

### A8. Firebase billing is $0 within Spark plan — NEW ASSUMPTION

Because `agenticaicolumbia-fb` is a new Firebase project, billing is on whatever plan was selected at creation (Spark = free, Blaze = pay-as-you-go). Spark's free tier (10 GB storage, 360 MB/day transfer) covers this app's ~1 MB footprint with massive headroom. Worth confirming the project is on Spark during the Step 5 billing check.

---

## Verification Pipeline (what we are about to do)

Cheapest signal first. Pre-push probe is now **trivial** compared to GCS — Firebase Hosting either works or doesn't, no URL form ambiguity.

### Step 1 — Phase 1 setup (outside CI)

None of this can safely run in CI on first creation. Run once before the first deploy of the new code.

**Already done:**
- ✓ Firebase CLI installed (`npm install -g firebase-tools@13`)
- ✓ `firebase login` completed
- ✓ Firebase project `agenticaicolumbia-fb` created (couldn't add Firebase to `agenticaicolumbia` — see "Why Firebase project is separate")
- ✓ `firebase login:ci` token generated and added as GitHub Secret `FIREBASE_TOKEN`
- ✓ `firebase projects:list` confirms `agenticaicolumbia-fb`

**Still pending:**

Nothing in Phase 1 — proceed to Step 2 (manual first deploy) or Step 3 (push to CI).

For hosting-site verification without a deploy, visit `https://agenticaicolumbia-fb.web.app` in a browser — should show Firebase's "Welcome" / "Site Not Found" placeholder page. (Note: the `firebase hosting:sites` command does not exist in firebase-tools@13; this URL visit is the equivalent verification.)

**Phase 1 verification:** `firebase projects:list` shows `agenticaicolumbia-fb`. Visiting `https://agenticaicolumbia-fb.web.app` before any deploy shows Firebase's "Site Not Found" / "Welcome" placeholder page (confirms the hosting site is provisioned and on air).

**Environment note:** During the earlier GCS probing we ran `gcloud config set project agenticaicolumbia` (was `jobsearch2026-vt`). Revert with `gcloud config set project jobsearch2026-vt` when done. Unrelated to Firebase — gcloud config tracks the GCP project, not the Firebase project.

### Step 2 — First deploy manually (optional but recommended)

Before relying on CI, do one deploy from local to verify the end-to-end Firebase path.

**Critical:** `NEXT_PUBLIC_API_URL` must be set at build time. Next.js inlines `NEXT_PUBLIC_*` vars into the JS bundle during `npm run build`. The code in `lib/api.ts:13-14`, `app/limit-exceeded/page.tsx:22`, and `components/UsageIndicator.tsx:20` falls back to `http://localhost:8901` if the var is unset — which means the deployed site will try to hit your local machine instead of the prod backend, producing `ERR_CONNECTION_REFUSED` in the browser console. (This is the same DRY violation flagged as out-of-scope follow-up #2 below.)

**Recommended approach: `.env.production` file** (shell-independent — bash, cmd, PowerShell all just work):

The file `frontend/.env.production` contains:
```
NEXT_PUBLIC_API_URL=https://painpan-backend-953400329307.us-central1.run.app
```

Next.js auto-loads it during `npm run build` (NODE_ENV=production). It's gitignored by the existing `.env.*` rule, so it doesn't end up in the repo — CI still sets the env var explicitly via `deploy.yml:80-89`. The file is a local convenience for manual deploys only.

```bash
cd frontend
npm ci
npm run build
firebase deploy --only hosting --project agenticaicolumbia-fb
```

**Alternative — inline env var** (if you'd rather not create the file):
- Bash / git bash: `export NEXT_PUBLIC_API_URL=https://painpan-backend-953400329307.us-central1.run.app` before `npm run build`
- cmd: `set NEXT_PUBLIC_API_URL=https://...` before `npm run build`
- PowerShell: `$env:NEXT_PUBLIC_API_URL="https://..."` before `npm run build`

**Verify the build before deploying:** after `npm run build`, grep the built bundle to confirm the prod URL made it in:
```bash
grep -l painpan-backend out/_next/static/chunks/**/*.js   # should list 4 files
grep -l localhost:8901 out/_next/static/chunks/**/*.js    # should find nothing
```
If localhost appears and painpan-backend doesn't, the env var didn't take — do not deploy.

After deploy: hard-refresh in the browser (Ctrl+Shift+R or DevTools → Network → "Disable cache" checked). The previous deploy's JS bundles are content-hashed and cached aggressively; a soft refresh will serve the old bundle from cache and the same `127.0.0.1` error will reappear even though the new bundle on the CDN is correct.

In DevTools → Network, the `/api/v1/analysis` request should now go to `https://painpan-backend-953400329307.us-central1.run.app`. Then push code for CI to take over.

**Pre-push CORS gotcha:** the manual Firebase deploy makes the new frontend live immediately, but the **backend on Cloud Run is still running with the old `CORS_ORIGINS`** (without `agenticaicolumbia-fb.web.app`). The new origin only takes effect when CI redeploys the backend from the updated `deploy-env.yaml`. So a smoke test done between "Firebase deploy succeeds" and "CI push completes" will hit:

```
Access to fetch at 'https://painpan-backend-...run.app/api/v1/analysis' from origin
'https://agenticaicolumbia-fb.web.app' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

This is expected and not a migration bug. To verify CORS end-to-end before pushing, update the backend's env vars from the already-updated `deploy-env.yaml` (~30s):

```bash
cd <project root>
gcloud run services update painpan-backend \
  --region=us-central1 \
  --env-vars-file=deploy-env.yaml
```

This is functionally identical to what CI's `gcloud run deploy` step does on push. `--env-vars-file` updates plaintext env vars only — secrets (`PROXY_URL`, `PROXY_ENABLED`) are managed via `--set-secrets` on the full deploy and aren't touched by this update.

**Avoid `--update-env-vars=CORS_ORIGINS=...`** for this case — gcloud parses the arg as a comma-separated `key=val,key=val` dict, so the commas inside the CORS URL list get treated as item separators and the command errors with `Bad syntax for dict arg`. The `^;^=` delimiter-override prefix (`--update-env-vars=^;^=CORS_ORIGINS="..."`) works as a surgical alternative, but the file-based command above is cleaner since `deploy-env.yaml` is already the source of truth. Once CI deploys after the push, the manual update is redundant.

### Step 3 — Push and watch CI

```bash
git add frontend/firebase.json frontend/.firebaserc frontend/next.config.js \
        .gitignore .github/workflows/deploy.yml deploy-env.yaml \
        docs/traces/2026-06-28_frontend-static-hosting-migration.md
git commit -m "Move frontend to Firebase Hosting (pivot from GCS)"
git push origin main
```

Watch Actions tab. New frontend steps: `Setup Node` → `Setup Firebase CLI` → `Build frontend (static export)` → `Deploy frontend to Firebase Hosting`. The deploy step is the one most likely to fail if `FIREBASE_TOKEN` is missing or Phase 1 wasn't done.

### Step 4 — Browser smoke test at the new URL

- `https://agenticaicolumbia-fb.web.app` loads the app (root)
- Internal nav: click each navbar link, confirm client-side routing works
- **Hard refresh on each route** (`/debug/`, `/how-it-works/`, `/rate-limit/`, `/limit-exceeded/`) — serves the page, not a 404. This is the verification that catches the failure mode that killed the GCS plan.
- Run a full analysis end-to-end
- DevTools network tab: WS connects (`wss://painpan-backend-953400329307.us-central1.run.app/ws/<run_id>` with 101 status)
- Logs stream start → `analysis_complete`
- Page refresh mid-analysis reconnects cleanly (buffered messages replay)
- Browser console: **no CORS errors** on any HTTP or WS request
- DevTools network tab: `_next/static/*` responses have `cache-control: public, max-age=31536000, immutable`

### Step 5 — 48h billing check

GCP Billing on `agenticaicolumbia` → `painpan-frontend` Cloud Run drops to near-zero (per-request billing only, no traffic going there). Firebase Billing on `agenticaicolumbia-fb` is $0 within Spark plan free tier. Combined spend on ~$0.25–0.35/day trajectory.

---

## Rollback Procedure

Same shape as the original plan:

1. `git revert <merge-commit>` — restores old `deploy.yml`, `deploy-env.yaml`, and removes `firebase.json` / `.firebaserc`
2. Push to `main` — CI redeploys the old frontend image to `painpan-frontend` Cloud Run (in `agenticaicolumbia` GCP project)
3. The old URL `https://painpan-frontend-953400329307.us-central1.run.app` resumes serving live traffic
4. Firebase Hosting site (in `agenticaicolumbia-fb`) and `gs://painpan-frontend` bucket (in `agenticaicolumbia` GCP project) can be left in place (both free at this scale) or cleaned up

---

## Phase 5 — Follow-up after verification (~1 week later)

Once the new URL is verified working for a week, a second commit removes the rollback scaffolding:

1. **Delete old Cloud Run service:** `gcloud run services delete painpan-frontend --region=us-central1 --project agenticaicolumbia`
2. **Delete orphaned GCS bucket:** `gsutil rm -r gs://painpan-frontend` (in `agenticaicolumbia` GCP project)
3. **Remove old origin from `deploy-env.yaml:1`:**
   ```yaml
   CORS_ORIGINS: "https://agenticaicolumbia-fb.web.app,http://localhost:3456,http://127.0.0.1:3456"
   ```
4. **Remove frontend cleanup steps** in `deploy.yml` (lines 111-114 for revisions, 125-130 for images — they'd no-op once the service is gone, but cleaner to remove)
5. **Delete `frontend/Dockerfile`** (dead code after this migration)
6. **Manually delete all old frontend revisions and Artifact Registry images** (CI won't do it after cleanup steps are removed). These live in the `agenticaicolumbia` GCP project:
   ```bash
   gcloud run revisions list --service=painpan-frontend --region=us-central1 --project agenticaicolumbia --format="value(name)" | xargs -I {} gcloud run revisions delete {} --region=us-central1 --project agenticaicolumbia --quiet
   gcloud artifacts docker images list us-central1-docker.pkg.dev/agenticaicolumbia/painpan/frontend --format="get(version)" | xargs -I {} gcloud artifacts docker images delete us-central1-docker.pkg.dev/agenticaicolumbia/painpan/frontend@{} --quiet
   ```

Note: the Phase 5 commands all target `agenticaicolumbia` (the original GCP project) since that's where the old frontend container + images live. The new Firebase project (`agenticaicolumbia-fb`) is left alone.

This Phase 5 becomes its own trace: `docs/traces/2026-07-XX_frontend-firebase-migration-cleanup.md`.

---

## Flagged but NOT bundled (separate traces)

Real findings from the audit, out of scope for this migration. Listed so they don't get lost:

1. **WS origin enforcement missing (security gap).** `manager.py:34` calls `await websocket.accept()` with no origin check; `main.py:140` has no validation either. CORS middleware covers HTTP only, not WS. Pre-existing — not introduced by this migration. Should be its own trace.

2. **3-way DRY violation in `NEXT_PUBLIC_API_URL` parsing.** Same pattern `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8901"` in `lib/api.ts:13-14`, `app/limit-exceeded/page.tsx:22`, `components/UsageIndicator.tsx:20`. The latter two also duplicate the `${apiUrl}/api/v1/usage` path. Per CLAUDE.md Simplicity First: not bundling with this migration. Separate cleanup trace.

3. **`main.py:69-71` bypasses `app/config.py` for `CORS_ORIGINS`.** Reads `os.getenv("CORS_ORIGINS")` directly, violating the project's "all env vars through `config`" rule. Pre-existing. Separate trace.

4. **Custom domain setup** for Firebase Hosting (e.g. `painpan.app`). Out of scope; the default `agenticaicolumbia-fb.web.app` is fine for the recruiter-demo. Future enhancement.

5. **Why couldn't `agenticaicolumbia` be selected in Firebase?** Likely an orphan Firebase binding on that project from an earlier experiment, or an org-policy / role restriction. Worth investigating as its own follow-up — if there's a stale Firebase binding, it may have other side effects. Not blocking this migration.

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/firebase.json` | NEW — hosting config (public dir, trailingSlash, headers, cleanUrls) |
| `frontend/.firebaserc` | NEW — pins default project to `agenticaicolumbia-fb` |
| `frontend/next.config.js` | UNCHANGED from prior commit attempt (already correct) |
| `.gitignore` | Add `frontend/.firebase/` to existing `# Frontend` block |
| `.github/workflows/deploy.yml:12` | Update `FRONTEND_URL` to Firebase URL |
| `.github/workflows/deploy.yml:68-99` | Replace GCS block with Firebase CLI setup + deploy |
| `deploy-env.yaml:1` | Replace GCS origin with `https://agenticaicolumbia-fb.web.app` (keep old Cloud Run origin during rollback) |
| `docs/traces/2026-06-28_frontend-static-hosting-migration.md` | This file (renamed from `...gcs-static-hosting-migration.md`) |

No backend changes. No test changes (no test files in `frontend/`). No removal of the old Cloud Run service (Phase 5).
