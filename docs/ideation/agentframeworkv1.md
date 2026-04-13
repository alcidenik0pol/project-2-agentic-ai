# Project Plan: Reddit Pain Domain Analyzer

---

## Disclaimer: Static vs Live Mode

This plan is written to run against static offline data (`data/sample_posts.json`) for development and testing. Every section that differs between test mode and live mode is explicitly marked.

**TEST MODE**: reads from `data/sample_posts.json`, skips Reddit API call entirely.
**LIVE MODE**: orchestrator calls `fetch_posts` tool which hits Reddit API at runtime, triggered by user input from the frontend.

The distinction matters because the agent framework, tool definitions, multi-agent handoffs, logging, and structured outputs are identical in both modes. Only the data source changes. This means everything built now transfers directly to live mode with one swap.

---

## System Overview: Agentic vs Non-Agentic

The critical difference between your current pipeline and the agent system is not what computations happen, it is who decides what happens next.

**Current (non-agentic):**
```
CLI script → calls function → calls function → calls function → done
Python code decides every step. LLM is a text-in/text-out resource.
```

**New (agentic):**
```
User input → Orchestrator Agent decides → calls tools → hands off to agents → aggregates results
LLM decides which tools to invoke, when to hand off, and what the final output is.
```

---

## Full Pipeline: Every Agent Operation

```
USER INPUT
"find business ideas for people struggling with debt"
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  ORCHESTRATOR AGENT                                  │
│  system prompt: routes queries, decides which        │
│  domains to analyze, sequences tool calls,           │
│  hands off to specialist agents                      │
│                                                      │
│  1. LLM call: classify user query into pain domain   │
│     → decides: ["finance", "work"]                   │
│                                                      │
│  2. TOOL CALL: fetch_posts(domains=["finance","work"])│
│     TEST MODE: reads sample_posts.json               │
│     LIVE MODE: calls Reddit API for those domains    │
│     → returns: List[RedditPost] (300-500 posts)      │
│                                                      │
│  3. LLM decision: enough data? → yes, proceed        │
│     (this is the agent deciding, not Python code)    │
│                                                      │
│  4. HANDOFF → ANALYST AGENT                          │
│     passes: raw posts + domain context               │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  ANALYST AGENT                                       │
│  system prompt: expert data analyst, surfaces        │
│  patterns in complaint data, never jumps to          │
│  conclusions without examining data first            │
│                                                      │
│  5. TOOL CALL: classify_posts(posts)                 │
│     → LLM tags each post: theme, is_complaint,       │
│       intensity                                      │
│     → returns: List[ClassifiedPost]                  │
│                                                      │
│  6. TOOL CALL: cluster_themes(classified_posts)      │
│     → embeds themes via text-embedding-004           │
│     → KMeans clustering, silhouette score picks k    │
│     → LLM names each cluster                        │
│     → returns: ClusteringResult (15 clusters,        │
│       post counts, upvote totals, top posts)         │
│                                                      │
│  7. LLM call: interpret clustering result            │
│     → surfaces top 3 clusters by signal strength    │
│     → writes analytical summary with specific        │
│       numbers (cluster X: 45 posts, 38k upvotes)    │
│                                                      │
│  8. HANDOFF → HYPOTHESIS AGENT                       │
│     passes: clustering result + analytical summary   │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  HYPOTHESIS AGENT                                    │
│  system prompt: business strategist, generates       │
│  actionable ideas grounded strictly in evidence      │
│  from the data, never invents unsupported claims     │
│                                                      │
│  9. TOOL CALL: generate_hypotheses(clustering_result)│
│     → structured output: 3 BusinessIdea objects     │
│       each with: name, description, target_cluster,  │
│       evidence (post_count, upvotes, top_titles),    │
│       confidence_reasoning                           │
│     → returns: HypothesisOutput                     │
│                                                      │
│  10. TOOL CALL: save_artifact(hypothesis_output)     │
│      → writes timestamped JSON to output/            │
│      → TEST MODE: local filesystem                   │
│      → LIVE MODE: same, also returned to frontend   │
│                                                      │
│  11. LLM call: formats final response for user       │
│      → natural language summary + structured data   │
└─────────────────────────────────────────────────────┘
        │
        ▼
FINAL OUTPUT
- Natural language hypothesis with evidence citations
- Structured JSON artifact saved to output/
- Full agent trace logged (see Logging section)
```

---

## Tool List

Every tool is a `@function_tool` decorated Python function. The agent decides when to call each one. Tools are not called by Python orchestration logic.

### Tool 1: `fetch_posts`
```
Purpose: retrieve Reddit posts for given pain domains
Inputs:  domains: list[str]  e.g. ["finance", "work"]
         limit: int           posts per subreddit (default 100)
Outputs: list[RedditPost]     raw posts with title, body, score, url

TEST MODE: ignores inputs, reads data/sample_posts.json, returns contents
LIVE MODE: maps domains → subreddits via DOMAIN_SUBREDDITS dict,
           calls Reddit public JSON API, returns live posts

Migration note: swap the function body only. Tool signature stays identical
so the agent's tool call does not change between modes.
```

### Tool 2: `classify_posts`
```
Purpose: tag each post with theme, complaint flag, intensity
Inputs:  posts: list[RedditPost]
Outputs: list[ClassifiedPost]  adds fields: theme, is_complaint, intensity

No difference between TEST and LIVE mode. Pure LLM computation over posts.
```

### Tool 3: `cluster_themes`
```
Purpose: group classified posts into named thematic clusters
Inputs:  classified_posts: list[ClassifiedPost]
Outputs: ClusteringResult  with clusters, post counts, upvote totals, top posts

Internally: ThemePreprocessor → ThemeExpander → embeddings → KMeans → LLM naming
No difference between TEST and LIVE mode.
```

### Tool 4: `generate_hypotheses`
```
Purpose: produce structured business ideas from cluster evidence
Inputs:  clustering_result: ClusteringResult
         domain_context: str   the original user query domain
Outputs: HypothesisOutput      3 BusinessIdea objects with full evidence

No difference between TEST and LIVE mode.
```

### Tool 5: `save_artifact`
```
Purpose: persist pipeline output to disk
Inputs:  data: dict
         artifact_type: str   e.g. "hypothesis", "clusters", "classified"
Outputs: str                  filepath where artifact was saved

TEST MODE: saves to output/ with timestamp
LIVE MODE: same, filepath also returned to frontend for download link
```

---

## Agent Definitions

### Orchestrator Agent
```
name: "orchestrator"
model: gemini-2.5-flash via GCloud/LiteLLM
instructions: |
  You are a research orchestrator. Your job is to:
  1. Understand the user's domain of interest
  2. Fetch relevant Reddit complaint data for that domain
  3. Hand off to the analyst agent for EDA
  Never skip the fetch step. Never generate hypotheses yourself.
  Always wait for clustering results before forming any conclusions.
tools: [fetch_posts]
handoffs: [analyst_agent]
output_type: None (conversational)
```

### Analyst Agent
```
name: "analyst"
model: gemini-2.5-flash via GCloud/LiteLLM
instructions: |
  You are a data analyst specializing in complaint pattern analysis.
  You receive raw Reddit posts and must:
  1. Classify every post before drawing any conclusions
  2. Cluster classified posts into themes
  3. Surface specific numbers: post counts, upvote totals, top posts per cluster
  4. Write an analytical summary citing those specific numbers
  Never summarize without running classify_posts and cluster_themes first.
tools: [classify_posts, cluster_themes]
handoffs: [hypothesis_agent]
output_type: None (conversational)
```

### Hypothesis Agent
```
name: "hypothesis"
model: gemini-2.5-flash via GCloud/LiteLLM
instructions: |
  You are a business strategist. You receive clustering analysis and must:
  1. Generate exactly 3 business hypotheses grounded in cluster evidence
  2. Each hypothesis must cite: cluster name, post count, upvote total,
     at least 2 supporting post titles
  3. Save the output as an artifact
  4. Never invent evidence. If a claim cannot be traced to a cluster, drop it.
tools: [generate_hypotheses, save_artifact]
handoffs: []
output_type: HypothesisOutput (structured)
```

---

## Logging System

This is not optional infrastructure. It goes in from day one. Every agent operation emits a structured log entry in real time. The goal is to see exactly what the agent is doing at every step without digging through output files.

### What gets logged

Every log entry has this structure:
```
{
  "timestamp": "2026-04-12T14:23:01.234Z",
  "level": "INFO|DEBUG|ERROR",
  "agent": "orchestrator|analyst|hypothesis",
  "event": "tool_call_start|tool_call_end|llm_call|handoff|error",
  "tool": "fetch_posts|classify_posts|...",   (if applicable)
  "details": { ... }                           (event-specific payload)
}
```

### Events to log

```
ORCHESTRATOR
  llm_call        → "classifying user query into domains"
                    details: {query, domains_identified}
  tool_call_start → "calling fetch_posts"
                    details: {domains, limit, mode: "test|live"}
  tool_call_end   → "fetch_posts complete"
                    details: {post_count, subreddits_hit, duration_ms}
  handoff         → "handing off to analyst"
                    details: {post_count}

ANALYST
  tool_call_start → "calling classify_posts"
                    details: {post_count}
  tool_call_end   → "classify_posts complete"
                    details: {classified_count, failed_count, duration_ms}
  tool_call_start → "calling cluster_themes"
                    details: {theme_count, unique_themes}
  tool_call_end   → "cluster_themes complete"
                    details: {cluster_count, k_selected, silhouette_score, duration_ms}
  llm_call        → "interpreting clustering result"
                    details: {top_clusters_by_signal}
  handoff         → "handing off to hypothesis agent"

HYPOTHESIS
  tool_call_start → "calling generate_hypotheses"
  tool_call_end   → "generate_hypotheses complete"
                    details: {hypothesis_count, ideas: [name, cluster, evidence_strength]}
  tool_call_start → "calling save_artifact"
  tool_call_end   → "artifact saved"
                    details: {filepath, size_bytes}

ERRORS (any agent)
  error           → details: {agent, tool, error_type, message, recoverable: bool}
```

### Implementation approach

Use Python's `logging` module with a custom formatter that outputs JSON to stdout and simultaneously to a rotating file at `logs/agent_run_{timestamp}.jsonl`. One line per event.

Add a second handler that pretty-prints a human-readable summary to the console in real time:

```
[14:23:01] ORCHESTRATOR  → classifying query: "debt business ideas"
[14:23:02] ORCHESTRATOR  → fetch_posts: 294 posts from 5 subreddits (test mode) [1.2s]
[14:23:02] ORCHESTRATOR  → handing off to analyst
[14:23:03] ANALYST       → classify_posts: 242/294 classified [45.1s]
[14:23:48] ANALYST       → cluster_themes: 15 clusters, k=15, silhouette=0.42 [12.3s]
[14:24:00] ANALYST       → handing off to hypothesis agent
[14:24:01] HYPOTHESIS    → generate_hypotheses: 3 ideas generated [3.2s]
[14:24:04] HYPOTHESIS    → artifact saved: output/hypothesis_20260412_142404.json
```

TEST MODE: logs to console + file. No frontend display.
LIVE MODE: log stream also piped to frontend via SSE or websocket so user sees agent progress in real time. This is the migration point for live mode.

---

## Migration Checklist: Test → Live

When the frontend is ready, these are the only changes needed:

| What | File | Change |
|------|------|--------|
| `fetch_posts` tool body | `tools/fetch.py` | swap static file read for Reddit API call |
| `DOMAIN_SUBREDDITS` dict | `app/collector/queries.py` | update to full 40-subreddit list |
| Log stream | `app/logging.py` | add SSE/websocket emitter alongside file handler |
| Entry point | `scripts/run_agent.py` | accept user input string instead of hardcoded query |
| Artifact delivery | `tools/artifacts.py` | return filepath to frontend for download link |

Everything else (agent definitions, tool signatures, multi-agent handoffs, structured outputs, Pydantic models) is identical between modes.