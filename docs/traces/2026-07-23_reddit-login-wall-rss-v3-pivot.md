# Trace: Reddit Login Wall — Pivot to RSS (v3 client)

**Date:** 2026-07-23
**Trigger:** Every subreddit returns `WARN: No posts found in r/X` in prod, regardless of proxy state. Same symptoms locally.

---

## Problem

Reddit rolled out a sitewide login wall in July 2026. Both unauthenticated
public surfaces the app relied on are dead:

| Endpoint | Behavior on 2026-07-23 |
|---|---|
| `old.reddit.com/r/X/hot/` (HTML scraper used by `reddit_v2`) | HTTP 302 → `/login/?reason=lor2` (login wall) |
| `old.reddit.com/r/X.json` | HTTP 302 → login wall |
| `www.reddit.com/r/X.json` (legacy `reddit_live`) | HTTP 403 (190KB web UI shell, "blocked" embedded) |
| `www.reddit.com/r/X/search.json` | HTTP 403 |
| `oauth.reddit.com/r/X` (no Bearer) | HTTP 403 (edge WAF) |

### Evidence the wall is sitewide, not IP-specific

- Tested from a residential IP (no proxy): same 302/403 results.
- Tested 5 User-Agents (`curl/7.88`, `python-requests/2.31`, a browser
  Chrome UA, an empty UA, the project's `complaint-analyzer:1.0` UA): all
  403 / 302 the same way. The wall is not UA-based.
- Tested through the IPVanish SOCKS5 proxy from Cloud Run: also returns 0
  posts (`scripts/test_reddit_v2_prod.py` against `painpan-backend`).
- A logged-in browser session can still access `.json` (cookies bypass the
  wall), but a deployed backend cannot use a user's cookies.

### Why "the proxy worked last week"

Reddit enforced the wall the week of 2026-07-XX. Before that, the IPVanish
proxy + a clean UA was enough. After enforcement, the wall is served to all
unauthenticated clients regardless of source IP.

### Why the failure was silent

`redditapiv2_fetcher.py:189-191` logs `WARN: No posts found in r/X` when
the parser returns `[]`. The parser returns `[]` when:
1. `requests` follows the 302 to the login page silently (default behavior).
2. The login page HTML has no `div.thing[data-fullname]` elements.
3. The parser yields zero posts. No exception is raised.

This looks identical to "the subreddit is genuinely empty." The broad
`except Exception: continue` in the fetcher loop then moves on to the next
subreddit, producing 20 `WARN` lines and zero collected data.

---

## Solution

Move to **Reddit's Atom RSS feeds**, the only unauthenticated public surface
left. All listing and comment endpoints have `.rss` variants that still
return HTTP 200 with structured Atom XML.

| Endpoint | Status on 2026-07-23 (residential IP, no proxy) |
|---|---|
| `www.reddit.com/r/X/hot.rss` | 200, ~67KB, 25 entries |
| `www.reddit.com/r/X/new.rss` | 200, ~7KB |
| `www.reddit.com/r/X/top.rss?t=week` | 200 |
| `www.reddit.com/r/X/search.rss?q=...&restrict_sr=1` | 200, real results |
| `www.reddit.com/comments/{post_id}/.rss` | 200, post + comments (t3_ + t1_) |

### Per-entry data available in RSS

- `<id>` (`t3_xxx` for posts, `t1_xxx` for comments)
- `<title>`, `<author><name>` (`/u/xxx`), `<link href="...">` (permalink)
- `<published>` (ISO timestamp), `<updated>`
- `<content type="html">` (HTML-encoded body; `<!-- SC_OFF -->` markers wrap selftext)
- `<category term="...">` (subreddit name on listing entries)

### Data NOT in RSS (vs. the v2 HTML scraper)

- `ups` (upvote count) — used by v2 to gate comment fetching and by the Analyst for weighting
- `num_comments`, `upvote_ratio`, `link_flair_text`
- `distinguished`, `stickied` flags

The fetcher drops the upvote threshold (default was 100) and lowers
`max_posts_with_comments` from 30 to 5, preserving the rate-limit budget
when every post is eligible for comment fetching.

---

## Files

### New

| File | Purpose |
|---|---|
| `app/reddit_v3/__init__.py` | Empty package marker |
| `app/reddit_v3/redditapiv3_parser.py` | Atom XML → dict (matches v2 dict shape) |
| `app/reddit_v3/redditapiv3_client.py` | HTTP client (Session/Retry/proxy/pacing/circuit-breaker identical to v2; endpoints changed to `.rss`) |
| `app/reddit_v3/redditapiv3_fetcher.py` | Orchestrator (structural copy of v2; `min_upvotes_for_comments=0`, `max_posts_with_comments=5`) |
| `scripts/test_reddit_v3_local.py` | End-to-end smoke test (1 subreddit, asserts `total_posts > 0`) |
| `docs/traces/2026-07-23_reddit-login-wall-rss-v3-pivot.md` | This file |

### Modified

| File | Change |
|---|---|
| `app/config.py` | Added `"reddit_v3"` to `DataSource` Literal |
| `app/agents/tools/fetch.py` | Router branch + `_fetch_reddit_v3` handler |
| `backend/app/models/api.py` | Added `"reddit_v3"` to `AnalysisRequest.data_source` Literal |
| `backend/app/api/routes/analysis.py` | Rate-limit tracking fires for `reddit_v3` too |
| `frontend/lib/types.ts` | Added `"reddit_v3"` to `DataSource` union |
| `frontend/lib/datasets.ts` | New `reddit_v3` entry in `DATASET_CARDS`; marked `reddit_v2` as broken |
| `frontend/components/ArchitectureDiagram.tsx` | `ARCH_PREPROCESSING` + `ARCH_LABELS` Records get a `reddit_v3` key (required by `Record<DataSource, ...>`) |
| `frontend/app/how-it-works/page.tsx` | `SOURCE_CONTENT` gets a `reddit_v3` entry; `isLive` accepts v3 |
| `frontend/app/page.tsx`, `frontend/components/Navbar.tsx`, `frontend/components/layout/MainLayout.tsx` | `dataSource === "reddit_live" || "reddit_v2"` checks extended to include `"reddit_v3"`; v1/v2 banner now offers "Use v3 (RSS) instead" |

### Untouched

- `app/reddit_v2/*` — kept verbatim for reference. Marked dead in the
  `DataSource` Literal comment and in the frontend's `DATASET_CARDS`.
- `app/reddit/client.py` — same; v1 is also dead.
- Existing tests, traces, docs — no changes needed (new code is additive).

---

## Architectural choices

### Why a new v3 path instead of rewriting v2 in place

1. **Rollback safety** — if RSS also breaks next week, the v2 code is still
   on disk and can be reverted to. Overwriting v2 destroys the fallback.
2. **Clear provenance** — the diff shows "add v3" instead of "mutate v2."
   Easier to review, easier to remove.
3. **Mirrors the v1→v2 precedent** — v2 was created the same way when v1
   died; v3 follows the established pattern.

### Why `max_posts_with_comments=5` (was 30 in v2)

v2's threshold `min_upvotes_for_comments=100` meant only a handful of posts
qualified for comment fetching in practice — maybe 5–10 per run. v3 has no
upvote data, so the threshold is effectively zero. Without lowering the cap,
v3 would try to fetch comments for every post (up to 30) and burn the
rate-limit budget on the comments endpoint, which throttles aggressively
(verified — comment-fetch storm triggered 429s and circuit-breaker cooldowns
during local testing).

5 posts × 20 comments = ~100 comments of signal for the Analyst. Same order
of magnitude as v2's effective output, well under rate limit.

### Why 429 is no longer in `status_forcelist`

The shared `Retry` config used to include 429. With `total=3` and
`backoff_factor=1`, that means each user-level request becomes 4 HTTP
attempts (1 + 3 retries) in rapid succession. When Reddit throttles, this
_multiplies_ the pressure and trips the circuit breaker faster.

The circuit breaker in `_make_request` handles 429 at the right level
(process-wide cooldown across all callers). Removing 429 from
`status_forcelist` lets the breaker do its job.

This required an additional wiring change: a 429 no longer raises
`RequestException` (urllib3 doesn't retry), so the breaker must be notified
via the response status code path. See `redditapiv3_client.py:149-152`.

---

## Verification

### Local smoke test (residential IP, no proxy)

```
$ python scripts/test_reddit_v3_local.py
======================================================================
TEST 1: _fetch_reddit_v3 with explicit subreddits (skip LLM picker)
======================================================================
data_source: reddit_v3
total_posts: 23
subreddits_queried: ['gaming']

first post:
  id:         1v4i7ik
  title:      Satisfying bread animation from Yakuza: Like a Dragon
  author:     Slow-Boysenberry3150
  subreddit:  gaming

======================================================================
RESULT: PASS
======================================================================
```

Listing endpoint returns 23 posts with full data. AutoModerator stickies
filtered out by the existing `author == "AutoModerator"` check.

### Known follow-up: behavior on prod (Cloud Run + IPVanish proxy)

Local test could not verify comment fetching — my residential IP got flagged
mid-test by Reddit after the probe storm, and `/comments/ID/.rss` started
returning 429 even at 6-second pacing. The fetcher degrades gracefully
(logs warning, continues with posts-only), so the test still passes, but
real comment coverage on prod is **TBD pending deploy**.

If prod also throttles `/comments/`, the options are:
1. Lower `max_posts_with_comments` to 3.
2. Add per-endpoint pacing (`/comments/` gets 15s, listings get 6s).
3. Drop comment fetching entirely and rely on post titles + selftext.

---

## Lessons

1. **Silent failures hide policy changes.** The "No posts found" warning is
   indistinguishable from "Reddit served a login wall." A 200 with empty
   parse should be logged with the response body snippet so this is
   debuggable next time.
2. **Reddit's enforcement is rolling, not announced.** The app worked last
   week and broke this week with no code change. Health checks should probe
   the actual data path, not just `/health`.
3. **RSS is Reddit's last unauthenticated surface.** It's been around since
   the beginning; it survives the WAF/login-wall layers because it's
   intended for feed readers. Worth remembering if `.json` OAuth also
   disappears.
4. **`urllib3.Retry` on 429 is a footgun.** It amplifies the throttling
   instead of relieving it. Only retry on server errors (5xx), never on
   client-side rate limits. The breaker handles 429 across the process.
5. **Cookies are the unauthenticated-authenticated path.** A logged-in
   browser sails through the wall. For a future iteration, supporting a
   `REDDIT_COOKIE` env var (refreshed manually) could restore `.json` access
   with upvote counts. Out of scope for this fix.
