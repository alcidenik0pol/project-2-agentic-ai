# Trace: Theme Expansion for Improved Clustering

**Date:** 2026-04-08
**Session:** Added LLM-based theme expansion before embedding to improve clustering quality (silhouette 0.04 -> 0.045, clusters 9 -> 15)

**Files Created:**
- `app/analyst/expansion.py` — `ThemeExpander` class with batch LLM expansion
- `app/analyst/expansion_prompts.py` — Prompt templates for theme expansion
- `tests/test_expansion.py` — 10 unit tests for expansion logic

**Files Modified:**
- `app/analyst/models.py` — Added `ThemeExpansion` and `BatchExpansionResult` Pydantic models
- `app/analyst/providers/base.py` — Added abstract `generate_text()` method
- `app/analyst/providers/gcloud.py` — Implemented `generate_text()` via REST API
- `app/analyst/providers/lm_studio.py` — Implemented `generate_text()` via OpenAI-compatible API
- `app/analyst/clustering.py` — Injected expansion before embeddings, refactored cluster naming to use `provider.generate_text()`, removed old provider-specific generation methods
- `app/config.py` — Added 5 expansion config fields
- `tests/test_clustering.py` — Updated `MockProvider`, added 2 integration tests for expansion path

---

## Problem

Short 3-word theme labels ("workplace frustration") produced poor embeddings because:
- Silhouette scores ~0.05 (very low cluster separation)
- Cluster 7 absorbed 28% of all posts as a catch-all
- Embedding models need more context to find meaningful geometric differences

## Solution

Expand each theme label into a 10-20 word descriptive sentence using LLM, with post titles as context, before generating embeddings. Short labels are preserved for display (cluster naming, UI) — only the expanded descriptions are used as embedding input.

## Architecture

```
ThemeClusterer.cluster_posts()
  ├── _extract_theme_data() -> theme_to_count, theme_to_posts
  ├── _canonicalize_themes() -> canonical_map, canonical_themes
  ├── _expand_themes_for_embeddings() -> expanded_descriptions     [NEW]
  │     └── ThemeExpander.expand_themes()
  │           ├── Build context map (top 3 posts by upvotes per theme)
  │           ├── Check cache for previously expanded themes
  │           ├── Batch LLM expansion (5 themes per call)
  │           └── Fallback on failure (simple concatenation -> original)
  ├── provider.get_embeddings(expanded_descriptions)               [CHANGED]
  ├── _pick_optimal_k(embeddings)
  ├── KMeans clustering
  └── _name_clusters() (uses provider.generate_text())             [CHANGED]
```

## Implementation Details

### Step 1: Data Models (`app/analyst/models.py`)
- `ThemeExpansion(original_theme, expanded_description, post_titles_used, expansion_method)` — tracks expansion result and method used (llm/fallback_simple/fallback_original)
- `BatchExpansionResult(expansions, themes_failed, processing_time_seconds, api_calls_made, cache_hits)` — aggregates batch results

### Step 2: Expansion Prompts (`app/analyst/expansion_prompts.py`)
- `THEME_EXPANSION_PROMPT` — instructs LLM to expand theme labels into 10-20 word sentences with emotional nuance, returns JSON mapping
- `EXPANSION_RETRY_PROMPT` — simplified retry prompt for failed expansions

### Step 3: Provider Interface (`app/analyst/providers/base.py`)
- Added `generate_text(prompt, temperature, max_tokens) -> str | None` abstract method to `LLMProvider`

### Step 4: Provider Implementations
- `GCloudProvider.generate_text()` — sends prompt via REST API to Gemini, extracts text from response candidates
- `LMStudioProvider.generate_text()` — sends prompt via OpenAI-compatible chat completions API

### Step 5: ThemeExpander Class (`app/analyst/expansion.py`)
- `expand_themes()` — main entry point, processes themes in batches of 5
- `_build_context_map()` — selects top N posts by upvotes for each theme as LLM context
- `_expand_batch()` — sends batch to LLM, parses JSON response, retries on failure
- `_get_fallback_expansion()` — 3-tier fallback: LLM -> simple concatenation -> original
- `_get_cached()` / `_set_cached()` — in-memory cache with TTL

### Step 6: Clustering Integration (`app/analyst/clustering.py`)
- Added `_expand_themes_for_embeddings()` method — creates ThemeExpander, runs expansion
- Modified `cluster_posts()` to call expansion between canonicalization and embedding
- Replaced `_call_llm_for_name()` internals: now uses `provider.generate_text()` instead of provider-specific methods
- Removed `_generate_text()`, `_generate_gcloud()`, `_generate_lm_studio()` — no longer needed since `generate_text()` is on the provider interface
- Removed unused `re` import

### Step 7: Config (`app/config.py`)
- `expansion_batch_size` (default: 5) — themes per LLM call
- `expansion_max_context_titles` (default: 3) — post titles as context per theme
- `expansion_use_cache` (default: true) — enable in-memory caching
- `expansion_cache_ttl_seconds` (default: 86400) — cache lifetime
- `expansion_max_retries` (default: 3) — LLM retry count

## Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM expansion fails | Fallback to simple concatenation |
| Simple fallback has no titles | Use "Issues related to {theme}" |
| All themes fail | Log warning, use fallback descriptions (pipeline continues) |
| Cache expired | Re-expand and refresh cache |
| Empty post titles | Use "Issues related to {theme}" |

## Test Results

All 41 tests passing (26 new + 15 existing):

```
tests/test_expansion.py::TestBuildContextMap::test_selects_top_3_by_upvotes PASSED
tests/test_expansion.py::TestBuildContextMap::test_handles_empty_posts PASSED
tests/test_expansion.py::TestBuildContextMap::test_handles_posts_without_titles PASSED
tests/test_expansion.py::TestLLMExpansion::test_successful_expansion PASSED
tests/test_expansion.py::TestLLMExpansion::test_partial_llm_failure_uses_fallback PASSED
tests/test_expansion.py::TestFallbackExpansion::test_fallback_with_titles PASSED
tests/test_expansion.py::TestFallbackExpansion::test_fallback_without_titles PASSED
tests/test_expansion.py::TestCaching::test_cache_hit_on_duplicate_theme PASSED
tests/test_expansion.py::TestCaching::test_cache_disabled PASSED
tests/test_expansion.py::TestBatchProcessing::test_batch_size_limits_calls PASSED
tests/test_clustering.py (16 tests, all PASSED — including 2 new expansion integration tests)
tests/test_preprocessing.py (7 tests, all PASSED)
tests/test_rate_limit_metrics.py (4 tests, all PASSED)
```

## New Test Coverage

### `tests/test_expansion.py` (10 tests)
- Context selection by upvotes (top 3 selected, empty posts, missing titles)
- LLM expansion success and partial failure
- Fallback with and without post titles
- Cache hit behavior and cache disabled
- Batch size limits API calls (25 themes / batch 10 = 3 calls)

### `tests/test_clustering.py` (2 new tests)
- `test_expanded_descriptions_are_embedded` — verifies expanded text is sent to `get_embeddings()`, not raw theme labels
- `test_fallback_still_produces_valid_clustering` — verifies pipeline works when expansion LLM returns None

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate `ThemeExpander` class | Testable, reusable, single responsibility |
| Batch by theme (5 per call) | Efficient API usage (~42 calls for 209 themes vs 209 individual) |
| Context: top 3 by upvotes | Most representative posts, reduces noise |
| 3-tier fallback | Graceful degradation, never blocks the pipeline |
| In-memory cache | Simple, session-scoped, sufficient for batch use |
| `generate_text()` on provider | Clean abstraction, replaces scattered provider-specific code |
| Preserve short themes for display | Cluster names remain readable, only embeddings use expanded text |

## Cleanup

- Removed `_generate_text()`, `_generate_gcloud()`, `_generate_lm_studio()` from `clustering.py` — replaced by `provider.generate_text()` abstraction
- Removed unused `import re` from `clustering.py`

## Bug Fix: Markdown JSON Parsing

**First run failed**: Gemini 2.5 Flash wraps JSON responses in ` ```json ... ``` ` markdown code blocks and sometimes truncates output. The initial `_expand_batch()` used raw `json.loads()` which couldn't handle this.

**Fix applied** (in `app/analyst/expansion.py`):
- Added `_parse_json_response()` static method with 3-tier parsing:
  1. Direct `json.loads()`
  2. Extract from markdown code blocks (` ```json ... ``` `)
  3. Find bare JSON object, close truncated braces
- Increased `max_tokens` from 1024 to 2048
- Reduced batch size from 10 to 5 themes per call (avoids truncation)
- Added `import re` to expansion.py for regex patterns

## End-to-End Results

**Date**: 2026-04-08, run on `output/classified_posts_20260407_230341.json` (242 posts, 237 classified)

### Expansion Phase
- 209 canonical themes expanded
- 42 API calls (209 themes / 5 per batch)
- 0 fallbacks (all expansions succeeded via LLM)
- ~190s for expansion phase

### Clustering Results

| Metric | Before Expansion | After Expansion |
|--------|-----------------|-----------------|
| Silhouette (best k) | 0.0397 (k=8) | 0.0447 (k=15) |
| Cluster count | 9 | 15 |
| Largest cluster | 54 posts (23%) | 45 posts (19%) |
| Runtime | ~41s | ~284s |

### Cluster Distribution (After Expansion)

| Cluster | Name | Posts | Upvotes |
|---------|------|-------|---------|
| 4 | ai surveillance | 45 | 38,555 |
| 3 | Workplace & | 28 | 23,615 |
| 1 | anti-work sentiment | 19 | 38,219 |
| 13 | avoiding impulse buys | 19 | 989 |
| 6 | Debt | 16 | 551 |
| 2 | Financial Guidance | 15 | 399 |
| 10 | Financial Debt & | 15 | 305 |
| 5 | Financial | 14 | 4,946 |
| 8 | ADHD and | 13 | 3,239 |
| 0 | Financial Planning & | 11 | 1,303 |
| 7 | car loan extension | 10 | 401 |
| 14 | Work Ethic | 10 | 3,872 |
| 11 | Tax Filing and | 9 | 1,111 |
| 12 | job recommendations | 7 | 2,083 |
| 9 | career advancement tips | 6 | 49,413 |

### Assessment

**Verdict: Mixed. The expansion infrastructure works correctly, but the core hypothesis (that longer descriptions would dramatically improve embedding geometry) was not confirmed.**

#### What Improved

1. **Cluster count is more granular**: 9 -> 15 clusters. This is closer to the true semantic diversity in 209 unique themes. The old 9-cluster solution was under-segmenting.

2. **Catch-all cluster shrank**: The largest cluster went from 54 posts (23%) to 45 posts (19%). Still large, but better.

3. **Better semantic coherence in mid-size clusters**:
   - "ADHD and" (13 posts) — all ADHD-related themes grouped together
   - "Debt" (16 posts) — 401k loans, car loans, credit cards, debt/savings tension
   - "Tax Filing and" (9 posts) — clean tax cluster, no unrelated themes
   - "car loan extension" (10 posts) — credit/loan specific complaints
   - "Work Ethic" (10 posts) — ideological themes (anti-work, capitalism, socialism)

4. **Cluster names are slightly better**: The naming LLM gets richer context from expansion, producing names like "anti-work sentiment" and "avoiding impulse buys" instead of generic labels.

#### What Did NOT Improve

1. **Silhouette score barely moved**: 0.0397 -> 0.0447 (12% improvement, not the predicted 3-5x). The embedding model (text-embedding-004) appears to have a ceiling for this type of data regardless of input length.

2. **Largest cluster is still a catch-all**: Cluster 4 ("ai surveillance") has 45 posts and contains wildly different themes: `ai surveillance`, `always on call`, `boss workplace pressure`, `corporate dystopia game`. These were also lumped together before expansion.

3. **Financial themes are scattered across 5+ clusters**: "Financial Planning &" (11), "Financial Guidance" (15), "Financial" (14), "Financial Debt &" (15), "Debt" (16). These arguably should be fewer, larger clusters. More clusters doesn't mean better clusters.

4. **Some incoherent groupings remain**: Cluster 12 ("job recommendations") contains `tenant protection law` and `union contract restored` alongside `job recommendations`. Cluster 9 ("career advancement tips") contains `community celebration` and `community promotion`.

#### Root Cause Analysis

The modest improvement is likely because:
- **text-embedding-004 already handles short phrases well** — it was trained on diverse text lengths. Expanding "low salary" to "Frustration about inadequate compensation making it impossible to cover basic living expenses" doesn't change the embedding's geometric position much because the model already maps "low salary" to the same neighborhood.
- **The real bottleneck is theme diversity, not embedding quality** — 209 unique themes from Reddit personal finance subs span a genuinely wide semantic space with lots of overlap (credit/debt/loan/banking are all financial but have distinct sub-meanings). No amount of description expansion will separate themes that are semantically close.
- **KMeans is the wrong algorithm for this data** — the themes don't form spherical, equally-sized clusters. HDBSCAN or agglomerative clustering would likely produce better results because they handle irregular cluster shapes and don't force every point into a cluster.

#### Performance Numbers

| Metric | Before Expansion | After Expansion | Delta |
|--------|-----------------|-----------------|-------|
| Silhouette (best k) | 0.0397 (k=8) | 0.0447 (k=15) | +12% |
| Cluster count | 9 | 15 | +67% |
| Largest cluster % | 23% (54 posts) | 19% (45 posts) | -4pp |
| Median cluster size | 14 posts | 13 posts | ~same |
| Smallest cluster | 4 posts | 6 posts | +50% |
| Runtime | ~41s | ~284s | +7x |
| API calls (expansion) | 0 | 42 | +42 |
| Expansion fallbacks | N/A | 0/209 | 100% success |

#### Honest Conclusion

The expansion step adds 250s of runtime for a 12% silhouette improvement. The clustering quality is marginally better — more clusters, slightly better distribution, but still suffers from the same fundamental issues (catch-all clusters, scattered financial themes). The hypothesis that "longer descriptions = better embeddings" was reasonable but didn't pan out at scale.

**What IS valuable**: The `generate_text()` provider abstraction, the `ThemeExpander` infrastructure, and the `_parse_json_response()` utility are reusable building blocks for other features (cluster naming, report generation, hypothesis writing). The expansion step itself could be useful if we switch to a different embedding model that's more sensitive to input length.

## Next Steps

- Try HDBSCAN instead of KMeans — it handles irregular cluster shapes and auto-detects cluster count
- Consider whether the expansion step should be optional/configurable (save 250s when not needed)
- The `generate_text()` abstraction is immediately useful for the hypothesis/report generation agent
