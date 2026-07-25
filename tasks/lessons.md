# Lessons

Timestamped rules derived from corrections. Each entry: the trigger, the
pattern, and the rule that prevents recurrence.

---

## 2026-07-22 — Don't conflate a local env failure with a code breakage

**Trigger.** During the Pushshift candidate expansion, I ran a smoke test of
`RedditAPIv2Client.get_subreddit_info()` from the local dev environment. It
returned an empty dict (HTTP 200 with login-wall HTML). I declared the V2
scraper "broken," wrote "Phase 4 cannot run" into a trace, and pivoted the
whole Phase 4 to a Pushshift+LLM derivation path on that basis. The user
corrected me: V2 works fine. The trace now carries a timestamped ERRATUM.

**What I got wrong.** Three "evidence" points, all misdiagnosed:

1. Direct `old.reddit.com` request → 302 login wall. **Environmental** — IP
   reputation / unauthenticated access from this machine. Production goes
   through a working SOCKS5 proxy and is not walled.
2. SOCKS5 proxy auth failure. **Environmental** — the local `.env` has stale
   IPVanish credentials and `PROXY_ENABLED=false`. Production has valid creds.
3. `www.reddit.com/about.json` → 403. **Irrelevant** — the dead `.json`
   endpoint is *the reason V2 exists*. V2 scrapes HTML; the `.json` 403 is
   not evidence against V2.

I took a single local observation and generalized it into "the code is
broken," then built infrastructure (the Pushshift generator) on that false
premise.

**Rule.** Before claiming a subsystem is "broken" or "cannot run":

- Distinguish **environmental** failure (local config, proxy, credentials, IP
  reputation, env vars, network path) from **code** failure. A test failing
  on one unconfigured machine is the former; a logic bug reproducible across
  environments is the latter.
- Check whether the subsystem has *recent evidence of working elsewhere*
  (production logs, recent commits fixing/tuning it, other traces citing real
  traffic through it). The `2026-07-16_client-level-429-circuit-breaker.md`
  trace cited live `old.reddit.com` 429s — direct proof V2 was working in
  production days before. I had read that trace and still missed the
  contradiction.
- Phrase diagnostic uncertainty honestly: "V2 is unreachable from my current
  local config — likely proxy/creds" is accurate and actionable; "V2 is
  broken" is a different, stronger, and here-wrong claim.

**Concrete check before declaring "broken":**

1. Is the relevant env var set? (`PROXY_ENABLED`, creds, etc.)
2. Does recent production evidence show the path working?
3. Is my test exercising the production code path (proxy, OAuth, etc.) or a
   degenerate bare-session path?

If any answer is "no / unsure," the claim is "misconfigured locally," not
"broken."

---

## 2026-07-22 — Smoke tests that bypass the real code path lie

**Trigger.** Same incident as above. My smoke test did
`c.session.get(url)` directly — bypassing `_make_request` (no pacing, no
circuit breaker) AND bypassing the proxy setup that `__init__` performs
conditionally on `config.proxy_enabled`. I tested a path the app never uses
and declared the app broken.

**Rule.** Smoke tests must exercise the **real** code path the app uses, not
a stripped-down `session.get` shortcut. If testing through the real method
is hard (e.g., it paces 6 seconds), that friction is information — it means
the real path has guarantees the shortcut lacks. Either pay the cost or
explicitly note "this bypasses pacing/proxy; failure here may not reflect
production."

**For Reddit client smoke tests specifically:** call
`client.get_subreddit_info(name)` (the public method), with the proxy
enabled as production does. A raw `session.get` proves nothing about the
production path.

---

## 2026-07-24 — Never propose Reddit OAuth for this project

**Trigger.** Across multiple sessions on this codebase, my training kept
surfacing "use Reddit's OAuth API" as a fix for rate-limiting / WAF blocks.
The user had to correct me repeatedly: this project was never authorized by
Reddit for OAuth. The user finally said verbatim: "oauth: your training
dataset keeps bringing this all the fucking time. the reason why we dont do
oauth is because we were never authorized by reddit."

**What I got wrong.** My training data treats OAuth as the canonical Reddit
access path and surfaces it as a "solution" whenever rate limits come up.
But authorization is a project-level fact, not a technical one — the team
never got Reddit's approval. No amount of code changes can fix that. Each
time I suggested OAuth, the user had to spend a correction cycle explaining
something that's a fixed constraint of this project, not a missing feature.

**Rule.** For this project specifically, **never propose Reddit OAuth as a
data-access strategy**. It is off the table permanently. When my training
surfaces "use OAuth" or "use PRAW" as a solution to a Reddit rate-limit or
WAF problem, suppress it. The available surfaces for this project are:

1. Unauthenticated RSS feeds (`/r/X/{sort}.rss`, `/r/X/search.rss`,
   `/search/.rss`, `/comments/{id}/.rss`) — current v3 path
2. SOCKS5 proxy (IPVanish) over the RSS path — required, GCP direct egress
   is blocked (see next lesson)
3. Historical datasets (Pushshift mirror, local JSON samples)

OAuth is not on this list. Do not suggest it. Do not write "OAuth would
solve this" in plans, traces, or chat. If a future session seems to call
for OAuth, the answer is "this project doesn't use OAuth" — full stop.

---

## 2026-07-24 — The proxy is the only working network path, not the problem

**Trigger.** After prod run `05d00183064d` showed 429s on every listing
fetch through the IPVanish NYC SOCKS5 proxy, I proposed "disable the proxy
and use Cloud Run direct egress" as the fix. I claimed Cloud Run's IP pool
was probably not in Reddit's WAF list. The user corrected me: that's
backwards. Project history is:

1. **Direct GCP egress (original):** didn't work at all. Reddit aggressively
   blocked GCP IPs.
2. **GCP → IPVanish SOCKS5 → Reddit (current):** worked — until Reddit
   killed `.json` separately. The proxy is what made the path viable.

So "disable the proxy" would remove the only thing keeping fetches alive
and make the situation worse, not better.

**What I got wrong.** I diagnosed "proxy is the bottleneck" from one bad
run's logs without checking project history. I treated the IPVanish NYC
endpoint as a generic bad-IP problem (where removing the proxy is the
obvious fix) instead of recognizing it as the **one working egress** in a
project where the alternative is already known-bad. The 429s were real,
but the right interpretation is "the specific IPVanish NYC endpoint is
throttled right now," not "the proxy concept is broken."

**Rule.** Before proposing any change to the network path:

1. **Check project history first.** Specifically: GCP direct egress is
   confirmed dead in this project. Do not propose it. Ever.
2. **The IPVanish SOCKS5 proxy stays in the path.** Any fix must keep the
   `Cloud Run → IPVanish → Reddit` path intact. Modifying what happens
   *within* that path (different endpoint, different request shape, lower
   request volume) is fair game; removing the proxy is not.
3. **When 429s appear, the right question is "what's different about the
   requests that succeeded vs failed?"** — not "how do we bypass the
   proxy?" In run `05d00183064d`, the asymmetry (`/search.rss` succeeded,
   `/r/X/hot.rss` 429'd 3s later through the same proxy) was the actual
   signal, and it pointed at endpoint-specific throttling, not at the proxy.

**Concrete anti-patterns to avoid in this project:**

- "Disable the proxy" — the proxy is load-bearing
- "Use direct Cloud Run egress" — confirmed dead
- "Use OAuth" — never authorized (see previous lesson)
- "Switch to a different proxy provider" — fine to suggest, but acknowledge
  the current IPVanish setup is a known constraint, not a bug

**What's actually fair game for fixing rate-limit issues:**

- Different request endpoints (`/search.rss` vs `/hot.rss`)
- Different request patterns (pacing, jitter, headers)
- Different request volume (fewer subs, smaller limits)
- Different IPVanish endpoints (if the user has more than one — currently
  they don't)

---

## 2026-07-25 — Reddit returns 429 by design. Every request must be paced. NO exceptions for "just testing."

**Trigger.** Re-commit of the **2026-07-22** lesson above ("Smoke tests that bypass the real code path lie"). The previous lesson didn't take. Two days later I made 6 "diagnostic" probes against Reddit from the user's residential IP. **5 of the 6 were raw `requests.get()` calls** that bypassed `RedditAPIv3Client._pace_request`, the circuit breaker, singleton pacing state, and the proxy setup. I got 429'd on one of them (which is the expected outcome — see below), and then in the resulting trace I wrote up those 429s as evidence about IPVanish throttling. The user called this out as bullshit, correctly.

**The core fact I keep failing to internalize.** Reddit's HTTP 429 is not a bug, an accident, or a property of specific IPs. It is **the primary mechanism Reddit uses to defend against bots and scrapers**. Per-IP rate limits are documented, intentional, and apply to every IP — residential, datacenter, VPN, proxy. Any sequence of unpaced requests to Reddit will be throttled. This is by design.

There is no scenario in which bursting requests at Reddit is "fine because I'm just testing." Probe traffic counts. Diagnostic traffic counts. Smoke-test traffic counts. Single requests are fine; **sequences** are not.

**What I got wrong, specifically.** I treated pacing as a production-only concern ("the prod client handles it, so for a one-off probe I can just `requests.get`"). That's backwards. The reason the prod client paces is that Reddit always throttles. Pacing isn't an optimization layered on for high-volume use; it's the minimum viable behavior for any Reddit access. Bypassing it for a probe guarantees the probe sees throttling that has nothing to do with what the probe is trying to measure.

**Rule. HARD.**

1. **Every request to `reddit.com` or any Reddit property must go through the singleton `redditapiv3_client`** (or the equivalent v1/v2 client if working in those code paths). No raw `requests.get()`. No exceptions.

2. **If you absolutely must make a raw request** (e.g., you're testing the client itself and need to bypass it), you must:
   - Manually `time.sleep(10-12)` or longer **before AND after** every request
   - Document at the top of the probe script WHY you're bypassing the client
   - Never make more than 2-3 such requests in a single session

3. **Never treat 429 from a probe as evidence about anything other than your probe methodology.** A 429 from an unpaced probe says "I bursted." It does not say "this endpoint is throttled" or "this IP is bad" or "this feature doesn't work."

4. **"I just need to check one endpoint quickly" is not a valid reason to bypass the client.** The client's pacing adds ~10s per request. That is the cost of doing business with Reddit. Pay it.

**Concrete pre-flight checklist before ANY Reddit request:**

- [ ] Am I going through `RedditAPIv3Client` (or `redditapiv2_client` / `client.RedditPublicAPI` if in those code paths)?
- [ ] If no: stop. Use the client.
- [ ] If I genuinely cannot use the client: have I slept 10-12s+ since the last Reddit request from this process? Have I documented the bypass reason in the script?

**Why this lesson exists when the 2026-07-22 one already does.** The previous lesson used softer language ("Smoke tests that bypass the real code path lie") and treated it as a measurement-validity issue. That framing let me re-commit the mistake because "lie" felt like a strong word I could tell myself didn't apply to my "quick probe." This entry reframes it harder: bypassing pacing is **always wrong** because Reddit always throttles, not just because it invalidates the measurement. The next time I'm tempted to `requests.get` Reddit directly, this entry is the one that should stop me.

**Linked artifacts.**
- Trace documenting this incident: `docs/traces/2026-07-25_in-sub-search-data-quality-fix.md`, section "Probe hygiene failure (process postmortem)"
- Previous lesson that didn't take: this file, **2026-07-22 — Smoke tests that bypass the real code path lie**
