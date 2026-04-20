# Trace: Query Context Propagation in LangGraph Pipeline

**Date:** 2026-04-18
**Session:** Fix dilution of the original user query as it flows through the agent pipeline. The query (e.g., "artificial intelligence") was stored in `AgentState.user_query` but never explicitly referenced in analyst prompts, hypothesis prompts, or the hypothesis generation LLM call — leading to generic or misaligned results.

**Files Modified:**
- `app/agents/tools/fetch.py` — Store `user_query` in shared data during fetch (P0)
- `app/agents/tools/hypothesis.py` — Read `user_query` from shared data, pass to generator (P0)
- `app/analyst/hypothesis.py` — Accept `user_query` kwarg in `generate_hypotheses()` and `_call_llm()` (P0)
- `app/analyst/hypothesis_prompts.py` — Add `{user_query}` placeholder and relevance instructions (P0)
- `app/agents/analyst.py` — Dynamic prompt with `{user_query}`, added `get_analyst_prompt()` (P1)
- `app/agents/hypothesis.py` — Dynamic prompt with `{user_query}`, added `get_hypothesis_prompt()` (P1)
- `app/agents/graph.py` — Use `get_analyst_prompt()`/`get_hypothesis_prompt()` in nodes (P1)
- `app/agents/runner.py` — Use `_get_system_prompt()` with dynamic query injection (P1)

**Files Not Modified:**
- `app/agents/tools/classify.py`, `cluster.py`, `artifacts.py`, `shared.py` — Tool data flow unchanged
- `app/analyst/classifier.py`, `clustering.py` — Business logic unchanged
- `app/agents/orchestrator.py` — Already receives the user query directly as the first message

---

## Problem

The original user query gets diluted or lost as it flows through the agent pipeline:

```
User: "artificial intelligence"
  │
  ▼
ORCHESTRATOR: sees query → calls fetch_posts(topic="artificial intelligence")
  │
  ▼  Graph edge: orchestrator → analyst
  │
ANALYST: system prompt has NO mention of the original query
         → classifies posts generically
  │
  ▼  Graph edge: analyst → hypothesis
  │
HYPOTHESIS AGENT: system prompt has NO mention of the original query
         → calls generate_hypotheses() with no query context
         → HYPOTHESIS_PROMPT has NO query placeholder
         → LLM generates generic business ideas, not AI-specific ones
```

The query exists in `AgentState.user_query` and is passed as the first user message via `_build_context_messages()`, but:

1. **Agent system prompts** never reference it — the LLM has to infer relevance from the message history alone
2. **The hypothesis generation LLM call** (the most critical prompt) has zero awareness of what the user asked about
3. **The hypothesis agent prompt** doesn't remind the agent to frame results in context of the original question

---

## Solution: Three-Layer Query Injection

### Layer 1: Shared Data Store (Tool-Level)

The `fetch_posts` tool already receives the topic. Now it also stores it as `user_query` in the shared data store:

```python
# app/agents/tools/fetch.py
set_shared_data("fetched_posts", full_data)
set_shared_data("user_query", topic)  # NEW
```

The `generate_hypotheses` tool reads it and passes it through:

```python
# app/agents/tools/hypothesis.py
user_query = get_shared_data("user_query") or ""
result = generator.generate_hypotheses(clustering_result, user_query=user_query)  # NEW
```

### Layer 2: Hypothesis LLM Prompt (Highest Impact)

The `HYPOTHESIS_PROMPT` template now includes the query at the very top:

```python
# app/analyst/hypothesis_prompts.py
HYPOTHESIS_PROMPT = """You are a product founder identifying specific, buildable business
opportunities from Reddit complaints.

USER'S ORIGINAL QUERY: {user_query}

IMPORTANT: The user specifically asked about "{user_query}". Every business idea you propose
MUST be directly relevant to this topic/niche. Prioritize ideas that address pain points
within the "{user_query}" space.
...
{clusters_json}"""
```

The `HypothesisGenerator._call_llm()` formats it:

```python
prompt = HYPOTHESIS_PROMPT.format(clusters_json=clusters_json, user_query=user_query)
```

### Layer 3: Agent System Prompts (Contextual Awareness)

Agent system prompts changed from static strings to parameterized templates:

```python
# app/agents/analyst.py
ANALYST_SYSTEM_PROMPT_TEMPLATE = """...
The user originally asked about: {user_query}
...
Keep the user's original query ("{user_query}") in mind when analyzing.
"""

def get_analyst_prompt(user_query: str) -> str:
    return ANALYST_SYSTEM_PROMPT_TEMPLATE.replace("{user_query}", user_query)
```

Same pattern for `app/agents/hypothesis.py` with `get_hypothesis_prompt()`.

The graph nodes inject the query at runtime:

```python
# app/agents/graph.py — analyst_node
user_query = state.get("user_query", "")
analyst_prompt = get_analyst_prompt(user_query)
result = _run_agent_loop(agent_name="analyst", system_prompt=analyst_prompt, ...)
```

---

## Data Flow: Before vs After

### BEFORE

```
user_query ─→ AgentState.user_query (stored but unused by prompts)
           ─→ _build_context_messages() (passed as first user message)
           ─→ fetch_posts(topic) (used for fetching)
           ╳ analyst system prompt (NO reference to query)
           ╳ hypothesis system prompt (NO reference to query)
           ╳ HYPOTHESIS_PROMPT (NO query placeholder)
           ╳ HypothesisGenerator.generate_hypotheses() (no query param)
```

### AFTER

```
user_query ─→ AgentState.user_query (stored)
           ─→ _build_context_messages() (passed as first user message)
           ─→ fetch_posts(topic)
              └─→ shared_data["user_query"] = topic          ← NEW
           ─→ analyst system prompt: "...asked about: {user_query}"  ← NEW
           ─→ hypothesis system prompt: "...asked about: {user_query}" ← NEW
           ─→ generate_hypotheses tool:
              └─→ reads shared_data["user_query"]             ← NEW
              └─→ HypothesisGenerator(user_query=...)         ← NEW
                  └─→ HYPOTHESIS_PROMPT.format(user_query=...) ← NEW
```

---

## Files Changed: Detailed Diff

### `app/agents/tools/fetch.py` (+3 lines)

```diff
     set_shared_data("fetched_posts", full_data)
+
+    # Store the original user query so downstream tools (hypothesis, etc.)
+    # can ground their output in what the user actually asked about.
+    set_shared_data("user_query", topic)
```

### `app/agents/tools/hypothesis.py` (+3 lines)

```diff
     provider = get_provider(config.llm_provider)
     generator = HypothesisGenerator(provider=provider)
-    result = generator.generate_hypotheses(clustering_result)
+
+    # Retrieve the original user query to ground hypotheses in what the user asked about
+    user_query = get_shared_data("user_query") or ""
+    result = generator.generate_hypotheses(clustering_result, user_query=user_query)
```

### `app/analyst/hypothesis.py` (signature change + threading)

```diff
-    def generate_hypotheses(self, clustering_result: ClusteringResult) -> HypothesisOutput:
+    def generate_hypotheses(self, clustering_result: ClusteringResult, *, user_query: str = "") -> HypothesisOutput:
         ...
-        raw = self._call_llm(cluster_table)
+        raw = self._call_llm(cluster_table, user_query=user_query)

-    def _call_llm(self, cluster_table: list[dict]) -> str:
+    def _call_llm(self, cluster_table: list[dict], *, user_query: str = "") -> str:
         clusters_json = json.dumps(cluster_table, indent=2, ensure_ascii=False)
-        prompt = HYPOTHESIS_PROMPT.format(clusters_json=clusters_json)
+        prompt = HYPOTHESIS_PROMPT.format(clusters_json=clusters_json, user_query=user_query)
```

### `app/analyst/hypothesis_prompts.py` (query context block added)

```diff
 HYPOTHESIS_PROMPT = """You are a product founder identifying specific, buildable business opportunities
 from Reddit complaints.
+
+USER'S ORIGINAL QUERY: {user_query}
+
+IMPORTANT: The user specifically asked about "{user_query}". Every business idea you propose MUST be directly
+relevant to this topic/niche. Prioritize ideas that address pain points within the "{user_query}" space.
+If the data contains complaints outside this scope, deprioritize them unless they are clearly adjacent.
```

### `app/agents/analyst.py` (template + function)

```diff
-ANALYST_SYSTEM_PROMPT = """You are the Analyst Agent...
+ANALYST_SYSTEM_PROMPT_TEMPLATE = """You are the Analyst Agent...
+
+The user originally asked about: {user_query}
 ...
+- Keep the user's original query ("{user_query}") in mind when analyzing — prioritize themes most relevant to what they asked about.
 """
+
+
+def get_analyst_prompt(user_query: str) -> str:
+    """Return the analyst system prompt with the user query injected."""
+    return ANALYST_SYSTEM_PROMPT_TEMPLATE.replace("{user_query}", user_query)
```

### `app/agents/hypothesis.py` (template + function)

Same pattern as analyst: `HYPOTHESIS_SYSTEM_PROMPT` → `HYPOTHESIS_SYSTEM_PROMPT_TEMPLATE` + `get_hypothesis_prompt()`.

### `app/agents/graph.py` (imports + node functions)

```diff
-from app.agents.analyst import ANALYST_SYSTEM_PROMPT
-from app.agents.hypothesis import HYPOTHESIS_SYSTEM_PROMPT
+from app.agents.analyst import get_analyst_prompt
+from app.agents.hypothesis import get_hypothesis_prompt

 def analyst_node(state):
-    result = _run_agent_loop(system_prompt=ANALYST_SYSTEM_PROMPT, ...)
+    user_query = state.get("user_query", "")
+    analyst_prompt = get_analyst_prompt(user_query)
+    result = _run_agent_loop(system_prompt=analyst_prompt, ...)

 def hypothesis_node(state):
-    result = _run_agent_loop(system_prompt=HYPOTHESIS_SYSTEM_PROMPT, ...)
+    user_query = state.get("user_query", "")
+    hypothesis_prompt = get_hypothesis_prompt(user_query)
+    result = _run_agent_loop(system_prompt=hypothesis_prompt, ...)
```

### `app/agents/runner.py` (legacy path also updated)

```diff
-from app.agents.analyst import ANALYST_SYSTEM_PROMPT
-from app.agents.hypothesis import HYPOTHESIS_SYSTEM_PROMPT
+from app.agents.analyst import get_analyst_prompt
+from app.agents.hypothesis import get_hypothesis_prompt

-SYSTEM_PROMPTS = {
-    "orchestrator": ORCHESTRATOR_SYSTEM_PROMPT,
-    "analyst": ANALYST_SYSTEM_PROMPT,
-    "hypothesis": HYPOTHESIS_SYSTEM_PROMPT,
-}
+def _get_system_prompt(agent_name: str, user_query: str) -> str:
+    if agent_name == "orchestrator":
+        return ORCHESTRATOR_SYSTEM_PROMPT
+    elif agent_name == "analyst":
+        return get_analyst_prompt(user_query)
+    elif agent_name == "hypothesis":
+        return get_hypothesis_prompt(user_query)
+    raise ValueError(f"Unknown agent: {agent_name}")
```

---

## Design Decisions

1. **`user_query` in shared data, not graph state.** The query already exists in `AgentState.user_query`. Adding it to the shared store makes it accessible to tools without modifying tool signatures or the `execute_tool()` dispatcher. Tools read it when they need it.

2. **`.replace()` instead of `.format()` for system prompts.** The system prompt templates are plain strings, not format strings with `{{}}` escaping. Using `.replace("{user_query}", user_query)` keeps the template readable and avoids double-brace confusion. The hypothesis prompt uses `.format()` because it already has `{clusters_json}` and uses `{{}}` for JSON examples.

3. **Backward-compatible keyword argument.** `generate_hypotheses(clustering_result, user_query="")` uses a keyword-only arg with a default empty string. Existing callers (e.g., `scripts/generate_hypothesis.py`) continue to work without changes.

4. **No changes to classification.** The plan included an optional P2 to add query context to post classification. Deliberately skipped — classification should identify all complaints objectively. Filtering by query relevance is better done at the hypothesis stage where we have the full picture.

---

## Verification

```bash
# Import check — all modules load cleanly
python -c "
from app.agents.analyst import get_analyst_prompt
from app.agents.hypothesis import get_hypothesis_prompt
from app.agents.graph import run_pipeline
from app.agents.runner import AgentOrchestrator
"

# Prompt formatting — query appears in all expected places
python -c "
p1 = get_analyst_prompt('artificial intelligence')
assert 'artificial intelligence' in p1

p2 = get_hypothesis_prompt('artificial intelligence')
assert 'artificial intelligence' in p2

from app.analyst.hypothesis_prompts import HYPOTHESIS_PROMPT
formatted = HYPOTHESIS_PROMPT.format(clusters_json='[]', user_query='test query')
assert 'test query' in formatted
"

# Docker rebuild — containers start with new code
docker compose down && docker compose build --no-cache && docker compose up -d --force-recreate
docker compose ps  # both containers Up
```

All checks passed. Containers rebuilt and running.

---

## Lessons Learned

1. **Query context must be explicit, not implicit.** The user query was in the message history, but LLMs don't reliably extract and prioritize it from conversational context. Explicit injection into system prompts and the hypothesis prompt is far more effective.

2. **Shared data store doubles as a context bus.** The `shared.py` module was designed for tool-level data passing (posts, classifications, clusters). Using it to also pass the user query is a natural extension — tools can read it without changing their call signatures.

3. **Static prompts are a maintenance hazard.** Renaming `ANALYST_SYSTEM_PROMPT` to `ANALYST_SYSTEM_PROMPT_TEMPLATE` + `get_analyst_prompt()` is a one-time cost, but it catches any other file still importing the old name. The grep found `runner.py` which also needed updating.

4. **`.replace()` vs `.format()` — pick one pattern.** System prompts use `.replace()` because they're simple strings. The hypothesis prompt uses `.format()` because it has existing placeholders. Mixing is fine as long as each file is consistent internally.
