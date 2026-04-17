# PainPan -- Reddit Pain Point Discovery

**Live app:** https://painpan-frontend-953400329307.us-central1.run.app/

Enter any topic or niche. The system queries Reddit, classifies complaints, clusters them by theme, and surfaces the top 5 buildable business ideas -- every finding traces back to a real Reddit post.

---

## Quick Start

### Prerequisites

- Python 3.11
- Node.js 22
- Conda (Miniconda or Anaconda)
- A Google Cloud service account key (for Vertex AI)
- A Reddit user agent string (optional: Reddit OAuth credentials for higher rate limits)

### 1. Backend Setup

```bash
# Create and activate conda environment
conda create -n agentic-ai-p2 python=3.11 -y
conda activate agentic-ai-p2

# Install Python dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Copy and fill in environment variables
cp .env.example .env
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

### 3. Run Locally

```bash
# Terminal 1: Start the backend (from project root)
conda activate agentic-ai-p2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8901 --reload

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

The frontend runs at `http://localhost:3456`, the backend at `http://localhost:8901`.

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
                  AgentOrchestrator (sync, in thread pool)
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
4. Agent handoff uses a convention: when an agent responds with `HANDOFF_TO_AGENT: <name>`, the runner (`app/agents/runner.py`) starts the next agent with a context message.

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

## Project Structure

```
project-2/
├── app/                          # Python agent pipeline
│   ├── config.py                 # Single source of truth for all env vars
│   ├── agents/                   # Multi-agent framework
│   │   ├── base.py               # Agent base class with tool execution loop
│   │   ├── runner.py             # AgentOrchestrator: manages agent handoff chain
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
| **Agent Framework** | Custom multi-agent runner with tool calling |
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
