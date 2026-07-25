# Trace: Pushshift Candidate Mining + Description-From-Content Pivot

**Date:** 2026-07-22
**Status:** DONE — all 5 phases landed. Pool expanded from 87 → 167 subs (89 existing carried forward + 80 Pushshift-derived). 4/4 regression tests pass. One known limitation surfaced: the selector's pre-existing `[:60]` cap hides all 80 new candidates from the LLM (see Known Limitation).

---

## Problem

The LLM subreddit selector (`app/collector/subreddit_selector.py`) picks subs for
a topic from `load_subreddit_descriptions()`, which reads a curated JSON of only
**87 subreddits** (`data/smallsample/subreddit_descriptions_20260414_091545.json`).
For any topic outside the curated domains (finance, health, relationships…), the
selector has too small a pool to find the right communities.

Goal: expand the candidate pool with high-value subreddits mined from the local
Pushshift snapshot, and produce a fresh `subreddit_descriptions_*.json` the
loader picks up automatically (it globs `data/**/subreddit_descriptions_*.json`
and picks newest by mtime).

---

## Original Plan (approved)

1. **Phase 1** — mine Pushshift for ~80 candidate subs missing from the curated 87.
2. **Phase 2** — append them to `docs/ideation/reddit/subreddit_urls.md` (with a review checkpoint).
3. **Phase 3** — fix the 4 v1-isms in `scripts/fetch_subreddit_descriptions.py` (it still imported the dead v1 client).
4. **Phase 4** — re-run the fetcher to produce fresh descriptions JSON.
5. **Phase 5** — verify end-to-end + regression tests.

---

## Phase 1 — Candidate Mining (DONE)

### Approach

New script `scripts/analyze_pushshift_candidates.py` queries the Pushshift
Parquet (`data/pushshift/RS_2018-01_00.parquet`, 11.26M rows, Jan 2018
submissions) via DuckDB, ranks subs by post count, applies a filter pipeline,
and writes a markdown report + JSON:

```
top 500 by COUNT(*) per LOWER(subreddit)
  → drop the 87 curated (DRY via load_subreddit_descriptions)
  → drop SPAM_BOT_BLOCKLIST  (autonewspaper, the_donald, cbts_stream, …)
  → drop NSFW_BLOCKLIST      (gonewild, ageplaypenpals, hotvids, …)
  → drop post_count < 500
  → take top 80
```

### Results

- Curated loaded: **87** (not 89 — the plan's "89" counted the URL markdown; the loader applies a `min_subscribers=1000` filter and yields 87).
- Top-500 pulled from Pushshift.
- Dropped: 14 curated, 23 spam/bot, 8 NSFW, 0 below threshold → 455 survived → wrote top 80.
- Sanity assertions (no blocklist/curated leakage) pass.

### Outputs

- `docs/ideation/reddit/pushshift_candidate_subreddits.md` — ranked table for human review.
- `docs/ideation/reddit/pushshift_candidates.json` — `[{rank, name, post_count, url}, …]` for the append step.

### Blocklist grew during review

First pass surfaced 6 heuristic false positives the initial blocklist missed. Rather than hand-edit the JSON, they were added to the blocklist constants with inline comments and the script re-run (reproducible + auto-renumbered):
- `ageplaypenpals`, `hotvids` → NSFW (name heuristic missed them)
- `cbts_stream` (banned QAnon), `shareyourblogpost` (blog spam), `freestuffnyc` (geo-restricted spam), `noncensored_bitcoin` (low-quality fork) → SPAM_BOT

---

## Phase 3 — Fetcher Migration (DONE)

4 surgical edits to `scripts/fetch_subreddit_descriptions.py`:

| # | What | From | TO |
|---|------|------|----|
| 1 | import | `from app.reddit.client import RedditPublicAPI` | `from app.reddit_v2.redditapiv2_client import RedditAPIv2Client` |
| 2 | URL regex | `r"https://reddit\.com/r/(\w+)"` | `r"https://reddit\.com/r/([A-Za-z0-9_\-]+)"` (the old one silently dropped hyphenated subs) |
| 3 | client | `client = RedditPublicAPI()` | `client = RedditAPIv2Client()` |
| 4 | dict assembly | `over18`/`created_utc` read via `.get()` from response | explicit defaults `False` / `0.0` (v2 parser returns neither key; the loop's `name` var was already the source of truth) |

Note: `name` was *already* sourced from the loop variable (line 106), not from the response — the original plan's "Edit 4" was mostly a stylistic clarification, not a bug fix. The `.get("over18", False)` defaults already handled missing keys correctly.

---

## Phase 4 — BLOCKED, then PIVOTED

> **ERRATUM (2026-07-22, post-review):** the "blocker" narrative below is **wrong**.
> The `RedditAPIv2Client` is a sound HTML scraper and works correctly in
> production (the proxy is enabled with valid credentials there; the
> `2026-07-16_client-level-429-circuit-breaker.md` trace documents live
> `old.reddit.com` traffic flowing through it). My local smoke test failed
> for **environmental** reasons — `PROXY_ENABLED=false` in the local `.env`
> and stale local proxy credentials — which I wrongly generalized into a
> claim that "the v2 scraper itself is broken" and "Phase 4 cannot run."
>
> That generalization was a diagnostic error. The three "evidence" points
> below are either environmental (points 1 and 2 — local config, not code)
> or irrelevant (point 3 — the dead `.json` endpoint is *why* V2 exists;
> V2 scrapes HTML, not `.json`, so its 403 is not evidence against V2).
>
> **Consequence:** the Pushshift-content pivot (Phase 4 as implemented)
> was chosen under a false premise. The derived descriptions are still
> valid and useful, but the *reason* given for not simply re-running the
> Phase-3-fixed fetcher does not hold. Running the fetcher against a
> properly-configured environment would yield real sidebar descriptions
> *and* real subscriber counts (fixing the Known Limitation below
> honestly). The Pushshift generator remains a viable fallback for
> environments without Reddit access, but it should not be framed as
> *necessary*.
>
> The original (incorrect) section is preserved verbatim below for
> traceability.

### The blocker (surfaced by the smoke test)

The plan said: "If [the smoke test] fails, stop and re-plan — the v2 scraper itself is broken." It failed. Both network paths to Reddit are dead from this environment:

1. **Direct requests to `old.reddit.com/r/<sub>/about/`** → `302` to `/login/?reason=lor2` (logged-out wall). The login-wall HTML is 302KB and contains none of the `.titlebox` / `.redditname` / `.subscribers` markers the parser expects, so `parse_subreddit_about` returns an empty-ish dict. Listing pages (`/r/<sub>/`) are also walled.
2. **Configured SOCKS5 proxy** (`nyc.socks.ipvanish.com`, IPVanish) → `SOCKS5 authentication failed`. The credentials in `.env` are rejected. `PROXY_ENABLED=false` to boot.

`www.reddit.com/r/<sub>/about.json` still returns 403 (the original v1 dead endpoint).

So Phase 4 as originally specified (re-run the fetcher, scrape `/about/`) is impossible until either the proxy credentials are rotated or a residential-IP path is restored. Not fixable from code.

### The pivot

The user proposed bypassing `/about/` entirely: **derive each subreddit's description from the Pushshift content itself**, since the Parquet already has every sub's actual posts (title + selftext). Two-step LLM process per sub:

1. **Assume** what the sub is about from its name alone.
2. **Confirm / disprove / enrich** the assumption using its top posts.

This is resilient to the login wall (no Reddit network access needed) and arguably produces *better* signal than the sidebar blurb — top posts are evidence of what the community actually discusses.

### Implementation

- **New script:** `scripts/generate_descriptions_from_pushshift.py`.
- **Scope:** the **80 new candidates only**. The 87 existing keep their real sidebar descriptions (regenerating would degrade them).
- **Merge:** read existing entries from `data/smallsample/subreddit_descriptions_20260414_091545.json`, append 80 new, write one combined `data/subreddit_descriptions_<ts>.json`. Loader picks it up by mtime; no loader changes.
- **Per sub:** `PushshiftClient.search_posts(subreddits=[name], limit=15)` (top-scoring Jan 2018 posts), then one Gemini-flash call with the assume→confirm→synthesize prompt. Output `{title, public_description}`.
- **Schema:** identical to existing JSON. `over18=False`, `created_utc=0.0` (same convention as the Phase 3 fetcher fix); `description` is set equal to `public_description` (matches the v2 parser convention; the loader only reads `public_description`).
- **`subscribers` field:** Pushshift has no subscriber count. Set to **Jan-2018 post_count** as the proxy — preserves relative ranking among the 80. Real subscriber counts for the 87 stay as-is. (See Known Limitation for the consequence.)
- **`max_tokens=2048`:** initial smoke test at 512 truncated mid-string — Gemini 2.5 Flash reasons before emitting JSON and burned the budget. 2048 gives ample headroom; the actual JSON output is ~250-370 chars.

### Results

- **80/80 generated, 0 failures.** 537s elapsed (~9 min, ~6.7s/sub avg).
- Combined file: `data/subreddit_descriptions_20260722_201742.json` — **169 entries** (89 carried over + 80 new).
- Loader loads 167 after its `min_subscribers=1000` filter drops 2 low-subscriber existing entries.
- The assume→confirm step produced grounded, specific titles. Examples where confirmation from posts clearly beat name-only guessing:
  - `r/jailbreak` → "iOS Jailbreaking" (correctly disambiguated from the prison sense — the name alone is ambiguous).
  - `r/technology` → "Technology Policy & Ethics" (picked up the discussion/policy angle, not just gadgets).
  - `r/cryptocurrency` → "Cryptocurrency Investments and Community Support" (surfaced the scam/complaint signal).
  - `r/hmmm` → "Hmmm" (honest about an image sub with no real topic — no overclaiming).

---

## Methodology Note — the Volume-vs-Complaint-Richness Bias

During Phase 1 review, a distribution check revealed that **ranking by raw post count is a flawed proxy for complaint-analysis value.**

### Post-count distribution (all 241,466 distinct subs, Jan 2018)

| threshold | subs | % |
|----------:|-----:|--:|
| ≥ 1 | 241,466 | 100% |
| ≥ 100 | 10,086 | 4.2% |
| ≥ 1,000 | 1,738 | 0.7% |
| ≥ 10,000 | 131 | 0.05% |
| ≥ 50,000 | 14 | 0.006% |

| p50 | p75 | p90 | p99 | max |
|----:|----:|----:|----:|----:|
| 2 | 5 | 25 | 697 | 241,446 |

Textbook power law: the median sub has 2 posts in the whole month. Only ~1,700 subs have ≥1,000 posts; only ~130 have ≥10,000.

### Bias introduced

The rank-80 cutoff (`hmmm`, 10,795 posts) sits in the top ~130 by volume. That pool over-indexes on:
- **Generic defaults** (askreddit, funny, pics, aww, videos, news) — high volume, near-zero complaint specificity.
- **Trading subs** (rocketleagueexchange, globaloffensivetrade, steamtradingcards, hardwareswap, fashionreps) — transactional, not complaint-rich.
- **Big gaming subs** (fortnitebr, overwatch, leagueoflegends, dota2, wow, fifa) — patch-note driven.

It systematically misses mid-tier niche complaint subs in the 5k–15k post range — exactly the kind already in the curated 87 (`personalfinance`, `antiwork`, `relationship_advice`). Lower volume, much higher complaint density per post.

### Decision (resolved)

User chose **option 1: accept top-80-by-volume**. All large established subs; the bias toward defaults/trading/gaming is acknowledged but accepted for this pass. Re-ranking by LLM-scored complaint density (option 3) or casting a wider net to the 500–10,000 post range (option 2) remain viable follow-ups if the selector's coverage of niche pain points turns out to be thin in practice.

---

## Phase 5 — Verification (DONE)

- **Loader picks up the new file:** `data/subreddit_descriptions_20260722_201742.json` is the newest under `data/**/` → loader selects it automatically. Returns **167 subs** (89 carried over minus 2 filtered by `min_subscribers=1000`, plus 80 new).
- **Known new candidate present:** `cryptocurrency` resolves in the loaded dict with a non-empty `public_description`.
- **Regression tests:** `pytest app/tests/test_subreddit_loader.py -v` → **4/4 pass**.
  - Test 3 (`test_loader_filters_low_subscribers`) required clearing the loader's module-level cache between the two calls — the cache is populated on first call regardless of arguments (pre-existing design). The test documents this quirk inline rather than touching the loader (cache fix is out of scope).

---

## Known Limitation — the `[:60]` selector cap hides all 80 new candidates

The pool expanded 87 → 167, but **0 of the 80 new candidates reach the LLM selector's prompt.** Concrete numbers from verification:

- Existing subs carry real subscriber counts: `gaming` 47M, `amitheasshole` 24M, `personalfinance` 21M, `television` 18M…
- The 80 Pushshift-derived entries use `subscribers = post_count` (Jan 2018 volume), maxing at 241k (`askreddit`).
- That's a **~3-orders-of-magnitude gap.** The selector sorts all 167 by `subscribers` desc and slices `formatted[:60]` (`app/collector/subreddit_selector.py:75`). All 80 new entries fall below the cut; the top-60 are entirely existing subs.

So the expansion is *loaded* but currently *invisible* to topic-time subreddit selection. The candidates still add value as a discovery aid (the report + `subreddit_urls.md` now document them) and would become selectable the moment the cap is raised/paginated or the subscriber proxy is rescaled. Two follow-up options (out of scope here):
1. Raise or paginate the `[:60]` cap (167 subs × ~200 chars ≈ 33KB prompt — large but feasible).
2. Rescale the `subscribers` proxy for Pushshift-derived entries (e.g. `post_count × N`) so they interleave with the real counts in the sort — fabrication, but restores visibility without touching the cap.

This was flagged in the original plan as a pre-existing throttle.

---

## Files Touched

| File | Action | Status |
|------|--------|--------|
| `scripts/fetch_subreddit_descriptions.py` | 4 surgical edits (v1→v2 migration) | DONE |
| `scripts/analyze_pushshift_candidates.py` | NEW — Pushshift ranking + filters | DONE |
| `docs/ideation/reddit/pushshift_candidate_subreddits.md` | generated artifact (80-row report) | DONE |
| `docs/ideation/reddit/pushshift_candidates.json` | generated artifact (machine-readable) | DONE |
| `scripts/append_candidates_to_urls.py` | NEW — appends candidates to URL markdown (reuses fetcher's parser) | DONE |
| `docs/ideation/reddit/subreddit_urls.md` | appended 80 URLs under one header (non-destructive) | DONE |
| `scripts/generate_descriptions_from_pushshift.py` | NEW — Phase 4 pivot (Pushshift + LLM) | DONE |
| `data/subreddit_descriptions_20260722_201742.json` | combined 89 + 80 = 169 entries | DONE |
| `app/tests/test_subreddit_loader.py` | NEW — 4 regression tests | DONE (4/4 pass) |

---

## Rollback

- Phase 3 edits: `git checkout scripts/fetch_subreddit_descriptions.py`. (The old v1 code was already broken — every request 403s — so reverting loses nothing functional.)
- Phase 1 outputs: `rm docs/ideation/reddit/pushshift_candidate_{subreddits.md,candidates.json}`. Loader is untouched; existing 87-sub JSON still wins.
- Once Phase 4 lands: delete the new `data/subreddit_descriptions_<ts>.json` — loader falls back to the smallsample file automatically.

---

## Related Traces

- `2026-07-15_pushshift-rename-and-dataset-cards.md` — establishes the 11.26M-row / 241,466-subreddit ground truth this work queries against.
- `2026-07-16_client-level-429-circuit-breaker.md` — the production log cited there confirms the IPVanish SOCKS5 proxy was the live Reddit path; its auth failure here is a credentials issue, not a code regression.
- `2026-04-16_socks5-proxy-reddit-waf-fix.md` — original proxy setup for bypassing the Reddit WAF on data-center IPs.
