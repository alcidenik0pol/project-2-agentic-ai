# Trace: Rename `arcticshift` → `pushshift` + Single-Source-of-Truth Dataset Cards

**Date:** 2026-07-15
**Status:** Done

---

## Problem

Two issues surfaced during a `/how-it-works` page review.

### 1. The dataset card had drifted from the truth

The "Dataset Composition" table for the historical Parquet source claimed **~241,000 submissions**. The actual number is **11,263,400 submissions across 241,466 distinct subreddits**. The old figure had confused *distinct subreddits* with *submissions* — off by ~46×.

A second drift: `sample_gaming` claimed **5 gaming subreddits**. The data file (`data/smallsample/gaming_test_20260416_105527.json`) actually has **4** (r/gaming, r/indiegaming, r/patientgamers, r/pcgaming, 36 posts total).

These numbers were duplicated across three places that could independently drift:
- `SOURCE_CONTENT` intro string
- `SOURCE_CONTENT.preprocessingCard` body
- `DATASET_COMPOSITION` row table

### 2. The source identifier was a misnomer

Internally the source was named `arcticshift`. The actual upstream is `fddemarco/pushshift-reddit` on HuggingFace — a single-shard Parquet of January 2018 Pushshift data. "Arctic Shift" is a *different*, much larger HF dataset (`RoyalFortune24/The-Arctic-Shift`) that this repo does not use.

---

## Fix

Two coordinated changes.

### A. Single source of truth: `frontend/lib/datasets.ts`

Created one `DatasetCard` per `DataSource`. Each card carries:
- `facts: DatasetFact[]` — the composition table rows (source/vintage/size/subreddits/queryMethod/comments/cache)
- `subredditGroups: SubredditGroup[]` — actual subreddits in the dataset (empty array = too many to enumerate)
- `subredditBlurb` — scope note above the subreddit list
- `dropdownLabel`, `description`, `shortLabel` — UI strings

`frontend/lib/data-sources.ts` was rewritten to **derive** the dropdown options from `DATASET_CARDS`. The how-it-works page renders the composition table and subreddit list straight from the selected card. Numbers now live in exactly one place per dataset.

Both previously-hidden sections (**Dataset Composition** and **Subreddits**) are now **always visible**, regardless of source. The old toggle was removed.

### B. Code + UI rename: `arcticshift` → `pushshift`

Identifier changed in:
- **Frontend** — `types.ts` (`DataSource` union), `AnalysisContext.tsx`, `page.tsx`, `how-it-works/page.tsx`, `ArchitectureDiagram.tsx`
- **Backend** — `app/config.py` (`DataSource` Literal + `DEFAULT_DATA_SOURCE`), `backend/app/models/api.py`, `backend/api/models/api.py`
- **Python module** — `app/arcticshift/` → `app/pushshift/`, class `ArcticShiftClient` → `PushshiftClient`, handler `_fetch_arcticshift` → `_fetch_pushshift`
- **Scripts/docs** — `scripts/test_arcticshift.py` → `test_pushshift.py`, plus `run_agent.py`, `test_game_search.py`, `test_remote_query_extended.py`, `test_business_idea_coercion.py`, `linanqiu_client.py` docstrings, `README.md`, `docs/datasets-bucket.md`

**Backward-compat fallback** in `app/pushshift/client.py::_get_parquet_path`: tries `data/pushshift/` first, falls back to legacy `data/arcticshift/` bucket prefix with a `WARNING` log. This kept production working through the code/bucket rename gap.

### C. Infra-side bucket rename (completed same day)

After the code rename landed, the GCS bucket prefix was moved to match: `gs://painpan-datasets/arcticshift/` → `gs://painpan-datasets/pushshift/` (server-side rewrite, two objects). Local `data/arcticshift/` was renamed to `data/pushshift/`. The code-side fallback remains as a safety net.

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/lib/datasets.ts` | **New.** `DatasetCard` interface + `DATASET_CARDS` record (one entry per source). Single source of truth for all dataset facts and subreddit lists. |
| `frontend/lib/data-sources.ts` | Rewritten to derive `DATA_SOURCES` from `DATASET_CARDS`. No more duplicate labels. |
| `frontend/lib/types.ts` | `DataSource` union: `"arcticshift"` → `"pushshift"` |
| `frontend/app/how-it-works/page.tsx` | Dropped in-page `SUBREDDIT_GROUPS` and `DATASET_COMPOSITION`; renders from `DATASET_CARDS`. Both sections always visible. Removed `collapsibleOpen` state and `ChevronDown` import. Fixed `sample_gaming` count (5→4). Added `reddit_v2` prose. |
| `frontend/components/ArchitectureDiagram.tsx` | Renamed `arcticshift` → `pushshift` keys; fixed sample_gaming "5 gaming subs" → "4 gaming subs"; added `reddit_v2` entries. |
| `frontend/contexts/AnalysisContext.tsx` | Default `dataSource`: `"arcticshift"` → `"pushshift"` |
| `frontend/app/page.tsx` | Default `currentDataSource`: `"arcticshift"` → `"pushshift"` |
| `app/config.py` | `DataSource` Literal + `DEFAULT_DATA_SOURCE` rename |
| `app/arcticshift/` → `app/pushshift/` | Directory moved |
| `app/pushshift/client.py` | Class `ArcticShiftClient` → `PushshiftClient`; logger strings `[ARCTICSHIFT]` → `[PUSHSHIFT]`; added backward-compat path fallback in `_get_parquet_path` |
| `app/pushshift/__init__.py` | Re-export `PushshiftClient` |
| `app/agents/tools/fetch.py` | Router branch `pushshift`; handler `_fetch_pushshift`; import `from app.pushshift.client import PushshiftClient`; docstrings |
| `app/linanqiu/linanqiu_client.py` | Docstring references `ArcticShiftClient` → `PushshiftClient` (3 spots) |
| `backend/app/models/api.py` | `AnalysisRequest.data_source` Literal: `arcticshift` → `pushshift` (default too) |
| `backend/api/models/api.py` | Same Literal rename |
| `scripts/test_arcticshift.py` → `scripts/test_pushshift.py` | File rename + content rename (imports, class refs, print strings) |
| `scripts/run_agent.py` | `--data-source` choices list |
| `scripts/test_game_search.py` | Imports + docstring |
| `scripts/test_remote_query_extended.py` | Docstring |
| `scripts/tests/test_business_idea_coercion.py` | Docstring reference |
| `README.md` | CLI flag value list |
| `docs/datasets-bucket.md` | Runtime path note + changelog entries for both the code rename and the bucket rename |

**Left untouched (intentional):**
- `output/reports/*_arcticshift*/` — historical timestamped run artifacts
- `output/fetch_stats.json` — historical stats snapshot
- `docs/traces/*.md` — immutable historical records (including this one's reference to past states)

---

## Pattern: The Drift Tax of Duplicate Facts

The original page had three places to update per dataset: intro, preprocessing card body, composition table. The 241K-was-actually-subreddits bug survived because updating one place doesn't force you to update the others — there is no compiler error for prose drift.

The fix isn't "be more careful next time." The fix is structural: make the fact live in one place and have every consumer read from it. `frontend/lib/datasets.ts` is now the only file you touch to change a dataset fact. The TypeScript `Record<DataSource, DatasetCard>` type adds a compile-time guarantee that every source has a card.

Corollary: when a name is wrong (`arcticshift` for Pushshift data), the wrongness propagates silently — UI labels, file paths, class names, log strings. Doing a full rename pays down that debt all at once. Half-renames (e.g., fixing only the UI) leave a worse mismatch than the original error, because future readers will trust whichever name they see first.

---

## Out of Scope / Known Caveats

- **`output/reports/*_arcticshift*/` directories kept.** These are timestamped artifacts of past runs. Renaming them would be revisionist — they record what was run at that time, under the name in use then.
- **`docs/traces/*.md` historical references kept.** Past traces mention `arcticshift` / `ArcticShiftClient` / `DEFAULT_DATA_SOURCE = "arcticshift"`. These describe the state of the code at the time of writing and should not be rewritten.
- **Backward-compat path fallback stays in `client.py`.** Even after the GCS bucket was renamed to `pushshift/`, the client still checks `data/arcticshift/` as a second candidate. This lets a revert (or a partially-deployed environment) work without code changes. The cost is a tiny amount of dead-feeling code; the benefit is a real safety net during rollout.
- **Architecture diagram still duplicates some facts.** `ARCH_PREPROCESSING` / `ARCH_LABELS` in `ArchitectureDiagram.tsx` carry short subtitles like "11.3M submissions / 241K subs" that overlap with the card facts. Not migrated in this pass — would be a follow-up if the drift recurs.
- **`backend/api/` duplicate path kept as-is.** Two `models/api.py` files exist (`backend/app/models/api.py` active, `backend/api/models/api.py` inert WIP). Both were renamed for consistency; the inert one is still inert.

---

## Verification

1. **TypeScript** — `npx tsc --noEmit` in `frontend/` is clean. The `Record<DataSource, DatasetCard>` type would have errored if any source were missing a card.
2. **Python imports** — `from app.pushshift.client import PushshiftClient; from app.agents.tools.fetch import _fetch_pushshift; from app.config import DEFAULT_DATA_SOURCE` all succeed; `DEFAULT_DATA_SOURCE` returns `"pushshift"`.
3. **Functional smoke** — `PushshiftClient()._get_parquet_path()` resolves to the local Parquet and logs the expected `[PUSHSHIFT]` lines.
4. **Grep audit** — Remaining `arcticshift`/`ArcticShift`/`Arctic Shift` hits in active code are all:
   - Intentional rename notes ("was 'arcticshift' — misnomer")
   - The backward-compat fallback in `client.py`
   - Accurate descriptions of the pre-rename GCS state in `docs/datasets-bucket.md`'s changelog
   - Historical trace docs in `docs/traces/`
5. **Datasets facts cross-checked** against source data:
   - Pushshift Parquet (`RS_2018-01_00.parquet`): 11,263,400 rows, 241,466 distinct subreddits (DuckDB `COUNT(*)` / `COUNT(DISTINCT subreddit)`)
   - Linanqiu JSON: 10,170 posts / 51 subreddits (from `linanqiu_dataset.json` metadata)
   - `sample_posts.json`: 30 posts across r/antiwork, r/personalfinance, r/ADHD
   - `gaming_test_20260416_105527.json`: 36 posts across 4 subreddits (NOT 5 as the old UI claimed)
   - HF dataset `fddemarco/pushshift-reddit` has only one shard for Jan 2018 (`RS_2018-01_00.parquet`), confirming this file IS the full month within the dataset
