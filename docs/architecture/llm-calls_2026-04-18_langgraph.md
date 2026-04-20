# LLM Call Inventory

_Generated: 2026-04-18 (Post-LangGraph Migration)_

_Source of truth: Codebase exploration_

> **This is the LANGGRAPH version.** Agent orchestration uses `langgraph.graph.StateGraph` with explicit graph edges. Calls 1-3 are now LangGraph node functions in `app/agents/graph.py` instead of the old `Agent.run()` loop in `base.py`. The LLM no longer emits `HANDOFF_TO_AGENT` text — graph edges handle agent transitions deterministically.

Every LLM inference in the system, where it happens, what prompt it uses, and what model serves it.

---

## Provider & Model Selection

All calls share a single provider, selected at runtime via `LLM_PROVIDER` env var (default: `gcloud`). Each provider supports two model tiers via the `use_fast` parameter on every method:

| Tier | Config Key | Default | Used for |
|---|---|---|---|
| **PRO** (primary) | `config.gcloud_model` | `gemini-2.5-pro` | Complex reasoning (Call 7 only) |
| **FAST** | `config.gcloud_model_fast` | `gemini-2.5-flash` | Simple tasks (Calls 1-6, 8) |

| Provider Key | Class | PRO Model | FAST Model |
|---|---|---|---|
| `gcloud` | `GCloudProvider` | `config.gcloud_model` | `config.gcloud_model_fast` |
| `lm_studio` | `LMStudioProvider` | `config.lm_studio_model` | *(ignored -- single local model)* |
| `openai_gemini` | `OpenAIGeminiProvider` | `config.gemini_model` | `config.gcloud_model_fast` |

Provider resolution: `app/analyst/providers/__init__.py` -> `get_provider(config.llm_provider)`

Model selection per call: `config.gcloud_model_fast if use_fast else config.gcloud_model`. Each provider method reads config directly -- no local variable cache.

---

## Call Summary Table

| # | Call Type | Invocation Site | Prompt Source | Parameters | Model Tier | Purpose |
|---|---|---|---|---|---|---|
| 1 | `chat_with_tools` | `app/agents/graph.py:150` (via `_run_agent_loop`) | `app/agents/orchestrator.py:3-20` | temp=0.3 | FAST | Orchestrator agent node |
| 2 | `chat_with_tools` | `app/agents/graph.py:150` (via `_run_agent_loop`) | `app/agents/analyst.py:3-23` | temp=0.3 | FAST | Analyst agent node |
| 3 | `chat_with_tools` | `app/agents/graph.py:150` (via `_run_agent_loop`) | `app/agents/hypothesis.py:3-25` | temp=0.3 | FAST | Hypothesis agent node |
| 4 | `classify_post` | `app/analyst/classifier.py:54` (per post) | `app/analyst/prompts.py:4-22` | temp=0.1, max_tokens=1024 | FAST | Per-post complaint classification |
| 5 | `generate_text` | `app/analyst/expansion.py:138` (per batch) | `app/analyst/expansion_prompts.py:3-33` | temp=0.3, max_tokens=2048 | FAST | Theme expansion for embeddings |
| 6 | `generate_text` | `app/analyst/clustering.py:287` (per cluster) | `app/analyst/cluster_prompts.py:4-19` | temp=0.3, max_tokens=256 | FAST | Cluster naming |
| 7 | `generate_structured` | `app/analyst/hypothesis.py:101` | `app/analyst/hypothesis_prompts.py:3-63` | temp=0.3, max_tokens=16384 | **PRO** | Generate top-5 hypotheses |
| 8 | `generate_structured` | `app/collector/subreddit_selector.py:119` | Inline `subreddit_selector.py:18-41` | temp=0.3, max_tokens=2048 | FAST | Subreddit selection |

---

## Agent Framework: LangGraph StateGraph

### What Changed from the Custom Framework

| Aspect | Before (Custom) | After (LangGraph) |
|--------|-----------------|-------------------|
| Agent loop | `Agent.run()` in `base.py` (50+ lines) | `_run_agent_loop()` in `graph.py` |
| Orchestration | `AgentOrchestrator` while-loop in `runner.py` | `StateGraph` with `add_edge()` calls |
| Handoff mechanism | Regex: `HANDOFF_TO_AGENT:\s*(\w+)` | Graph edges: `add_edge("orchestrator", "analyst")` |
| State management | Accumulated in local variables | `AgentState` TypedDict passed between nodes |
| Entry point | `AgentOrchestrator().run(query)` | `run_pipeline(query, run_dir, callbacks)` |

### Graph Structure

```
StateGraph(AgentState)
  │
  ├── set_entry_point("orchestrator")
  ├── add_edge("orchestrator", "analyst")
  ├── add_edge("analyst", "hypothesis")
  └── add_edge("hypothesis", END)
```

Each node function (`orchestrator_node`, `analyst_node`, `hypothesis_node`) calls `_run_agent_loop()` which contains the same tool-calling loop as the old `Agent.run()`. The LLM still decides which tools to call within each node — only the inter-node transitions changed from regex to graph edges.

### AgentState TypedDict

```python
class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    user_query: str
    run_dir: str
    agents_run: list[str]
    total_tool_calls: int
    agent_results: dict[str, Any]
    final_response: str
```

---

## Detailed Call Breakdown

### Call 1: Orchestrator Agent Node

- **File:** `app/agents/graph.py:150` (via `_run_agent_loop` called from `orchestrator_node` at line 267)
- **Method:** `provider.chat_with_tools(messages, tools, temperature=0.3, use_fast=True)`
- **Model tier:** FAST (simple routing)
- **Agent:** Orchestrator (first node in the graph)
- **Tools available:** `fetch_posts`
- **User message:** The raw user query string
- **Triggered by:** `run_pipeline()` in `app/agents/graph.py:402` -> graph invokes `orchestrator_node`
- **Transition:** Graph edge `orchestrator → analyst` (no handoff text)

**System Prompt** (`app/agents/orchestrator.py:3-20`):

```
You are the Orchestrator Agent for a Reddit signal analysis system.

Your job:
1. Understand the user's topic or question about a niche/market
2. Use the fetch_posts tool to gather Reddit posts about that topic
3. Provide a brief summary of what was fetched for the next agent

Workflow:
- Call fetch_posts with the user's topic
- After fetching, provide a brief summary of what was fetched (both complaints and expressed desires/gaps)
- The system will automatically route your results to the Analyst Agent

Important:
- You have ONE tool: fetch_posts. Use it to get raw Reddit data.
- After fetching, ALWAYS provide a summary of the results.
- Do NOT try to classify or analyze posts yourself.
- Be concise in your summaries.
```

---

### Call 2: Analyst Agent Node

- **File:** `app/agents/graph.py:150` (via `_run_agent_loop` called from `analyst_node` at line 307)
- **Method:** `provider.chat_with_tools(messages, tools, temperature=0.3, use_fast=True)`
- **Model tier:** FAST (simple routing)
- **Agent:** Analyst (second node in the graph)
- **Tools available:** `classify_posts`, `cluster_themes`
- **User message:** Context message built by `_build_context_messages("orchestrator", ...)` in `graph.py:197-213`
- **Triggered by:** Graph edge `orchestrator → analyst`
- **Transition:** Graph edge `analyst → hypothesis` (no handoff text)

**System Prompt** (`app/agents/analyst.py:3-23`):

```
You are the Analyst Agent for a Reddit complaint analysis system.

Your job:
1. Take raw Reddit posts from the Orchestrator
2. Use classify_posts to identify complaint themes and intensity
3. Use cluster_themes to group similar complaints into thematic clusters
4. Provide a summary of the clusters found

Workflow:
- The previous agent will provide fetched posts in the conversation.
- Call classify_posts to classify the posts.
- Then call cluster_themes to group similar complaints into clusters.
- After clustering, provide a summary of the clusters found.
- The system will automatically route your results to the Hypothesis Agent.

Important:
- You have TWO tools: classify_posts and cluster_themes. Use them IN ORDER.
- classify_posts FIRST, then cluster_themes with the output.
- After clustering, ALWAYS provide a summary of results.
- Be thorough — all posts must be classified before clustering.
```

---

### Call 3: Hypothesis Agent Node

- **File:** `app/agents/graph.py:150` (via `_run_agent_loop` called from `hypothesis_node` at line 346)
- **Method:** `provider.chat_with_tools(messages, tools, temperature=0.3, use_fast=True)`
- **Model tier:** FAST (formatting only -- the agent delegates Call 7 to PRO)
- **Agent:** Hypothesis (third/final node in the graph)
- **Tools available:** `generate_hypotheses`, `save_artifact`
- **User message:** Context message built by `_build_context_messages("analyst", ...)` in `graph.py:197-213`
- **Triggered by:** Graph edge `analyst → hypothesis`
- **Transition:** Graph edge `hypothesis → END` (final node, no handoff)

**System Prompt** (`app/agents/hypothesis.py:3-25`):

```
You are the Hypothesis Agent for a Reddit complaint analysis system.

Your job:
1. Take clustered complaint data from the Analyst
2. Use generate_hypotheses to create up to 5 ranked business ideas
3. Use save_artifact to persist the hypothesis results
4. Return a final summary to the user

Workflow:
- The previous agent will provide clustering results in the conversation.
- Call generate_hypotheses to create business ideas from the clustering result.
- Then call save_artifact with artifact_type "hypothesis" to persist the results.
- Finally, provide a clear, readable summary of the top business ideas.

Important:
- You have TWO tools: generate_hypotheses and save_artifact. Use them IN ORDER.
- generate_hypotheses FIRST, then save_artifact with the results.
- For save_artifact, pass the data returned by generate_hypotheses as data_json and "hypothesis" as artifact_type.
- This is the FINAL agent — provide the complete response to the user.
- Present the ideas clearly with ALL fields returned by the tool: pain point, solution description, core features, revenue model, first user step, target user, and confidence.
- Be specific and grounded in the data — no vague generalizations.
- Format the report with clear sections for each idea. Include core_features, revenue_model, and first_user_step as distinct bullet points — these are the most valuable fields for the reader.
```

---

### Call 4: Post Classification (per post, parallel execution)

- **File:** `app/analyst/classifier.py:54` -> provider `classify_post()` method
  - gcloud: `app/analyst/providers/gcloud.py:457-556` (REST POST to Vertex AI)
  - lm_studio: `app/analyst/providers/lm_studio.py:181-265` (OpenAI SDK)
  - openai_gemini: `app/analyst/providers/openai_gemini.py:205-256` (OpenAI SDK)
- **Parameters:** `temperature=0.1`, `max_tokens=1024`, `use_fast=True`
- **Model tier:** FAST (structured extraction, temp=0.1)
- **Execution model:** Parallel via `ThreadPoolExecutor` (default: 10 workers, configurable via `CLASSIFICATION_MAX_WORKERS`)
- **No system prompt** -- prompt sent as a single user message
- **Unchanged from pre-LangGraph version**

**Parallel execution architecture** (`app/analyst/classifier.py`):

```
classify_batch()  (dispatcher)
    |
    +-- _classify_parallel()       (default, when config.classification_enable_parallel=True and posts > 1)
    |   +-- ThreadPoolExecutor(max_workers=min(config.classification_max_workers, post_count, 20))
    |       +-- _classify_post_timed() x N  (concurrent threads)
    |           +-- provider.classify_post()
    +-- _classify_sequential()     (fallback, CLASSIFICATION_ENABLE_PARALLEL=false)
        +-- classify_post() x N  (one at a time, with request_delay between calls)
```

- Thread-safe shared state via `threading.Lock` (results dict, failure counter)
- Index mapping preserves original post order across concurrent completion
- Per-future timeout via `config.classification_request_timeout` (default: 30s)
- Early stopping: cancels remaining futures on consecutive failure threshold
- Sequential fallback available via `CLASSIFICATION_ENABLE_PARALLEL=false` env var

**Config fields:**

| Field | Default | Env Var | Purpose |
|-------|---------|---------|---------|
| `classification_max_workers` | 10 | `CLASSIFICATION_MAX_WORKERS` | Max concurrent threads |
| `classification_request_timeout` | 30s | `CLASSIFICATION_REQUEST_TIMEOUT` | Per-future timeout |
| `classification_enable_parallel` | true | `CLASSIFICATION_ENABLE_PARALLEL` | Master switch |

**User Prompt -- first attempt** (`app/analyst/prompts.py:4-22`):

```
Given this Reddit post, identify the core complaint in 3 words or less.

Return ONLY a JSON object in this exact format:
{{
  "theme": "core complaint theme (3 words or less)",
  "is_complaint": true/false,
  "intensity": "low" | "medium" | "high"
}}

Rules:
- theme: Maximum 3 words, capture the main pain point
- is_complaint: true if expressing frustration, problem, or dissatisfaction
- intensity: "high" = strong emotion/anger, "medium" = clear complaint, "low" = mild annoyance

Post Title: {title}
Post Body: {selftext}
Subreddit: r/{subreddit}

Return ONLY the JSON object, no additional text.
```

**User Prompt -- retry** (`app/analyst/prompts.py:24-36`):

```
IMPORTANT: Your previous response was invalid. You MUST return ONLY valid JSON.

Analyze this Reddit post and return a JSON object with NO additional text, NO markdown, NO explanation.

Post Title: {title}
Post Body: {selftext}
Subreddit: r/{subreddit}

Required JSON format (return EXACTLY this structure):
{{"theme": "3 words max", "is_complaint": true, "intensity": "low"}}
{{"theme": "3 words max", "is_complaint": false, "intensity": "low"}}

Return ONLY the JSON, nothing else:
```

**Telemetry** (in `ClassificationResult.substep_timing`):

```json
{
  "llm_calls": 56.69,
  "concurrency_savings": 43.97,
  "total_calls": 5,
  "avg_time_per_call": 11.338,
  "parallel": true,
  "max_workers": 5,
  "throughput": 0.39
}
```

In parallel mode, `concurrency_savings` = `llm_time - wall_time` (time saved by concurrent execution).

---

### Call 5: Theme Expansion (per batch of ~5 themes)

- **File:** `app/analyst/expansion.py:138`
- **Method:** `provider.generate_text(prompt, temperature=0.3, max_tokens=2048, use_fast=True)`
- **Model tier:** FAST (simple text expansion)
- **Called once per batch** (batch size = `config.expansion_batch_size`, default 5)
- **No system prompt** -- prompt sent as a single user message
- **Purpose:** Expands short theme labels into 10-20 word descriptions for better embedding quality
- **Unchanged from pre-LangGraph version**

**User Prompt -- first attempt** (`app/analyst/expansion_prompts.py:3-33`):

```
You are analyzing Reddit complaints to improve semantic clustering.

Your task: Expand each short theme label into a full, descriptive sentence that captures the essence of the complaint.

For each theme, you'll receive:
1. The theme label (2-4 words)
2. 3 example post titles that exemplify this complaint

Your expanded description should:
- Be 10-20 words long
- Include specific details from the post titles
- Capture the emotional nuance (frustration, anxiety, confusion)
- Use natural language similar to the original posts
- Focus on the pain point, not solutions

Output format: Return ONLY a JSON object mapping each theme to its expanded description.

Example input:
{{
  "workplace frustration": ["My boss ignored my PTO request", "I hate my corporate job", "Toxic work environment"]
}}

Example output:
{{
  "workplace frustration": "Frustration with toxic workplace environments, unreasonable management demands, and lack of work-life balance"
}}

Real data to process:
{themes_data}

Return ONLY the JSON object, no additional text.
```

**User Prompt -- retry** (`app/analyst/expansion_prompts.py:35-43`):

```
IMPORTANT: Your previous response was invalid. Return ONLY valid JSON.

Expand these theme labels into full descriptions:
{themes_data}

Output format (return EXACTLY this structure):
{{"theme": "expanded description as a full sentence"}}

Return ONLY the JSON, nothing else:
```

---

### Call 6: Cluster Naming (per cluster)

- **File:** `app/analyst/clustering.py:287`
- **Method:** `provider.generate_text(prompt, temperature=0.3, max_tokens=256, use_fast=True)`
- **Model tier:** FAST (3-5 word naming)
- **Called once per cluster** after KMeans grouping
- **No system prompt** -- prompt sent as a single user message
- **Validation:** Truncation detection + one retry with strengthened prompt (lines 292-305)
- **Unchanged from pre-LangGraph version**

**User Prompt** (`app/analyst/cluster_prompts.py:4-19`):

```
You are an analyst grouping user complaints into semantic clusters.

Below is a list of complaint themes that have been algorithmically grouped together.
Give this cluster a short, descriptive name (3-5 words) that captures the common thread.

Themes in this cluster:
{themes}

Rules:
- 3-5 words maximum
- Use plain, descriptive language (not marketing jargon)
- Focus on the pain point, not the solution
- Return ONLY the cluster name, nothing else
- IMPORTANT: Do not truncate your response. The name must be a complete, grammatically correct phrase. If your response ends with "&", "and", "or", a comma, or is obviously cut off, you have failed. Write a complete name.

Cluster name:
```

---

### Call 7: Hypothesis Generation

- **File:** `app/analyst/hypothesis.py:101`
- **Method:** `provider.generate_structured(prompt, temperature=0.3, max_tokens=16384, use_fast=False)`
- **Model tier:** **PRO** (complex reasoning -- the only call requiring creative synthesis, evidence linkage, and nuanced confidence reasoning)
- **Called once** per pipeline run
- **No system prompt** -- prompt sent as a single user message
- **JSON enforcement:** gcloud sets `responseMimeType: "application/json"`; openai_gemini uses `response_format={"type": "json_object"}`; lm_studio falls back to plain `generate_text`
- **Unchanged from pre-LangGraph version**

**User Prompt** (`app/analyst/hypothesis_prompts.py:3-63`):

```
You are a product founder identifying specific, buildable business opportunities from Reddit complaints.

You will be given a list of Reddit complaint clusters. Each cluster represents a real pattern
of frustration expressed by real people, with post counts and upvote totals as signal strength.

Your job: identify the top 5 most SPECIFIC, CONCRETE product opportunities that directly address
the complaints from this data. Each idea must be something you could actually build and ship in 3-6 months.

REJECT THESE GENERIC PATTERNS:
- "A platform for X" -> What specifically does the platform do? What buttons does the user click?
- "A certification system" -> Who certifies? What's the mechanism?
- "An ecosystem" -> Too vague. Be concrete.
- "A tool that helps with X" -> How specifically? What's the core interaction?
- "An AI-powered solution for X" -> What does the AI actually do step by step?

FOR EACH IDEA, YOU MUST SPECIFY:
1. Core feature: What does it actually DO? (buttons, flows, user journey)
2. Revenue model: How does it make money? (subscription tiers with prices, transaction fee %, ads, freemium, etc.)
3. First user step: Describe exactly what the user does in the first 30 seconds after signing up
4. Evidence linkage: supporting_post_titles must DIRECTLY quote the exact frustration. No tangential connections.

Rules:
- Every claim must reference specific clusters, post counts, or upvote numbers from the input
- Do not invent pain points not present in the data
- Prefer clusters with high upvotes AND high post count (both signal breadth and intensity)
- The solution must directly address the stated complaint, not a tangentially related problem
- idea_name should be a concrete product name (e.g., "SteamSpy for Indie Devs"), not a category (e.g., "GameDev Insights Platform")
- solution_description must describe specific features and user flows, not abstract benefits
- core_features must list 3-5 tangible features the product has
- revenue_model must include explicit pricing or monetization mechanism
- first_user_step must describe what happens in the first 30 seconds of use

Return a JSON object matching this exact schema. No markdown, no preamble, just JSON.

{{
  "ideas": [
    {{
      "rank": 1,
      "idea_name": "Concrete product name (e.g., 'SubredditTracker Pro')",
      "pain_point": "One sentence quoting the specific frustration from posts",
      "solution_description": "What it does specifically - describe the core interaction, user flow, and key screens",
      "core_features": "3-5 specific features separated by commas (e.g., 'keyword rank tracking, competitor comparison, email alerts, A/B testing')",
      "revenue_model": "How it makes money with pricing (e.g., 'Freemium: $0 for 1 game, $29/mo for 10 games, $99/mo unlimited')",
      "first_user_step": "What the user does in first 30 seconds (e.g., 'User enters Steam app ID, dashboard shows keyword rankings within 10 seconds')",
      "target_user": "Who experiences this pain most - be specific (e.g., 'solo indie devs with <3 released games')",
      "evidence": {{
        "cluster_name": "exact name from input",
        "post_count": <number>,
        "total_upvotes": <number>,
        "supporting_post_titles": ["title1", "title2", "title3"]
      }},
      "confidence": "high|medium|low",
      "confidence_reasoning": "Why this confidence level - reference specific signal strength"
    }}
  ],
  "analysis_summary": "2-3 sentences on overall pattern across clusters",
  "data_limitations": "Honest caveat about what this dataset can and cannot tell us"
}}

Clusters:
{clusters_json}
```

---

### Call 8: Subreddit Selection

- **File:** `app/collector/subreddit_selector.py:119`
- **Method:** `provider.generate_structured(prompt, temperature=0.3, max_tokens=2048, use_fast=True)`
- **Model tier:** FAST (selection/sorting)
- **Called once** per pipeline run (before Reddit fetching)
- **No system prompt** -- prompt sent as a single user message
- **Fallback:** Keyword-based matching if LLM call fails
- **Unchanged from pre-LangGraph version**

**User Prompt** (`app/collector/subreddit_selector.py:18-41`):

```
You are selecting relevant subreddits for Reddit complaint analysis.

TOPIC: {topic}

AVAILABLE SUBREDDITS:
{subreddit_list}

Your task:
1. Select ALL subreddits that could contain complaints about this topic
2. Rank them by relevance (most relevant first)
3. Return EXACTLY {max_subreddits} subreddits (or fewer if topic is very niche)

Rules:
- Consider both direct topic matches AND adjacent domains
- Include general complaint subreddits if topic is broad
- Use the descriptions to understand each subreddit's focus
- Return subreddit names WITHOUT "r/" prefix

Output format (strict JSON):
{{
    "selected": ["subreddit1", "subreddit2", ...],
    "reasoning": "Brief explanation"
}}
```

---

## Non-LLM API Calls (Embeddings)

| Call | File | Model | Provider |
|---|---|---|---|
| Embedding generation | `app/analyst/clustering.py:93` | `text-embedding-004` (gcloud) / `gemini-embedding-2-preview` (openai_gemini) / provider default (lm_studio) | `provider.get_embeddings(texts)` |

---

## Data Flow Diagram

```
User Query
    |
    v
[Call 8] Subreddit Selection (FAST) -> Selects relevant subreddits
    |
    v
=== LangGraph: enter orchestrator node ===
[Call 1] Orchestrator Agent (FAST)
    |-- tool call: fetch_posts -> Reddit API (not LLM)
    |-- no more tool calls -> node done
    |
    v  graph edge: orchestrator -> analyst
    |
=== LangGraph: enter analyst node ===
[Call 2] Analyst Agent (FAST)
    |-- tool call: classify_posts
    |       |-- [Call 4] classify_post x N (FAST, PARALLEL, ThreadPoolExecutor, 10 workers)
    |       |-- Non-complaint posts preserved for EDA display
    |       |-- Complaint-only filter applied before clustering
    |       |-- [Call 5] expand_themes x batches (FAST, theme expansion)
    |       `-- embedding + KMeans clustering
    |-- tool call: cluster_themes
    |       `-- [Call 6] generate_text x K (FAST, one per cluster name)
    |-- no more tool calls -> node done
    |
    v  graph edge: analyst -> hypothesis
    |
=== LangGraph: enter hypothesis node ===
[Call 3] Hypothesis Agent (FAST)
    |-- tool call: generate_hypotheses
    |       `-- [Call 7] generate_structured (PRO, one call)
    |-- tool call: save_artifact (file I/O, not LLM)
    |-- no more tool calls -> node done
    |
    v  graph edge: hypothesis -> END
    |
FINAL RESPONSE (formatted summary of 5 business ideas)
```

---

## Non-Complaint Filtering (Defense-in-Depth)

The clustering pipeline filters non-complaint posts at two layers:

1. **Tool boundary** (`app/agents/tools/cluster.py:50-56`): Only passes `is_complaint=True` posts to the clusterer
2. **Internal extraction** (`app/analyst/clustering.py:160-166`): Skips non-complaints when building the theme map

Non-complaint posts remain in the full dataset for EDA display. Only the clustering input is filtered.

Default behavior: `is_complaint` defaults to `True` when the key is missing (backward-compatible).

---

## Run Logging & Substep Timing

Every pipeline stage persists structured JSON logs with granular timing via `app/agents/tools/run_logger.py`.

### Output Files Per Run

```
output/reports/{date}/{run_id}/
  |-- metadata.json             # Run metadata
  |-- subreddit_selection.json  # LLM reasoning + selected subreddits
  |-- fetch_stats.json          # Posts fetched, subreddits queried, timing
  |-- classification_eda.json   # Theme/intensity distributions + substep timing
  |-- clustering_eda.json       # Cluster details + substep timing breakdown
  |-- hypothesis.json           # Final hypotheses + substep timing
  |-- report.md                 # Formatted summary
  |-- workflow_report.md        # Markdown summary with timing tables
```

### Timing Data Flow

```
classifier.py: classify_batch()
    |  tracks llm_time per call
    |  -> ClassificationResult.substep_timing
         |
         v
classify.py (tool) -> run_logger.save_classification_eda()
         |
         v
classification_eda.json -> workflow_report.md

clustering.py: cluster_posts()
    |  times each substep (expansion, embeddings, kmeans, naming)
    |  reads BatchExpansionResult.llm_time_seconds for expansion LLM time
    |  -> ClusteringResult.substep_timing
         |
         v
cluster.py (tool) -> run_logger.save_clustering_eda()
         |
         v
clustering_eda.json -> workflow_report.md

hypothesis.py: generate_hypotheses()
    |  times table prep and LLM call
    |  -> HypothesisOutput.llm_time_seconds + table_preparation_time_seconds
         |
         v
hypothesis.json -> workflow_report.md
```

### Pydantic Models with Timing Fields

| Model | Timing Fields |
|---|---|
| `ClassificationResult` | `substep_timing: dict[str, float]` |
| `BatchExpansionResult` | `llm_time_seconds: float` |
| `ClusteringResult` | `substep_timing: dict[str, float]` |
| `HypothesisOutput` | `llm_time_seconds: float`, `table_preparation_time_seconds: float` |

### Error Handling

Every logging call is wrapped in try/except at the call site so logging failures never break the pipeline.

---

## Intermediary Results Streaming

After the analyst agent completes, classification and clustering EDA data streams to the frontend via the existing WebSocket connection.

```
Pipeline (thread pool)
  |
  v
on_agent_completed("analyst")        # callback from graph.py node function
  |-- read classification_eda.json from run dir
  |-- stream via WebSocket (intermediary_result message)
  |-- read clustering_eda.json from run dir
  |-- stream via WebSocket (intermediary_result message)
  |
  v
on_agent_completed("hypothesis")
  |-- read hypothesis.json from run dir
  |-- stream via WebSocket (intermediary_result message)
  |
  v
Frontend (WebSocketContext)
  |-- classificationEDA state
  |-- clusteringEDA state
  |-- hypothesis data
  |
  v
TabbedResultsDisplay
  |-- Tab: Business Ideas (always visible)
  |-- Tab: Classification EDA (enables on data arrival)
  |-- Tab: Clustering Results (enables on data arrival)
```

WebSocket message type: `intermediary_result` with `result_type` of `classification_eda`, `clustering_eda`, or `hypothesis`.

---

## Summary Statistics

- **Total LLM call types:** 8
- **Agent framework calls:** 3 (Orchestrator, Analyst, Hypothesis) -- now LangGraph nodes
- **Analysis pipeline calls:** 4 (Classification, Expansion, Clustering, Hypothesis) -- unchanged
- **Infrastructure calls:** 1 (Subreddit Selection) -- unchanged
- **Total prompt files:** 6 (3 in agents/, 2 in analyst/, 1 inline)
- **Max token count:** 16,384 (Hypothesis Generation)
- **Temperature range:** 0.1-0.3 (low temperature for consistency)
- **Model tiers:** FAST for 7 calls (gemini-2.5-flash), PRO for 1 call (gemini-2.5-pro)
- **Parallel execution:** Call 4 (Classification) via ThreadPoolExecutor, 10 workers default
- **Run logging:** All 8 call types logged to structured JSON with substep timing
- **Agent SDK:** LangGraph `StateGraph` with 3 nodes and 3 explicit edges
