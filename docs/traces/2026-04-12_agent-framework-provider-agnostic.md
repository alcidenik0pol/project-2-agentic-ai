# Trace: Agent Framework — Provider-Agnostic Multi-Agent Pipeline

**Date:** 2026-04-12
**Session:** Implementing chat_with_tools() in the LLM provider abstraction, rewiring the agent framework to use providers instead of hardcoded OpenAI client, adding shared data store for inter-tool communication

**Files Created:**
- `app/agents/tools/shared.py` — Shared data store for passing data between tools without going through LLM context

**Files Modified:**
- `app/analyst/providers/base.py` — Added `ToolCallInfo`, `ChatToolResponse` dataclasses and `chat_with_tools()` abstract method
- `app/analyst/providers/gcloud.py` — Implemented `chat_with_tools()` with OpenAI-to-Gemini format conversion
- `app/analyst/providers/lm_studio.py` — Implemented `chat_with_tools()` via OpenAI SDK
- `app/analyst/providers/openai_gemini.py` — Implemented `chat_with_tools()` via OpenAI SDK
- `app/analyst/providers/__init__.py` — Exported `ChatToolResponse`, `ToolCallInfo`
- `app/agents/base.py` — Replaced hardcoded `OpenAI` client with `LLMProvider` abstraction
- `app/agents/runner.py` — Replaced `OpenAI` client with `get_provider()`, added shared data store integration
- `app/agents/tools/__init__.py` — Re-exported shared data functions from `shared.py`
- `app/agents/tools/fetch.py` — Stores full data in shared store, returns compact summary to LLM
- `app/agents/tools/classify.py` — Reads from shared store, no JSON parameter needed
- `app/agents/tools/cluster.py` — Reads from shared store, no JSON parameter needed
- `app/agents/tools/hypothesis.py` — Reads from shared store, no JSON parameter needed
- `scripts/run_agent.py` — Removed GEMINI_API_KEY requirement, displays provider name
- `scripts/test_agent_imports.py` — Updated tests for new architecture

---

## Problem

The project scored **1/10** on Core Requirements for the Columbia Agentic AI grading rubric. Three gaps needed solving simultaneously:

| Gap | Issue | Points |
|-----|-------|--------|
| Agent Framework | No framework. Plain Python classes. | 1 |
| Tool Calling | LLM was text-in/text-out. Python orchestrated everything. | 1 |
| Multi-agent Pattern | No handoff logic between agents. Agents were just function calls. | 2 |

The existing code had agent files (`base.py`, `runner.py`, tools) from a prior attempt, but they had a critical flaw: **hardcoded `OpenAI` client**. The runner and base agent both imported `from openai import OpenAI` and constructed a client using `GEMINI_API_KEY`. This meant:
- The gcloud provider (with service account auth) couldn't be used
- Users needed a separate API key just for the agent pipeline
- The provider abstraction built for classification/clustering was bypassed entirely

---

## Solution: chat_with_tools() in the Provider ABC

The key insight: `PostClassifier`, `ThemeClusterer`, and `HypothesisGenerator` all accept an `LLMProvider` instance. By adding a `chat_with_tools()` method to the same ABC, the agent framework gains the same provider-agnostic behavior.

### Before (Hardcoded OpenAI)

```
Agent.__init__(client: OpenAI, model: str)
  └── self.client.chat.completions.create(messages=..., tools=...)

AgentOrchestrator.__init__()
  ├── Requires GEMINI_API_KEY
  └── self.client = OpenAI(api_key=..., base_url=...)
```

### After (Provider Abstraction)

```
Agent.__init__(provider: LLMProvider)
  └── self.provider.chat_with_tools(messages=..., tools=...)

AgentOrchestrator.__init__(provider_name=None)
  ├── self.provider = get_provider(provider_name or config.llm_provider)
  └── Works with gcloud / lm_studio / openai_gemini
```

---

## Architecture

### Dataclasses Added to base.py

```
@dataclass
class ToolCallInfo:
    id: str           # e.g., "fetch_posts_0"
    name: str         # e.g., "fetch_posts"
    arguments: str    # JSON string of arguments

@dataclass
class ChatToolResponse:
    content: str | None = None
    tool_calls: list[ToolCallInfo] = field(default_factory=[])
```

These provide a provider-agnostic representation of LLM responses that may contain text, tool calls, or both.

### chat_with_tools() Implementation Per Provider

```
LLMProvider.chat_with_tools(messages, tools, temperature) -> ChatToolResponse
  │
  ├── GCloudProvider
  │     ├── _convert_messages_to_gemini()   # system->user/model pair, assistant->model, tool->function
  │     ├── _convert_tools_to_gemini()       # OpenAI schemas -> Gemini functionDeclarations
  │     ├── POST to Vertex AI REST endpoint
  │     └── _parse_gemini_tool_response()    # Gemini candidates -> ChatToolResponse
  │
  ├── LMStudioProvider
  │     ├── client.chat.completions.create(tools=..., tool_choice="auto")
  │     └── Parse OpenAI response -> ChatToolResponse
  │
  └── OpenAIGeminiProvider
        ├── client.chat.completions.create(tools=..., tool_choice="auto")
        └── Parse OpenAI response -> ChatToolResponse
```

### Pipeline Flow

```
USER INPUT "Find business ideas for people struggling with debt"
    │
    ▼
ORCHESTRATOR AGENT (tools: [fetch_posts])
    │  Iteration 1: LLM calls fetch_posts(topic="...")
    │  fetch_posts loads data/sample_posts.json (test mode)
    │  Stores full data in shared store, returns compact summary
    │  Iteration 2: LLM sees summary, outputs "HANDOFF_TO_AGENT: analyst"
    │
    ▼
ANALYST AGENT (tools: [classify_posts, cluster_themes])
    │  Iteration 1: LLM calls classify_posts()
    │  classify_posts reads from shared store -> PostClassifier.classify_batch()
    │  30/30 posts classified, stores results in shared store
    │  Iteration 2: LLM calls cluster_themes()
    │  cluster_themes reads from shared store -> ThemeClusterer.cluster_posts()
    │  9 clusters found, stores results in shared store
    │  Iteration 3: LLM outputs "HANDOFF_TO_AGENT: hypothesis"
    │
    ▼
HYPOTHESIS AGENT (tools: [generate_hypotheses, save_artifact])
    │  Iteration 1: LLM calls generate_hypotheses()
    │  Reads from shared store -> HypothesisGenerator.generate_hypotheses()
    │  3 business ideas generated
    │  Iteration 2: LLM calls save_artifact(data=..., type="hypothesis")
    │  Writes output/hypothesis_*.json
    │  Iteration 3: LLM outputs final formatted response (no handoff)
    │
    ▼
FINAL RESPONSE (formatted summary of 3 business ideas)
```

### Shared Data Store

The critical design decision: **data flows between tools through a shared store, not through LLM context**.

```
app/agents/tools/shared.py
  ├── _shared_data: dict[str, Any]  # module-level singleton
  ├── set_shared_data(key, data)
  ├── get_shared_data(key) -> Any | None
  └── clear_shared_data()

Data flow:
  fetch_posts → set_shared_data("fetched_posts", {...})
  classify_posts → get_shared_data("fetched_posts") → set_shared_data("classified_posts", {...})
  cluster_themes → get_shared_data("classified_posts") → set_shared_data("clustered_data", {...})
  generate_hypotheses → get_shared_data("clustered_data")
```

Tools return **compact summaries** to the LLM (e.g., `{"status": "success", "total_posts": 30}`), not the full data. This prevents the `MALFORMED_FUNCTION_CALL` error.

---

## Debugging Saga: Two Bugs That Blocked the Pipeline

### Bug 1: 30-Second Timeout on Large Contexts

**Symptom:** Orchestrator succeeded (small messages), but analyst timed out after 30s when calling Gemini.

```
requests.exceptions.ReadTimeout: HTTPSConnectionPool(
    host='us-central1-aiplatform.googleapis.com', port=443
): Read timed out. (read timeout=30)
```

**Root Cause:** The analyst received a large context message (system prompt + user query + orchestrator response + 8000 chars of fetched posts JSON). Gemini needed more than 30s to process this.

**Fix:** Multiplied timeout by 3 for `chat_with_tools()` calls:
```python
timeout=self._timeout * 3  # Longer timeout for tool-calling with large contexts
```

### Bug 2: MALFORMED_FUNCTION_CALL from Gemini

**Symptom:** After fixing the timeout, the analyst agent returned empty content with `finishReason=MALFORMED_FUNCTION_CALL`.

```
WARNING: Empty response from Gemini. finishReason=MALFORMED_FUNCTION_CALL, parts=[]
```

**Root Cause:** The runner was passing 8000 chars of fetched posts JSON in the context message. When the LLM tried to call `classify_posts(posts_json="<8000 char string>")`, Gemini's function calling couldn't handle the malformed/incomplete argument.

**Failed approach:** Reducing the JSON size to 4000 chars. Still malformed.

**Actual fix:** Complete architectural change — the shared data store. Tools no longer accept JSON arguments from the LLM. Instead:
1. `fetch_posts` stores full data in shared store, returns a compact summary
2. `classify_posts` reads from shared store (no parameters needed)
3. `cluster_themes` reads from shared store (no parameters needed)
4. `generate_hypotheses` reads from shared store (no parameters needed)

This eliminates the MALFORMED_FUNCTION_CALL entirely because the LLM never needs to pass large JSON strings as tool arguments.

### Bug 3: Circular Import

**Symptom:** After creating the shared data store in `app/agents/tools/__init__.py`, all imports failed.

```
cannot import name 'get_shared_data' from partially initialized module 'app.agents.tools'
```

**Root Cause:** `fetch.py` imports `from app.agents.tools import set_shared_data`, but `app/agents/tools/__init__.py` imports `from app.agents.tools.fetch import fetch_posts`. Circular dependency.

**Fix:** Moved the shared data store to a standalone module `app/agents/tools/shared.py` with zero dependencies on other tool modules. All tool files import from `shared.py` instead of `__init__.py`.

---

## Successful Run Trace

**Command:**
```bash
conda run -n agentic-ai-p2 python scripts/run_agent.py \
  "Find business ideas for people struggling with debt" --mode test
```

**Timeline:**
```
20:28:08  Pipeline started. Provider: gcloud (gemini-2.5-flash). Mode: test.
20:28:08  Orchestrator agent started (iteration 1/20)
20:28:10  Tool call: fetch_posts(topic="business ideas for people struggling with debt")
          → Loaded 30 sample posts from data/sample_posts.json
          → Stored in shared_data["fetched_posts"]
          → Returned summary: {"status": "success", "total_posts": 30}
20:28:12  Orchestrator handoff: -> analyst
20:28:12  Analyst agent started (iteration 1/20)
20:28:13  Tool call: classify_posts()
          → Read 30 posts from shared_data["fetched_posts"]
          → PostClassifier.classify_batch() with gcloud provider
          → 30/30 classified successfully (174.4s, ~5.8s per post)
          → Stored in shared_data["classified_posts"]
20:31:08  Tool call result: 30/30 successful
20:31:09  Tool call: cluster_themes()
          → Read from shared_data["classified_posts"]
          → ThemeClusterer: 29 themes -> 29 canonical -> 9 clusters
          → 6 LLM calls for theme expansion, 29 embeddings (768-dim)
          → Stored in shared_data["clustered_data"]
20:32:14  Tool call result: 9 clusters in 59.1s
20:32:17  Analyst handoff: -> hypothesis
20:32:17  Hypothesis agent started (iteration 1/20)
20:32:19  Tool call: generate_hypotheses()
          → Read from shared_data["clustered_data"]
          → HypothesisGenerator: 3 ideas from 9 clusters (21.3s)
20:32:40  Tool call result: 3 ideas generated
20:32:46  Tool call: save_artifact(artifact_type="hypothesis")
          → Saved to output/hypothesis_20260412_163246.json (5821 bytes)
20:32:54  Final response (formatted summary of 3 ideas)

Total: 5 tool calls across 3 agents in ~4.5 minutes
```

**Output (3 business ideas):**

| Rank | Name | Pain Point | Evidence | Confidence |
|------|------|-----------|----------|------------|
| 1 | FinSimplify | Complex tax filing, financial planning confusion | 9 posts, 52,252 upvotes (TurboTax complaints, 401k issues) | High |
| 2 | Workplace Advocate | Unreasonable managerial demands, work-life balance | 7 posts, 15,476 upvotes (manager disrespect) | High |
| 3 | FocusFlow Ads | Disruptive advertising for neurodivergent users | 3 posts, 1,144 upvotes (YouTube ads = "torture" for ADHD) | Medium |

---

## Lessons Learned

1. **Never pass large JSON through LLM context.** Gemini's function calling breaks with MALFORMED_FUNCTION_CALL when arguments exceed a certain size. Use a shared data store for inter-tool data transfer and return only compact summaries to the LLM.

2. **The provider abstraction is the right pattern.** Adding `chat_with_tools()` to the existing `LLMProvider` ABC meant the agent framework automatically works with all three providers (gcloud, lm_studio, openai_gemini) without any provider-specific code in the agent layer.

3. **Gemini format conversion is non-trivial.** The `_convert_messages_to_gemini()` method handles: system prompts (Gemini has no system role — uses user/model pair), assistant messages with tool calls (Gemini uses `functionCall` parts), and tool responses (Gemini uses `functionResponse` with matching function name). The `functionResponse.name` must match the function declaration name, not the call ID.

4. **Circular imports in Python are silent killers.** When tool files import from `__init__.py` and `__init__.py` imports from tool files, the solution is a separate shared module with zero dependencies. The pattern: `shared.py` (no imports from package) -> `tool_file.py` (imports from shared) -> `__init__.py` (imports from tool_file).

5. **Timeout multiplier for tool-calling contexts.** The same Gemini model that responds in 2s for simple prompts needs 30-90s when the context includes tool definitions + multi-turn conversation history. Multiply the base timeout by 3 for `chat_with_tools()`.

6. **The LLM decides, Python executes.** The agent framework's key property: the LLM chooses which tools to call and in what order. Python only executes what the LLM requests. This is the difference between "tool calling" (agent framework) and "Python orchestration" (regular code). The logs show the LLM made independent decisions: orchestrator chose fetch_posts then handoff, analyst chose classify then cluster then handoff, hypothesis chose generate then save.
