# Proxy Test Protocol

A structured 6-test sequence to verify the SOCKS5h proxy configuration end-to-end. Each test builds on the previous — if an earlier test fails, stop and fix that before continuing.

## Test 1: Raw Proxy Connectivity (No App Code)

```bash
conda run -n agentic-ai-p2 python -c "import requests; r = requests.get('https://www.reddit.com/r/gaming/hot.json?limit=1', proxies={'http':'socks5h://EdWv9jTcB:Wz3O4CBnCnS@nyc.socks.ipvanish.com:1080','https':'socks5h://EdWv9jTcB:Wz3O4CBnCnS@nyc.socks.ipvanish.com:1080'}, timeout=30); print(f'Status: {r.status_code}, Keys: {list(r.json().keys())[:3]}')"
```

**What it tests:** The minimum viable proxy test. Verifies the dependency chain (`requests[socks]` → PySocks → SOCKS5h protocol) works before involving any app code.

**If it fails:** The problem is credentials or network — not your code.

---

## Test 2: Config Loads Proxy from `.env`

```bash
conda run -n agentic-ai-p2 python -c "from dotenv import load_dotenv; load_dotenv(); from app.config import config; print(f'proxy_enabled={config.proxy_enabled}, proxy_url={\"***set***\" if config.proxy_url else None}')"
```

**What it tests:** The config flow at `app/config.py`. Validates that `PROXY_ENABLED` parses `"true"` → `True` and that `PROXY_URL` is loaded from `.env`.

**If it fails:** `.env` is missing or has wrong values.

---

## Test 3: `RedditPublicAPI` Session Has Proxy Attached

```bash
conda run -n agentic-ai-p2 python -c "from dotenv import load_dotenv; load_dotenv(); from app.reddit.client import RedditPublicAPI; api = RedditPublicAPI(); print(f'Session proxies: {api.session.proxies}')"
```

**What it tests:** That `app/reddit/client.py` correctly applies the proxy to `self.session.proxies`. The constructor reads the singleton `config` and sets both `"http"` and `"https"` keys.

**If it fails:** Config-to-session wiring is broken. If it prints `{}`, the proxy is silently not applied.

---

## Test 4: End-to-End Fetch Through the App Stack

```bash
conda run -n agentic-ai-p2 python -c "from dotenv import load_dotenv; load_dotenv(); from app.reddit.client import RedditPublicAPI; api = RedditPublicAPI(); posts = api.get_subreddit_posts('gaming', limit=3); print(f'Fetched {len(posts)} posts'); [print(f'  - {p[\"title\"][:60]}') for p in posts[:3]]"
```

**What it tests:** The full production path: `.env` → `Config.from_env()` → `RedditPublicAPI.__init__()` → `session.proxies` → `_pace_request()` → `_make_request()` → actual Reddit JSON endpoint. Includes pacing and retry strategy.

**If it fails:** Any issue in the full request pipeline.

---

## Test 5: Compare With Proxy Disabled (Baseline)

```bash
PROXY_ENABLED=false conda run -n agentic-ai-p2 python -c "from dotenv import load_dotenv; load_dotenv(); from app.reddit.client import RedditPublicAPI; api = RedditPublicAPI(); print(f'Session proxies: {api.session.proxies}')"
```

**What it tests:** The opt-in default (`proxy_enabled: bool = False`) and the guard in the client constructor. Verifies that without the env var, the session has no proxies — confirming backward compatibility.

**If it fails:** Backward compatibility regression.

---

## Test 6: Verify `socks5h` (Not `socks5`) — DNS Leak Check

```bash
conda run -n agentic-ai-p2 python -c "import socket; import socks; s = socks.socksocket(); s.set_proxy(socks.SOCKS5, 'nyc.socks.ipvanish.com', 1080, True, 'EdWv9jTcB', 'Wz3O4CBnCnS'); s.connect(('www.reddit.com', 443)); print(f'Remote IP via proxy: {s.getpeername()}'); s.close()"
```

**What it tests:** DNS resolution goes through the proxy (the `h` in `socks5h`). The `True` parameter in `set_proxy` enables remote DNS resolution. Without it, Reddit's WAF could see the DNS query origin and block even though the HTTP connection uses the proxy.

**If it fails:** DNS leak to real IP — the proxy URL uses `socks5` instead of `socks5h`.

---

## Summary

| # | What it tests | Code path | If it fails, the problem is |
|---|---------------|-----------|----------------------------|
| 1 | Raw proxy connectivity | PySocks → IPVanish | Credentials or network |
| 2 | Config loads env vars | `config.py` env parsing | `.env` missing or wrong values |
| 3 | Session gets proxy | `client.py` constructor | Config-to-session wiring broken |
| 4 | Full fetch through stack | `client.py` entire pipeline | Any issue in the full path |
| 5 | Proxy is opt-in default | `config.py` default, `client.py` guard | Backward compat regression |
| 6 | DNS resolution through proxy | `socks5h` protocol | DNS leak to real IP |
