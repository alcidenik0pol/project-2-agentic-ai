# Trace: Reddit API Shutdown — Data Access Request Submitted

**Date:** 2026-05-29
**Trigger:** Reddit deprecated the public JSON API (`reddit.com/r/*/hot.json`). All post collection now fails with 403/410 errors regardless of proxy or IP.

---

## Problem

Reddit shut down public unauthenticated API access. The `.json` suffix endpoints that powered our data collection no longer work:

```
GET https://www.reddit.com/r/espresso/hot.json
→ 403 Forbidden / 410 Gone
```

This affects all data collection — the core functionality of the app is blocked.

**Timeline:**
- Previously: Public JSON API worked (with WAF bypass via SOCKS5 proxy)
- Now: All public endpoints return 403/410 — no workaround exists

---

## Root Cause

Reddit's API policy change. They now require OAuth app registration and explicit data access approval for all API usage, including read-only access to public posts.

This is not a WAF block or rate limit — it's a policy enforcement. No proxy or IP rotation will bypass it.

---

## Solution: Apply for Reddit Data Access

Submitted a Data Access Request through Reddit's official form.

**Application details:**
- **Role:** Developer (educational project)
- **Platform:** Devvit not applicable (external cross-subreddit analysis tool)
- **Use case:** Columbia University graduate course project
- **Access type:** Read-only (GET endpoints only)
- **Volume:** Low (~10-20 queries total over semester)
- **Source code:** https://github.com/alcidenik0pol/project-2-agentic-ai

**Key points emphasized in application:**
1. Non-commercial educational use
2. Read-only — never posts, comments, or modifies content
3. Low volume with local caching
4. Every finding links back to original Reddit posts (attribution)
5. External analysis tool that doesn't fit Devvit's architecture

---

## Files Created

| File | Purpose |
|------|---------|
| `docs/ideation/reddit/20260529 apichanges/questionnaire.md` | Original form questions |
| `docs/ideation/reddit/20260529 apichanges/questionnaire-answers.md` | Copy-paste answers for submission |

---

## Current Status

**Waiting for Reddit response.**

Possible outcomes:
1. **Approved** → Receive OAuth credentials, update `app/reddit/client.py` to use authenticated endpoints
2. **Denied** → Need alternative data source (cached data, different platform, or pivot project scope)
3. **No response** → Follow up in 1-2 weeks

---

## Fallback Options (if denied)

1. **Pre-cached dataset**: Run collection locally one time, ship static data with the app
2. **Alternative platform**: Switch to Hacker News API (public, no auth required) or Twitter/X API
3. **Hybrid**: Use Reddit data already collected in previous runs, supplement with live HN data

---

## Next Steps

1. Wait for Reddit response (typically 3-7 business days)
2. If approved: implement OAuth flow in `app/reddit/client.py`
3. If denied: evaluate fallback options above

---

## Lessons Learned

1. **Platform APIs can disappear without warning** — Even established patterns (Reddit's `.json` suffix) are not guaranteed to persist. Always have a fallback data source.
2. **Educational/non-commercial framing matters** — Reddit's form explicitly asks about purpose. Being transparent about student status and low-volume usage improves approval odds.
3. **Devvit is Reddit's preferred path** — They push all developers toward Devvit first. External apps need explicit justification for why Devvit doesn't work.
