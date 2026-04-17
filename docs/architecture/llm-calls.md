# LLM Call Inventory

_Generated: 2026-04-13_

Every LLM inference in the system, where it happens, what prompt it uses, and what model serves it.

---

## Provider & Model Selection

All calls share a single provider, selected at runtime via `LLM_PROVIDER` env var (default: `gcloud`).

| Provider Key | Class | Default Model | Config Key |
|---|---|---|---|
| `gcloud` | `GCloudProvider` | `gemini-2.5-flash` | `config.gcloud_model` |
| `lm_studio` | `LMStudioProvider` | `qwen3.5-27b-claude-4.6-opus-reasoning-distilled` | `config.lm_studio_model` |
| `openai_gemini` | `OpenAIGeminiProvider` | `gemini-2.5-flash` | `config.gemini_model` |

Provider resolution: `app/analyst/providers/__init__.py` -> `get_provider(config.llm_provider)`

---

## Call Summary Table

| # | Call Type | Invocation Site | Prompt Source | Parameters | Purpose |
|---|---|---|---|---|---|
| 1 | `chat_with_tools` | `app/agents/base.py:71` | `app/agents/orchestrator.py:3-20` | temp=0.3 | Orchestrator agent loop |
| 2 | `chat_with_tools` | `app/agents/base.py:71` | `app/agents/analyst.py:3-23` | temp=0.3 | Analyst agent loop |
| 3 | `chat_with_tools` | `app/agents/base.py:71` | `app/agents/hypothesis.py:3-23` | temp=0.3 | Hypothesis agent loop |
| 4 | `classify_post` | `app/analyst/classifier.py:74` (per post) | `app/analyst/prompts.py:4-22` | temp=0.1, max_tokens=1024 | Per-post complaint classification |
| 5 | `generate_text` | `app/analyst/clustering.py:268` (per cluster) | `app/analyst/cluster_prompts.py:4-18` | temp=0.3, max_tokens=64 | Cluster naming |
| 6 | `generate_text` | `app/analyst/expansion.py:138-139` (per batch) | `app/analyst/expansion_prompts.py:3-33` | temp=0.3, max_tokens=2048 | Theme expansion for embeddings |
| 7 | `generate_structured` | `app/analyst/hypothesis.py:101-105` | `app/analyst/hypothesis_prompts.py:3-42` | temp=0.3, max_tokens=8192 | Generate top-5 business hypotheses |

---

## Detailed Call Breakdown

### Call 1: Orchestrator Agent

- **File:** `app/agents/base.py:71`
- **Method:** `provider.chat_with_tools(messages, tools, temperature=0.3)`
- **Agent:** Orchestrator (first agent in the pipeline)
- **Tools available:** `fetch_posts`
- **User message:** The raw user query string
- **Triggered by:** `AgentOrchestrator.run()` in `app/agents/runner.py:94`

**System Prompt** (`app/agents/orchestrator.py:3-20`):

```
You are the Orchestrator Agent for a Reddit complaint analysis system.

Your job:
1. Understand the user's topic or question about a niche/market
2. Use the fetch_posts tool to gather Reddit posts about that topic
3. Pass the results to the Analyst Agent for classification and clustering

Workflow:
- Call fetch_posts with the user's topic
- Once you have the data, respond with: HANDOFF_TO_AGENT: analyst
- Include a brief summary of what was fetched so the analyst has context

Important:
- You have ONE tool: fetch_posts. Use it to get raw Reddit data.
- After fetching, ALWAYS hand off to the analyst agent.
- Do NOT try to classify or analyze posts yourself.
- Be concise in your summaries.
```

---

### Call 2: Analyst Agent

- **File:** `app/agents/base.py:71`
- **Method:** `provider.chat_with_tools(messages, tools, temperature=0.3)`
- **Agent:** Analyst (second agent in the pipeline)
- **Tools available:** `classify_posts`, `cluster_themes`
- **User message:** Context message from orchestrator handoff (`app/agents/runner.py:140-144`)
- **Triggered by:** `AgentOrchestrator.run()` in `app/agents/runner.py:94`

**System Prompt** (`app/agents/analyst.py:3-23`):

```
You are the Analyst Agent for a Reddit complaint analysis system.

Your job:
1. Take raw Reddit posts from the Orchestrator
2. Use classify_posts to identify complaint themes and intensity
3. Use cluster_themes to group similar complaints into thematic clusters
4. Hand off the clustering results to the Hypothesis Agent

Workflow:
- The previous agent will provide fetched posts in the conversation.
- Call classify_posts with the posts data (pass the JSON from fetch_posts output).
- Then call cluster_themes with the classification results.
- After clustering, respond with: HANDOFF_TO_AGENT: hypothesis
- Include a summary of the clusters found so the hypothesis agent has context.

Important:
- You have TWO tools: classify_posts and cluster_themes. Use them IN ORDER.
- classify_posts FIRST, then cluster_themes with the output.
- After clustering, ALWAYS hand off to the hypothesis agent.
- Be thorough — all posts must be classified before clustering.
```

---

### Call 3: Hypothesis Agent

- **File:** `app/agents/base.py:71`
- **Method:** `provider.chat_with_tools(messages, tools, temperature=0.3)`
- **Agent:** Hypothesis (third/final agent in the pipeline)
- **Tools available:** `generate_hypotheses`, `save_artifact`
- **User message:** Context message from analyst handoff (`app/agents/runner.py:147-151`)
- **Triggered by:** `AgentOrchestrator.run()` in `app/agents/runner.py:94`

**System Prompt** (`app/agents/hypothesis.py:3-23`):

```
You are the Hypothesis Agent for a Reddit complaint analysis system.

Your job:
1. Take clustered complaint data from the Analyst
2. Use generate_hypotheses to create up to 5 ranked business ideas
3. Use save_artifact to persist the hypothesis results
4. Return a final summary to the user

Workflow:
- The previous agent will provide clustering results in the conversation.
- Call generate_hypotheses with the clustering result data.
- Then call save_artifact with the hypothesis output (type: "hypothesis").
- Finally, provide a clear, readable summary of the top business ideas.

Important:
- You have TWO tools: generate_hypotheses and save_artifact. Use them IN ORDER.
- generate_hypotheses FIRST, then save_artifact with the results.
- After saving, provide the FINAL response to the user (no handoff).
- Present the ideas clearly with pain point, product, target user, and confidence.
- Be specific and grounded in the data — no vague generalizations.
```

---

### Call 4: Post Classification (per post)

- **File:** `app/analyst/classifier.py:74` -> provider `classify_post()` method
  - gcloud: `app/analyst/providers/gcloud.py:490-514` (REST POST to Vertex AI)
  - lm_studio: `app/analyst/providers/lm_studio.py:219-224` (OpenAI SDK)
  - openai_gemini: `app/analyst/providers/openai_gemini.py:230-235` (OpenAI SDK)
- **Parameters:** `temperature=0.1`, `max_tokens=1024`
- **Called once per post**, with retries on parse failure (up to `config.gcloud_max_retries`)
- **No system prompt** — prompt sent as a single user message

**User Prompt — first attempt** (`app/analyst/prompts.py:4-22`):

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

**User Prompt — retry** (`app/analyst/prompts.py:24-36`):

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

---

### Call 5: Cluster Naming (per cluster)

- **File:** `app/analyst/clustering.py:268`
- **Method:** `provider.generate_text(prompt, temperature=0.3, max_tokens=64)`
- **Called once per cluster** after KMeans grouping
- **No system prompt** — prompt sent as a single user message

**User Prompt** (`app/analyst/cluster_prompts.py:4-18`):

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

Cluster name:
```

---

### Call 6: Theme Expansion (per batch of ~5 themes)

- **File:** `app/analyst/expansion.py:138-139`
- **Method:** `provider.generate_text(prompt, temperature=0.3, max_tokens=2048)`
- **Called once per batch** (batch size = `config.expansion_batch_size`, default 5)
- **No system prompt** — prompt sent as a single user message
- **Purpose:** Expands short theme labels into 10-20 word descriptions for better embedding quality

**User Prompt — first attempt** (`app/analyst/expansion_prompts.py:3-33`):

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

**User Prompt — retry** (`app/analyst/expansion_prompts.py:35-43`):

```
IMPORTANT: Your previous response was invalid. Return ONLY valid JSON.

Expand these theme labels into full descriptions:
{themes_data}

Output format (return EXACTLY this structure):
{{"theme": "expanded description as a full sentence"}}

Return ONLY the JSON, nothing else:
```

---

### Call 7: Hypothesis Generation

- **File:** `app/analyst/hypothesis.py:101-105`
- **Method:** `provider.generate_structured(prompt, temperature=0.3, max_tokens=8192)`
- **Called once** per pipeline run
- **No system prompt** — prompt sent as a single user message
- **JSON enforcement:** gcloud sets `responseMimeType: "application/json"`; openai_gemini uses `response_format={"type": "json_object"}`; lm_studio falls back to plain `generate_text`

**User Prompt** (`app/analyst/hypothesis_prompts.py:3-42`):

```
You are a business analyst specializing in identifying unmet market needs from social data.

You will be given a list of Reddit complaint clusters. Each cluster represents a real pattern
of frustration expressed by real people, with post counts and upvote totals as signal strength.

Your job: identify the top 5 most actionable business opportunities from this data.

Rules:
- Every claim must reference specific clusters, post counts, or upvote numbers from the input
- Do not invent pain points not present in the data
- Prefer clusters with high upvotes AND high post count (both signal breadth and intensity)
- The product must directly solve the stated complaint, not a tangentially related problem
- Be specific: "app that does X" not "platform that helps people with Y"

Return a JSON object matching this exact schema. No markdown, no preamble, just JSON.

{{
  "ideas": [
    {{
      "rank": 1,
      "idea_name": "Short brandable name",
      "pain_point": "One sentence, plain language description of the pain",
      "product_description": "What it does, specifically - be concrete",
      "target_user": "Who experiences this pain most",
      "evidence": {{
        "cluster_name": "exact name from input",
        "post_count": <number>,
        "total_upvotes": <number>,
        "supporting_post_titles": ["title1", "title2", "title3"]
      }},
      "confidence": "high|medium|low",
      "confidence_reasoning": "Why this confidence level"
    }}
  ],
  "analysis_summary": "2-3 sentences on overall pattern across clusters",
  "data_limitations": "Honest caveat about what this dataset can and cannot tell us"
}}

Clusters:
{clusters_json}
```

---

## Non-LLM API Calls (Embeddings)

These are embedding calls, not text generation, but listed for completeness.

| Call | File | Model | Provider |
|---|---|---|---|
| Embedding generation | `app/analyst/clustering.py:93` | `text-embedding-004` (gcloud) / `gemini-embedding-2-preview` (openai_gemini) / provider default (lm_studio) | `provider.get_embeddings(texts)` |

---

## Data Flow Diagram

```
User Query
    |
    v
[Call 1] Orchestrator Agent (chat_with_tools)
    |-- tool call: fetch_posts -> Reddit API (not LLM)
    |-- handoff: HANDOFF_TO_AGENT: analyst
    |
    v
[Call 2] Analyst Agent (chat_with_tools)
    |-- tool call: classify_posts
    |       |-- [Call 4] classify_post x N (one per post)
    |       |-- [Call 6] expand_themes x batches (theme expansion)
    |       `-- embedding + KMeans clustering
    |-- tool call: cluster_themes
    |       `-- [Call 5] generate_text x K (one per cluster name)
    |-- handoff: HANDOFF_TO_AGENT: hypothesis
    |
    v
[Call 3] Hypothesis Agent (chat_with_tools)
    |-- tool call: generate_hypotheses
    |       `-- [Call 7] generate_structured (one call)
    |-- tool call: save_artifact (file I/O, not LLM)
    `-- final response to user
```
