# Workflow Report
_Generated: 2026-04-18T22:02:44.096264+00:00_

## 1. Subreddit Selection

**Topic:** health
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> The selected subreddits cover direct health conditions (ADHD, depression, anxiety, socialanxiety, 30PlusSkinCare), health-related issues impacting personal life (deadbedrooms, lonely), financial complaints stemming from health costs (povertyfinance, personalfinance, debtfree), systemic complaints about healthcare (workreform, fuckcars), and general support communities where health struggles are frequently discussed (offmychest, trueoffmychest, parenting, mommit, beyondthebump, relationship_advice, relationships, adulting).

### Selected Subreddits
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/30PlusSkinCare
- r/deadbedrooms
- r/workreform
- r/povertyfinance
- r/personalfinance
- r/debtfree
- r/offmychest
- r/trueoffmychest
- r/parenting
- r/mommit
- r/beyondthebump
- r/fuckcars
- r/lonely
- r/relationship_advice
- r/relationships
- r/adulting

## 2. Data Fetching

**Topic:** health
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 108.3s

### Subreddits Queried
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/30PlusSkinCare
- r/deadbedrooms
- r/workreform
- r/povertyfinance
- r/personalfinance
- r/debtfree
- r/offmychest
- r/trueoffmychest
- r/parenting
- r/mommit
- r/beyondthebump
- r/fuckcars
- r/lonely
- r/relationship_advice
- r/relationships
- r/adulting

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 40.4s
**Throughput:** 2.5 posts/s
**Unique themes:** 97

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 384.8 | 100.0 calls, avg 3.848s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 97
- Non-complaints: 3

### Intensity Distribution
- high: 72
- medium: 23
- low: 5

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | No complaint | 3 |
| 2 | Suicidal thoughts | 2 |
| 3 | Shower chore | 1 |
| 4 | Change judgment | 1 |
| 5 | Anger aftermath | 1 |
| 6 | Mood/energy shifts | 1 |
| 7 | Parents deny ADHD | 1 |
| 8 | Crowd shutdown | 1 |
| 9 | ADHD narrative confusion | 1 |
| 10 | Mindless scrolling | 1 |
| 11 | Intense rejection pain | 1 |
| 12 | Need breakfast ideas | 1 |
| 13 | Forgetting vitamins | 1 |
| 14 | Can't focus | 1 |
| 15 | Doctor changing meds | 1 |
| 16 | Loss of control | 1 |
| 17 | Misdirected focus | 1 |
| 18 | Normal isn't stimulating | 1 |
| 19 | Time doesn't change | 1 |
| 20 | Struggle under pressure | 1 |

## 4. Clustering EDA

**Original themes:** 96
**Canonical themes:** 96
**Deduplication ratio:** 1.000
**Final clusters:** 12
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 123.9s
**Total posts in clusters:** 97
**Total upvotes in clusters:** 2,994

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 87.6 | 70.7% |
| Theme Expansion Llm | 87.6 | 70.7% |
| Embedding Generation | 9.0 | 7.3% |
| Kmeans Clustering | 0.8 | 0.7% |
| Cluster Naming | 26.2 | 21.2% |

### Cluster Size Stats
- Min posts: 2
- Max posts: 32
- Mean posts: 8.1

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 1 | Profound Despair and Suicidal Thoughts | 31 | 32 | 697 | 21.8 |
| 9 | Neurodivergent Daily Life Challenges | 9 | 9 | 496 | 55.1 |
| 7 | Unstable Condition Management | 4 | 4 | 387 | 96.8 |
| 10 | Medication Access and Jaw Issues | 3 | 3 | 330 | 110.0 |
| 3 | Medication Anxiety and Focus | 9 | 9 | 324 | 36.0 |
| 2 | Personal Ineffectiveness and Struggle | 7 | 7 | 220 | 31.4 |
| 4 | Severe Mental Health Struggle | 13 | 13 | 162 | 12.5 |
| 8 | Sleep and mental distress | 5 | 5 | 143 | 28.6 |
| 5 | Lack of specific, useful content | 3 | 3 | 108 | 36.0 |
| 6 | ADHD life struggles | 5 | 5 | 66 | 13.2 |
| 11 | Emotional and physical drain | 5 | 5 | 57 | 11.4 |
| 0 | Activity Engagement Challenges | 2 | 2 | 4 | 2.0 |

### Theme Breakdown by Cluster

**Profound Despair and Suicidal Thoughts** (32 posts, 697 upvotes)
  - death anxiety
  - debilitating depression
  - depression hopelessness
  - done with life
  - extreme suffering
  - financial ruin
  - future path struggle
  - inevitable suicide
  - lack of support
  - life is hell
  - life is unbearable
  - life is unfair
  - life ruined me
  - life unfulfilling
  - life's too hard
  - lifelong suffering
  - lost realness
  - loved ones' pain
  - meaningless existence
  - no friends
  - past actions' impact
  - profound despair
  - self-loathing
  - self-perceived curse
  - severe depression
  - suicidal ideation
  - suicidal thoughts
  - time doesn't change
  - tired of life
  - unbearable suffering
  - unfulfilled life

**Neurodivergent Daily Life Challenges** (9 posts, 496 upvotes)
  - adhd narrative confusion
  - brain works differently
  - can't recognize faces
  - focus difficulty
  - meds worsen autism
  - normal isn't stimulating
  - out of place
  - sexual dysfunction
  - shower chore

**Unstable Condition Management** (4 posts, 387 upvotes)
  - medication wears off
  - mood/energy shifts
  - relapse urges
  - unclear diagnosis

**Medication Access and Jaw Issues** (3 posts, 330 upvotes)
  - medication access issues
  - no medication access
  - recessed jaw

**Medication Anxiety and Focus** (9 posts, 324 upvotes)
  - doctor changing meds
  - drug cocktail fear
  - forgetting vitamins
  - medication nervousness
  - meds heighten fear
  - misdirected focus
  - poor focus
  - stimulant anxiety
  - withdrawal concern

**Personal Ineffectiveness and Struggle** (7 posts, 220 upvotes)
  - ai makes useless
  - can't focus
  - change judgment
  - execution difficulty
  - inability to study
  - life never works
  - struggle under pressure

**Severe Mental Health Struggle** (13 posts, 162 upvotes)
  - anger aftermath
  - depression cycle
  - depression relapse
  - depression's severe impact
  - drowning in thoughts
  - explain mental health
  - hopeless struggle
  - loss of control
  - mental health struggle
  - mental state confusion
  - severe mental distress
  - unhealthy hyper-fixation
  - worsening mental health

**Sleep and mental distress** (5 posts, 143 upvotes)
  - can't nap
  - hlf posts demoralize
  - mental fogginess
  - mind won't shut
  - sleepless, unmedicated

**Lack of specific, useful content** (3 posts, 108 upvotes)
  - common advice limited
  - mindless scrolling
  - need breakfast ideas

**ADHD life struggles** (5 posts, 66 upvotes)
  - adhd career discrimination
  - adhd work struggle
  - intense rejection pain
  - no booster access
  - parents deny adhd

**Emotional and physical drain** (5 posts, 57 upvotes)
  - chronic pain impact
  - crowd shutdown
  - lack of dopamine
  - lack of joy
  - lack of motivation

**Activity Engagement Challenges** (2 posts, 4 upvotes)
  - hobby inconsistency
  - reading difficulty

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 61.9 |
| Parse + validation | 0.0 |
| **Total** | **61.9** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 Crisis & Support Navigator
**Pain point:** Profound despair, suicidal ideation, and feeling life is unbearable due to a perceived lack of support and understanding.
**Target user:** Individuals experiencing severe mental health distress, including depression, anxiety, and suicidal ideation, who are seeking structured support and actionable crisis management tools.
**Confidence:** high
**Core features:** Personalized Crisis Plan Builder, Vetted Peer Support Matching, Resource Directory, Mood & Trigger Journal, Safety Check-ins
**Revenue model:** Freemium: Basic crisis plan and resource directory are free. Premium subscription ($9.99/month or $99/year) for access to vetted, moderated peer support groups, advanced journaling features, and safety check-in customization.
**Evidence:** 32 posts, 697 upvotes

### #2 Meds & Me
**Pain point:** Anxiety and confusion surrounding medication management, including dosage changes, side effects, interactions, and concerns about withdrawal or effectiveness.
**Target user:** Individuals managing chronic mental health conditions (e.g., ADHD, depression, anxiety) who are on multiple medications or frequently adjust their treatment plans.
**Confidence:** high
**Core features:** Smart Medication Reminders, Side Effect & Mood Tracker, Medication Interaction Checker, Withdrawal & Adjustment Guides, Doctor Discussion Prep
**Revenue model:** Subscription-based: $5.99/month or $59.99/year. Free 7-day trial.
**Evidence:** 9 posts, 324 upvotes

### #3 Executive Edge
**Pain point:** Struggling with executive dysfunction, inability to focus on tasks, difficulty initiating daily activities like showering, and feeling generally ineffective despite effort.
**Target user:** Adults and young adults with ADHD or other neurodivergent conditions who struggle with executive dysfunction, task initiation, and maintaining daily habits.
**Confidence:** high
**Core features:** Micro-Task Breakdown, Gamified Progress Tracking, Virtual Body Doubling, Task Initiation Prompts, Sensory-Friendly Interface
**Revenue model:** Subscription-based: $7.99/month or $79.99/year. Free basic task list and 3-day trial of premium features.
**Evidence:** 7 posts, 220 upvotes

### #4 Micro-Habit Hub
**Pain point:** Frustration with generic mental health advice and a desire for specific, actionable, small daily habits and 'life hacks' tailored for ADHD and anxiety management.
**Target user:** Individuals with ADHD, anxiety, or general mental health struggles who are overwhelmed by generic advice and seek practical, bite-sized strategies.
**Confidence:** medium
**Core features:** Curated Micro-Habit Library, Community Contribution & Upvoting, Personalized Habit Builder, 'Why it works' Explanations, Themed Collections
**Revenue model:** Freemium: Basic library and habit tracking are free. Premium ($4.99/month or $49.99/year) for unlimited custom habit creation, advanced analytics, and access to expert-curated 'challenge packs.'
**Evidence:** 3 posts, 108 upvotes

### #5 MedFinder Global
**Pain point:** Significant difficulty and anxiety due to lack of access to prescribed medications, especially in regions with shortages or limited stock.
**Target user:** Individuals relying on specific medications (especially for chronic conditions like ADHD, depression) who frequently face supply chain issues or regional shortages.
**Confidence:** medium
**Core features:** Real-time Stock Checker, Community Reporting, Alternative Pharmacy Directory, Shortage Alerts & Updates, Telehealth/Prescription Transfer Guide
**Revenue model:** Freemium: Basic search and community reporting are free. Premium ($3.99/month or $39.99/year) for real-time push notifications for stock updates, advanced search filters, and priority access to new features. Could also explore partnerships with pharmacies for verified stock data (B2B).
**Evidence:** 3 posts, 330 upvotes

### Analysis Summary
The Reddit complaints reveal significant struggles within mental health, particularly for individuals with ADHD and depression. Key themes include profound despair and suicidal ideation, challenges with medication management (anxiety, side effects, access), and pervasive executive dysfunction impacting daily life and the ability to act on generic advice. There's a strong demand for highly specific, actionable tools and structured support rather than vague solutions.

### Data Limitations
The dataset is limited to Reddit posts, which may not represent the full spectrum of health complaints and skews towards self-reported experiences, particularly within mental health subreddits. The signal strength (upvotes, post count) indicates intensity and breadth within this specific user base but may not generalize to the broader population. Some clusters contain posts that are not directly health-related, requiring careful filtering.
