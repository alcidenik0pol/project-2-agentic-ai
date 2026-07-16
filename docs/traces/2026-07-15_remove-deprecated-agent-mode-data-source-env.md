# Trace: Remove Deprecated `agent_mode` / `DATA_SOURCE` Env Var

**Date:** 2026-07-15
**Status:** Done

---

## Problem

The app carried two redundant, stale mechanisms for choosing a data source:

1. **`agent_mode`** (`"test"` / `"live"`) — a deprecated field with **no conditional logic reading it**. `fetch.py` routed purely on `data_source`. `agent_mode` survived only as display text (banners, reports, folder names) and stale env hints.
2. **`DATA_SOURCE` env var** — superseded for the web flow. The frontend dropdown already drives the full chain: `AnalysisContext → POST {data_source} → AnalysisRequest → set_data_source_override(run.data_source) → get_data_source()` in `fetch.py`. The env var was only a fallback, never consulted for web requests.

A latent CLI bug came along with this: `scripts/run_agent.py` exposed only `--mode test|live`, and `--mode live` silently ran with `data_source=sample_default` — the flag did nothing.

---

## Fix

Deleted the dead code and made the data-source override the single source of truth.

- **Frontend dropdown** stays the single driver for the web flow (unchanged wiring via `set_data_source_override`).
- **CLI** gets a real `--data-source` flag with the 6 `DataSource` values.
- **`get_data_source()`** fallback changed from the removed `config.data_source` to the existing `DEFAULT_DATA_SOURCE = "arcticshift"` constant.
- The override mechanism (`_data_source_override` / `set_data_source_override` / `get_data_source`) is **kept** — it is what makes the dropdown work.

### What was removed from `app/config.py`

- `Config.agent_mode` field + `AGENT_MODE` env loading
- `Config.data_source` field + `DATA_SOURCE` env loading
- `_agent_mode_override`, `set_agent_mode_override()`, `get_agent_mode()` (entire block)

### What was kept

- `DEFAULT_DATA_SOURCE = "arcticshift"` constant
- `DataSource` type alias
- `_data_source_override` / `set_data_source_override` / `get_data_source`

---

## Files Modified

| File | Change |
|------|--------|
| `app/config.py` | Core removal: `agent_mode` + `data_source` fields, env loading, `_agent_mode_override`/`set_agent_mode_override`/`get_agent_mode` block; `get_data_source()` fallback → `DEFAULT_DATA_SOURCE` |
| `backend/app/main.py` | Banner: `Mode: {config.agent_mode}` → `Source: {get_data_source()}` |
| `backend/app/services/analysis_service.py` | Dropped `get_agent_mode` import + stale `AGENT_MODE` comment; error/success reports now read `**Data source:** {run.data_source}` (per-run value, more correct than the global) |
| `scripts/run_agent.py` | `--mode test|live` → `--data-source <6 choices>` (default `sample_default`); `_make_run_dir(mode)` → `_make_run_dir(data_source)`; banner + report updated |
| `scripts/test_langgraph_integration.py` | `set_agent_mode_override("test")` → `set_data_source_override("sample_default")` |
| `scripts/test_agent_imports.py` | Diagnostic now prints `data_source={get_data_source()}` |
| `.env.example` | Deleted `# AGENT_MODE=test ...` line |
| `deploy-env.yaml` | Deleted `AGENT_MODE: "live"` |
| `README.md` | Replaced `# === Agent Mode ===` block + config-knobs table row with the dropdown/CLI mechanism |
| 11 module headers + `fetch.py` (6 spots) | `# Used when: config.data_source == "..."` → `# Used when: get_data_source() == "..."` (comment-only) |

---

## Pattern: Let the Override Mechanism Be the Single Source of Truth

This is a continuation of the `2026-04-15_frozen-config-mode-override` → `2026-04-18_report-mode-mismatch-fix` arc. Those traces introduced `get_agent_mode()` / `get_data_source()` to work around the frozen-config-singleton problem, then chased down the call sites that still read the field directly.

The leftover problem was that the **field itself** (`Config.agent_mode`, `Config.data_source`) and its **env var** (`AGENT_MODE`, `DATA_SOURCE`) were never pruned. They sat in `config.py` as plausible-looking fallbacks that were in fact dead for the web flow and actively misleading for the CLI (the `--mode` flag appeared to do something it didn't).

The lesson: once a runtime override mechanism is the real driver, grep is not enough — you must also **delete the superseded field and env var**, or they keep generating "but why doesn't setting this work?" tickets. Dead config knobs are a liability, not a safety net. When pruning, the constant default (`DEFAULT_DATA_SOURCE`) is the only fallback the getter needs.

---

## Out of Scope / Known Caveats

- **`backend/api/` left as-is.** After removal, 3 refs dangle there (`backend/api/main.py:36`, `backend/api/project_imports.py:54`, `backend/api/services/analysis_service.py:231`). These are **inert** — nothing imports `backend/api/`, so the live app is unaffected. Follow-up: clean when the WIP refactor resumes.
- **`docs/traces/*.md` left as-is** — historical timestamped records (including this one's predecessors). They document past work and should not be rewritten.
- **Concurrency (deferred):** `_data_source_override` is a bare module global. Two overlapping web requests could clobber each other's data source. Acceptable for the single-user demo (Cloud Run `max-instances=1`); track separately. Candidate fix: `contextvars`.

---

## Verification

1. **Import sanity** — `assert not hasattr(config, 'agent_mode'); assert not hasattr(config, 'data_source')` passes; `get_data_source()` returns `arcticshift`.
2. **Grep clean** — zero hits for `agent_mode` / `AGENT_MODE` / `get_agent_mode` / `config.data_source` in `app/`, `backend/app/`, `scripts/`, `.env.example`, `deploy-env.yaml`, `README.md`. Remaining hits are only the inert `backend/api/` and these historical traces.
3. **CLI** — `--help` shows `--data-source` with the 6 choices; old `--mode live` is correctly rejected as `unrecognized arguments`.
4. **`scripts/test_langgraph_integration.py`** — 8/8 pass.
5. **`scripts/test_agent_imports.py`** — 9/9 pass (config diagnostic now prints `data_source=arcticshift`).
6. **pytest `app/tests/`** — 20 passed; 2 failed (`test_reddit_api_connection`, `test_search_function`) due to pre-existing Reddit WAF 403 blocks on live-API tests — unrelated to this change.
7. **Full CLI run + web end-to-end** — not run here (require LLM credentials). The arg-parsing and import paths they exercise are already verified above.
