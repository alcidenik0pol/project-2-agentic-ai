# Workflow Report
_Generated: 2026-04-18T13:57:11.770307+00:00_

## 1. Subreddit Selection

**Topic:** artificial intelligence
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> Selected subreddits cover direct complaints about AI in software development, gaming, and tech support, as well as its significant impact on careers, business, and general daily frustrations. Includes forums for specific industries affected by AI (music, indie games) and broader financial implications.

### Selected Subreddits
- r/cscareerquestions
- r/softwaregore
- r/gamedev
- r/talesfromtechsupport
- r/assholedesign
- r/mildlyinfuriating
- r/gaming
- r/pcgaming
- r/entrepreneur
- r/careerguidance
- r/productivity
- r/antiwork
- r/jobs
- r/smallbusiness
- r/recruitinghell
- r/workreform
- r/WeAreTheMusicMakers
- r/selfhosted
- r/indiegaming
- r/personalfinance

## 2. Data Fetching

**Topic:** artificial intelligence
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 215.7s

### Subreddits Queried
- r/cscareerquestions
- r/softwaregore
- r/gamedev
- r/talesfromtechsupport
- r/assholedesign
- r/mildlyinfuriating
- r/gaming
- r/pcgaming
- r/entrepreneur
- r/careerguidance
- r/productivity
- r/antiwork
- r/jobs
- r/smallbusiness
- r/recruitinghell
- r/workreform
- r/WeAreTheMusicMakers
- r/selfhosted
- r/indiegaming
- r/personalfinance

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 43.8s
**Throughput:** 2.3 posts/s
**Unique themes:** 94

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 425.3 | 100.0 calls, avg 4.253s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 90
- Non-complaints: 10

### Intensity Distribution
- high: 30
- medium: 51
- low: 19

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Software gore | 3 |
| 2 | Mass layoffs | 2 |
| 3 | No complaint | 2 |
| 4 | Software glitch | 2 |
| 5 | Software error | 2 |
| 6 | No recognition | 1 |
| 7 | Strict language requirements | 1 |
| 8 | Team disorganization | 1 |
| 9 | Grind culture burnout | 1 |
| 10 | Losing coding skills | 1 |
| 11 | Learning difficulty | 1 |
| 12 | Blind AI expectations | 1 |
| 13 | Declining code quality | 1 |
| 14 | Financial pressure | 1 |
| 15 | Career path regret | 1 |
| 16 | Location decision | 1 |
| 17 | No career growth | 1 |
| 18 | Market correction | 1 |
| 19 | Lack connections | 1 |
| 20 | Career path choice | 1 |

## 4. Clustering EDA

**Original themes:** 85
**Canonical themes:** 85
**Deduplication ratio:** 1.000
**Final clusters:** 15
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 129.9s
**Total posts in clusters:** 90
**Total upvotes in clusters:** 27,430

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 93.6 | 72.0% |
| Theme Expansion Llm | 93.5 | 72.0% |
| Embedding Generation | 7.7 | 5.9% |
| Kmeans Clustering | 0.8 | 0.6% |
| Cluster Naming | 27.6 | 21.3% |

### Cluster Size Stats
- Min posts: 1
- Max posts: 14
- Mean posts: 6.0

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 2 | Unfair Hiring Process Complaints | 5 | 5 | 13,004 | 2600.8 |
| 4 | Product Glitches and Annoyances | 10 | 10 | 6,136 | 613.6 |
| 14 | Android TV Storage Issues | 3 | 3 | 2,468 | 822.7 |
| 3 | Job Instability and Stress | 7 | 8 | 1,993 | 249.1 |
| 1 | Software and Hardware Glitches | 10 | 14 | 1,391 | 99.4 |
| 0 | Operational & Growth Obstacles | 11 | 11 | 1,218 | 110.7 |
| 12 | UI Display Glitches | 5 | 5 | 385 | 77.0 |
| 9 | System Component Malfunctions | 4 | 4 | 210 | 52.5 |
| 10 | Unsustainable Workload and AI Misuse | 9 | 9 | 196 | 21.8 |
| 7 | Tech Career Struggle & Burnout | 6 | 6 | 146 | 24.3 |
| 8 | Hiring and Vendor Challenges | 3 | 3 | 80 | 26.7 |
| 11 | Unclear Design and Information | 4 | 4 | 77 | 19.2 |
| 5 | Inaccurate Time Estimates | 3 | 3 | 62 | 20.7 |
| 6 | Translation Tool Limitations | 4 | 4 | 50 | 12.5 |
| 13 | Garbled User Name | 1 | 1 | 14 | 14.0 |

### Theme Breakdown by Cluster

**Unfair Hiring Process Complaints** (5 posts, 13,004 upvotes)
  - camera double standard
  - candidate quality
  - experienced, no interviews
  - hate ai interviews
  - mandatory drugs

**Product Glitches and Annoyances** (10 posts, 6,136 upvotes)
  - bad autocorrect
  - broken title
  - corrupted text
  - excessive verification
  - exclamation mark spam
  - hidden cancel button
  - irrelevant content
  - meta ai button
  - missing content
  - subreddit rules

**Android TV Storage Issues** (3 posts, 2,468 upvotes)
  - android tv broken
  - huge system storage
  - impossible storage

**Job Instability and Stress** (8 posts, 1,993 upvotes)
  - career path regret
  - fear of termination
  - financial pressure
  - laid off, worried
  - mass layoffs
  - salary negotiation anxiety
  - wfh stress

**Software and Hardware Glitches** (14 posts, 1,391 upvotes)
  - billboard error
  - blank screen
  - camera glitch
  - fish in game
  - garbled text
  - os wake glitch
  - phone glitch
  - software error
  - software glitch
  - software gore

**Operational & Growth Obstacles** (11 posts, 1,218 upvotes)
  - difficult to understand
  - learning difficulty
  - location decision
  - no access
  - no career growth
  - no preferences
  - no recognition
  - no score loss
  - slow dev work
  - team disorganization
  - unfair sole responsibility

**UI Display Glitches** (5 posts, 385 upvotes)
  - duplication bug
  - icon transparency bug
  - screen cropped itself
  - ui cloned
  - ui too big

**System Component Malfunctions** (4 posts, 210 upvotes)
  - corrupted clock options
  - equalizer failure
  - fastboot blocked
  - ram speed error

**Unsustainable Workload and AI Misuse** (9 posts, 196 upvotes)
  - blind ai expectations
  - declining code quality
  - excessive multitasking
  - excessive work hours
  - losing coding skills
  - management misuses ai
  - marketing hype
  - outdated codebase
  - work-induced insomnia

**Tech Career Struggle & Burnout** (6 posts, 146 upvotes)
  - developer incompetence
  - grind culture burnout
  - junior job scarcity
  - lack connections
  - major choice difficulty
  - prep uncertainty

**Hiring and Vendor Challenges** (3 posts, 80 upvotes)
  - leaving tech
  - ml background filters
  - vendor management burden

**Unclear Design and Information** (4 posts, 77 upvotes)
  - confusing menu
  - dangerous instructions
  - poor web design
  - uninformative labels

**Inaccurate Time Estimates** (3 posts, 62 upvotes)
  - software inaccuracy
  - time squished
  - wrong travel time

**Translation Tool Limitations** (4 posts, 50 upvotes)
  - outdated ides
  - strict language requirements
  - translation not fixed
  - translator broken

**Garbled User Name** (1 posts, 14 upvotes)
  - garbled name

## 5. Hypothesis Summary
