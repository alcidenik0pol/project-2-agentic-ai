# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What We Are Building

A multi-agent data analysis app. The user inputs a topic or niche. The system queries Reddit, analyzes the posts and comments, and returns a structured report of recurring complaints, their frequency, and whether existing solutions exist.

### The Core User Value
Surface unsolved pain points in any niche, grounded in real Reddit data, not model knowledge.

### Data Source
Reddit API (OAuth). One topic query fans out across relevant subreddits.

### Agent Responsibilities
- **Agent 1 (Collector)**: Takes the user topic, identifies relevant subreddits, fetches posts and comments via Reddit API, returns raw structured data.
- **Agent 2 (Analyst)**: Takes raw data, clusters complaints by theme, counts frequency, weights by upvotes, checks for existing solutions, returns ranked findings.

### Output
A ranked table of complaint themes with frequency, upvote weight, and existing solution status. Plus a one-paragraph hypothesis: the biggest unsolved pain in this niche and why.

### What the System Does NOT Do
- Does not validate whether a business idea is good.
- Does not generate complaints from model knowledge. Every finding must trace back to a real Reddit post with a link.
- Does not call the Reddit API twice for the same topic. First result is stored and reused.

---

## EVALUATION: Assignment Requirements Mapping

This section tracks how our implementation maps to the Columbia Agentic AI Project 2 grading criteria (30 pts total).

### Three Required Steps

| Step | Our Implementation | Points |
|------|-------------------|--------|
| **1. Collect** | Reddit API via Agent 1 (Collector) - fetches posts/comments at runtime | 5 |
| **2. EDA** | Agent 2 clusters complaints, counts frequency, weights by upvotes | 5 |
| **3. Hypothesize** | One-paragraph hypothesis with evidence from ranked findings | 5 |

### Core Requirements (10 pts)

| Requirement | Our Implementation | Points |
|-------------|-------------------|--------|
| Frontend | TBD | 2 |
| Agent Framework | TBD (LangGraph / OpenAI SDK / CrewAI) | 1 |
| Tool Calling | Reddit API tool + analysis tools | 1 |
| Non-trivial Dataset | Reddit posts/comments (thousands of rows) | 1 |
| Multi-agent Pattern | Collector + Analyst with distinct prompts | 2 |
| Deployed | TBD | 2 |
| README.md | TBD | 1 |

### Grab Bag Electives (need 2, 2.5 pts each)

| Elective | Our Implementation | Points |
|----------|-------------------|--------|
| Iterative refinement loop | Collector can re-query if Analyst finds gaps | 2.5 |
| Second data retrieval method | TBD (HN API for solution checking?) | 2.5 |
| Artifacts | TBD (save reports to disk) | 2.5 |
| Structured output | TBD (Pydantic models for findings) | 2.5 |
| Data visualization | TBD | 2.5 |
| Parallel execution | TBD | 2.5 |

### Key Constraint Checklist
- [ ] Data NOT hard-coded in system prompts
- [ ] Dataset too large to load into context (Reddit posts = thousands of rows)
- [ ] At least TWO agents with DIFFERENT system prompts
- [ ] Dynamic behavior: different topics trigger different subreddit queries
- [ ] Deployed and accessible online

### Key Definitions (from teacher's clarifications)
- **"At runtime"**: Data fetched when user submits topic, not pre-baked
- **"Tool call"**: Agent decides to invoke, not automatic backend processing
- **"Distinct agents"**: Different prompts AND responsibilities - swapping them changes results
- **"EDA vs generic summary"**: Must reveal patterns/anomalies, not just describe raw data

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## Python Environment

**CRITICAL: Use the local conda environment for ALL Python operations.**

### Conda Environment: `agentic-ai-p2`

All Python development, testing, and execution MUST use the `agentic-ai-p2` conda environment.

**Rules:**
- **DO**: Always activate conda before running Python: `conda activate agentic-ai-p2`
- **DO**: Install all packages via conda or pip while environment is active
- **DON'T**: Use system Python or virtualenv (venv, poetry, etc.)
- **DON'T**: Run Python scripts without activating the conda environment first

### Creating the Environment (if not exists)
```bash
# Create environment with Python 3.11
conda create -n agentic-ai-p2 python=3.11 -y

# Activate
conda activate agentic-ai-p2

# Install dependencies
pip install -r requirements.txt
```

### Verifying Active Environment
```bash
# Should show (agentic-ai-p2) in prompt and output
which python
python --version
```

### Bash Tool Usage
When using the Bash tool for Python commands:
- Always prefix with conda activation: `conda run -n agentic-ai-p2 <command>`
- Or activate first in an interactive shell
- Example: `conda run -n agentic-ai-p2 python scripts/manual_test.py`

## Environment Variables

**CRITICAL:** All environment variables MUST be loaded through `app/config.py`.

- **DO:** Use `from app.config import config; config.reddit_client_id`
- **DON'T:** Use `os.getenv("REDDIT_CLIENT_ID")` anywhere in the app

This ensures:
- Single source of truth for all configuration
- Easy validation and error handling
- Simple to mock in tests
- Clear visibility of what the app needs to run

## History
The `LEARNING.md` file contains insights, tips, and best practices discovered during previous tasks. Read this file before running new tasks to benefit from prior knowledge. Update it with any new findings after each task run if necessary (only when new information is available or when you need to update existing information).

You have full access to the entire memory, plus you can track changes via git. Every entry is timestamped.

## Plan mode Specific Instructions

Review this plan thoroughly before making any code changes. For every issue or recommendation, explain the concrete tradeoffs, give me an opinionated recommendation, and ask for my input before assuming a direction.

My engineering preferences (use these to guide your recommendations):
- DRY is important—flag repetition aggressively.
- Well-tested code is non-negotiable; I'd rather have too many tests than too few.
- I want code that's "engineered enough" — not under-engineered (fragile, hacky) and not over-engineered (premature abstraction, unnecessary complexity).
- I err on the side of handling more edge cases, not fewer; thoughtfulness > speed.
- Bias toward explicit over clever.

**1. Architecture review**

Evaluate:
- Overall system design and component boundaries.
- Dependency graph and coupling concerns.
- Data flow patterns and potential bottlenecks.
- Scaling characteristics and single points of failure.
- Security architecture (auth, data access, API boundaries).

**2. Code quality review**

Evaluate:
- Code organization and module structure.
- DRY violations—be aggressive here.
- Error handling patterns and missing edge cases (call these out explicitly).
- Technical debt hotspots.
- Areas that are over-engineered or under-engineered relative to my preferences.

**3. Test review**

Evaluate:
- Test coverage gaps (unit, integration, e2e).
- Test quality and assertion strength.
- Missing edge case coverage—be thorough.
- Untested failure modes and error paths.

**4. Performance review**

Evaluate:
- N+1 queries and database access patterns.
- Memory-usage concerns.
- Caching opportunities.
- Slow or high-complexity code paths.

**For each issue you find**

For every specific issue (bug, smell, design concern, or risk):
- Describe the problem concretely, with file and line references.
- Present 2–3 options, including "do nothing" where that's reasonable.
- For each option, specify: implementation effort, risk, impact on other code, and maintenance burden.
- Give me your recommended option and why, mapped to my preferences above.
- Then explicitly ask whether I agree or want to choose a different direction before proceeding.

**Workflow and interaction**
- Do not assume my priorities on timeline or scale.
- After each section, pause and ask for my feedback before moving on.

---

**BEFORE YOU START:**

Ask if I want one of two options:

1/ BIG CHANGE: Work through this interactively, one section at a time (Architecture → Code Quality → Tests → Performance) with at most 4 top issues in each section.

2/ SMALL CHANGE: Work through interactively ONE question per review section

FOR EACH STAGE OF REVIEW: output the explanation and pros and cons of each stage's questions AND your opinionated recommendation and why, and then use AskUserQuestion. Also NUMBER issues and then give LETTERS for options and when using AskUserQuestion make sure each option clearly labels the issue NUMBER and option LETTER so the user doesn't get confused. Make the recommended option always the 1st option.