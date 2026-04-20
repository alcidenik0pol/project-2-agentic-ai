# Trace: Report Mode Mismatch Fix

**Date:** 2026-04-18
**Status:** Done

---

## Problem

The generated `report.md` always showed `**Mode:** test` even when scraping was enabled and the run directory was correctly named `184716_live`. The mode override was working for data fetching (see trace `2026-04-15_frozen-config-mode-override.md`) but the report generation still read the frozen config default.

Example of the bug:
- Run directory: `output/reports/2026-04-18/184716_live/`
- `fetch_stats.json`: `"mode": "live"` (correct, Reddit API was called)
- `report.md`: `**Mode:** test` (wrong)

---

## Root Cause

The frozen config override mechanism (`get_agent_mode()`) was added in the earlier trace but only applied to the fetch tool. The report generation in two locations still used `config.agent_mode` directly:

1. **`scripts/run_agent.py:110`** — CLI report generation
2. **`backend/app/services/analysis_service.py:320, 336`** — API error report and success report generation

All three locations had:
```python
f"**Mode:** {config.agent_mode}\n"
```

Since `config` is a frozen dataclass created at import time with `agent_mode="test"` (the default), this always produced "test" regardless of the runtime override set by `set_agent_mode_override()`.

---

## Fix

Changed all three report generation sites to use the override-aware getter:

```python
# Before
f"**Mode:** {config.agent_mode}\n"

# After
f"**Mode:** {get_agent_mode()}\n"
```

---

## Files Modified

| File | Line(s) | Change |
|------|---------|--------|
| `scripts/run_agent.py:110` | Report generation | `config.agent_mode` -> `get_agent_mode()` |
| `backend/app/services/analysis_service.py:216` | Import | Added `get_agent_mode` to import from `app.config` |
| `backend/app/services/analysis_service.py:320` | Error report | `config.agent_mode` -> `get_agent_mode()` |
| `backend/app/services/analysis_service.py:336` | Success report | `config.agent_mode` -> `get_agent_mode()` |

---

## Pattern: Incomplete Override Adoption

This is a follow-up to the `2026-04-15_frozen-config-mode-override` trace. That trace introduced `get_agent_mode()` and updated the fetch tool, but missed the report generation paths. The lesson: when introducing a getter function to replace direct field access, grep for **all** usages of the old pattern (`config.agent_mode`) and replace them, not just the one that was obviously broken at the time.

Other remaining `config.agent_mode` usages (startup banners, logging) are acceptable because they execute before any runtime override is set.

---

## Verification

1. Run a live analysis with scraping enabled
2. Check `report.md` shows `**Mode:** live`
3. Run with scraping disabled (test mode)
4. Check `report.md` shows `**Mode:** test`
