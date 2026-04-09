# Trace: Theme Clustering with Embeddings + K-Means

**Date:** 2026-04-08
**Session:** Semantic clustering of 209 unique complaint themes into 9 named groups using text-embedding-004 and k-means
**Files Created:**
- `app/analyst/preprocessing.py`
- `app/analyst/clustering.py`
- `app/analyst/cluster_prompts.py`
- `scripts/cluster_themes.py`
- `tests/test_preprocessing.py`
- `tests/test_clustering.py`

**Files Modified:**
- `app/analyst/providers/base.py` (added `get_embeddings()`)
- `app/analyst/providers/gcloud.py` (implemented embeddings via REST)
- `app/analyst/providers/lm_studio.py` (implemented embeddings via OpenAI API)
- `app/analyst/models.py` (added `ThemeCluster`, `ClusteringResult`)
- `app/config.py` (added clustering config fields)
- `requirements.txt` (added scikit-learn, numpy)

---

## Overall Pipeline Method

This clustering step is **Step 3** in the three-stage multi-agent pipeline:

```
Stage 1: COLLECT          Stage 2: CLASSIFY (free-form)    Stage 3: CLUSTER (semantic)
─────────────────         ─────────────────────────        ──────────────────────────
User enters topic          Each post gets a free-form       Unique themes are embedded,
       │                   complaint label from LLM         clustered via k-means, and
       ▼                              │                     named by LLM
Agent 1 (Collector)                  │                              │
  ├── Find subreddits                ▼                              ▼
  ├── Fetch posts            Agent 2 (Analyst)              ThemeClusterer
  ├── Fetch comments           ├── LLM reads each post        ├── Normalize & deduplicate themes
  └── Store raw data           ├── LLM assigns free-form      ├── Embed with text-embedding-004
       │                       │   theme (≤3 words)            ├── K-means with silhouette score
       │                       ├── is_complaint flag           ├── LLM names each cluster
       │                       └── intensity level             └── Map clusters back to posts
       │                              │                              │
       ▼                              ▼                              ▼
  output/raw_posts.json      output/classified_posts_*.json   output/*_clustered.json
```

### Why Three Stages?

Each stage produces a distinct artifact that the next stage consumes:

| Stage | Input | Output | Agent |
|-------|-------|--------|-------|
| 1. Collect | User topic string | Raw Reddit posts + comments (JSON) | Collector (Agent 1) |
| 2. Classify | Raw posts | Each post tagged with free-form theme, is_complaint, intensity | Analyst LLM tool call |
| 3. Cluster | Classified posts | Themes grouped into 8-15 semantic clusters with names + counts | ThemeClusterer |

The key insight: **Stage 2 uses free-form labeling** (the LLM chooses its own words), which means 242 posts produce ~209 unique theme strings. Many are near-duplicates ("workplace frustration" vs "workplace frustrations"). Stage 3 resolves this by using embeddings to find semantic similarity, clustering, and giving each group a canonical name.

---

## Clustering Pipeline Architecture

```
ThemeClusterer.cluster_posts(posts)
  │
  ├── 1. _extract_theme_data()
  │     └── Normalize each post's theme, count occurrences
  │
  ├── 2. _canonicalize_themes()
  │     └── Deduplicate near-matches via SequenceMatcher (0.95 threshold)
  │
  ├── 3. provider.get_embeddings(canonical_themes)
  │     └── Vertex AI text-embedding-004, batched 5/request → (n, 768) array
  │
  ├── 4. _pick_optimal_k(embeddings)
  │     └── Silhouette score over k=8..15, pick best
  │
  ├── 5. KMeans(n_clusters=k).fit_predict(embeddings)
  │     └── Each theme gets a cluster label
  │
  ├── 6. _name_clusters()
  │     └── LLM call per cluster: "name this group of themes"
  │
  ├── 7. _build_clusters()
  │     └── Aggregate post counts and upvote totals per cluster
  │
  └── 8. _assign_clusters_to_posts()
        └── Add {cluster: {id, name}} to each post dict

Output: ClusteringResult (clusters + annotated posts)
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| `get_embeddings()` on the provider interface | Follows existing provider pattern; same auth, retry logic, config |
| Separate `preprocessing.py` module | Testable in isolation; reusable if we change clustering approach |
| New `*_clustered.json` output files | Non-breaking; preserves original classified files for traceability |
| Silhouette score for k selection | Automates k selection; fallback to `min_k` on failure |
| Batch embeddings (5 per request) | Vertex AI API limit per predict call |
| 0.95 dedup threshold | Aggressive enough for "workplace frustration"/"workplace frustrations" but not "low salary"/"low morale" |

---

## Implementation Details

### 1. Provider Interface Extension

Added `get_embeddings(texts: list[str]) -> np.ndarray` to `LLMProvider` base class. Both providers now implement it:

**GCloudProvider** — Uses Vertex AI `text-embedding-004:predict` REST endpoint:
- Batches texts into groups of 5 (API limit)
- Each batch: `{"instances": [{"content": "..."}]}`
- Response: `predictions[].embeddings.values` → 768-dim vectors
- Reuses existing credential refresh and retry logic

**LMStudioProvider** — Uses OpenAI-compatible `/v1/embeddings` endpoint:
- Single call with full list (no batching needed for local)
- Standard `client.embeddings.create()` call

### 2. ThemePreprocessor

Two operations:
- `normalize()` — lowercase, strip whitespace, collapse multiple spaces
- `deduplicate_themes()` — sort themes by frequency (descending), use `SequenceMatcher.ratio()` to find near-duplicates above 0.95 threshold, map to most frequent variant

### 3. Pydantic Models

```python
class ThemeCluster(BaseModel):
    cluster_id: int
    name: str           # LLM-generated, 3-5 words
    themes: list[str]   # canonical themes in this cluster
    post_count: int     # total posts
    total_upvotes: int  # sum of upvotes

class ClusteringResult(BaseModel):
    clusters: list[ThemeCluster]
    posts: list[dict]   # posts with cluster field added
    original_theme_count: int
    canonical_theme_count: int
    cluster_count: int
    processing_time_seconds: float
    provider_used: str
    embedding_model: str
```

### 4. Cluster Naming

Simple prompt: given a list of themes in a cluster, return a 3-5 word name. Uses `generateContent` on Gemini 2.5 Flash (not the classification prompt). Fallback: use the first theme in the cluster.

### 5. Configuration

Six new fields in `Config`:

| Field | Env Var | Default |
|-------|---------|---------|
| `clustering_min_k` | `CLUSTERING_MIN_K` | `8` |
| `clustering_max_k` | `CLUSTERING_MAX_K` | `15` |
| `clustering_embedding_model` | `CLUSTERING_EMBEDDING_MODEL` | `"text-embedding-004"` |
| `clustering_preprocess_case_normalize` | `CLUSTERING_PREPROCESS_CASE_NORMALIZE` | `true` |
| `clustering_preprocess_dedup_threshold` | `CLUSTERING_PREPROCESS_DEDUP_THRESHOLD` | `0.95` |
| `clustering_use_silhouette` | `CLUSTERING_USE_SILHOUETTE` | `true` |

---

## End-to-End Run

**Input:** `output/classified_posts_20260407_230341.json`
- 242 total posts, 237 classified, 5 failed
- 209 unique themes after normalization

**Silhouette scores:**

| k | silhouette |
|---|-----------|
| 8 | 0.0531 |
| **9** | **0.0628** (best) |
| 10 | 0.0542 |
| 11 | 0.0588 |
| 12 | 0.0500 |
| 13 | 0.0499 |
| 14 | 0.0496 |
| 15 | 0.0451 |

**Optimal k = 9** (highest silhouette score)

**Embeddings:** 209 themes → 209 × 768 matrix (42 API calls, ~20s)

**Results:**

| Cluster | Name | Posts | Upvotes |
|---------|------|-------|---------|
| 7 | Workplace Issues | 66 | 61,860 |
| 3 | Financial Guidance | 43 | 1,962 |
| 4 | Modern Life Challenges | 28 | 54,625 |
| 6 | Personal Finance | 23 | 2,347 |
| 0 | banking frustration | 22 | 484 |
| 1 | Worker Rights | 16 | 2,853 |
| 2 | Financial Account | 16 | 4,971 |
| 8 | capitalism critique religion | 12 | 17,714 |
| 5 | government job cuts | 11 | 22,185 |

**Total time:** 41.6 seconds (20s embeddings + 3s k-means + 18s cluster naming)

**Output:** `output/classified_posts_20260407_230341_clustered.json`

---

## Results Appreciation

### Cluster-by-Cluster Examples and Quality Assessment

#### Cluster 7: Workplace Issues — 66 posts, 61,860 upvotes (57 themes)

This is the dominant cluster, absorbing over a quarter of all posts. The themes are tightly coherent:

```
toxic work culture, workplace frustration, workplace dissatisfaction,
workplace drudgery, workplace dread, workplace burnout anxiety,
workplace complaint, workplace neglect, workplace death,
salary range dishonesty, pto policy change, pto request ignored,
office temperature conflict, pointless office meetings,
quitting retail job, resignation without counteroffer
```

**Assessment:** Strong. The embedding model correctly recognized that "workplace drudgery", "workplace dread", and "toxic work culture" are semantically close. The cluster captures the core anti-work subreddit sentiment well. The high upvote count (61,860) confirms this is the most resonant complaint category.

**One concern:** At 57 themes, this cluster may be a catch-all for work-adjacent topics. "Corporate dystopia game" and "workplace dress code" are in the same cluster but represent very different complaints. A higher k (or a second pass splitting this cluster) might produce cleaner sub-groups like "workplace culture/morale" vs "specific workplace grievances".

---

#### Cluster 3: Financial Guidance — 43 posts, 1,962 upvotes (34 themes)

Advice-seeking themes, clearly a distinct behavioral pattern:

```
financial advice, financial advice request, financial advice seeking,
personal finance advice, budgeting advice, investing vs debt,
retirement planning, retirement planning help, retirement savings advice,
home buying advice, inheritance financial advice, tax filing advice
```

**Assessment:** Very strong. The model picked up that these are not complaints per se — they're requests for guidance. "Advice", "help", "strategy", and "planning" dominate the vocabulary. The cluster is internally coherent and clearly distinct from Cluster 6 (Personal Finance transactions) and Cluster 0 (banking frustration).

---

#### Cluster 4: Modern Life Challenges — 28 posts, 54,625 upvotes (25 themes)

The most heterogeneous cluster:

```
adhd daily survival, adhd medication effects, adhd testosterone treatment,
mental noise, mental noise overload, neurodivergence questions,
audhd identity exploration, executive dysfunction struggles,
youtube ad disruption, youtube ads adhd, subscription fatigue,
ai surveillance, always on call, content policy update,
managing seasonal hypersexuality, pharmaceutical profit model
```

**Assessment:** This is a ragbag cluster — ADHD/mental health topics got mixed with YouTube complaints, AI surveillance, and a subreddit content policy. The 54,625 upvotes are inflated by the policy post (49,277 upvotes alone). The embedding model treated "ADHD" and "YouTube" as semantically close (likely because they co-occur in Reddit discussions about attention/distraction), but this cluster lacks a clear semantic center.

**Root cause:** These themes all share the pattern of "modern life annoyance" without a more specific common thread. The short 2-3 word labels make it hard for embeddings to disambiguate. A pre-clustering step that expanded themes into fuller descriptions might help.

---

#### Cluster 6: Personal Finance — 23 posts, 2,347 upvotes (20 themes)

Transaction-oriented financial topics:

```
mortgage down payment, mortgage payoff decision, mortgage refinance question,
mortgage recast decision, mortgage payment confusion,
first home buyer, home buying savings, real estate purchase,
car loan extension, car loan refinancing, credit card rewards,
tax filing question, tax credit question
```

**Assessment:** Strong. Cleanly captures the "I'm making a financial transaction and need help" pattern. Clearly distinct from Cluster 3 (seeking advice) and Cluster 0 (frustrated with financial institutions). The mortgage-heavy composition makes sense given the personal finance subreddit content.

---

#### Cluster 0: Banking Frustration — 22 posts, 484 upvotes (21 themes)

Institution-directed anger:

```
banking frustration, overdraft complaint, credit dispute,
credit line denial, credit score drop, gym billing dispute,
debt collection help, student loan anxiety, high medical bills,
healthcare cost frustration, divorce financial crisis, tax debt crisis
```

**Assessment:** Good. These are people frustrated *at* institutions (banks, gyms, tax authorities, healthcare), not seeking advice. The low upvote count (484) indicates these are niche individual complaints rather than viral posts. The cluster name "banking frustration" from the LLM is reasonable though slightly narrow — "financial institution grievances" might be more accurate given that healthcare costs and gym billing disputes are in there.

---

#### Cluster 1: Worker Rights — 16 posts, 2,853 upvotes (16 themes)

Labor organizing and worker solidarity:

```
labor rights violation, labor union betrayal, union formation success,
union contract restored, union organization advocacy,
unpaid work abuse, worker solidarity, underpaid craftsmanship,
living wage inquiry, service industry abuse, shareholder criticism
```

**Assessment:** Very strong. Thematically tight — union activity, labor violations, wage disputes. Even the three "community" themes (celebration, discussion, promotion) that snuck in are r/antiwork community-building posts related to worker organizing. The LLM name "Worker Rights" is accurate.

---

#### Cluster 2: Financial Account — 16 posts, 4,971 upvotes (15 themes)

Account-specific problems and strategies:

```
missing 401k funds, missing 401k money, forgotten subscriptions,
ira contribution error, roth conversion strategy, roth ira investments,
retirement account issue, retirement account mistake,
turbotax frustration, tax software complaint, resume deception
```

**Assessment:** Mostly coherent — retirement account issues, tax tool frustrations, and "where did my money go" problems. "Resume deception" is a misfit here; it was likely embedded close to "deception" in financial contexts. The cluster name "Financial Account" is accurate for the majority.

---

#### Cluster 8: Capitalism Critique Religion — 12 posts, 17,714 upvotes (11 themes)

Systemic critique:

```
capitalism critique religion, economic inequality, economic injustice,
wage inequality, wealth inequality, degree inflation,
entitled rich client, executive compensation, money versus purpose,
socialism history, pharmaceutical profit model
```

**Assessment:** Strong. These are systemic/macro-level complaints about economic systems. The LLM name "capitalism critique religion" is a bit odd — likely the LLM saw both "capitalism critique" and "pharmaceutical profit model" and tried to be inclusive. A better name might be "Systemic Economic Inequality". The high upvote count (17,714) shows these resonate widely.

---

#### Cluster 5: Government Job Cuts — 11 posts, 22,185 upvotes (10 themes)

Layoffs and housing pressure:

```
government job cuts, job cuts, job loss housing, mass layoffs,
layoffs economic impact, layoffs worker rights, job market struggles,
rental cost analysis, sell vs rent decision, tenant protection law
```

**Assessment:** Mixed. The job cuts themes are coherent, but "rental cost analysis", "sell vs rent decision", and "tenant protection law" are housing topics that got pulled in, likely because job loss and housing insecurity co-occur in embeddings. The cluster should probably be "Job Loss and Housing Insecurity" or split into two smaller clusters. The 22,185 upvotes are driven by posts about mass federal layoffs that went viral.

---

### Overall Assessment

| Quality | Clusters | Notes |
|---------|----------|-------|
| Strong | 3 (Financial Guidance), 6 (Personal Finance), 1 (Worker Rights), 8 (Capitalism Critique) | Internally coherent, clearly distinct from each other |
| Good | 0 (Banking Frustration), 2 (Financial Account) | Mostly coherent with minor misfits |
| Needs work | 7 (Workplace Issues), 4 (Modern Life Challenges), 5 (Government Job Cuts) | Over-clustered (7 is too broad) or ragbag (4 mixes unrelated topics) |

### Identified Issues and Potential Improvements

1. **Cluster 7 is too large (57 themes, 66 posts).** This absorbs ~28% of all classified posts. Running a second k-means pass within this cluster (sub-clustering) might split it into meaningful sub-groups like "workplace culture/morale", "specific workplace policies", and "quitting/resignation".

2. **Cluster 4 (Modern Life Challenges) is a ragbag.** ADHD/mental health, YouTube complaints, and content policy updates don't belong together. The root cause: short 2-3 word themes lack the semantic richness for clean embeddings. A possible fix: expand themes to short sentences (e.g., "workplace frustration" → "employee feels frustrated with their workplace") before embedding.

3. **Three finance clusters (0, 3, 6) overlap in theme space.** Cluster 0 (banking frustration), 3 (financial guidance), and 6 (personal finance) all deal with money. The distinctions (anger vs. advice vs. transactions) are meaningful but the boundary is fuzzy. This is reflected in the low silhouette scores (0.05-0.06 range).

4. **The 0.95 dedup threshold didn't merge any themes.** All 209 original themes remained distinct after deduplication. This suggests the LLM (Stage 2) produces sufficiently diverse labels that exact or near-exact duplicates are rare. The dedup logic is still valuable as a safety net for larger datasets.

---

## Testing

### Unit Tests (25 total, all passing)

**test_preprocessing.py (11 tests)**
- `TestNormalize`: lowercase, strip, collapse spaces, no-op, empty, whitespace-only
- `TestDeduplicateThemes`: near-duplicate merge, distinct separation, single theme, empty input, typo merge

**test_clustering.py (14 tests)**
- `TestExtractThemeData`: basic count, skip unclassified, skip empty themes
- `TestPickOptimalK`: silhouette disabled, k clamped to n_samples, valid silhouette selection
- `TestClusterPosts`: basic clustering, cluster assignment, empty input, no classified posts, single theme, upvote aggregation
- `TestAssignClustersToPosts`: null for unclassified, preserves original data

Uses `MockProvider` with deterministic hash-based embeddings and `MockClusterer` that overrides LLM naming.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No classified posts | Return empty `ClusteringResult` with warning |
| Single unique theme | Return single cluster, skip k-means |
| API failure mid-embed | Retry up to `gcloud_max_retries`, then raise |
| Too few themes for k range | Clamp `max_k` to `min(len(themes)-1, max_k)` |
| LLM naming fails | Fallback to first theme in cluster |
| Silhouette score fails | Fallback to `min_k` |

---

## Lessons Learned

1. **Deduplication happens on normalized strings, not raw.** The pipeline normalizes first (lowercase, strip), then deduplicates. Tests need to feed already-normalized input to `deduplicate_themes()`.

2. **Silhouette scores on short text embeddings are low.** A score of 0.06 is typical for 3-word theme embeddings — the clusters are real but the boundaries are fuzzy. This is expected; the LLM naming step adds semantic coherence that raw geometry doesn't capture.

3. **`_generate_text()` needs provider-specific paths.** The existing provider interface only has `classify_post()` (which returns an `EnrichedPost`), not raw text generation. For cluster naming, we need raw text output. Added `_generate_gcloud()` and `_generate_lm_studio()` to `ThemeClusterer` that call the underlying API directly. In a future refactor, `generate_text()` should be added to the `LLMProvider` interface.

4. **The `import time` in `classify_post()` was a local import.** When adding `get_embeddings()` (which also needs `time.sleep`), moved it to module-level in `gcloud.py`. Easy to miss.
