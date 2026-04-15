# Trace: Non-Complaint Theme Filter

**Date:** 2026-04-15
**Status:** Done

---

## The Problem

The classifier returns `is_complaint=False` for posts that aren't complaints, but still assigns them a `theme` field (e.g., "No complaint", "Not a complaint", "general discussion"). The clustering pipeline ignored the `is_complaint` flag and included ALL themes — complaint and non-complaint alike — in embedding, KMeans, and cluster naming.

Consequence: clusters were diluted by non-complaint themes, and cluster names like "Concerns about" or "Uncertainty" emerged from garbage meta-labels rather than real pain points.

Identified in pipeline assessment `output/reports/2026-04-15/195637_live/assessment.md`:
> "Classifier returning meta-labels like 'No complaint' (3x), 'Not a complaint' (2x) as themes. These aren't complaint themes — they're classification outputs masquerading as themes."

---

## Solution Overview

Add `is_complaint` filtering at **two layers** for defense-in-depth:

1. **Tool boundary** (`cluster.py`): Only pass complaint posts to the clusterer
2. **Internal extraction** (`clustering.py`): Skip non-complaints when building the theme map

Non-complaint posts remain in the full dataset for EDA display — only the clustering input is filtered.

---

## Files Changed

### Modified: `app/agents/tools/cluster.py` — Tool-level filter

```python
# BEFORE (line 50-51):
# Filter to only classified posts (with a theme)
classified = [p for p in posts if p.get("classification") and p["classification"].get("theme")]

# AFTER (lines 50-56):
# Filter to only classified complaint posts (is_complaint=True with a theme)
classified = [
    p for p in posts
    if p.get("classification")
    and p["classification"].get("theme")
    and p["classification"].get("is_complaint", True)
]
```

### Modified: `app/analyst/clustering.py` — Internal theme extraction

```python
# BEFORE (lines 160-164):
for i, post in enumerate(posts):
    classification = post.get("classification")
    if not classification or not isinstance(classification, dict):
        continue
    theme = classification.get("theme", "").strip()

# AFTER (lines 160-166):
for i, post in enumerate(posts):
    classification = post.get("classification")
    if not classification or not isinstance(classification, dict):
        continue
    if not classification.get("is_complaint", True):
        continue
    theme = classification.get("theme", "").strip()
```

---

## Data Flow (Before vs After)

```
BEFORE:
Posts → classify_batch() → [all themes, including "No complaint"] → _extract_theme_data → embed → KMeans → clusters

AFTER:
Posts → classify_batch() → cluster.py tool filter (is_complaint=True only)
                                → _extract_theme_data (is_complaint check)
                                → embed → KMeans → clusters
                         ↘ non-complaints preserved for EDA display
```

---

## Key Design Decisions

1. **Filter at two locations** rather than one — defense in depth. If someone bypasses the tool filter (calls `ThemeClusterer` directly), the internal method still catches non-complaints.
2. **Default `is_complaint` to `True`** when the key is missing — defensive. Posts classified by older code that didn't set this field are treated as complaints (preserving backward compatibility).
3. **Don't filter in the classifier itself** — the classifier's job is to classify, not to filter. Non-complaint posts should remain available for EDA tables and display.

---

## Complete File List

| File | Change Type |
|------|-------------|
| `app/analyst/clustering.py` | Modified — added `is_complaint` check in `_extract_theme_data` |
| `app/agents/tools/cluster.py` | Modified — added `is_complaint` check in tool-level filter |

---

## Verification

Run a test pipeline and confirm:
- Non-complaint themes ("No complaint", "Not a complaint") do NOT appear in cluster names or themes
- Post counts reflect only complaint posts in clustering
- Non-complaint posts still appear in classification EDA data
- `original_theme_count` reflects complaint themes only
