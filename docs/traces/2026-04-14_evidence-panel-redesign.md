# Trace: Evidence Panel Redesign — No Slop Edition

**Date:** 2026-04-14
**Session:** Fix the "Show evidence" panel in IdeaCard. Three problems: no cluster context, no clickable post links, ambiguous post count ("Posts: 5" but only showing 1 title).

---

## Files Modified

| File | Change |
|------|--------|
| `app/analyst/models.py` | Added `SupportingPost` model; expanded `HypothesisEvidence` with `cluster_themes`, `shown_post_count`, `supporting_posts`; kept legacy `supporting_post_titles` as `exclude=True` for backwards compat |
| `backend/app/models/api.py` | Added `SupportingPostAPI`; mirrored new `HypothesisEvidenceAPI` fields |
| `app/analyst/hypothesis.py` | Rewrote `_prepare_cluster_table()` to extract full post metadata (title, url, upvotes, subreddit) instead of 100-char truncated titles; added `cluster_themes` and `shown_post_count` |
| `app/analyst/hypothesis_prompts.py` | Updated LLM prompt schema to request `supporting_posts` objects and `cluster_themes` instead of flat `supporting_post_titles` |
| `app/agents/tools/hypothesis.py` | Updated serialization to use new field names (`supporting_posts`, `cluster_themes`, `shown_post_count`) |
| `frontend/lib/types.ts` | Added `SupportingPost` interface; updated `HypothesisEvidence` to match new backend schema |
| `frontend/components/IdeaCard.tsx` | Redesigned evidence panel: cluster themes, clickable Reddit links, per-post metadata, clear "Top N posts by upvotes" heading |

## Architecture

```
Reddit Posts (fetched by Collector)
        │
        ▼
_prepare_cluster_table()
  - Groups posts by cluster
  - Top 3 by upvotes
  - Extracts: title, url, upvotes, subreddit     ← NEW (was: title[:100] only)
  - Includes: cluster.themes                       ← NEW
        │
        ▼
LLM Prompt (hypothesis_prompts.py)
  - Receives sample_posts with full metadata       ← NEW
  - Instructed to copy posts exactly into evidence  ← NEW
        │
        ▼
HypothesisOutput (Pydantic)
  - evidence.supporting_posts: [{title, url, upvotes, subreddit}]  ← NEW
  - evidence.cluster_themes: [...]                                 ← NEW
  - evidence.shown_post_count: N                                   ← NEW
        │
        ▼
hypothesis.json → API (HypothesisOutputAPI) → Frontend
        │
        ▼
IdeaCard.tsx evidence panel
  - "Cluster: name" + "Themes: a, b, c"
  - "5 posts in cluster • 9,227 total upvotes"
  - "Top 3 posts by upvotes:" ← eliminates ambiguity
  - Each post → clickable <a href> to Reddit
  - Per-post: subreddit • upvotes
```

## Design Decisions

1. **LLM copies posts verbatim rather than generating URLs.** The prompt sends `sample_posts` with real URLs and instructs the LLM to copy them exactly into `supporting_posts`. This avoids hallucinated links while keeping the data flow simple — no post-processing step needed to map titles back to URLs.

2. **Backwards compatibility via `exclude=True`.** Old hypothesis.json files have `supporting_post_titles` (flat strings). The internal model accepts this field but excludes it from serialization, so old files parse without error and new files never emit it.

3. **`shown_post_count` defaults to 0.** Old files won't have this field. Making it default to 0 (instead of required) means `HypothesisOutputAPI(**data)` won't blow up on historical data.

4. **Title truncation raised from 100 to 200 chars.** The old 100-char limit was cutting off meaningful context. Reddit titles can be up to 300 chars; 200 gives enough room while keeping the LLM context manageable.

5. **No new components created.** The evidence panel stays inline in IdeaCard.tsx. The change is purely data-model + rendering — no new UI components needed for what amounts to a better display of the same expand/collapse pattern.

## Verification Performed

- [x] TypeScript types match backend Pydantic models (field names, types)
- [x] No remaining references to `supporting_post_titles` in `.py`, `.ts`, or `.tsx` files
- [x] Backwards compat: old hypothesis.json files will parse (all new fields have defaults)
- [x] Agent tool serialization updated to match new model fields
- [x] API model mirrors internal model structure
- [x] LLM prompt schema matches expected Pydantic output shape

## What Was NOT Done

- **No unit tests added** for the new Pydantic models or hypothesis logic changes
- **No migration script** for old hypothesis.json files (handled via default values instead)
- **No visual regression testing** (no node_modules available for TypeScript compilation check)
- **No changes to the clustering pipeline** — only the evidence extraction and display were touched
