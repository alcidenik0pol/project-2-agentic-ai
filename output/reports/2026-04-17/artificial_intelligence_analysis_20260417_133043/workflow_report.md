# Workflow Report
_Generated: 2026-04-17T13:39:04.114996+00:00_

## 1. Subreddit Selection

**Topic:** artificial intelligence
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> Artificial intelligence can generate complaints across various domains. Subreddits like cscareerquestions, antiwork, workreform, recruitinghell, careerguidance, and jobs are highly relevant for complaints about AI's impact on employment, careers, and the workforce. Softwaregore and assholedesign are relevant for complaints about AI software malfunctions or poorly designed AI systems. Entrepreneur, smallbusiness, productivity, and selfhosted address issues with AI tools and their business/personal application. Gamedev, gaming, and pcgaming cover complaints about AI in game development and gameplay. Finally, general complaint subreddits like mildlyinfuriating, offmychest, trueoffmychest, anxiety, and depression are suitable for personal frustrations, anxieties, or broader societal concerns related to AI.

### Selected Subreddits
- r/cscareerquestions
- r/softwaregore
- r/antiwork
- r/workreform
- r/recruitinghell
- r/careerguidance
- r/jobs
- r/gamedev
- r/entrepreneur
- r/smallbusiness
- r/productivity
- r/selfhosted
- r/assholedesign
- r/mildlyinfuriating
- r/offmychest
- r/trueoffmychest
- r/anxiety
- r/depression
- r/gaming
- r/pcgaming

## 2. Data Fetching

**Topic:** artificial intelligence
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 185.4s

### Subreddits Queried
- r/cscareerquestions
- r/softwaregore
- r/antiwork
- r/workreform
- r/recruitinghell
- r/careerguidance
- r/jobs
- r/gamedev
- r/entrepreneur
- r/smallbusiness
- r/productivity
- r/selfhosted
- r/assholedesign
- r/mildlyinfuriating
- r/offmychest
- r/trueoffmychest
- r/anxiety
- r/depression
- r/gaming
- r/pcgaming

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-pro
**Processing time:** 48.8s
**Throughput:** 2.0 posts/s
**Unique themes:** 93

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 458.9 | 100.0 calls, avg 4.589s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 93
- Non-complaints: 7

### Intensity Distribution
- high: 30
- medium: 54
- low: 16

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Software error | 6 |
| 2 | Software gore | 2 |
| 3 | Missing content | 2 |
| 4 | Laid off, worried | 1 |
| 5 | Career paths | 1 |
| 6 | Salary uncertainty | 1 |
| 7 | WFH stress | 1 |
| 8 | Job insecurity | 1 |
| 9 | LinkedIn connections | 1 |
| 10 | Cannot understand coworkers | 1 |
| 11 | Hard job market | 1 |
| 12 | Unemployed, no interviews | 1 |
| 13 | Leaving tech | 1 |
| 14 | AI code quality | 1 |
| 15 | AI interview questions | 1 |
| 16 | Devs quitting | 1 |
| 17 | Offer negotiation advice | 1 |
| 18 | Feeling incompetent | 1 |
| 19 | Snap layoffs | 1 |
| 20 | No visa sponsorship | 1 |

## 4. Clustering EDA

**Original themes:** 86
**Canonical themes:** 86
**Deduplication ratio:** 1.000
**Final clusters:** 14
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 148.2s
**Total posts in clusters:** 93
**Total upvotes in clusters:** 33,040

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 111.3 | 75.1% |
| Theme Expansion Llm | 111.3 | 75.1% |
| Embedding Generation | 4.0 | 2.7% |
| Kmeans Clustering | 1.3 | 0.9% |
| Cluster Naming | 31.3 | 21.1% |

### Cluster Size Stats
- Min posts: 1
- Max posts: 23
- Mean posts: 6.6

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 8 | Unjustified demands or requirements | 2 | 2 | 11,546 | 5773.0 |
| 13 | Leadership Betrayal and | 3 | 3 | 10,827 | 3609.0 |
| 7 | Software and App Malfunctions | 17 | 23 | 3,821 | 166.1 |
| 9 | Workplace Instability and Stress | 8 | 8 | 1,907 | 238.4 |
| 5 | Inaccurate Storage Reporting | 3 | 3 | 1,486 | 495.3 |
| 10 | AI Impact on Developer Work | 6 | 6 | 1,137 | 189.5 |
| 1 | Tech Career Dissatisfaction and Stress | 10 | 10 | 707 | 70.7 |
| 6 | App Functionality Issues | 7 | 7 | 590 | 84.3 |
| 0 | Content and Access Problems | 5 | 6 | 537 | 89.5 |
| 2 | Job Search & Market Struggles | 13 | 13 | 184 | 14.2 |
| 3 | Poor or Missing Content | 4 | 4 | 148 | 37.0 |
| 4 | Poor Information and Guidance | 4 | 4 | 74 | 18.5 |
| 11 | Content and Translation Errors | 3 | 3 | 72 | 24.0 |
| 12 | Unwanted spam calls | 1 | 1 | 4 | 4.0 |

### Theme Breakdown by Cluster

**Unjustified demands or requirements** (2 posts, 11,546 upvotes)
  - drug requirement
  - unjustified document request

**Leadership Betrayal and** (3 posts, 10,827 upvotes)
  - feeling behind
  - feeling lost, obsolete
  - leadership betrayal

**Software and App Malfunctions** (23 posts, 3,821 upvotes)
  - app malfunctioning
  - google's odd behavior
  - improper shutdown
  - maintenance failed
  - menu error
  - missing apps
  - os glitching
  - outdated ides
  - ram speed glitch
  - screen distortion
  - software bug
  - software error
  - software glitch
  - software gore
  - software malfunction
  - spotify glitch
  - ui duplication

**Workplace Instability and Stress** (8 posts, 1,907 upvotes)
  - broken trust
  - financial feasibility
  - job insecurity
  - laid off, worried
  - lost coworker trust
  - salary uncertainty
  - snap layoffs
  - wfh stress

**Inaccurate Storage Reporting** (3 posts, 1,486 upvotes)
  - huge system storage
  - impossible disk size
  - negative usage

**AI Impact on Developer Work** (6 posts, 1,137 upvotes)
  - ai cheating
  - ai code quality
  - ai review bottleneck
  - bizarre coding question
  - deep thinking loss
  - forced ai projects

**Tech Career Dissatisfaction and Stress** (10 posts, 707 upvotes)
  - cannot understand coworkers
  - coding burnout
  - devs quitting
  - feeling incompetent
  - job not technical
  - leaving tech
  - manager undermining
  - stuck in java
  - work-induced insomnia
  - work-life balance

**App Functionality Issues** (7 posts, 590 upvotes)
  - glitched recommendations
  - glitched settings
  - incorrect data
  - meta ai button
  - suggestions accessibility
  - worst autocorrect
  - wrong profile pic

**Content and Access Problems** (6 posts, 537 upvotes)
  - broken image
  - broken intro
  - missing content
  - no access
  - slower brainpower

**Job Search & Market Struggles** (13 posts, 184 upvotes)
  - ai interview questions
  - career value uncertainty
  - hard job market
  - job market uncertainty
  - job search difficulty
  - missed insight
  - no interview calls
  - no visa sponsorship
  - role relevance
  - skill mismatch
  - too early applying
  - uncertain tech transition
  - unemployed, no interviews

**Poor or Missing Content** (4 posts, 148 upvotes)
  - empty post
  - no content
  - poor web design
  - useless hint

**Poor Information and Guidance** (4 posts, 74 upvotes)
  - dangerous instructions
  - driver planning unclear
  - incorrect estimate
  - no bus info

**Content and Translation Errors** (3 posts, 72 upvotes)
  - malformed title
  - missing text
  - translator broken

**Unwanted spam calls** (1 posts, 4 upvotes)
  - spam calls

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 82.5 |
| Parse + validation | 0.0 |
| **Total** | **82.5** |
| **Model:** gcloud:gemini-2.5-pro | |

**Total ideas generated:** 5

### #1 CodeReviewGuard
**Pain point:** Management is pushing for more AI-generated code, but the code review process has become a bottleneck and they don't understand the code isn't production-ready.
**Target user:** Senior developers and tech leads at companies that are heavily adopting AI coding assistants like Copilot.
**Confidence:** high
**Core features:** Automated PR comments with risk scores, AI-generated code detection, Security vulnerability scanning, Performance and style guide analysis, Manager-facing quality dashboards
**Revenue model:** SaaS Subscription: Free for public repos and teams up to 3. Pro plan at $29/developer/month for private repos and advanced features. Enterprise plan with custom pricing for on-premise deployment.
**Evidence:** 6 posts, 1,137 upvotes

### #2 LayoffSignal
**Pain point:** Employees are anxious about job security and want to know the warning signs that they might be laid off.
**Target user:** Tech employees who are feeling anxious about job security in a volatile market.
**Confidence:** high
**Core features:** Anonymous signal submission, Company-specific stability score and timeline, Industry benchmark comparisons, Real-time alerts for new signals at your company, Curated feed of public layoff news
**Revenue model:** Freemium: Free to view data for your own company and contribute signals. Premium subscription at $9.99/month to unlock viewing data for any company, set advanced alerts, and access detailed trend reports.
**Evidence:** 8 posts, 1,907 upvotes

### #3 StorageSleuth
**Pain point:** My phone's operating system is reporting an impossibly large amount of storage being used by 'System', and I can't figure out what it is or how to clean it.
**Target user:** Non-technical smartphone users (especially Android) whose phones are running out of space and don't trust the built-in storage manager.
**Confidence:** high
**Core features:** Deep storage analysis beyond OS capabilities, Interactive sunburst chart visualization, Bloatware identification and removal suggestions, Duplicate file finder, One-tap cache cleaner for social media apps
**Revenue model:** Freemium: Free scan and analysis. A one-time in-app purchase of $4.99 unlocks all cleaning features, scheduled scans, and duplicate file deletion.
**Evidence:** 3 posts, 1,486 upvotes

### #4 DevMeetingScribe
**Pain point:** I literally cannot understand my coworkers in meetings, especially with accents and technical jargon.
**Target user:** Software developers on remote or multi-national teams, especially junior developers or those new to a company.
**Confidence:** medium
**Core features:** Real-time transcription, Automated technical jargon identification and definition, Team-specific acronym dictionary, AI-generated summaries of technical decisions, Action item tracking
**Revenue model:** Subscription SaaS: $15/user/month for unlimited transcription and a 30-day history. Team Plan at $12/user/month (min 5 users) with a shared team dictionary for jargon.
**Evidence:** 10 posts, 707 upvotes

### #5 JobFitAI
**Pain point:** The junior job market is terrible, I'm applying to hundreds of jobs and not hearing back, and I don't know what's actually working right now.
**Target user:** Junior developers and recent computer science graduates struggling to get interviews in a competitive job market.
**Confidence:** medium
**Core features:** Resume vs. Job Description side-by-side analysis, AI-powered suggestions for resume edits, Keyword optimization scoring, Real-time market skill trend dashboard, Cover letter generation based on resume and job description
**Revenue model:** Freemium: 3 free analyses per month. Pro subscription at $19/month for unlimited analyses, cover letter generation, and full access to the market skills trend dashboard.
**Evidence:** 13 posts, 184 upvotes

### Analysis Summary
Across the clusters, two dominant patterns emerge: significant career-related anxiety within the tech industry and frustration with the quality and reliability of software. The career anxiety is driven by a tough job market, layoff fears, and the disruptive impact of AI on developer workflows. The software frustrations range from simple UI glitches to fundamental failures in reporting critical information like device storage.

### Data Limitations
This analysis is based on a small, specific snapshot of Reddit posts. The data does not represent all user frustrations and is biased towards what gets upvoted on r/cscareerquestions and r/softwaregore. The upvote counts can be influenced by post timing and title quality, not just the severity of the underlying problem.
