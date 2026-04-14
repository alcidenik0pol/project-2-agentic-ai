# Reddit Pain Point Analyzer

Multi-agent system that queries Reddit, analyzes posts and comments, and returns ranked business ideas grounded in real complaint data.

## Quick Start

### 1. Set up environment

```bash
conda create -n agentic-ai-p2 python=3.11 -y
conda activate agentic-ai-p2
pip install -r requirements.txt
pip install fastapi uvicorn websockets
```

### 2. Configure `.env`

Copy `.env.example` to `.env` and fill in your LLM provider credentials:

```bash
cp .env.example .env
```

At minimum, set one of:
- `LLM_PROVIDER=gcloud` + `GCLOUD_SERVICE_ACCOUNT_KEY_PATH` (Vertex AI)
- `LLM_PROVIDER=openai_gemini` + `GEMINI_API_KEY` (Gemini API)

### 3. Run the app

**Option A: Web UI (recommended)**

Terminal 1 — start the backend:
```bash
conda activate agentic-ai-p2
uvicorn backend.app.main:app --host 0.0.0.0 --port 8901 --reload
```

Terminal 2 — start the frontend:
```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:3456** in your browser.

**Option B: CLI only**

```bash
conda activate agentic-ai-p2
python scripts/run_agent.py "gaming complaints"
python scripts/run_agent.py "remote work pain points" --mode live
```

**Option C: Docker**

```bash
docker-compose up
```

Backend at http://localhost:8901, frontend at http://localhost:3456.

## Ports

| Service | Port |
|---------|------|
| Backend (FastAPI) | 8901 |
| Frontend (Next.js) | 3456 |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/analysis` | Start analysis (returns run_id) |
| `GET` | `/api/v1/results/{run_id}` | Get results |
| `GET` | `/api/v1/results/{run_id}/file/{filename}` | Download artifact (hypothesis.json, report.md) |
| `GET` | `/api/v1/rate-limit` | Reddit API throttle status |
| `GET` | `/api/v1/health` | Server health check |
| `WS` | `/ws/{run_id}` | Real-time analysis updates |

## Agent Pipeline

```
User Query
    │
    ▼
Orchestrator Agent ── fetch_posts ──▶ Reddit API
    │
    ▼
Analyst Agent ── classify_posts, cluster_themes
    │
    ▼
Hypothesis Agent ── generate_hypotheses, save_artifact
    │
    ▼
Ranked Business Ideas + Report
```

## Modes

- **test** — uses sample/cached data, no Reddit API calls. Fast, for development.
- **live** — calls Reddit API in real time. Produces real results.

Set via `AGENT_MODE` env var, or toggle in the web UI, or pass `--mode live` on the CLI.

## Project Structure

```
├── app/                    # Agent pipeline (shared by CLI and web)
│   ├── agents/             # Agent classes, tools, orchestrator
│   ├── analyst/            # Classification, clustering, hypothesis generation
│   ├── collector/          # Reddit fetching, subreddit selection
│   ├── reddit/             # Reddit API client with rate limiting
│   └── config.py           # Centralized env var config
├── backend/                # FastAPI web server
│   └── app/
│       ├── api/            # REST routes + WebSocket manager
│       ├── models/         # Pydantic API models
│       ├── services/       # Analysis service, rate limit tracker
│       └── main.py         # FastAPI entry point
├── frontend/               # Next.js web UI
│   ├── app/                # Pages and layout
│   ├── components/         # UI components (ChatInterface, AgentFlow, etc.)
│   ├── hooks/              # React hooks (useWebSocket, useAnalysis)
│   └── lib/                # API client, WebSocket client, types
├── scripts/                # CLI entry points
├── output/                 # Generated reports and artifacts
└── docker-compose.yml
```
