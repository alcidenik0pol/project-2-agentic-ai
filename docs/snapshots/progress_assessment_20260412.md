# Progress Assessment — 2026-04-12

---

## WHAT THIS PROJECT ACTUALLY IS RIGHT NOW

A collection of **separate CLI scripts** that form a 4-step offline pipeline. There is no web interface. There is no agent framework. There is no single entry point. Each step is run manually from the command line, and its output becomes the input to the next step via a JSON file.

### The Pipeline (as actually run)

```
Step 0: Fetch raw posts          Step 1: Classify each post       Step 2: Cluster into themes      Step 3: Generate business ideas
scripts/fetch_sample_posts.py     scripts/classify_posts.py        scripts/cluster_themes.py        scripts/generate_hypothesis.py
        │                                │                               │                               │
        ▼                                ▼                               ▼                               ▼
  data/sample_posts.json      output/classified_posts_*.json  output/*_clustered.json     output/*_hypothesis.json
  (294 posts, no topic tag)   (each post tagged as             (15 clusters, 242 posts,     (3 business ideas with
                                complaint or not)                KMeans on embeddings)         evidence from clusters)
```

### How each step actually works

**Step 0 — Fetch posts** (`scripts/fetch_sample_posts.py`)
- Calls `RedditFetcher.fetch_posts_for_topic("python")` — but the topic is hardcoded to `"python"` in `scripts/run_fetcher.py:38`
- **Original vision** (from `docs/ideation/reddit/subreddit_urls.md`): 8 categories (Finance, Work, Relationships, Parenting, Mental Health, Health, Housing, Life Stage), ~40 subreddits total
- **What the code actually supports**: `app/collector/queries.py` has a `DOMAIN_SUBREDDITS` dict with **11 domains** (programming, python, javascript, webdev, data, devops, mobile, gaming, finance, fitness, startups) — each mapping to 3-5 subreddits. This does NOT match the original vision's categories at all. The original 40 subreddits are not in the code.
- **Per-query behavior**: `get_subreddits_for_topic()` returns **max 5 subreddits** by default. It matches the topic keyword against those 11 domains, takes top 3 from each match, then pads with up to 2 general complaint subs (AskReddit, rant, unpopularopinion, complaints). Unmatched topics get only the 2 generals.
- **What actually ran**: The data was fetched from **3 subreddits**: `["antiwork", "personalfinance", "ADHD"]` — likely passed explicitly as the `subreddits` parameter, since these don't match any keyword in `DOMAIN_SUBREDDITS`
- Builds a search query like `(python) AND (problem OR issue OR complaint OR ...)` using `COMPLAINT_TERMS` list (16 terms)
- Calls Reddit's public JSON API (`/r/{subreddit}/search.json`) — no auth required
- Rate-limited to 10 requests/minute
- Fetches up to 100 posts per topic, plus comments for posts with 100+ upvotes (capped at 30 posts)
- Saves to `data/sample_posts.json` with **30 posts**, and `data/sample_posts_20260407_145826.json` with **294 posts** — both from those same 3 subreddits
- **Reality**: This was run once. The data files in `data/` are the result. The pipeline since then has been operating on those static files. The 242 posts that made it through classification came from combining `sample_posts.json` (30) + `sample_posts_20260407_145826.json` (294) + `sample_posts_20260407_150700.json` (294), deduplicated to 242.

**Step 1 — Classify posts** (`scripts/classify_posts.py`)
- Loads JSON files from `data/` (those same 294 posts)
- For each post, sends the title + body text to an LLM with the `CLASSIFICATION_PROMPT` from `app/analyst/prompts.py`
- The LLM returns: `{theme, is_complaint, intensity}` — e.g., `"content policy update", false, "low"`
- Uses `PostClassifier.classify_batch()` which calls the LLM sequentially, one post at a time, with a 1-second delay between requests
- Provider: defaults to `gcloud` (Gemini 2.5 Flash via Vertex AI REST API), can also use LM Studio locally
- Saves to `output/classified_posts_20260407_230341.json`
- **Reality**: Classified 242 of the 294 posts. The rest presumably failed or were filtered.

**Step 2 — Cluster into themes** (`scripts/cluster_themes.py`)
- Loads the classified JSON from step 1
- Extracts all unique theme strings from the classifications (209 unique themes)
- Passes them through `ThemePreprocessor` (case normalization, dedup)
- Then `ThemeExpander` batches themes to the LLM to canonicalize them (merge similar ones like "banking switch question" and "financial advice seeking" under one name)
- Generates embeddings using Google's `text-embedding-004` model
- Runs KMeans clustering on the embeddings, testing k values 8-15, picks best by silhouette score
- The LLM then names each cluster based on its themes (e.g., "anti-work sentiment", "ai surveillance")
- Assigns each post to a cluster
- Saves to `output/classified_posts_20260407_230341_clustered.json` (7,750 lines, 15 clusters, 242 posts, 209 original themes → 15 named clusters, 169,001 total upvotes across all clusters)

**Cluster breakdown (by post count descending):**

| Cluster | Posts | Upvotes | Themes |
|---------|-------|---------|--------|
| ai surveillance | 45 | 38,555 | 38 |
| Workplace & | 28 | 23,615 | 27 |
| anti-work sentiment | 19 | 38,219 | 16 |
| avoiding impulse buys | 19 | 989 | 17 |
| Debt | 16 | 551 | 16 |
| Financial Guidance | 15 | 399 | 12 |
| Financial Debt & | 15 | 305 | 11 |
| Financial | 14 | 4,946 | 11 |
| ADHD and | 13 | 3,239 | 11 |
| Financial Planning & | 11 | 1,303 | 10 |
| car loan extension | 10 | 401 | 10 |
| Work Ethic | 10 | 3,872 | 10 |
| Tax Filing and | 9 | 1,111 | 7 |
| job recommendations | 7 | 2,083 | 7 |
| career advancement tips | 6 | 49,413 | 6 |

**Step 3 — Generate business hypotheses** (`scripts/generate_hypothesis.py`)
- Loads the clustered JSON from step 2
- Builds a summary table: for each cluster, extracts cluster name, post count, total upvotes, top 3 post titles by upvotes
- Sends this table to Gemini 2.5 Flash with `HYPOTHESIS_PROMPT` asking for 3 actionable business ideas
- The LLM returns structured JSON (enforced by `responseMimeType: application/json`)
- Parsed through Pydantic `HypothesisOutput` model
- Saves to `output/classified_posts_20260407_230341_hypothesis.json`
- Output: 3 ideas — "WorkLife Shield", "FinSense AI", "WorkerVoice" — each with evidence citing specific clusters

### What's NOT connected

- **No single entry point.** Each script must be run manually in sequence. There's no orchestrator.
- **No user input.** The topic was hardcoded to "python". The query builder (`app/collector/queries.py`) has a keyword-to-subreddit mapping for ~11 domains. If you type a topic that doesn't match any keyword, it falls back to general complaint subreddits (AskReddit, rant, etc.).
- **No frontend.** Zero web UI. All interaction is CLI.
- **No agent framework.** No LangGraph, CrewAI, OpenAI SDK, PydanticAI, or Google ADK. The code is plain Python classes calling each other.
- **No LLM tool calling.** The LLM never decides which tool to invoke. Python code calls the LLM, then Python code calls the next function. The LLM is a text-in/text-out resource, not an agent that orchestrates anything.
- **No deployment.** Runs locally only. No Dockerfile, no cloud config.
- **No README.md** at the project root.
- **The data pipeline ran once.** The `data/sample_posts*.json` files were fetched once and then reused across multiple classification/clustering runs. The fetcher is not integrated into the main pipeline — it's a separate manual step.

### LLM providers

Two providers, abstracted behind `LLMProvider` base class:

| Provider | File | Model | When used |
|----------|------|-------|-----------|
| GCloud | `app/analyst/providers/gcloud.py` | Gemini 2.5 Flash | Default. All production runs. REST API to Vertex AI. |
| LM Studio | `app/analyst/providers/lm_studio.py` | Qwen 3.5 27B (local) | Alternative. OpenAI-compatible API to localhost:1234. |

Both support: `classify_post()`, `generate_text()`, `generate_structured()`, `get_embeddings()` (GCloud only for embeddings).

### File inventory (non-exhaustive, key files only)

```
app/
  config.py                          — All env vars, singleton Config object
  collector/
    fetcher.py                       — RedditFetcher: fetch posts + comments from Reddit
    queries.py                       — build_complaint_query(), get_subreddits_for_topic()
    rate_limiter.py                  — Rate limit tracking
  reddit/
    client.py                        — RedditPublicAPI: raw HTTP to Reddit JSON API
  analyst/
    classifier.py                    — PostClassifier: LLM-based complaint classification
    clustering.py                    — ThemeClusterer: embeddings + KMeans + LLM naming
    hypothesis.py                    — HypothesisGenerator: business idea generation
    expansion.py                     — ThemeExpander: canonical theme naming via LLM
    preprocessing.py                 — ThemePreprocessor: case normalization, dedup
    prompts.py                       — CLASSIFICATION_PROMPT, RETRY_PROMPT
    cluster_prompts.py               — Cluster naming prompt
    expansion_prompts.py             — Theme expansion prompt
    hypothesis_prompts.py            — HYPOTHESIS_PROMPT
    models.py                        — 10 Pydantic models
    providers/
      base.py                        — LLMProvider ABC
      gcloud.py                      — GCloudProvider (Gemini via Vertex AI)
      lm_studio.py                   — LMStudioProvider (local via OpenAI API)
  models/
    reddit.py                        — RedditPost, RedditComment, PostWithComments, CollectionResult

scripts/
  fetch_sample_posts.py              — Step 0: fetch from Reddit
  classify_posts.py                  — Step 1: classify posts
  cluster_themes.py                  — Step 2: cluster into themes
  generate_hypothesis.py             — Step 3: generate business ideas
  run_fetcher.py                     — Hardcoded "python" topic fetcher
  + test/debug scripts

tests/
  test_clustering.py                 — ThemeClusterer tests (283 lines)
  test_expansion.py                  — ThemeExpander tests (214 lines)
  test_preprocessing.py              — Preprocessor tests (78 lines)
  test_rate_limit_metrics.py         — Rate limiter tests (74 lines)

output/                              — Pipeline artifacts (JSON files)
data/                                — Raw fetched posts (JSON files)
```

---

## GRADING ASSESSMENT (30 pts)

### Step 1: Collect (5 pts) — 5/5

| Sub-criterion | Status | Where |
|---------------|--------|-------|
| Real external data source | DONE | `app/reddit/client.py:21` `RedditPublicAPI` — Reddit public JSON API, no auth needed |
| Retrieved at runtime | DONE | `app/collector/fetcher.py:61` `fetch_posts_for_topic()` — builds and executes API calls live |
| Non-trivial dataset | DONE | 242+ posts, 7,750 lines of clustered output |
| Collection method: API integration | DONE | `app/reddit/client.py` — HTTP GET to `/r/{subreddit}/search.json` |
| Dynamic to different questions | DONE | `app/collector/queries.py:56` `build_complaint_query(topic)` + `queries.py:121` `get_subreddits_for_topic(topic)` map topic keywords to subreddits and build search queries |

### Step 2: EDA (5 pts) — 5/5

| Sub-criterion | Status | Where |
|---------------|--------|-------|
| At least one tool call over collected data | DONE | LLM classification (`app/analyst/classifier.py:19` `PostClassifier`), embeddings (`app/analyst/providers/gcloud.py` `get_embeddings()`), KMeans (`app/analyst/clustering.py:20` `ThemeClusterer`) |
| EDA method: Text analysis | DONE | Theme extraction, sentiment/intensity classification, topic clustering via embeddings + KMeans |
| Dynamic EDA | DONE | Different topics → different themes → different clusters. KMeans k auto-selected via silhouette score. |
| Specific findings surfaced | DONE | Ranked clusters with post counts + upvote totals. E.g., "ai surveillance" = 45 posts, 38,555 upvotes |

### Step 3: Hypothesize (5 pts) — 5/5

| Sub-criterion | Status | Where |
|---------------|--------|-------|
| Data-derived hypothesis | DONE | `app/analyst/hypothesis.py:21` `HypothesisGenerator.generate_hypotheses()` — takes `ClusteringResult` as input |
| Explains reasoning | DONE | Each `BusinessIdea.confidence_reasoning` + `HypothesisOutput.analysis_summary` |
| Cites evidence | DONE | `HypothesisEvidence` model: cluster_name, post_count, total_upvotes, supporting_post_titles |
| Communication format | DONE | Natural language summary + structured JSON output |

### Core Requirements (10 pts) — 1/10

| Requirement | Status | Details |
|-------------|--------|---------|
| Frontend (2 pts) | MISSING | No web UI. CLI scripts only. |
| Agent Framework (1 pt) | MISSING | Zero framework imports in entire codebase. Plain Python classes. |
| Tool Calling (1 pt) | MISSING | LLM never decides which tools to call. Python code orchestrates everything procedurally. |
| Non-trivial Dataset (1 pt) | DONE | Reddit API, 242+ posts per run |
| Multi-agent pattern (2 pts) | AT RISK | Two classes with different prompts exist (`PostClassifier` + `HypothesisGenerator`), but no framework-based handoff/orchestration pattern. May get partial credit (0-1/2). |
| Deployed (2 pts) | MISSING | Local only. No Dockerfile, no cloud config, no URL. |
| README.md (1 pt) | MISSING | No `README.md` at project root. `CLAUDE.md` exists but is a dev instruction file for Claude Code. |

### Grab Bag Electives (5 pts) — 5/5

| Elective | Status | Where |
|----------|--------|-------|
| Structured Output (2.5 pts) | DONE | 10 Pydantic models in `app/analyst/models.py`. GCloud provider uses `responseMimeType: application/json` to enforce valid JSON. |
| Artifacts (2.5 pts) | DONE | Timestamped JSON files in `output/`: classified posts, clustered analysis, hypothesis output. Written by each script. |

### Score Card

| Section | Max | Score |
|---------|-----|-------|
| Step 1: Collect | 5 | **5** |
| Step 2: EDA | 5 | **5** |
| Step 3: Hypothesize | 5 | **5** |
| Frontend | 2 | **0** |
| Agent framework | 1 | **0** |
| Tool calling | 1 | **0** |
| Non-trivial dataset | 1 | **1** |
| Multi-agent pattern | 2 | **0-1** |
| Deployed | 2 | **0** |
| README.md | 1 | **0** |
| Elective 1: Structured output | 2.5 | **2.5** |
| Elective 2: Artifacts | 2.5 | **2.5** |
| **TOTAL** | **30** | **18.5-19.5** |

---

## THE SIX GAPS (what to build next)

### Gap 1: Agent Framework (1 pt)
- **Current state**: Plain Python classes calling each other. No framework.
- **What's needed**: Wrap the pipeline in LangGraph, OpenAI Agents SDK, CrewAI, PydanticAI, or Google ADK.
- **This is the linchpin** — solving this also solves tool calling and multi-agent pattern.

### Gap 2: Tool Calling (1 pt)
- **Current state**: Python code calls functions directly. LLM is a text-in/text-out resource.
- **What's needed**: The LLM must decide which tools to invoke (e.g., "I need to fetch Reddit data" → calls the fetch tool).
- **Teacher's words**: "A tool call is when the agent decides to invoke [a tool], not automatic backend processing."

### Gap 3: Multi-agent pattern (2 pts, currently at risk for 0-1)
- **Current state**: `PostClassifier` and `HypothesisGenerator` are separate classes with different prompts, but called sequentially by CLI scripts with no handoff logic.
- **What's needed**: An explicit pattern like orchestrator-handoff, fan-out, or agent-as-tool-call via a framework.

### Gap 4: Frontend (2 pts)
- **Current state**: No web UI. Four separate CLI scripts.
- **What's needed**: A web interface the grader can load and interact with. Streamlit is the fastest path.

### Gap 5: Deployment (2 pts)
- **Current state**: Local only.
- **What's needed**: Deployed and accessible online. Streamlit Cloud or Hugging Face Spaces.

### Gap 6: README.md (1 pt)
- **Current state**: No `README.md` at project root.
- **What's needed**: Document all three steps with file + function/class name mappings per the grading checklist.

---

## DEPENDENCY MAP

```
Agent Framework (LangGraph)
  ├── unlocks → Tool Calling (LLM decides to invoke tools)
  └── unlocks → Multi-agent pattern (orchestrator-handoff)

Frontend (Streamlit)
  ├── wraps → The pipeline into a web UI
  └── enables → Deployment (Streamlit Cloud)

README.md → standalone, no dependencies, fastest to write
```

Recommended order: **Framework → Frontend → Deploy → README**

Framework first because it's the linchpin (3-4 points). Then frontend wraps it. Then deploy. Then README last since it documents the final state.
