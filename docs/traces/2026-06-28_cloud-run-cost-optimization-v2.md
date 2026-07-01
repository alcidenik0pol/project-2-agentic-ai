# Cloud Run Cost Optimization v2

**Date:** 2026-06-28
**Problem:** ~$1.31/day (~$39/month) on a recruiter-demo app that should be near-idle
**Result:** Target ~$0.65–0.75/day (~$20–22/month); stretch target of ~$5/month requires follow-up #1 (move frontend to static hosting) — **NOT IMPLEMENTED** in this change
**Status: UNTESTED** — see banner below

---

> ## ⚠️ UNTESTED — DEPLOYED BUT NOT VERIFIED
>
> The changes in this trace are pushed to `main` (commit `631a807`) and the
> GitHub Actions deploy is expected to succeed, but **end-to-end verification has
> not been performed.** Specifically, the following are all still pending the
> verification checklist at the bottom of this doc:
>
> - The WebSocket auto-close behavior (does the server actually close with code 1000 ~15 min after `analysis_complete`?)
> - The billing delta (does spend actually drop to ~$0.65–0.75/day?)
> - The instance cap (are both services really capped at 1 instance?)
>
> Treat the numbers and behavior below as **projected**, not measured, until the
> checklist is complete.

---

## Goal of the Change

Three levers, in order of expected impact:

1. **Hard-cap instances at 1 per service** — removes the scenario where two
   concurrent cold starts each spin a second instance and double-bill CPU.
2. **Raise concurrency now that the second-query deadlock is fixed** — lets a
   single instance absorb multiple in-flight requests instead of scaling out.
3. **Plug the WebSocket idle-billing leak** from abandoned recruiter tabs by
   having the server initiate a clean close (code 1000) 15 minutes after
   `analysis_complete`.

This is a sibling to [`2026-06-07_cloud-run-cost-reduction.md`](./2026-06-07_cloud-run-cost-reduction.md) (v1). v1 blocked crawlers, added CPU throttling, and added CI cleanup of revisions/images. v2 takes the next step on the same cost driver.

---

## Solution Components

### 1. Backend deploy flags

**File:** `.github/workflows/deploy.yml:65-66`

The backend deploy step changed two flags; `--timeout=3600` was deliberately kept.

```yaml
--max-instances=1 \   # was 2
--concurrency=20      # was 1
```

**Why keep `--timeout=3600`?** Long-running analyses stream over WebSocket for many minutes. Lowering the timeout would cause Cloud Run to kill the request mid-run, breaking the WS before `analysis_complete`. The instance cap (1) is what bounds cost; the timeout just lets a legitimate long run finish.

**Why raise concurrency to 20?** With the second-query deadlock fixed (see [`2026-04-19_second-query-hang-deadlock-fix.md`](./2026-04-19_second-query-hang-deadlock-fix.md)), a single backend instance can now safely multiplex multiple runs without deadlocking. This is the enabler that makes `--max-instances=1` viable without queueing.

> **Note on concurrency choice:** the prior commit `ecace90` reduced backend concurrency to 1 to work around the deadlock; commit `48e90b4` then noted that CPU < 1 on Cloud Run requires concurrency = 1. v2 reverses both: CPU stays at 1, so concurrency > 1 is allowed, and the deadlock fix means it's safe.

---

### 2. Frontend deploy flags

**File:** `.github/workflows/deploy.yml:91,96,97`

```yaml
--cpu=1 \             # was 0.5  (line 91)
--max-instances=1 \   # was 2    (line 96)
--concurrency=10      # was 1    (line 97)
```

**Why bump frontend CPU from 0.5 back to 1?** Cloud Run requires `--cpu >= 1` whenever `--concurrency > 1`. v1 set frontend CPU to 0.5 (saving money when the frontend served requests); v2 raises it back to 1 so concurrency can go up and `--max-instances=1` can hold. The net is still a win because the instance cap dominates: one instance at CPU 1 beats two instances at CPU 0.5.

**Why frontend concurrency 10 (vs backend 20)?** Frontend requests are short HTTP renders; 10 is plenty for the recruiter-demo traffic profile. Backend requests are long WS streams, so it gets headroom to 20.

---

### 3. WebSocket auto-close after `analysis_complete`

**File:** `backend/app/api/websocket/manager.py`

The leak: once a recruiter opens the app and runs an analysis, the WS stays open as long as their tab does. If they walk away, the WS keeps the backend instance alive billing CPU at idle until Cloud Run's scale-down (or the 3600s timeout). For a demo app, this is the dominant cost path.

The fix schedules a server-initiated clean close 15 minutes after the run completes — enough grace for a reviewer to scroll results, short enough to release the instance this billing cycle.

**New state — `ConnectionManager.__init__` (line 30):**

```python
# run_id -> pending auto-close task scheduled on analysis_complete
self._auto_close_tasks: dict[str, asyncio.Task] = {}
```

**New method — `_schedule_auto_close` (lines 69-85):**

```python
async def _schedule_auto_close(self, run_id: str, delay: int = 900) -> None:
    """Close the WS connection after a grace period post-completion.

    Caps idle billing from abandoned tabs: once analysis_complete has been
    sent, the frontend no longer needs the WS for streaming. The 15-minute
    grace gives a reviewer time to scroll results before we close with code
    1000 (normal closure), which the frontend handles gracefully.
    """
    await asyncio.sleep(delay)
    ws = self._connections.get(run_id)
    if ws is None:
        return
    try:
        await ws.close(code=1000, reason="analysis_complete auto-close")
    except Exception as e:
        logger.warning(f"Auto-close failed for run_id={run_id}: {e}")
    self.disconnect(run_id)
```

**Wired into `mark_run_complete` (lines 87-94):**

```python
async def mark_run_complete(self, run_id: str) -> None:
    """Mark a run as complete. Keeps the buffer for 5 minutes for late connections."""
    import time
    self._buffer_expiry[run_id] = time.time() + 300
    # Schedule WS auto-close 15 min after completion to cap idle billing.
    task = asyncio.create_task(self._schedule_auto_close(run_id, delay=900))
    self._auto_close_tasks[run_id] = task
    logger.info(f"Run {run_id} marked complete, buffer expires in 5 minutes")
```

**Cancellation on early disconnect (lines 63-66, inside `disconnect`):**

```python
# Cancel any pending auto-close task; the connection is gone.
task = self._auto_close_tasks.pop(run_id, None)
if task and not task.done():
    task.cancel()
```

This is important: if the user refreshes or closes their tab within the 15-minute grace window, `disconnect` fires and cancels the scheduled close so it doesn't try to close an already-gone WS.

**Only WS protocol change:** server-initiated close with code 1000. No handshake, message format, or origin changes — the frontend already handles clean close gracefully.

---

### 4. `robots.txt` — already in place

**File:** `frontend/public/robots.txt`

```
User-agent: *
Disallow: /
```

This already exists from v1 (see [`2026-06-07_cloud-run-cost-reduction.md`](./2026-06-07_cloud-run-cost-reduction.md)). Called out here only so it isn't a surprise later — no change was made in commit `631a807`. It contributes ~$0.02–0.05/day of savings already baked into the baseline.

---

## WebSocket Safety Verification

Raising backend concurrency from 1 → 20 is the riskiest of the three levers. It is justified by three prior traces:

| Prior trace | What it fixed | Why it matters here |
|-------------|---------------|---------------------|
| [`2026-04-19_second-query-hang-deadlock-fix.md`](./2026-04-19_second-query-hang-deadlock-fix.md) | Second query deadlocked on `future.result()` blocking | Fixed via fire-and-forget `run_coroutine_threadsafe` in `analysis_service.py:55-64`. Without this, concurrency > 1 would re-deadlock. |
| [`2026-04-19_websocket-lifecycle-fixes.md`](./2026-04-19_websocket-lifecycle-fixes.md) | WS lifecycle desync on new run | Fixed via `prepareNewRun()` in the frontend. Auto-close only fires **after** `analysis_complete`, so it never races a live stream. |
| [`2026-04-14_log-streaming-fix.md`](./2026-04-14_log-streaming-fix.md) | Log handler lost across runs | Fixed via `preserve_handlers=[run.ws_handler]`. Logs keep streaming across the higher-concurrency multiplexing. |

**Only WS protocol change in v2:** the server-initiated close (code 1000) 15 min after completion. No handshake, message, or origin changes.

---

## Expected Savings

Ported from the plan; these are **projections, not measurements** (see UNTESTED banner).

| Lever | Expected Savings | Notes |
|-------|-----------------|-------|
| WS auto-close (15 min cap) | ~$0.20–0.30/day | Caps idle billing from abandoned recruiter tabs |
| `--max-instances 2→1` (both services) | ~$0.33/day | Eliminates second-instance cold starts |
| Frontend `--cpu 0.5→1` | ~+$0.03/day (cost) | Bounded by max-instances=1; net positive because it enables concurrency>1 |
| `robots.txt` (from v1) | ~$0.02–0.05/day | Already in place; in the baseline |
| Backend `--concurrency 1→20` | $0 direct | **Enabler**, not a direct saving — makes `--max-instances=1` viable |
| **Total projected** | **$1.31 → ~$0.65–0.75/day** | Stretch target (~$5/month) needs follow-up #1 |

---

## Pending Verification (UNTESTED)

These steps mirror the plan's verification section. None are checked yet.

- [ ] GitHub Actions deploy succeeds for both services
- [ ] Smoke test: run an analysis end-to-end
- [ ] WS streams logs start → `analysis_complete`
- [ ] Page refresh mid-analysis reconnects cleanly
- [ ] **WS auto-close test:** leave tab open after completion; ~15 min later, Cloud Run logs show server-initiated close code 1000; frontend stays in "completed" state
- [ ] **Auto-close cancellation test:** refresh within 15-min grace; old WS closes cleanly, new WS connects
- [ ] Cloud Run metrics: instance count capped at 1 per service
- [ ] GCP Billing → Cloud Run over 48h confirms ~$0.65–0.75/day trajectory
- [ ] If still > $0.80/day after 48h: follow-up #1 (static frontend) is the next lever

---

## Follow-ups — NOT IMPLEMENTED

Both follow-ups are scoped and analyzed but **not implemented** in commit `631a807`. Each is labeled with its expected cost benefit and the concrete approach.

### #1. Move frontend to static hosting — HIGH impact (~$0.40/day) — **NOT IMPLEMENTED**

This is the lever that reaches the ~$5/month stretch target.

**Approach (verified viable):**
- **No SSR, no `next/image`, no middleware, no API routes** in the frontend — confirmed during planning. Static export is a drop-in.
- **Only code change required:** remove `rewrites()` from `frontend/next.config.js:3-10`. The rewrites point to `http://127.0.0.1:8901` — a dev-only proxy that has no effect in Cloud Run (frontend and backend are already separate origins in prod).
- **Cross-origin WS already works:** frontend → backend is already cross-origin in production today, and FastAPI does not validate WS origin. So moving the frontend off Cloud Run does not change the WS connection path.
- **CORS update required:** add the new static-hosting origin (e.g. a Cloud Storage bucket's `storage.googleapis.com` URL or a custom domain) to `CORS_ORIGINS` in `deploy-env.yaml`.
- **Deploy rewrite:** replace the frontend `gcloud run deploy` step (`.github/workflows/deploy.yml:82-97`) with a `gsutil rsync frontend/out gs://<bucket>` step. The frontend build step already runs via Docker; it would switch to `next build` producing `out/`.

**Why not in this commit:** scope discipline. v2 takes the cheap CPU/WS wins first; static hosting rewrites the deploy pipeline and is its own trace.

### #2. Multi-stage backend Dockerfile — LOW impact — **NOT IMPLEMENTED**

Smaller, hygiene-grade win.

**Approach:**
- `backend/Dockerfile:7` currently installs `build-essential` in the **runtime layer**, which bloats the image by ~200MB.
- A multi-stage build (builder stage with `build-essential` for any compiled wheels, runtime stage with only the installed packages) would cut image size meaningfully.
- Benefit: faster cold starts (less to pull) and lower Artifact Registry storage costs (compounded by the v1 cleanup step).

**Why not in this commit:** cost benefit is small relative to #1 and to the WS/instance-cap levers; deferred to a hygiene pass.

---

## Files Modified

| File | Change |
|------|--------|
| `.github/workflows/deploy.yml:65-66` | Backend: `--max-instances 2→1`, `--concurrency 1→20` |
| `.github/workflows/deploy.yml:91,96,97` | Frontend: `--cpu 0.5→1`, `--max-instances 2→1`, `--concurrency 1→10` |
| `backend/app/api/websocket/manager.py:30` | Added `_auto_close_tasks` dict |
| `backend/app/api/websocket/manager.py:63-66` | `disconnect()` cancels pending auto-close task |
| `backend/app/api/websocket/manager.py:69-85` | New `_schedule_auto_close` method (sleeps 900s → `ws.close(code=1000)` → disconnect) |
| `backend/app/api/websocket/manager.py:87-94` | `mark_run_complete` schedules the auto-close task |

**Note:** `frontend/public/robots.txt` already existed with the exact content from v1 — **no change** in commit `631a807`. Called out for completeness only.

---

## Cost Breakdown

| Component | Before (v1) | After (v2, projected) | Savings |
|-----------|-------------|----------------------|---------|
| WS idle billing (abandoned tabs) | ~$0.20–0.30/day | ~$0/day | ~$0.20–0.30/day |
| Second-instance cold starts | ~$0.33/day | ~$0/day | ~$0.33/day |
| Frontend CPU bump (0.5 → 1, enables concurrency) | — | ~+$0.03/day | ~−$0.03/day (cost) |
| Static hosting (follow-up #1) | — | — | **NOT IMPLEMENTED** (~$0.40/day projected) |
| **Total projected** | **~$1.31/day** | **~$0.65–0.75/day** | **~$0.55/day** |

**Key insight:** v1 was about *preventing wake-ups* (block bots). v2 is about *shortening the time an instance stays alive once woken* (instance cap + WS auto-close). The two are complementary — v1 reduces the rate, v2 reduces the duration.
