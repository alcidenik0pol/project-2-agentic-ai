# LEARNING.md

Insights, debugging tips, and lessons learned during development.

---

## 2026-07-16: Starlette 1.x strips CORS headers — pin BOTH fastapi AND starlette

### Symptom
After deploy, the Firebase frontend cross-origin requests to Cloud Run failed CORS:
`OPTIONS /api/v1/analysis → 405 Method Not Allowed`, and simple `GET` requests returned
200 with **no `access-control-*` headers at all**. `CORS_ORIGINS` env var was correctly
deployed and contained the frontend origin.

### Root cause (corrected after initial misdiagnosis)
**First attempt** pinned `fastapi==0.135.3` — but this was insufficient. fastapi 0.135.3
declares `starlette>=0.46.0` with **no upper bound**, so a fresh `pip install` resolves
the latest matching version: **starlette 1.3.1**. In Starlette 1.x, `BaseHTTPMiddleware`
(used by `@app.middleware("http")`) silently strips CORS headers added by the inner
`CORSMiddleware`. Our `check_usage_limit` middleware is registered via `@app.middleware("http")`
AFTER `CORSMiddleware`, making it the outermost middleware — so it eats all CORS headers
from every response.

The local conda env was installed months ago and still had starlette 0.52.1 (pre-1.x),
where the middleware interaction works. The bug only surfaced in the Docker image because
pip resolved starlette 1.3.1 fresh.

### Diagnosis trail
1. `curl -i` on prod GET `/health` with `Origin` header → 200 but zero `access-control-*`
   headers (not just preflight — ALL CORS headers missing).
2. CI build log: `Collecting starlette>=0.46.0 (from fastapi==0.135.3)` →
   `Downloading starlette-1.3.1`.
3. Local test with starlette 0.52.1 + same middleware pattern → CORS works perfectly.

### Fix
Pin **both** in `backend/requirements.txt`:
```
fastapi==0.135.3
starlette==0.52.1
```

### Rules
- **Pinning a package does NOT pin its transitive deps.** `fastapi==0.135.3` still allows
  `starlette>=0.46.0` to resolve to 1.x. Pin the leaf dependency that actually breaks.
- **Always check the CI build log's `Successfully installed` line** — it shows the exact
  resolved versions. Don't assume pip resolved what you intended.
- **`@app.middleware("http")` + `CORSMiddleware` ordering matters.** The `@app.middleware`
  decorator adds `BaseHTTPMiddleware` as the outermost layer. If it runs OUTSIDE
  `CORSMiddleware`, it can strip CORS headers in certain Starlette versions. In Starlette
  0.52.x this works; in 1.x it doesn't. Either pin starlette or ensure CORSMiddleware is
  registered LAST (outermost).
- **Local-works/prod-broken + only difference is dependency versions ⇒ version drift.**
  Compare `pip show <pkg>` locally vs the build log before chasing code or config.

---

## 2026-07-15: Cooperative cancel needs to escape broad `except Exception` handlers

When implementing a "Stop" button via a module-level cancel flag, the flag-raised exception (`PipelineCancelled`) is a subclass of `Exception`. Two places silently swallow it unless handled explicitly:

1. **`execute_tool` (`app/agents/tools/__init__.py`)** wraps every tool call in `try/except Exception` and converts errors to a JSON string. A cancel raised inside a tool becomes a benign tool-error string instead of propagating. Fix: add `except PipelineCancelled: raise` **before** the generic `except Exception`.
2. **The fetcher's per-subreddit loop** wraps `_fetch_from_subreddit` in `try/except Exception: continue`. If the cancel check is placed **inside** that try, it gets caught and the loop `continue`s. Fix: put the `if is_cancelled(): raise` check **before/outside** the `try:` so it propagates from the for-loop directly.

Rule: when adding a sentinel exception for control flow, grep for every `except Exception` on the propagation path and order the specific `except` clause first. Place cancel checks outside try blocks that swallow exceptions.

Also: `_run_in_thread` runs the sync pipeline via `run_in_executor`, so `task.cancel()` (asyncio) cannot interrupt the thread. A cooperative flag checked inside the loop is the only way to stop the fetch phase mid-run. `task.cancel()` still works for the async LLM/analyst phase — keep both signals.

### Cancel checks must cover the comment-fetch sub-phase, not just per-subreddit

**Live-tested finding:** a per-subreddit cancel check is NOT enough. `_fetch_from_subreddit` loops over every post in the listing and calls `fetch_comments_for_post` for high-upvote posts — each comment fetch is a separate rate-limited HTTP request (~6s pacing). One subreddit can spend minutes in comment-fetching (up to `max_posts_with_comments=30` × 6s). A cancel arriving mid-comment-fetch never reaches the per-subreddit check, so the thread ran **44+ seconds** after Stop before the fix.

**Fix:** add a second `if is_cancelled(): raise PipelineCancelled()` at the top of the per-post loop inside `_fetch_from_subreddit`, and add `except PipelineCancelled: raise` before that function's outer `except Exception` (which otherwise swallows it into a logged error). Verified live: thread stop latency dropped from 44s+ to **~3s**.

Rule: when adding cooperative cancel to a loop, audit EVERY nested loop that performs rate-limited/blocking work, not just the outermost one. The check belongs wherever consecutive iterations each perform a user-visible wait.

---

## 2026-07-15: MSYS/Git-Bash silently swallows `.cmd` shims (gcloud, npm) — CRITICAL

**Confirmed cases on this machine:**
- **gcloud** — reports exit 0 with empty output on real failure (see below).
- **npm** — exits 0 with empty output when backgrounded; the dev server never starts and you get no error. Foreground `npm run dev` also produces no output when run via the Bash tool.

Same root cause for both: Windows `.cmd` shims are incompatible with MSYS pipe/background handling. Route through `cmd.exe //c`.

### Symptom
`gcloud storage` (and likely other gcloud) commands run via the Bash tool on this Windows/MSYS machine return **exit code 0 with empty output even when they actually fail**. `gcloud storage buckets create`, `gcloud storage cp`, and `gcloud storage objects describe` all reported success (exit 0, no errors) — but the bucket never got created and uploads went nowhere. Redirecting to a file also produced empty files.

### Root cause
The gcloud CLI's stdout/stderr buffering is incompatible with MSYS/Git-Bash's pipe handling on this machine. Both output AND the real exit status are lost. You cannot trust `echo "EXIT:$?"` after a gcloud command run directly through MSYS bash here.

### Fix: route gcloud through `cmd.exe //c`
```bash
# BROKEN (MSYS swallows output + exit code, reports false success):
gcloud storage buckets create gs://x --project=y
echo "EXIT:$?"   # prints 0 even on failure

# WORKS (real output + real exit code):
cmd.exe //c "gcloud storage buckets create gs://x --project=y"
```
`cmd.exe //c` captures the true stdout, stderr, and exit code. Always verify GCS state (`buckets describe`, `storage ls --recursive`) via `cmd.exe //c` too.

### Path-with-spaces gotcha (second-order)
When passing a source path containing spaces into `cmd.exe //c "gcloud storage cp \"path with spaces\" gs://..."`, bash's quote-escaping mangles the path and gcloud reports "matched no objects or files". **Workaround:** copy the file to a no-spaces path first (e.g. `F:/_Dev/tmp.parquet`), upload that, then delete the temp copy.

### Rule
On this machine, **always run `.cmd` shims (gcloud, npm, npx, yarn, pnpm) through `cmd.exe //c`** and treat MSYS-direct results as untrusted. This wasted significant effort before diagnosis, in both the gcloud deployment session and (separately) the local dev-server restart session.

---

## 2026-07-15: Don't blanket-apply a plan step when it conflicts with intent (banner bug)

The reddit_v2 plan said "extend both MainLayout checks to `|| reddit_v2`" — meaning the banner check AND the nav-disable check. I had explicit doubt ("the banner says 'offline' which is false for v2") but rationalized it and applied both. Result: selecting the working v2 scraper showed a giant "Data collection is temporarily offline" banner, making it look broken and untestable. User caught it immediately.

**Rule:** when a plan step conflicts with user intent/correctness, STOP and flag it rather than interpreting the plan charitably. The nav-disable extension was right (enables the rate-limit tab for v2); the banner extension was wrong (v2 works). They needed opposite treatments, not the same one. Ask which is meant when "extend both" produces a false-negative UI message.

**Touchstone for future "show X for data source" checks:** the offline/degraded banner applies to the *broken* source (`reddit_live`), never to the working replacement.

---

## 2026-07-15: old.reddit.com HTML structure (for reddit_v2 scraper)

Validated against live HTML before writing the parser — the plan's field map had three errors that would have produced silent zero-values. **Always curl real HTML before trusting a selector spec.**

### Gotchas discovered
- Post **comment count** attribute is `data-comments-count` (hyphenated), NOT `data-commentscount`.
- **Comment scores** have NO `data-score` attribute (only posts do). The canonical score lives in `.tagline .score.unvoted[title]` (title attr = numeric point count). Reddit renders three `.score` siblings (dislikes/unvoted/likes); the `.unvoted` one is the real value.
- **Top-level comments** have no `.parent a[href]` (their `.parent` is just `<a name="...">`). Derive `parent_id` as `t3_{post_id}` for them, matching the JSON API.
- `class=" thing ..."` has a **leading space** after the quote — `BeautifulSoup`'s `div.thing` still matches, but raw `grep 'class="thing'` returns 0 (don't grep to validate structure; use bs4).
- **`upvote_ratio` is not exposed** in old.reddit HTML — parser returns `None`; the Pydantic model accepts it.
- **Selftext** (`data-permalink`) is collapsed on listing pages (`.usertext-body .md` is None even for self posts) but IS present on the comments page. The fetcher doesn't enrich from the comments page, so listing `selftext` is usually None — acceptable.
- `data-timestamp` (ms epoch) and `data-permalink` (clean path) are available directly on post `div.thing` — prefer these over parsing `a.title[href]` / ISO `<time>`.
- **`/r/{sub}/about/` returns 404** on old.reddit for unauthenticated access ("page not found"). `get_subreddit_info` returns `None` on 404; the fetcher doesn't depend on it.

### Proxy note
The v2 client copies v1's proxy config verbatim. Locally `config.proxy_enabled=True` points at a SOCKS5 endpoint whose auth fails, so the live `test_redditapiv2.py` **skips locally** (graceful). On Cloud Run the `PROXY_URL` env var makes it work. The proxy is identical to v1's handling — not a v2-specific concern.

### Verification approach
- 16 offline parser unit tests against saved real HTML fixtures in `app/tests/fixtures/` lock in the structure contract (`pytest app/tests/test_redditapiv2_parser.py`).
- Live end-to-end verified with proxy temporarily disabled: listing + comments (2-element JSON shape) + rate-limit tracking all work against `old.reddit.com`.

---

## 2026-07-15: Frontend Shows "Running" State on Page Reload (Stale Recovery Bug)

### Symptom
After restarting the backend, reloading the frontend page shows the UI as if an analysis is running ("mining" / stuff happening) even though no analysis was submitted.

### Root Cause
The frontend has a **localStorage recovery feature** in `frontend/contexts/WebSocketContext.tsx` (lines 391-409) that:
1. Saves `analysis_run_id`, `analysis_phase`, `analysis_timestamp` to localStorage when an analysis is running
2. On page reload, checks localStorage and auto-reconnects to the saved run if < 15 minutes old

When the backend is restarted, old runs are lost, but localStorage still holds stale state. The frontend tries to reconnect to a non-existent run, causing the UI to appear stuck in "running" state.

### Fix: Clear localStorage
Run in browser console (F12 → Console):
```javascript
localStorage.removeItem("analysis_run_id");
localStorage.removeItem("analysis_phase");
localStorage.removeItem("analysis_timestamp");
```

Then reload the page.

### Alternative: Disable Recovery Feature
Remove or comment out the recovery `useEffect` in `WebSocketContext.tsx` (lines 391-409).

---

## Debugging Commands Reference

### Check for Multiple Backend Processes
```bash
# List all Python processes
tasklist | grep -i python

# Get command line details for each Python process
wmic process where "name='python.exe'" get processid,commandline

# Check what's listening on backend/frontend ports
netstat -aon | grep -E "3456|8901"
```

### Kill Stray Processes
```bash
# Kill specific PIDs
taskkill //F //PID <pid1> //PID <pid2>

# Find and kill by port (get PID from netstat first)
netstat -aon | grep "8901"
taskkill //F //PID <pid>
```

### Restart Backend
```bash
cd "F:\_Dev\_Columbia\Agentic AI\project 2\backend"
conda run -n agentic-ai-p2 --no-capture-output python -m uvicorn app.main:app --host 0.0.0.0 --port 8901
```

### Restart Frontend
```bash
# npm.cmd silently exits when backgrounded in MSYS bash — route through cmd //c (see rule above).
cd "F:\_Dev\_Columbia\Agentic AI\project 2\frontend" && cmd //c "npm run dev"
```
For a full restart recipe (kill + backend + frontend + verify), see CLAUDE.md → "Running Locally" → "Restart both servers".

### Clear Next.js Cache (if stale compilation)
```bash
cd "F:\_Dev\_Columbia\Agentic AI\project 2\frontend"
rm -rf .next
npm run dev -- -p 3456
```

---

## JSON Escape Bug in LLM Output

### Symptom
`hypothesis.json` contains invalid `\'` escape sequences from LLM output, causing JSON parse errors.

### Fix
Added `sanitize_json_escapes()` function using regex:
```python
import re

def sanitize_json_escapes(text: str) -> str:
    """Fix invalid JSON escape sequences from LLM output."""
    return re.sub(r"(?<!\\)\\'", "'", text)
```

Applied in:
- `backend/app/services/analysis_service.py`
- `backend/app/api/routes/results.py`
- `app/agents/tools/artifacts.py`
