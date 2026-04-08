# Important Clarifications

This document addresses ambiguities in the project requirements to help ensure correct implementation.

---

## 1. "Real-World Data" / "Non-trivial Dataset"

### What It IS
- Data from actual external sources (APIs, databases, public datasets, web sources)
- Datasets large enough to require programmatic querying (thousands+ rows)
- Data that exists independently of your project (Census data, sports stats, stock prices, etc.)
- Pre-existing datasets you bundle (CSV, SQLite, Parquet) that are substantial

### What It IS NOT
- A 50-row CSV you hand-curated specifically for this project
- Synthetic/fake data generated for testing
- A few hardcoded examples embedded in your code
- Data small enough to paste entirely into a prompt

### Gray Area
- **Bundled vs. Hard-coded**: Bundling a 100,000-row CSV file is acceptable. Hard-coding 50 rows as a Python list in your source code is not.

---

## 2. "Hard-coded into the System Prompt"

### What It IS
- Embedding the actual data values directly in the agent's system message
- Pasting CSV contents into the prompt text
- Storing data as string literals in Python code that get inserted into prompts

### What It IS NOT
- Bundling data files (CSV, SQLite, PDFs) with your application
- Having the agent read from files at runtime
- Storing API keys or connection strings as environment variables

### Key Distinction
The agent must **actively retrieve** data through a mechanism (query, API call, file read) at runtime, not have the data pre-baked into its instructions.

---

## 3. "At Runtime"

### What It IS
- Data fetched when the user asks a question
- Queries executed in response to user input
- API calls made during the conversation
- File reads triggered by the agent's decision-making

### What It IS NOT
- Data loaded once at application startup and cached forever (without any agent-driven retrieval logic)
- Pre-computed results stored and returned verbatim
- Static responses regardless of user question

### Gray Area
- **Pre-indexing for RAG**: Embedding documents into a vector store before runtime is acceptable. The retrieval step still happens at runtime.
- **Cached API responses**: Light caching is fine, but the agent must demonstrate it can fetch fresh/alternative data.

---

## 4. "Tool Call"

### What It IS
- A function the agent invokes through the framework's tool-calling mechanism
- SQL query execution via a tool
- API calls wrapped as tools
- Sub-agent invocations via handoff or agent-as-tool patterns
- Python code execution in a sandbox (if wrapped as a callable tool)

### What It IS NOT
- Regular Python function calls in your backend code
- Hard-coded logic that runs before the agent sees the request
- Internal helper functions the agent doesn't directly control

### Key Distinction
The **agent decides** to call the tool based on the conversation. It's not automatic backend processing.

---

## 5. "Multi-Agent Pattern" / "Distinct Agents"

### What It IS
- Two or more agents with **different system prompts** and **different responsibilities**
- Orchestrator that hands off to specialist agents
- Generator-critic patterns where one creates, another evaluates
- Fan-out patterns where parallel agents work on subtasks

### What It IS NOT
- The same agent called multiple times
- Two agents with identical or nearly-identical system prompts
- An agent that just calls a regular Python function (not another agent)
- Cosmetic role names without meaningful prompt differences

### Key Distinction
Each agent should have a distinct **purpose** and **behavior** encoded in its system prompt. Ask: "Could I swap these agents and get the same result?" If yes, they're not distinct enough.

---

## 6. "Dynamic to Different Questions"

### What It IS
- Different user questions trigger different queries/tools
- Agent adapts SQL queries based on the question
- Agent chooses different analysis methods based on what's being asked
- Tool usage patterns change meaningfully across question types

### What It IS NOT
- Same query runs every time, just formatted differently in output
- Fixed pipeline that ignores question content
- Cosmetic variations that don't change the actual computation

### Test
Ask two meaningfully different questions. Does the agent's tool usage meaningfully differ?

---

## 7. "Generic Summary vs. EDA"

### What It IS (Valid EDA)
- Surfaces specific numbers, patterns, or anomalies
- Computes statistics (means, correlations, distributions)
- Identifies trends, outliers, or segments
- Produces findings that feed into hypothesis formation

### What It IS NOT (Generic Summary)
- "Here are the first 10 rows of the data"
- "The dataset has X columns and Y rows"
- Re-stating metadata without analysis
- Dumping raw data without computation

### Key Distinction
EDA should **reveal something** that wasn't obvious from just looking at the raw data.

---

## 8. "Hypothesis from Data, Not Model Weights"

### What It IS
- Claims backed by specific data points retrieved during the session
- "Revenue grew 12% because Q3 Northeast sales increased 23%"
- Evidence citations that reference actual computed results
- Reasoning that traces back to tool outputs

### What It IS NOT
- Generic claims that could apply to any dataset
- Assertions based on the model's training knowledge
- Hypotheses that don't reference specific findings from the EDA phase
- Making up numbers that weren't actually computed

### Test
Could this hypothesis have been generated without running the tools? If yes, it's not data-derived.

---

## 9. "Large Enough That Loading Entirely Into Context Is Impractical"

### What It IS
- Datasets requiring thousands of tokens to represent fully
- Data that necessitates selective retrieval (queries, filtering)
- Files measured in megabytes, not kilobytes
- Datasets where you couldn't paste all rows into a prompt

### What It IS NOT
- A 100-row CSV that fits easily in context
- Data so small the agent could "see" all of it without tools

### Rule of Thumb
If you could paste the entire dataset into a single prompt without hitting token limits, it's probably too small.

---

## 10. "Iterative Refinement Loop"

### What It IS
- Agent queries → analyzes → identifies gaps → queries again
- Multiple rounds of data collection and analysis
- Stopping condition based on sufficiency of information
- Deep research pattern with backtracking

### What It IS NOT
- Single-pass: collect once, analyze once, done
- Pre-defined fixed number of iterations regardless of findings
- Loops that don't actually change behavior based on intermediate results

### Key Distinction
The agent should **recognize when it needs more information** and take action to get it.

---

## 11. "Artifacts"

### What It IS
- Files written to disk during execution (CSVs, PNGs, markdown reports)
- Persistent outputs that exist after the session ends
- Generated content saved with file paths

### What It IS NOT
- In-memory data structures
- Console output only
- Temporary variables that don't persist

### Gray Area
- **Displaying a chart in the UI**: This may or may not count as an artifact depending on whether it's also saved to disk. Check with instructor if this is your primary artifact claim.

---

## 12. "Structured Output"

### What It IS
- JSON mode or constrained decoding
- Pydantic models for validated outputs
- Tool call schemas that enforce structure
- Output schemas defined in advance

### What It IS NOT
- Freeform text that happens to look like JSON
- Post-hoc parsing of unstructured output
- Regex extraction from natural language

### Key Distinction
The structure is **enforced** by the framework, not extracted after the fact.

---

## Quick Reference: Common Edge Cases

| Question | Answer |
|----------|--------|
| Can I bundle a CSV file with my app? | Yes, as long as it's large and the agent queries it dynamically |
| Does calling the same agent twice count as multi-agent? | No, need distinct agents with different prompts |
| Does a sub-agent count as a tool call? | Yes, if invoked via tool/handoff mechanism |
| Can I pre-embed documents for RAG? | Yes, retrieval still happens at runtime |
| Does showing a chart in UI count as artifact? | Maybe - save to disk to be safe |
| Is caching API responses allowed? | Light caching ok, but must demonstrate dynamic capability |
