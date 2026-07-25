# Interview Narrative — Analytical Rigor (v2)

Two STAR stories, lifted verbatim from project traces.
Built to be scanned, not read. Numbers are deployed inside arguments, not banked.

---

## 1. The one-liner (memorize verbatim)

> A multi-agent system that surfaces **unsolved pain points in any niche**, grounded in **real Reddit data** — not model knowledge.

---

## 2. Architecture in 30 seconds

**LangGraph 3-agent state machine** (`app/agents/graph.py:394-410`): `Orchestrator → Analyst → Hypothesis → END`, strictly linear — no re-query edge.

**Why LangGraph over CrewAI / OpenAI SDK** (comparison table: `docs/traces/2026-04-18_langgraph-agent-sdk-migration.md`): provider-agnostic against our existing 3-provider abstraction; explicit `StateGraph` edges replace fragile regex handoffs; `TypedDict` state is inspectable. Each agent has **distinct prompts AND distinct tool sets** (orchestrator=1, analyst=2, hypothesis=2) — swapping any two breaks the pipeline because the tool registry and context builder are per-node.

- **5 tools**: `fetch_posts`, `classify_posts`, `cluster_themes`, `generate_hypotheses`, `save_artifact`.
- **Backend**: FastAPI on Cloud Run (`--max-instances=1`, `--concurrency=20`, 512 MiB / 1 vCPU, `--timeout=3600`) + Firebase Hosting frontend.
- **Data paths**: config default is **Pushshift** (historical, HuggingFace via DuckDB, frozen Jan 2018); the **live production path is `reddit_v3`** (Atom RSS). Three Reddit clients (v1/v2/v3) coexist on disk for rollback.

---

## 3. STORY A — "Walk me through a time you used data to change direction"

**Spine:** the live data source kept dying under our feet. Each death forced a structural decision, and every decision was grounded in a measurable signal. `TRIGGER → SIGNAL → DECISION → RESULT`.

| # | Pivot | Trigger signal (measured) | Decision | Result |
|---|---|---|---|---|
| 1 | **WAF block** (Apr 2026) | Same code + same UA: **HTTP 200 from residential IP, HTTP 403 from Cloud Run**. Tested **5 User-Agents** — all walled identically → **IP-reputation block, not UA-based**. | Tunnel through a **SOCKS5h proxy (IPVanish)** from Cloud Run. | Live traffic restored. (The `h` matters: **DNS resolution happens at the proxy**, not the caller — without it, Cloud DNS leaks the datacenter IP and the WAF trips anyway.) |
| 2 | **`.json` shutdown** (May 29) | **100% of `.json` endpoints → 403/410**, including OAuth edge. Policy change, not reputation — proxy can't help. | Build **v2 HTML scraper** on `old.reddit.com`; ship outage banner; file Reddit Data Access Request. | v2 runs in prod for ~6 weeks. |
| 3 | **Login wall** (July 2026) | `old.reddit.com` → **HTTP 302 `/login?reason=lor2`**. **Silent failure**: logs identical to "sub is genuinely empty" (parser returns `[]` either way). | Pivot to **v3 RSS feeds** (`hot.rss`, `search.rss`, `comments/{id}/.rss`) — last unauthenticated surface. | v3 verified on prod run `cd32b8b47e94`: **73 posts / 8 subs**. |
| 4 | **Cost discipline** (Jul 17, parallel) | **~$2/day Vertex actual vs $0.30–1.22 modeled = 28× tracker gap.** **416,479 tokens (336,290 in + 80,189 out)** recorded for July; root cause = `thoughtsTokenCount` not counted + embeddings untracked. | Ship **measurement fix first** + **one** safe reduction (disable thinking on classification; temp 0.1 JSON extraction). Defer Pro→Flash, thinking caps, Flash-Lite. | "Measure twice, cut once." Phase 2 waits for real per-SKU data. |

Every pivot was triggered by a *measurable* signal, and every decision was *additive* — dead code stays on disk. v1, v2, v3 all coexist. Not "clean," but correct: rollback safety > tidiness.

---

## 4. STORY B — "How did you measure success on X?"

Two layers, because the question has two valid reads.

### Layer 1 — Analytical rigor (the EDA, not a summary)

The analyst is a **5-stage hybrid pipeline**, not a single LLM pass. Each stage gets `MECHANISM / VALUE / RATIONALE`, with the number that justifies the stage deployed inline.

#### Stage 1 — Classify
- **MECHANISM:** per-post LLM call, Flash, temp 0.1, thinking disabled, output `{theme, is_complaint, intensity}`. Parallelized via `ThreadPoolExecutor` (`classifier.py:193`, `max_workers = min(config.classification_max_workers, total, 20)`, default 10).
- **VALUE:** compresses raw post text to an aggregatable 3-word label; gates out non-complaints at **two layers** (`cluster.py:50-56` and `clustering.py:165`, per `2026-04-15_non-complaint-theme-filter.md`); adds an intensity axis separate from upvotes.
- **RATIONALE:** pure embedding on raw post text produced catch-all clusters — the original trace documents **Cluster 7 absorbing 66 posts / 57 themes (28% of data), silhouette ≈ 0.05–0.06** (`2026-04-08_theme-clustering-embeddings.md`). Classification compresses each post to its semantic essence *as a reasoning model understands it* — exactly what embedding models can't do.
- **Inline numbers (prod `cd32b8b47e94`):** 60 posts classified, **79 high-intensity / 21 medium, 99 complaints / 1 non-complaint, 100% success**.

#### Stage 2 — Dedup
- **MECHANISM:** `difflib.SequenceMatcher.ratio() ≥ 0.95`, frequency-sorted canonical, zero API calls.
- **VALUE:** prevents "bug" / "bugs" from splitting a cluster.
- **RATIONALE:** free (pure Python), aggressive enough for typos/plurals only — semantic dedup is Stage 4's job, so we don't pre-empt it.
- **Inline numbers:** sample run 97 → 97 (ratio 1.0). The safety net didn't fire on that run; it exists for noisier LLM output.

#### Stage 3 — Expand
- **MECHANISM:** per-batch LLM call, 5 themes/batch, Flash, temp 0.3, top-3 post titles as context, 10–20 word output sentence. **This stage costs 75% of clustering wall-clock — it deserves the most careful defense.**
- **VALUE:** disambiguates polysemous labels ("debt" → credit-card vs student-loan vs national) using real post titles; adds emotional valence the bare label lacks.
- **RATIONALE + honest result:** `2026-04-08_theme-expansion-for-clustering.md` is unusually candid — the predicted silhouette gain was 3–5×, the **measured gain was 0.0397 → 0.0447 (+12%)**. But cluster granularity improved measurably: catch-all cluster shrank **54 → 45 posts (23% → 19%)**, and coherent ADHD / debt / tax-filing / car-loan clusters emerged where none had before. The honest framing: expansion trades **107.05 s of 141.77 s (75% of clustering wall-clock)** for more granular mid-sized clusters, not for silhouette. **Self-criticism to land:** if rebuilding today, expansion would be the first thing made optional, and KMeans would be swapped for HDBSCAN (the trace explicitly recommends this).
- **Inline numbers:** batch_size=5, max_tokens=2048 (raised from 1024 after a truncation bug), in-memory cache TTL=86400 s.

#### Stage 4 — Embed + KMeans with silhouette selection
- **MECHANISM:** `text-embedding-004` → 768-dim; `KMeans(n_init=10, random_state=42)`; silhouette-selected `k ∈ [8,15]` (`clustering.py:228-252`).
- **VALUE:** cluster count is **chosen by the data**, not hardcoded. Reproducible (fixed seed + 10 restarts). Cheap (KMeans itself: ~0.9 s).
- **RATIONALE — why hybrid LLM-then-embed:**
  - **Pure embedding KMeans fails:** short labels produce ragbag clusters (trace documents **Cluster 4 mixing ADHD/mental-health with YouTube complaints** because the embedding model saw them as semantically close — co-occurrence in attention/distraction discussions). Silhouette on 3-word labels ≈ 0.05.
  - **Pure LLM clustering fails:** 200+ themes don't fit in a single prompt with room for pairwise reasoning; stochastic at scale; one giant LLM call per clustering decision is unreviewable and expensive.
  - **The hybrid:** LLM does what it does well (semantic compression of unstructured text → structured label, then human-readable cluster naming); embeddings+KMeans do what they do well (pairwise similarity at scale, deterministically, cheaply). Each stage hands the next a more refined representation: `raw post → 3-word label → deduped label → 10-20 word expansion → 768-dim vector → cluster ID → cluster name`.
- **RATIONALE — why silhouette over elbow / fixed-k:** elbow is subjective (human eyeballing); fixed k assumes you know the topic's semantic diversity ahead of time (indie games ≈ 6 pain themes, personal finance ≈ 15). Silhouette is a scalar optimizable programmatically. Range [8,15] is tight because silhouette is noisy on short-text embeddings — wider would just be noise.
- **Inline numbers:** sample sweep selected **k=9** (scores: k=8→0.053, k=9→0.063 best, k=15→0.045). Prod run `cd32b8b47e94` settled at **9 clusters from 26 themes**.

#### Stage 5 — Name
- **MECHANISM:** per-cluster LLM call, Flash, temp 0.3, validates truncation, retries with strengthened prompt.
- **VALUE:** the cluster is an **emergent entity no individual post sees**. The classifier labels one post at a time; the namer looks at 10–50 themes KMeans grouped together and abstracts them. The name is the handle the hypothesis LLM reasons about ("Workplace Issues, 66 posts, 61,860 upvotes"), not cluster ID 7.
- **RATIONALE:** separate from classify because emergent. The trace notes "the LLM naming step adds semantic coherence that raw geometry doesn't capture."

#### Cross-cutting Layer 1 paragraphs

**Three-metric significance, deliberately not collapsed.** `post_count` (breadth across users) + `total_upvotes` (aggregate intensity) + `avg_upvotes` (per-incident intensity, normalized). The failure mode each prevents — diagnosed in a real incident: **Cluster 4 "Modern Life Challenges" had 54,625 upvotes inflated by a single 49,277-upvote policy post**. A single combined score would have hidden this inflation; keeping the three metrics separate made it diagnosable. The hypothesis prompt (`hypothesis_prompts.py:35`: *"Prefer clusters with high upvotes AND high post count (both signal breadth and intensity)"*) explicitly tells the LLM to weigh breadth AND intensity together; the `HypothesisEvidence` Pydantic schema carries both fields through.

**Evidence chain (URL grounding).** Enforced at three layers: (1) `SupportingPost.url: str = Field(...)` is Pydantic-required (`models.py:136`); (2) the prompt forbids fabrication — "supporting_posts must be copied EXACTLY from the cluster's sample_posts"; (3) `_prepare_cluster_table` (`hypothesis.py:110-120`) passes through the full Reddit URL each post already carries. The URL survives every stage — `fetch_posts → classify_posts → cluster_themes → generate_hypotheses → hypothesis.json` — so every business idea in the final artifact carries a real Reddit URL.

**EDA artifacts persisted to disk.** `classification_eda.json`, `clustering_eda.json`, `hypothesis.json`, `workflow_report.md` — one per stage, written to the run's output dir. Each artifact is the receipt for debugging the next stage: when the hypothesis LLM produces a weird idea, you read the clustering EDA; when clustering produces weird clusters, you read the classification EDA. The pipeline runs 5–12 minutes per query; the artifacts make every stage reviewable without re-running.

### Layer 2 — Operational rigor

**Graceful degradation under IP-level rate limiting — verified in prod run `cd32b8b47e94`.** 3 of 8 subs 429'd on the burst. The singleton-level breaker (3-strike threshold, 60 s cooldown, max 2 cooldowns before trip — `circuit_breaker.py:35-37`) paused all callers simultaneously for 60 s, the fetcher resumed, **73 posts from the remaining 5 subs**. WITHOUT the singleton breaker, the fetcher would have iterated the remaining 5 subs, each calling `session.request`, each 429-ing, each costing ~20 s of urllib3 backoff for zero data. End state with no breaker: ~25 posts (from the 3 that succeeded pre-burst) instead of 73. This is a design property tested, not a victory lap.

**Why the breaker lives at the client-singleton, not per-fetcher.** The `ee612ece0a71` cascade incident (`2026-07-16_client-level-429-circuit-breaker.md`): 3 concurrent pipeline runs sharing the singleton client overwhelmed the proxy IP. A per-fetcher breaker would have seen only 2 local 429s per run — under the 3-threshold for all three — while the proxy IP saw 6 simultaneously; no fetcher would have tripped. The singleton breaker sees the **aggregate** rate because all three runs share `client._breaker` — one run's 429 pushes the shared counter toward the threshold, and the cooldown timestamp blocks every other caller's next `before_request`. All three pause together. (The `ee612ece0a71` log itself: **100 posts / 551 comments / 70 requests** succeeded in the first ~60 s before the cascade — that log justified the singleton design.)

**Why 429 is NOT in `status_forcelist`.** With `Retry(total=3, backoff_factor=1)` (`redditapiv3_client.py:71-75`), one user-level 429 becomes **4 HTTP attempts over 7 seconds** (1 + 1 s + 2 s + 4 s waits), all during the throttle window — multiplying the pressure, not relieving it. The breaker's 60 s process-wide cooldown is the correct layer.

**Cost discipline — "measure twice, cut once."** The 28× tracker gap and its root cause (`thoughtsTokenCount` + embeddings untracked) are the Story A beat above; the operational outcome belongs here. Phase 1 shipped the measurement fix + **one** safe reduction (disable thinking on classification — temp 0.1 JSON extraction needs no reasoning). Phase 2 (Pro→Flash, thinking caps, Flash-Lite) waits for real per-SKU data. Cloud Run side: `max-instances=1` + `concurrency=20` + WS auto-close 15 min after `analysis_complete` (`delay=900`) + Firebase migration (~$0.40/day lifted off Cloud Run) → projected **~$1.31/day → $0.65–0.75/day**.

---

## 5. "What did you learn?" — follow-up ammo

Four lessons, each traces to a real incident:

1. **Silent failures hide policy changes.** v2 logged `WARN: No posts found in r/X` identically for "sub is empty" and "Reddit served a login wall." A 200 with empty parse should carry a body snippet. *(Source: 2026-07-23 v3 pivot trace.)*
2. **Measure twice, cut once.** The 28× gap meant any "optimization" would have been speculative. Ship the instrument before fixing the leak. *(Source: 2026-07-17 Vertex Phase 1 trace.)*
3. **Distinguish environmental failure from code failure.** The Pushshift description pivot was built on a false premise — local proxy credentials were stale; the v2 scraper was sound in prod. The ERRATUM in `2026-07-22_pushshift-candidate-mining-and-description-pivot.md` is the receipt. *(Source: 2026-07-22 ERRATUM.)*
4. **Dead paths stay on disk for rollback.** v1/v2/v3 coexist. Not "clean," but every pivot was *additive* — the diff shows "add v3," not "mutate v2."

---

## 6. Honest limitations (if they probe)

- **No automated existing-solution checker.** Roadmap item; would use the HN Algolia API.
- **Pushshift is frozen at Jan 2018.** Keeps the pipeline functional through the login wall, but cannot surface current complaints. It is the config default; `reddit_v3` (RSS) is the live path that surfaces current pain.
- **`/comments/{id}/.rss` not yet verified on prod.** Listings verified; comments path still TBD (the `cd32b8b47e94` run never invoked it).
- **Hypothesis schema originally rejected `ideas: []`** for off-topic queries (Pydantic `min_length=1`); now relaxed to allow empty ideas with a non-empty `data_limitations` explanation.
- **Pushshift mining did not reach the selector.** The 80 candidates mined from Pushshift exist only in `docs/ideation/reddit/pushshift_candidate_subreddits.md` — they were never merged into `data/subreddit_descriptions_*.json`, and the loader (`subreddit_loader.py`) globs that JSON path only. The selector never sees them. This is a data-integration gap, not a slice cap.
- **Expansion trades 75% of clustering wall-clock for ~12% silhouette improvement.** Would be the first thing made optional on rebuild. The trace also recommends HDBSCAN over KMeans — themes don't form spherical, equally-sized clusters.
- **No iterative refinement loop.** LangGraph is strictly linear (`graph.py:403-408`); what exists is prompt-level gap-detection-and-abort (`graph.py:237-261`) — the LLM is instructed to stop if an upstream stage produced nothing, rather than re-query.

---

## 7. Files referenced (citable if asked "show me the code")

| File | Reference | What it shows |
|---|---|---|
| `app/agents/graph.py` | `:394-410` | LangGraph state machine: 3 nodes, strictly linear edges |
| `app/agents/graph.py` | `:237-261` | Prompt-level gap-detection-and-abort (not a re-query loop) |
| `app/analyst/clustering.py` | `:228-252` | Silhouette KMeans selection over `k ∈ [min_k, max_k]`, `n_init=10`, `random_state=42` |
| `app/analyst/clustering.py` | `:165` | Second-layer `is_complaint` filter (defense-in-depth) |
| `app/agents/tools/cluster.py` | `:50-56` | First-layer `is_complaint` filter (tool boundary) |
| `app/analyst/classifier.py` | `:178, :193` | `ThreadPoolExecutor`, `max_workers = min(10, total, 20)` |
| `app/analyst/hypothesis.py` | `:110-120` | `_prepare_cluster_table` passes through full Reddit URLs |
| `app/analyst/hypothesis_prompts.py` | `:35` | "high upvotes AND high post count" — breadth + intensity |
| `app/analyst/models.py` | `:136` | `SupportingPost.url: str = Field(...)` — Pydantic-required |
| `app/reddit/circuit_breaker.py` | `:35-37` | Thresholds: `3 / 60s / 2`, client-singleton level |
| `app/reddit_v3/redditapiv3_client.py` | `:71-75` | `status_forcelist=[500, 502, 503, 504]` — 429 removed |
| `app/config.py` | `:21-32` | `DataSource` literal + `DEFAULT_DATA_SOURCE = "pushshift"` |
| `app/collector/subreddit_loader.py` | `:19-30` | Globs `data/**/subreddit_descriptions_*.json` (not the .md) |
| `.github/workflows/deploy.yml` | `:59-66` | `--max-instances=1 --concurrency=20 --memory=512Mi --cpu=1 --timeout=3600` |
| `backend/app/api/websocket/manager.py` | `:104-127` | `_schedule_auto_close(delay=900)` — WS close 15 min post-complete |
| `docs/traces/2026-04-18_langgraph-agent-sdk-migration.md` | — | LangGraph vs CrewAI/OpenAI SDK comparison table |
| `docs/traces/2026-04-08_theme-clustering-embeddings.md` | — | Pure-embedding failure modes (Cluster 7 = 66 posts, Cluster 4 ragbag) |
| `docs/traces/2026-04-08_theme-expansion-for-clustering.md` | — | The honest expansion verdict (0.0397 → 0.0447, +12%) |
| `docs/traces/2026-04-15_non-complaint-theme-filter.md` | — | Defense-in-depth for `is_complaint` |
| `docs/traces/2026-06-28_cloud-run-cost-optimization-v2.md` | — | `max-instances=1` + WS auto-close reasoning |
| `docs/traces/2026-06-28_frontend-static-hosting-migration.md` | — | 10 GCS URL forms tested → all failed → Firebase |
| `docs/traces/2026-07-16_client-level-429-circuit-breaker.md` | — | `ee612ece0a71` cascade; singleton-breaker justification |
| `docs/traces/2026-07-17_vertex-cost-optimization-phase1.md` | — | The 28× gap; measurement-first decision |
| `docs/traces/2026-07-23_reddit-login-wall-rss-v3-pivot.md` | — | v3 pivot + prod run `cd32b8b47e94` |
| `docs/traces/2026-07-22_pushshift-candidate-mining-and-description-pivot.md` | — | Pool 87 → 167, 11.26 M rows, ERRATUM |
