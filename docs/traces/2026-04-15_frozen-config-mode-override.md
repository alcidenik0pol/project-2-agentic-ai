# Trace: Live Mode Config Override (Frozen Singleton Fix)

**Date:** 2026-04-15
**Status:** Done

---

## The Problem

The pipeline always ran in test mode even when "live" was requested from the API. The assessment of run `195637_live` showed:
- Directory named `_live` (from the API request)
- But `fetch_stats.json` showed `"mode": "test"`, `"source": "data/sample_posts.json"`
- Subreddit selection was skipped entirely

---

## Root Cause

`Config` is a frozen dataclass singleton created at module import time (`app/config.py:178`):

```python
@dataclass(frozen=True)
class Config:
    agent_mode: str = "test"

config = Config.from_env()  # Created once at import, frozen forever
```

When the FastAPI backend starts, it imports `app.config`, which creates and freezes the singleton with `agent_mode="test"` (the default).

Later, when a "live" request comes in, `analysis_service.py` tried to override it:

```python
os.environ["AGENT_MODE"] = run.mode  # Sets env var
# ... later ...
from app.config import config  # Returns the ALREADY-FROZEN singleton
```

Setting `os.environ["AGENT_MODE"]` has no effect because:
1. The config singleton was already created at FastAPI startup
2. `from app.config import config` returns the cached module-level singleton
3. `frozen=True` prevents mutation anyway

---

## Solution

Add a runtime override mechanism to `config.py` that bypasses the frozen singleton:

```python
# Module-level override (checked before the frozen singleton)
_agent_mode_override: str | None = None

def set_agent_mode_override(mode: str) -> None:
    global _agent_mode_override
    _agent_mode_override = mode

def get_agent_mode() -> str:
    return _agent_mode_override or config.agent_mode
```

Then use `get_agent_mode()` instead of `config.agent_mode` wherever the mode is read at runtime.

---

## Files Changed

### Modified: `app/config.py` — Added override functions

Added `set_agent_mode_override()` and `get_agent_mode()` after the singleton (lines 180-196).

### Modified: `app/agents/tools/fetch.py` — Use override-aware getter

```python
# BEFORE:
from app.config import config
# ...
mode = config.agent_mode

# AFTER:
from app.config import get_agent_mode
# ...
mode = get_agent_mode()
```

### Modified: `backend/app/services/analysis_service.py` — Use override instead of env var

```python
# BEFORE:
os.environ["AGENT_MODE"] = run.mode

# AFTER:
from app.config import set_agent_mode_override
set_agent_mode_override(run.mode)
```

Also removed unused `import os`.

### Modified: `scripts/run_agent.py` — Consistent override mechanism

```python
# BEFORE:
if args.mode:
    import os
    os.environ["AGENT_MODE"] = args.mode

# AFTER:
if args.mode:
    from app.config import set_agent_mode_override
    set_agent_mode_override(args.mode)
```

Also updated `_make_run_dir()` call to use `get_agent_mode()` instead of `config.agent_mode`.

---

## Key Design Decisions

1. **Module-level variable, not frozen mutation** — `frozen=True` is a useful guarantee for all other config fields. Adding a separate override variable is less invasive than removing `frozen=True`.
2. **Only `agent_mode` gets an override** — This is the only field that needs runtime switching (test vs live). Other fields don't need this pattern.
3. **`get_agent_mode()` returns override OR config** — If no override is set, it falls back to the frozen singleton value. This means the `.env` default still works.
4. **Removed dead `os.environ` approach** — The old env var override was never working (in the API path). Replaced it entirely.

---

## Verification

1. Start the FastAPI backend
2. Submit an analysis request with `"mode": "live"`
3. Confirm `fetch_stats.json` shows `"mode": "live"` and actual Reddit data
4. Confirm subreddit selection runs (Call 8 in the LLM inventory)
