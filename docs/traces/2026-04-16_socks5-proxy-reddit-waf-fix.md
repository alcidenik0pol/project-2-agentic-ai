# Trace: SOCKS5 Proxy for Reddit WAF 403 Fix

**Date:** 2026-04-16
**Trigger:** Reddit API returns 403 Forbidden from Google Cloud Run data center IPs. All post collection fails in production (0 posts), while identical code works locally.

---

## Problem

Reddit's WAF blocks requests from Google Cloud data center IPs when using the unauthenticated public JSON API. Every request returns:

```
403 Client Error: Blocked for url: https://www.reddit.com/r/.../hot.json
```

**Evidence:**
- Local (residential IP): 200 OK, posts collected normally
- Cloud Run (data center IP): 403 Forbidden, 0 posts collected
- Same code, same configuration, same user agent
- Only difference: source IP address

```
┌─────────────────────────────────────────────────────────────────┐
│  Local Machine (Residential IP)                                 │
│  → Public JSON API → Generic User-Agent → 200 OK                │
│                                                                  │
│  Docker/Cloud Run (Data Center IP)                              │
│  → Public JSON API → Generic User-Agent → 403 Forbidden (WAF)   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Solution

Route all Reddit API requests through an IPVanish SOCKS5 proxy to use residential-class IP addresses instead of Google Cloud's data center IPs.

**Proxy details:**
- Protocol: SOCKS5h (DNS resolution through proxy)
- Server: `nyc.socks.ipvanish.com:1080`
- Credentials stored in Google Secret Manager

---

## Files Modified

| File | Change |
|------|--------|
| `requirements.txt` | Changed `requests>=2.31.0` to `requests[socks]>=2.31.0` (installs PySocks) |
| `backend/requirements.txt` | Same change for Docker image |
| `app/config.py` | Added `proxy_enabled: bool` and `proxy_url: str | None` fields + `from_env()` loading |
| `app/reddit/client.py` | Added proxy configuration to `requests.Session` when enabled |
| `.env` | Added `PROXY_ENABLED=true` and `PROXY_URL=socks5h://...` |
| `deploy-env.yaml` | Added `PROXY_ENABLED: "true"` with placeholder for PROXY_URL |

---

## Implementation Details

### Config (`app/config.py`)

Added two fields to the `Config` dataclass:

```python
# Proxy settings (for bypassing Reddit WAF blocks on data center IPs)
proxy_enabled: bool = False
proxy_url: str | None = None
```

Loaded from environment in `from_env()`:

```python
proxy_enabled=os.getenv("PROXY_ENABLED", "false").lower() == "true",
proxy_url=os.getenv("PROXY_URL"),
```

Defaults to disabled — no proxy when env vars are unset (backward compatible).

### Reddit Client (`app/reddit/client.py`)

Proxy applied at session level in `__init__()`:

```python
if config.proxy_enabled and config.proxy_url:
    self.session.proxies = {
        "http": config.proxy_url,
        "https": config.proxy_url,
    }
    logger.info(f"[PROXY] Enabled: {config.proxy_url}")
```

This applies the proxy to **all** requests made through the session — `get_subreddit_posts()`, `get_post_comments()`, `search_posts()`, etc. No per-method changes needed.

### Why `socks5h` not `socks5`

The `h` suffix means DNS resolution also goes through the proxy. Without it, DNS queries leak the real IP (Google Cloud data center) which can trigger WAF blocks even though the HTTP connection uses the proxy.

---

## Production Deployment

### Google Secret Manager

Created two secrets:

```bash
echo -n "socks5h://user:pass@nyc.socks.ipvanish.com:1080" | \
  gcloud secrets create proxy-url --data-file=- --replication-policy=automatic

echo -n "true" | \
  gcloud secrets create proxy-enabled --data-file=- --replication-policy=automatic
```

### Cloud Run

Mounted secrets as env vars on `painpan-backend`:

```bash
gcloud run services update painpan-backend --region=us-central1 \
  --set-secrets="PROXY_URL=proxy-url:latest,PROXY_ENABLED=proxy-enabled:latest"
```

Deployed as revision `painpan-backend-00009-m4x`.

### `deploy-env.yaml` Security

The tracked `deploy-env.yaml` uses a placeholder value for `PROXY_URL` instead of real credentials:

```yaml
PROXY_URL: "REPLACE_WITH_SECRET"  # Set via: gcloud run services update --set-secrets=...
```

Actual credentials live only in Secret Manager and `.env` (gitignored).

---

## Verification

### Local Proxy Test

```python
proxies = {
    "http": "socks5h://user:pass@nyc.socks.ipvanish.com:1080",
    "https": "socks5h://user:pass@nyc.socks.ipvanish.com:1080",
}
response = requests.get("https://www.reddit.com/r/gaming/hot.json?limit=5",
                        proxies=proxies, timeout=30)
# Result: Status 200, 5 posts fetched
```

### End-to-End via RedditPublicAPI

```python
from app.reddit.client import RedditPublicAPI
api = RedditPublicAPI()  # loads config with PROXY_ENABLED=true
posts = api.get_subreddit_posts("gaming", limit=3)
# Result: 3 posts fetched successfully through proxy
```

### Config Loading

```python
from app.config import config
print(config.proxy_enabled)   # True
print(config.proxy_url)       # socks5h://...
```

---

## Known Risk: IPVanish IPs May Still Be Blocked

IPVanish uses well-known VPN data center IPs. Reddit may still block them.

**Fallback strategy if proxy is also blocked:**
1. Run collection locally through proxy (residential IP + proxy = less suspicious)
2. Cache results to database or Cloud Storage
3. Deployed app reads from cache instead of hitting Reddit live

This hybrid approach ensures the deployed app always has data, even if Reddit blocks all proxy IPs.

---

## Lessons Learned

1. **Reddit WAF blocks by IP class, not just behavior** — Even well-paced, single-request-per-6-seconds access gets blocked from data center IPs. The WAF fingerprinting is IP-reputation based.
2. **`socks5h` vs `socks5` matters** — Without the `h`, DNS leaks the real IP. Always use `socks5h` when the proxy's purpose is IP masking.
3. **Session-level proxy is cleaner than per-request** — Setting `session.proxies` once in `__init__()` covers all methods automatically, no risk of forgetting to pass proxies on a new endpoint.
4. **Test proxy before full implementation** — The plan wisely called for testing the proxy first. If it had returned 403, we would have skipped straight to the cache fallback.
5. **`conda run` doesn't support newlines in arguments** — On Windows, `conda run -n env python -c "..."` fails if the script string contains newlines. Write to a temp file and run that instead.
6. **`gcloud` output can be swallowed in some terminal environments** — On Windows/MSYS2, some gcloud commands produce no visible output when called without the full path. Use the full `gcloud.cmd` path for reliable output.
