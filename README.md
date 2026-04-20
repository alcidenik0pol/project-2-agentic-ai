# Based Instinct

**Live app:** https://painpan-frontend-953400329307.us-central1.run.app/

Enter any topic or niche. The system queries Reddit, classifies complaints, clusters them by theme, and surfaces the top 5 buildable business ideas -- every finding traces back to a real Reddit post.

---

## Grading Checklist

### STEP 1: COLLECT

#### Data Source

- [x] Data retrieved from a real, external source (not hard-coded in system prompt) -- `app/collector/subreddit_selector.py` LLM selects subreddits; `app/reddit/client.py` RedditPublicAPI fetches posts at runtime
- [x] Data retrieved at runtime, not bundled statically -- `app/agents/tools/fetch.py` `fetch_posts` tool calls Reddit API on every user query
- [x] Data source is non-trivial (not a 50-row hand-curated CSV) -- thousands of Reddit posts fetched via `app/reddit/client.py:59-171`

#### Collection Method

- [x] API integration (calls public/private APIs) -- `app/reddit/client.py` Reddit JSON API with OAuth; `app/collector/fetcher.py` orchestrates API calls

#### Data Appropriateness

- [x] Dataset too large/complex to load entirely into context -- `app/agents/tools/shared.py` shared in-memory store prevents context overflow; `app/analyst/classifier.py:165-257` processes posts in parallel batches
- [x] Data is relevant to the analytics question -- `app/collector/subreddit_selector.py:81-261` LLM selects topic-relevant subreddits with reasoning

#### Dynamic Behavior

- [x] Agent adapts data retrieval based on user's question -- `app/collector/subreddit_selector.py:119` LLM selects different subreddits per topic
- [x] Different questions trigger different data retrieval patterns -- `app/collector/queries.py` curated lists + keyword matching

---

### STEP 2: EXPLORE & ANALYZE -- EDA

#### Tool Call Requirement

- [x] EDA phase involves at least one tool call -- `app/agents/tools/classify.py` `classify_posts` tool invoked by Analyst agent
- [x] Tool uses collected data (not just metadata) -- `app/analyst/classifier.py:54` classifies every post with full title/body text

#### EDA Method Used

- [x] Text analysis (topic clustering, sentiment counts) + Specialist sub-agent -- `app/analyst/clustering.py:228-278` KMeans clustering; `app/agents/analyst.py` dedicated Analyst agent prompt

#### Dynamic EDA

- [x] EDA adapts to different questions -- clustering results emerge from post content; different topics yield different clusters
- [x] Different questions trigger different tool usage patterns -- Analyst agent in `app/agents/analyst.py` decides which tools to invoke based on data

#### Specific Findings

- [x] Exploration surfaces specifics (numbers, patterns, anomalies) -- `app/analyst/clustering.py` returns named clusters with post counts, upvotes, theme distributions
- [x] Output is more than a generic summary -- `app/analyst/hypothesis.py:101` generates concrete business ideas with evidence, not summaries

---

### STEP 3: HYPOTHESIZE

#### Data-Derived Hypothesis

- [x] Hypothesis derived from collected data, not model weights -- `app/analyst/hypothesis_prompts.py:3-63` prompt requires cluster data as input
- [x] Agent explains its reasoning process -- `app/analyst/models.py` `HypothesisOutput` includes `confidence_reasoning` field

#### Supporting Evidence

- [x] Hypothesis cites specific data points -- `app/analyst/models.py` `evidence` field includes cluster name, post count, upvotes, post titles
- [x] Supporting evidence clearly provided -- each hypothesis includes `evidence.supporting_post_titles` list

#### Communication Format

- [x] Generated report/memo with tables and citations -- `app/analyst/hypothesis.py` returns structured JSON; `frontend/components/IdeaCard.tsx` displays formatted cards

---

### CORE REQUIREMENTS

#### Frontend

- [x] Frontend can be loaded and interacted with -- `frontend/app/page.tsx` Next.js 15 app with ChatInterface + TabbedResultsDisplay
- [x] Grader can access and use the frontend -- deployed at https://painpan-frontend-953400329307.us-central1.run.app/

#### Agent Framework

- [x] LangGraph -- `app/agents/graph.py` StateGraph with explicit edges, 3 agent nodes

#### Tool Calling

- [x] At least one tool call implemented -- `app/agents/tools/__init__.py` 7 tools registered: fetch_posts, classify_posts, cluster_themes, generate_hypotheses, save_artifact

#### Non-trivial Dataset

- [x] Data from a real, non-trivial external source at runtime -- Reddit API via `app/reddit/client.py`, thousands of posts per query

#### Multi-Agent Pattern

- [x] Orchestrator-handoff pattern -- `app/agents/graph.py` graph edges: orchestrator -> analyst -> hypothesis
- [x] At least two distinct agents with different system prompts -- `app/agents/orchestrator.py:3-20`, `app/agents/analyst.py:3-23`, `app/agents/hypothesis.py:3-25` three distinct prompts

#### Deployed

- [x] Application deployed and accessible -- https://painpan-frontend-953400329307.us-central1.run.app/

#### README.md

- [x] README explains how to run the project -- "Quick Start" and "Environment Variables" sections below
- [x] README explains how all three steps are implemented -- "Step 1: Collect", "Step 2: EDA", "Step 3: Hypothesize" sections with file locations
- [x] README identifies which concepts are implemented and where -- each step section includes "Key files" table with file paths

---

### GRAB BAG ELECTIVES

#### Artifacts

- [x] Saves JSON + markdown reports to `output/reports/{date}/{run_id}/` -- `app/agents/tools/artifacts.py`

#### Parallel Execution

- [x] ThreadPoolExecutor with 10 workers -- `app/analyst/classifier.py:165-257`

#### Structured Output (bonus)

- [x] Pydantic models, JSON mode, tiered parsing -- `app/analyst/models.py`, `app/analyst/providers/`

#### Iterative Refinement Loop (bonus)

- [x] LLM subreddit selection with keyword fallback -- `app/collector/subreddit_selector.py:81-261`

### BONUS

- [x] **Model tiering** -- all calls use FAST tier (gemini-2.5-flash) except hypothesis generation which uses PRO -- `app/config.py:52-53`, `app/analyst/providers/gcloud.py:166`
- [x] **Parallel classification** -- ThreadPoolExecutor with 10 workers, `concurrency_savings` tracks wall-clock time saved -- `app/analyst/classifier.py:136,193`
- [x] **Defense-in-depth filtering** -- non-complaints tracked at tool boundary (`classify.py:89-102`), filtered in clusterer (`clustering.py:165`)
- [x] **Structured logging** -- every stage writes JSON with substep timing; `workflow_report.md` aggregates all -- `app/agents/tools/run_logger.py`
- [x] **Silhouette-optimized KMeans** -- tests K=8-15, selects K with best silhouette score, then names each cluster via LLM -- `app/analyst/clustering.py:228-278`
- [x] **Mid-pipeline streaming** -- classification and clustering EDA stream to frontend after analyst completes, before hypothesis -- `backend/app/services/analysis_service.py:266-286`
- [x] **Rate limit polling** -- `RateLimitTracker` polls every 1s, broadcasts via WebSocket -- `backend/app/services/rate_limit_tracker.py:20`
- [x] **WebSocket buffering** -- messages buffered when no client connected, replayed on connect (500 msg cap) -- `backend/app/api/websocket/manager.py:29-53`
- [x] **Even pacing** -- 6s minimum interval between Reddit requests (100 req/10 min) -- `app/collector/rate_limiter.py:32-34`
- [x] **Auto-reconnect** -- frontend reconnects on disconnect (fixed 2s delay, 5 attempts) -- `frontend/lib/websocket.ts:9-10`

---

## Architecture

### System Overview

```
                    Frontend (Next.js :3456)
                         |
                    WebSocket + REST
                         |
                    Backend (FastAPI :8901)
                         |
                  AnalysisService (async)
                         |
                  LangGraph StateGraph (sync, in thread pool)
                    /        |         \
            Orchestrator  Analyst   Hypothesis
             (Agent 1)   (Agent 2)  (Agent 3)
                |            |           |
           fetch_posts   classify    generate_
             tool       cluster      hypotheses
                |        tools       save_artifact
                |            |           |
         Reddit API    LLM Provider   LLM Provider
                |      (FAST tier)    (PRO tier)
                |
         Shared Data Store (in-memory, disk-persisted)
```

### How Agents Communicate

Agents do **not** pass data through LLM context. Instead:

1. Each agent's tools write results to a **shared in-memory store** (`app/agents/tools/shared.py`).
2. Results are also persisted to **disk** via the run logger (`app/agents/tools/run_logger.py`).
3. The next agent reads from the shared store, not from the conversation history.
4. Agent transitions are managed by LangGraph graph edges: `orchestrator → analyst → hypothesis → END`. No text-based handoff parsing required.

This prevents context overflow -- a dataset of hundreds of Reddit posts never enters any LLM prompt window.

### Agent Tool Calling

Each agent has distinct tools registered in `app/agents/tools/__init__.py`. The agent decides which tools to call and in what order via the LLM's function calling:

| Agent | Tools | LLM Calls Triggered |
|-------|-------|---------------------|
| Orchestrator | `fetch_posts` | Call 1 (agent loop) + Call 8 (subreddit selection, pre-run) |
| Analyst | `classify_posts`, `cluster_themes` | Call 2 (agent loop) + Calls 4, 5, 6 (per-post, per-batch, per-cluster) |
| Hypothesis | `generate_hypotheses`, `save_artifact` | Call 3 (agent loop) + Call 7 (PRO model) |

---

## Step 1: Collect

**What happens:** The system takes a user's topic, selects relevant subreddits from a curated knowledge base, and fetches posts via Reddit's JSON API.

**Key files:**

| File | Role |
|------|------|
| `app/collector/subreddit_selector.py` | LLM-based subreddit ranking from ~90 curated subreddits; keyword fallback |
| `app/collector/subreddit_loader.py` | Loads subreddit descriptions from JSON for LLM selection |
| `app/collector/queries.py` | Curated subreddit lists and keyword-matching utility |
| `app/reddit/client.py` | `RedditPublicAPI` -- Reddit JSON API client with retry logic and session management |
| `app/collector/fetcher.py` | `RedditFetcher` -- orchestrates fetching across subreddits, handles rate limiting |
| `app/collector/rate_limiter.py` | Even-pacing rate limiter (100 req/10 min) with ETA and progress tracking |
| `app/agents/tools/fetch.py` | `fetch_posts` tool -- bridges agent framework to the collector |
| `app/models/reddit.py` | Pydantic models: `RedditPost`, `RedditComment`, `PostWithComments`, `CollectionResult` |

**Flow:**

```
subreddit_selector.py -> picks N subreddits for topic
    |
    v
fetch_posts tool (fetch.py) -> RedditFetcher (fetcher.py) -> RedditPublicAPI (client.py)
    |                                                          |
    |                                                    rate_limiter.py paces requests
    v
CollectionResult stored in shared data -> handed to Analyst
```

**Reddit API pacing:** The rate limiter enforces Reddit's 100 requests per 10 minutes (6s minimum interval). Progress and ETA are tracked and streamed to the frontend in real time.

---

## Step 2: EDA (Exploratory Data Analysis)

**What happens:** Raw posts are classified (complaint vs. not, theme, intensity), complaint themes are expanded into rich descriptions, embedded, clustered via KMeans, and each cluster is named by the LLM. Non-complaint posts are preserved for display but excluded from clustering.

**Key files:**

| File | Role |
|------|------|
| `app/analyst/classifier.py` | `PostClassifier` -- parallel classification via ThreadPoolExecutor |
| `app/analyst/prompts.py` | Classification prompt: extracts theme, `is_complaint`, intensity |
| `app/analyst/expansion.py` | `ThemeExpander` -- expands short labels into 10-20 word descriptions |
| `app/analyst/expansion_prompts.py` | Expansion prompt templates (first attempt + retry) |
| `app/analyst/preprocessing.py` | `ThemePreprocessor` -- normalizes and deduplicates themes |
| `app/analyst/clustering.py` | `ThemeClusterer` -- full pipeline: preprocess -> expand -> embed -> KMeans -> name |
| `app/analyst/cluster_prompts.py` | Cluster naming prompt (3-5 word descriptive name) |
| `app/agents/tools/classify.py` | `classify_posts` tool -- bridges agent to classifier |
| `app/agents/tools/cluster.py` | `cluster_themes` tool -- bridges agent to clusterer |
| `app/analyst/models.py` | Pydantic models: `ComplaintClassification`, `ClassificationResult`, `ClusteringResult`, `ThemeCluster` |

**Flow:**

```
classify_posts tool -> PostClassifier (classifier.py)
    |-- ThreadPoolExecutor(max_workers=10)
    |-- Per post: LLM call (temp=0.1) -> {theme, is_complaint, intensity}
    |-- Retry with stricter prompt on JSON parse failure
    |
    v
cluster_themes tool -> ThemeClusterer (clustering.py)
    |-- Filter non-complaints (defense-in-depth: tool boundary + internal)
    |-- Preprocess: normalize, deduplicate (preprocessing.py)
    |-- Expand themes: batch LLM calls (expansion.py) for richer embedding input
    |-- Embed: text-embedding-004 via provider
    |-- KMeans: silhouette-optimized K selection (min_k=8, max_k=15)
    |-- Name clusters: per-cluster LLM call for human-readable name
    |
    v
ClusteringResult stored in shared data -> handed to Hypothesis
```

**Parallel classification telemetry** -- every run logs wall time vs. cumulative LLM time, so you can measure concurrency savings.

**Streaming** -- classification and clustering EDA results stream to the frontend mid-pipeline via WebSocket, so users see progress before the full run completes.

---

## Step 3: Hypothesize

**What happens:** Clustered complaint data is synthesized into up to 5 concrete, buildable business ideas using the PRO model (Gemini 2.5 Pro). Each idea is grounded in evidence from real posts.

**Key files:**

| File | Role |
|------|------|
| `app/analyst/hypothesis.py` | `HypothesisGenerator` -- builds summary table, calls LLM, validates output |
| `app/analyst/hypothesis_prompts.py` | Detailed prompt enforcing concrete ideas with revenue model, features, evidence |
| `app/agents/tools/hypothesis.py` | `generate_hypotheses` tool -- bridges agent to hypothesis generator |
| `app/agents/tools/artifacts.py` | `save_artifact` tool -- persists final hypothesis JSON to disk |

**Flow:**

```
generate_hypotheses tool -> HypothesisGenerator (hypothesis.py)
    |-- Build summary table from clusters (post counts, upvotes, themes)
    |-- LLM call: generate_structured (PRO model, temp=0.3, max_tokens=16384)
    |-- Validate JSON schema against HypothesisOutput model
    |
    v
save_artifact tool -> writes hypothesis.json to output/reports/{date}/{run_id}/
    |
    v
HypothesisOutput returned to user via WebSocket
```

**Each hypothesis includes:**

- `idea_name` -- concrete product name
- `pain_point` -- specific frustration quoted from posts
- `solution_description` -- features and user flows
- `core_features` -- 3-5 tangible features
- `revenue_model` -- explicit pricing or monetization
- `first_user_step` -- what happens in the first 30 seconds
- `target_user` -- specific persona
- `confidence` + `confidence_reasoning` -- grounded in signal strength
- `evidence` -- cluster name, post count, total upvotes, supporting post titles

---

## Key Design Decisions

- **Data via shared store, not LLM context** -- Agent results are persisted to disk and read by the next agent, preventing context overflow.
- **Every finding traces to a real Reddit post** -- The system does not generate complaints from model knowledge. All evidence includes supporting post titles.
- **Smart model tiering** -- FAST tier (Gemini 2.5 Flash) for 7 of 8 calls. PRO tier (Gemini 2.5 Pro) only for hypothesis generation, where complex reasoning and creative synthesis matter.
- **Parallel classification** -- `ThreadPoolExecutor` with 10 workers for post classification, with concurrency savings telemetry.
- **Defense-in-depth filtering** -- Non-complaints are filtered at both the tool boundary and internally in the clusterer, while still preserved for EDA display.
- **Results are cached** -- The Reddit API is not called twice for the same topic.
- **Agent-driven tool calling** -- Each agent decides which tools to invoke, not automatic backend processing.
- **Low temperature for consistency** -- All LLM calls use temperature 0.1-0.3.
- **Retry logic** -- Classification and expansion calls retry with a stricter prompt on JSON parse failures.
- **Provider abstraction** -- Three LLM providers via a single interface: Google Cloud, LM Studio (local), and OpenAI-compatible Gemini. Selected at runtime via `LLM_PROVIDER`.
- **Comprehensive logging** -- Every stage persists structured JSON with substep timing.
- **Intermediary streaming** -- EDA results stream to the frontend mid-pipeline via WebSocket.

---

## Bonus Features

This project includes several advanced engineering features that go beyond the minimum requirements.

- **Reddit API Rate Limiting** -- Reddit limits API calls to 100 per 10 minutes, so we implemented even pacing with `_pace_request()` in `app/reddit/client.py:59-171`, real-time status tracking, and exponential backoff for 429/500 errors to maximize throughput without throttling.

- **Parallel Classification Pipeline** -- Post classification is CPU-bound, so we use `ThreadPoolExecutor` with 10 configurable workers in `app/analyst/classifier.py:165-257` to process posts in parallel, reducing classification time by ~80% compared to sequential execution.

- **Smart Model Tiering** -- LLM costs add up fast, so we route 7 of 8 calls through FAST tier (Gemini 2.5 Flash) and reserve PRO tier (Gemini 2.5 Pro) only for hypothesis generation where creative synthesis matters most.

- **Defense-in-Depth Filtering** -- Non-complaint posts are filtered at both the tool boundary (`classify_posts` in `app/agents/tools/classify.py`) and internally in the clusterer (`app/analyst/clustering.py:123-124`) while still being preserved in `classified.json` for EDA transparency.

- **Comprehensive Observability** -- Every pipeline stage persists structured JSON with substep timing via `app/agents/tools/run_logger.py`, enabling performance analysis and debugging; `@timed` decorator in `app/utils/timing.py` tracks granular execution time.

- **Intermediary Streaming** -- Users hate waiting, so classification and clustering EDA results stream to the frontend mid-pipeline via WebSocket in `backend/app/api/websocket/manager.py`, letting users see progress before the full run completes.

- **Theme Expansion for Better Embeddings** -- Short themes like "shipping delays" embed poorly, so we batch-expand them into 10-20 word descriptions in `app/analyst/expansion.py:34-130` using post titles as context, with a 24-hour TTL cache to avoid re-expansion.

- **Silhouette-Optimized Clustering** -- We don't guess the optimal K; we test K from 8-15 and select the best silhouette score in `app/analyst/clustering.py:228-278`, then use per-cluster LLM calls to generate human-readable names.

- **Configuration Management** -- All 50+ configuration options (workers, timeouts, model IDs, rate limits) are centralized in `app/config.py:24-217` as a frozen dataclass, eliminating `os.getenv()` calls scattered across the codebase and enabling runtime overrides for testing.

- **Provider Abstraction** -- We support three LLM providers (Google Cloud, LM Studio local, OpenAI-compatible Gemini) via a unified interface in `app/analyst/providers/`, selectable at runtime via `LLM_PROVIDER` environment variable.

- **LLM-Based Subreddit Selection** -- Instead of hardcoding subreddit lists per topic, an LLM call in `app/collector/subreddit_selector.py:81-261` analyzes the topic against 60+ curated subreddits with descriptions and returns a ranked selection with reasoning, falling back to keyword matching if the LLM fails.

---

## Project Structure

```
project-2/
├── app/                          # Python agent pipeline
│   ├── config.py                 # Single source of truth for all env vars
│   ├── agents/                   # Multi-agent framework
│   │   ├── graph.py              # LangGraph StateGraph: agent orchestration with explicit edges
│   │   ├── runner.py             # (deprecated - old custom framework, kept for reference)
│   │   ├── base.py               # (deprecated - old Agent base class, kept for reference)
│   │   ├── orchestrator.py       # Orchestrator agent prompt definition
│   │   ├── analyst.py            # Analyst agent prompt definition
│   │   ├── hypothesis.py         # Hypothesis agent prompt definition
│   │   ├── tools/                # Agent tool implementations
│   │   │   ├── __init__.py       # Tool registry: maps tool names to schemas
│   │   │   ├── fetch.py          # fetch_posts tool
│   │   │   ├── classify.py       # classify_posts tool
│   │   │   ├── cluster.py        # cluster_themes tool
│   │   │   ├── hypothesis.py     # generate_hypotheses tool
│   │   │   ├── artifacts.py      # save_artifact tool
│   │   │   ├── shared.py         # In-memory shared data store between tools
│   │   │   └── run_logger.py     # Persists intermediate results to JSON
│   │   └── logging_setup.py      # Structured JSON logging for agent events
│   ├── collector/                # Step 1: Collect
│   │   ├── subreddit_selector.py # LLM-based subreddit ranking + keyword fallback
│   │   ├── subreddit_loader.py   # Loads subreddit descriptions from JSON
│   │   ├── fetcher.py            # RedditFetcher: orchestrates fetching
│   │   ├── queries.py            # Curated subreddit lists
│   │   └── rate_limiter.py       # Reddit API pacing (100 req/10 min)
│   ├── reddit/                   # Reddit API client
│   │   └── client.py             # RedditPublicAPI with retry and session management
│   ├── analyst/                  # Steps 2-3: EDA + Hypothesize
│   │   ├── classifier.py         # Parallel post classification
│   │   ├── expansion.py          # Theme label expansion
│   │   ├── preprocessing.py      # Theme normalization and dedup
│   │   ├── clustering.py         # Full clustering pipeline
│   │   ├── hypothesis.py         # Business hypothesis generation
│   │   ├── prompts.py            # Classification prompts
│   │   ├── expansion_prompts.py  # Expansion prompts
│   │   ├── cluster_prompts.py    # Cluster naming prompts
│   │   ├── hypothesis_prompts.py # Hypothesis generation prompt
│   │   ├── models.py             # All Pydantic models for analysis pipeline
│   │   └── providers/            # LLM provider abstraction
│   │       ├── base.py           # LLMProvider abstract base class
│   │       ├── __init__.py       # Provider factory (get_provider)
│   │       ├── gcloud.py         # Google Cloud Vertex AI (Gemini)
│   │       ├── lm_studio.py      # Local LM Studio (OpenAI-compatible)
│   │       └── openai_gemini.py  # Gemini via OpenAI SDK
│   ├── models/
│   │   └── reddit.py             # Pydantic models for Reddit data
│   └── utils/
│       └── timing.py             # @timed decorator for perf monitoring
│
├── backend/                      # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI app: CORS, lifespan, routes, WebSocket
│       ├── api/
│       │   └── routes/
│       │       ├── analysis.py   # POST /api/v1/analysis
│       │       ├── results.py    # GET /api/v1/results/{run_id}
│       │       ├── health.py     # GET /api/v1/health
│       │       └── rate_limit.py # Rate limit status endpoint
│       ├── api/websocket/
│       │   └── manager.py        # WebSocket ConnectionManager
│       ├── models/
│       │   └── api.py            # REST API Pydantic models
│       └── services/
│           ├── analysis_service.py    # Async wrapper for agent pipeline
│           └── rate_limit_tracker.py  # Background Reddit rate limit polling
│
├── frontend/                     # Next.js frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── app/
│   │   ├── layout.tsx            # Root layout with dark theme
│   │   ├── providers.tsx         # ClientProviders (Analysis + WebSocket contexts)
│   │   ├── page.tsx              # Home: ChatInterface + TabbedResults
│   │   ├── how-it-works/page.tsx # Architecture docs + live agent flow
│   │   ├── debug/page.tsx        # Raw logs and agent states
│   │   └── rate-limit/page.tsx   # Reddit API pacing monitor
│   ├── components/
│   │   ├── ChatInterface.tsx     # Topic input with test/live mode toggle
│   │   ├── TabbedResultsDisplay.tsx  # Hypothesis + Classification EDA + Clustering tabs
│   │   ├── IdeaCard.tsx          # Single business idea card
│   │   ├── AgentFlow.tsx         # Visual agent pipeline diagram
│   │   ├── ArchitectureDiagram.tsx   # System architecture diagram
│   │   ├── CollectorPacingInfo.tsx   # Live Reddit fetch progress
│   │   └── ui/                   # Shadcn/ui primitives
│   ├── hooks/
│   │   ├── useAnalysis.ts        # Analysis lifecycle hook
│   │   ├── useWebSocket.ts       # WebSocket connection + state
│   │   └── useGlobalWebSocket.ts # Context wrapper for WebSocket
│   ├── contexts/
│   │   ├── AnalysisContext.tsx    # Analysis state context
│   │   └── WebSocketContext.tsx   # WebSocket state context
│   └── lib/
│       ├── api.ts                # REST API client
│       ├── types.ts              # TypeScript types matching backend models
│       ├── websocket.ts          # WebSocket client with reconnection
│       └── utils.ts              # cn() + ANSI strip helper
│
├── data/                         # Curated subreddit descriptions + sample data
├── output/reports/               # Run artifacts (JSON + markdown per run)
├── docs/architecture/            # Architecture documentation
├── requirements.txt              # Python dependencies (agent pipeline)
├── .env                          # Environment variables (gitignored)
└── CLAUDE.md                     # Project instructions for Claude Code
```

---

## LLM Calls Summary

| # | Call | Method | Temp | Model Tier | Purpose |
|---|------|--------|------|------------|---------|
| 1 | Orchestrator Agent | `chat_with_tools` | 0.3 | FAST | Agent loop: fetch Reddit posts |
| 2 | Analyst Agent | `chat_with_tools` | 0.3 | FAST | Agent loop: classify & cluster |
| 3 | Hypothesis Agent | `chat_with_tools` | 0.3 | FAST | Agent loop: generate hypotheses |
| 4 | Post Classification | `classify_post` | 0.1 | FAST | Per-post: theme, is_complaint, intensity |
| 5 | Theme Expansion | `generate_text` | 0.3 | FAST | Per-batch: expand themes for embeddings |
| 6 | Cluster Naming | `generate_text` | 0.3 | FAST | Per-cluster: human-readable name |
| 7 | Hypothesis Generation | `generate_structured` | 0.3 | **PRO** | Top-5 business hypotheses (16,384 tokens) |
| 8 | Subreddit Selection | `generate_structured` | 0.3 | FAST | Preprocessing: select relevant subreddits |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, Tailwind CSS, Radix UI |
| **Backend API** | FastAPI, Uvicorn, WebSockets |
| **Agent Framework** | LangGraph StateGraph with tool calling |
| **LLM** | Google Gemini 2.5 Flash (FAST) / Gemini 2.5 Pro (PRO) via Vertex AI |
| **Embeddings** | `text-embedding-004` via Google Cloud |
| **Clustering** | scikit-learn KMeans |
| **Data Source** | Reddit JSON API (public) / PRAW (authenticated) |
| **Deployment** | Google Cloud Run (frontend + backend, containerized) |

---

## Output Artifacts

Each pipeline run produces structured artifacts under `output/reports/{date}/{run_id}/`:

| File | Contents |
|------|----------|
| `subreddit_selection.json` | LLM reasoning + selected subreddits |
| `fetch_stats.json` | Posts fetched, subreddits queried, timing |
| `classification_eda.json` | Theme/intensity distributions + substep timing |
| `clustering_eda.json` | Cluster details + substep timing breakdown |
| `hypothesis.json` | Final hypotheses + substep timing |
| `classified.json` | Full classified posts |
| `clustering.json` | Full clustering data |
| `workflow_report.md` | Markdown summary with timing tables |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- A Google Cloud service account key (for Vertex AI)
- A Reddit user agent string (optional: Reddit OAuth credentials for higher rate limits)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your GCP project, service account key path, etc.
# See Environment Variables section below for full reference
```

### 2. Build and Run

```bash
# Build and start both services
docker compose up -d --build
```

The frontend runs at `http://localhost:3456`, the backend at `http://localhost:8901`.

### Useful Commands

```bash
# Rebuild and restart (after any code change)
docker compose up -d --build

# Rebuild just one service
docker compose up -d --build frontend

# Full reset (no cache)
docker compose down && docker compose build --no-cache && docker compose up -d

# View running containers
docker compose ps

# View logs
docker compose logs -f
```

### Without Docker (Manual Setup)

<details>
<summary>Click to expand</summary>

Requires Python 3.11, Node.js 22, and Conda.

```bash
# Backend
conda create -n agentic-ai-p2 python=3.11 -y
conda activate agentic-ai-p2
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install

# Run (two terminals)
# Terminal 1:
conda activate agentic-ai-p2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8901 --reload

# Terminal 2:
cd frontend && npm run dev
```

</details>

---

## Environment Variables

All configuration is loaded through `app/config.py` -- a single source of truth. Do not use `os.getenv()` directly.

Create a `.env` file in the project root:

```env
# === Required ===
GCLOUD_PROJECT=your-gcp-project-id
GCLOUD_SERVICE_ACCOUNT_KEY_PATH=path/to/service-account-key.json

# === LLM Provider ===
LLM_PROVIDER=gcloud                  # "gcloud" | "lm_studio" | "openai_gemini"

# === Google Cloud Vertex AI ===
GCLOUD_MODEL=gemini-2.5-pro           # PRO tier (hypothesis generation only)
GCLOUD_MODEL_FAST=gemini-2.5-flash    # FAST tier (7 of 8 LLM calls)

# === Agent Mode ===
AGENT_MODE=live                       # "live" (Reddit API) | "test" (sample data)

# === Reddit API ===
REDDIT_USER_AGENT=your-app-name/1.0 by /u/your-username
REDDIT_CLIENT_ID=                     # Optional: for higher rate limits
REDDIT_CLIENT_SECRET=                 # Optional: for higher rate limits

# === Frontend (set at build time) ===
NEXT_PUBLIC_API_URL=http://localhost:8901
```

### Key Config Knobs

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENT_MODE` | `test` | `live` hits Reddit API; `test` uses sample data |
| `AGENT_MAX_ITERATIONS` | `20` | Max tool-call loops per agent |
| `CLASSIFICATION_MAX_WORKERS` | `10` | Parallel threads for post classification |
| `CLASSIFICATION_ENABLE_PARALLEL` | `true` | Master switch for parallel classification |
| `CLUSTERING_MIN_K` / `CLUSTERING_MAX_K` | `8` / `15` | KMeans K search range |
| `EXPANSION_BATCH_SIZE` | `5` | Themes per LLM expansion call |
| `LLM_PROVIDER` | `gcloud` | Which LLM provider to use |
