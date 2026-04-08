# Grading Checklist - Agentic AI Project 2

Use this checklist to verify all requirements are met. Total: 30 points.

---

## STEP 1: COLLECT (5 points)

### Data Source (2 pts)
- [ ] Does the agent retrieve data from a real, external source (not hard-coded in system prompt)?
- [ ] Is the data retrieved at runtime, not bundled statically?
- [ ] Is the data source non-trivial (not a 50-row hand-curated CSV)?

### Collection Method (1 pt)
- [ ] Which method is used?
  - [ ] SQL composition (dynamically writes and executes SQL queries)
  - [ ] API integration (calls public/private APIs)
  - [ ] RAG (retrieves from embedded document corpus)
  - [ ] Web search/crawling (uses web search API or scrapes pages)

### Data Appropriateness (1 pt)
- [ ] Is the dataset large/complex enough that loading entirely into context is impractical?
- [ ] Is the data relevant to the analytics question being asked?

### Dynamic Behavior (1 pt)
- [ ] Does the agent adapt its data retrieval based on the user's question?
- [ ] Can different questions trigger different data retrieval patterns?

---

## STEP 2: EXPLORE & ANALYZE - EDA (5 points)

### Tool Call Requirement (2 pts)
- [ ] Does the EDA phase involve at least one tool call?
- [ ] Does the tool use some amount of the collected data (not just metadata)?

### EDA Method Used (1 pt)
- [ ] Which EDA method is used?
  - [ ] Statistical aggregation (means, medians, distributions, correlations, growth rates)
  - [ ] Filtering and grouping (segments by category, time period, threshold)
  - [ ] Text analysis (sentiment counts, keyword extraction, entity frequency, topic clustering)
  - [ ] Specialist sub-agent (dedicated analytical prompt, invoked via tool/handoff)
  - [ ] Code execution (Python with pandas/numpy/scipy in sandboxed environment)
  - [ ] Other (specify): ___________

### Dynamic EDA (1 pt)
- [ ] Does the EDA adapt to different questions?
- [ ] Can different questions trigger different tools or different tool usage patterns?

### Specific Findings (1 pt)
- [ ] Does the exploration surface something specific (a number, pattern, anomaly)?
- [ ] Is the output more than a generic summary of raw data?

---

## STEP 3: HYPOTHESIZE (5 points)

### Data-Derived Hypothesis (2 pts)
- [ ] Is the hypothesis derived from the collected data, not model weights?
- [ ] Does the agent explain its reasoning process?

### Supporting Evidence (2 pts)
- [ ] Does the hypothesis cite specific data points?
- [ ] Is supporting evidence clearly provided?

### Communication Format (1 pt)
- [ ] What format is used for the hypothesis?
  - [ ] Natural language summary with specific data points
  - [ ] Generated report/memo with tables and citations
  - [ ] Visualization with explanatory caption
  - [ ] Comparison of competing explanations with evidence for/against each

---

## CORE REQUIREMENTS (10 points)

### Frontend (2 pts)
- [ ] Is there a frontend that can be loaded and interacted with?
- [ ] Can the grader access and use the frontend?

### Agent Framework (1 pt)
- [ ] Which framework is used?
  - [ ] OpenAI Agents SDK
  - [ ] Google ADK
  - [ ] LangGraph
  - [ ] PydanticAI
  - [ ] CrewAI
  - [ ] Other (specify): ___________
- [ ] File location: ___________

### Tool Calling (1 pt)
- [ ] Is at least one tool call implemented?
- [ ] File location: ___________

### Non-trivial Dataset (1 pt)
- [ ] Is data retrieved from a real, non-trivial external source at runtime?
- [ ] File location of data retrieval logic: ___________

### Multi-Agent Pattern (2 pts)
- [ ] Which pattern is used?
  - [ ] Orchestrator-handoff
  - [ ] Generator-critic
  - [ ] Fan-out
  - [ ] Agent-as-tool-call
  - [ ] Other (specify): ___________
- [ ] Are there at least two distinct agents with different system prompts?
- [ ] File locations of agent definitions:
  - Agent 1: ___________
  - Agent 2: ___________

### Deployed (2 pts)
- [ ] Is the application deployed and accessible?
- [ ] Deployment URL/Access method: ___________

### README.md (1 pt)
- [ ] Is there a README.md explaining how to run the project?
- [ ] Does the README explain how all three steps (Collect → EDA → Hypothesize) are implemented?
- [ ] Does the README identify which concepts are implemented and where (file + function/class name)?

---

## GRAB BAG ELECTIVES (5 points - at least 2 required, 2.5 pts each)

### Elective 1 (2.5 pts)
- [ ] Which elective is implemented?
  - [ ] Iterative refinement loop
  - [ ] Code execution (Python/pandas)
  - [ ] Artifacts (CSVs, charts, reports)
  - [ ] Structured output (JSON mode)
  - [ ] Second data retrieval method
  - [ ] Data visualization
  - [ ] Parallel execution
- [ ] File location: ___________

### Elective 2 (2.5 pts)
- [ ] Which elective is implemented?
  - [ ] Iterative refinement loop
  - [ ] Code execution (Python/pandas)
  - [ ] Artifacts (CSVs, charts, reports)
  - [ ] Structured output (JSON mode)
  - [ ] Second data retrieval method
  - [ ] Data visualization
  - [ ] Parallel execution
- [ ] File location: ___________

---

## README DOCUMENTATION CHECK

### Concept Mapping
For each implemented concept, the README must specify:
- [ ] Collect - File + function/class: ___________
- [ ] EDA - File + function/class: ___________
- [ ] Hypothesize - File + function/class: ___________
- [ ] Agent framework - File + function/class: ___________
- [ ] Tool calling - File + function/class: ___________
- [ ] Multi-agent pattern - File + function/class: ___________
- [ ] Elective 1 - File + function/class: ___________
- [ ] Elective 2 - File + function/class: ___________

---

## Verification Summary

| Section | Points | Verified |
|---------|--------|----------|
| Step 1: Collect | 5 | [ ] |
| Step 2: EDA | 5 | [ ] |
| Step 3: Hypothesize | 5 | [ ] |
| Core Requirements | 10 | [ ] |
| Grab Bag (2 electives) | 5 | [ ] |
| **Total** | **30** | [ ] |
