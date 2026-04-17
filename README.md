# PainPan -- Reddit Pain Point Discovery

**Live app:** https://painpan-frontend-953400329307.us-central1.run.app/

Enter any topic or niche. The system queries Reddit, classifies complaints, clusters them by theme, and surfaces the top 5 buildable business ideas -- every finding traces back to a real Reddit post.

## How It Works

The pipeline has 8 distinct LLM call types across three agents and a preprocessing step:

```
User Query
    |
    v
[Call 8] Subreddit Selection (FAST) -> LLM picks relevant subreddits from curated knowledge base
    |
    v
[Call 1] Orchestrator Agent (FAST) -> fetch_posts tool hits Reddit API (OAuth)
    |
    v
[Call 2] Analyst Agent (FAST)
    |-- [Call 4] classify_post x N (FAST, parallel, 10 workers) -- theme + intensity per post
    |-- [Call 5] expand_themes (FAST, batched) -- richer descriptions for embeddings
    |-- embeddings + KMeans clustering
    |-- [Call 6] name clusters (FAST, one per cluster)
    |
    v
[Call 3] Hypothesis Agent (FAST) -> delegates to [Call 7] generate_structured (PRO)
    |
    v
Top 5 Ranked Business Ideas + Report
```

### Preprocessing: Subreddit Selection

Before any agent runs, an LLM call ranks ~90 curated subreddits across 11 domains (Finance, Work, Relationships, Health, Housing, Entertainment, etc.) by relevance to the user's topic. Falls back to keyword matching if the LLM call fails.

### Agent 1: Orchestrator

Takes the user's topic and uses a `fetch_posts` tool to gather Reddit posts from the selected subreddits via the Reddit API (OAuth). Hands off to the Analyst with a summary of what was collected.

### Agent 2: Analyst

1. **Classify** -- Each post gets an LLM call to extract complaint theme, `is_complaint` flag, and intensity (low/medium/high). Runs in parallel via `ThreadPoolExecutor` (10 workers default).
2. **Expand themes** -- Short 2-3 word theme labels are expanded into 10-20 word descriptions (in batches of ~5) for better embedding quality.
3. **Embed & cluster** -- Expanded themes are converted to embeddings (`text-embedding-004`), then grouped via KMeans.
4. **Name clusters** -- Each cluster receives a human-readable name from the LLM.

### Agent 3: Hypothesis

Takes the ranked clusters and generates up to 5 concrete business hypotheses. Each hypothesis includes a product name, pain point (quoted from posts), solution description, core features, revenue model with pricing, first user step (30 seconds), target user persona, confidence level with reasoning, and evidence linkage (cluster name, post count, upvotes, supporting post titles).

## Key Design Decisions

- **Data via shared store, not LLM context** -- Agent results are persisted to disk and read by the next agent, preventing context overflow.
- **Every finding traces to a real Reddit post** -- The system does not generate complaints from model knowledge. All evidence includes supporting post titles.
- **Smart model tiering** -- FAST tier (Gemini 2.5 Flash) for 7 of 8 calls. PRO tier (Gemini 2.5 Pro) only for hypothesis generation, where complex reasoning and creative synthesis matter. Good cost/performance balance.
- **Parallel classification** -- `ThreadPoolExecutor` with 10 workers for post classification, with concurrency savings telemetry so you can measure actual throughput gains.
- **Defense-in-depth filtering** -- Non-complaints are filtered at both the tool boundary and internally in the clusterer, while still preserved for EDA display.
- **Results are cached** -- The Reddit API is not called twice for the same topic.
- **Agent-driven tool calling** -- Each agent decides which tools to invoke based on its current step, not automatic backend processing.
- **Low temperature for consistency** -- All LLM calls use temperature 0.1-0.3.
- **Retry logic** -- Classification and expansion calls retry with a stricter prompt if the LLM returns invalid JSON.
- **Provider abstraction** -- Three LLM providers supported via a single interface: Google Cloud (Gemini 2.5 Flash/Pro), LM Studio (local), and OpenAI-compatible Gemini. Selected at runtime via `LLM_PROVIDER` env var.
- **Comprehensive logging** -- Every stage persists structured JSON with substep timing to `output/reports/{date}/{run_id}/`.
- **Intermediary streaming** -- Classification and clustering EDA results stream to the frontend mid-pipeline via WebSocket. Users see progress before the full run completes.

## LLM Calls Summary

| # | Call | Method | Temp | Purpose |
|---|------|--------|------|---------|
| 1 | Orchestrator Agent | `chat_with_tools` | 0.3 | Agent loop: fetch Reddit posts |
| 2 | Analyst Agent | `chat_with_tools` | 0.3 | Agent loop: classify & cluster |
| 3 | Hypothesis Agent | `chat_with_tools` | 0.3 | Agent loop: generate hypotheses |
| 4 | Post Classification | `classify_post` | 0.1 | Per-post: theme, is_complaint, intensity |
| 5 | Theme Expansion | `generate_text` | 0.3 | Per-batch: expand themes for embeddings |
| 6 | Cluster Naming | `generate_text` | 0.3 | Per-cluster: human-readable name |
| 7 | Hypothesis Generation | `generate_structured` | 0.3 | Top-5 business hypotheses (PRO model, 16,384 tokens) |
| 8 | Subreddit Selection | `generate_structured` | 0.3 | Preprocessing: select relevant subreddits |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, Tailwind CSS, Radix UI |
| **Backend API** | FastAPI, Uvicorn, WebSockets |
| **Agent Framework** | Custom multi-agent runner with tool calling |
| **LLM** | Google Gemini 2.5 Flash (FAST) / Gemini 2.5 Pro (PRO) via Vertex AI |
| **Embeddings** | `text-embedding-004` via Google Cloud |
| **Clustering** | scikit-learn KMeans |
| **Data Source** | Reddit API (OAuth via PRAW) |
| **Deployment** | Google Cloud Run (frontend + backend, containerized) |

## Output Artifacts

Each pipeline run produces structured artifacts under `output/reports/{date}/{run_id}/`:

- `subreddit_selection.json` -- LLM reasoning + selected subreddits
- `fetch_stats.json` -- Posts fetched, subreddits queried, timing
- `classification_eda.json` -- Theme/intensity distributions + substep timing
- `clustering_eda.json` -- Cluster details + substep timing breakdown
- `hypothesis.json` -- Final hypotheses + substep timing
- `classified.json` -- Full classified posts
- `clustering.json` -- Full clustering data
- `workflow_report.md` -- Markdown summary with timing tables
