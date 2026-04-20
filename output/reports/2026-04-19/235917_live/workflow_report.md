# Workflow Report
_Generated: 2026-04-20T00:06:06.212308+00:00_

## 1. Subreddit Selection

**Topic:** health
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> The selected subreddits cover direct health conditions (ADHD, depression, anxiety, socialanxiety, 30PlusSkinCare), broader healthcare system complaints (workreform, personalfinance, povertyfinance, debtfree), and the significant impact of health on personal lives and relationships (parenting, mommit, daddit, offmychest, trueoffmychest, beyondthebump, deadbedrooms, lonely, relationships, relationship_advice, dating). These communities are likely places where individuals vent about health-related struggles, costs, access, or how health affects their daily lives and interactions.

### Selected Subreddits
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/workreform
- r/30PlusSkinCare
- r/parenting
- r/mommit
- r/daddit
- r/povertyfinance
- r/debtfree
- r/offmychest
- r/trueoffmychest
- r/beyondthebump
- r/deadbedrooms
- r/lonely
- r/personalfinance
- r/relationships
- r/relationship_advice
- r/dating

## 2. Data Fetching

**Topic:** health
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 134.3s

### Subreddits Queried
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/workreform
- r/30PlusSkinCare
- r/parenting
- r/mommit
- r/daddit
- r/povertyfinance
- r/debtfree
- r/offmychest
- r/trueoffmychest
- r/beyondthebump
- r/deadbedrooms
- r/lonely
- r/personalfinance
- r/relationships
- r/relationship_advice
- r/dating

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 47.3s
**Throughput:** 2.1 posts/s
**Unique themes:** 99

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 443.7 | 100.0 calls, avg 4.437s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 95
- Non-complaints: 5

### Intensity Distribution
- high: 83
- medium: 13
- low: 4

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Constant sadness | 2 |
| 2 | Stop doom scrolling | 1 |
| 3 | Feeling stuck | 1 |
| 4 | ADHD work paralysis | 1 |
| 5 | Medication misunderstanding | 1 |
| 6 | Perceived annoyingness | 1 |
| 7 | Parents deny ADHD | 1 |
| 8 | Not life-changing | 1 |
| 9 | Short Vyvanse duration | 1 |
| 10 | Difficulty regulating | 1 |
| 11 | Meds not working | 1 |
| 12 | Shower monotony | 1 |
| 13 | Improved focus tips | 1 |
| 14 | Socializing feels bad | 1 |
| 15 | Parents deny meds | 1 |
| 16 | Losing track food | 1 |
| 17 | Guilt over introversion | 1 |
| 18 | Behavior uncertainty | 1 |
| 19 | Costly mistakes | 1 |
| 20 | Medication side effects | 1 |

## 4. Clustering EDA

**Original themes:** 94
**Canonical themes:** 94
**Deduplication ratio:** 1.000
**Final clusters:** 8
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 133.6s
**Total posts in clusters:** 95
**Total upvotes in clusters:** 3,672

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 99.8 | 74.8% |
| Theme Expansion Llm | 99.8 | 74.7% |
| Embedding Generation | 16.1 | 12.1% |
| Kmeans Clustering | 0.9 | 0.7% |
| Cluster Naming | 16.4 | 12.3% |

### Cluster Size Stats
- Min posts: 4
- Max posts: 28
- Mean posts: 11.9

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 4 | Profound Mental & Emotional Distress | 17 | 17 | 1,051 | 61.8 |
| 1 | Daily Life & Mental Struggles | 10 | 10 | 759 | 75.9 |
| 5 | Profound Despair and Suffering | 27 | 28 | 701 | 25.0 |
| 0 | Profound Loneliness and In | 11 | 11 | 566 | 51.5 |
| 2 | ADHD Diagnosis and Treatment Struggles | 11 | 11 | 330 | 30.0 |
| 7 | Medication and Emotional Struggles | 6 | 6 | 141 | 23.5 |
| 3 | Medication Side Effects & Issues | 8 | 8 | 110 | 13.8 |
| 6 | Workplace Insecurity and Doubt | 4 | 4 | 14 | 3.5 |

### Theme Breakdown by Cluster

**Profound Mental & Emotional Distress** (17 posts, 1,051 upvotes)
  - adhd struggle
  - always tired
  - can't recognize people
  - depression ruining relationship
  - difficulty regulating
  - email overwhelm
  - extreme nostalgia
  - feeling depressed
  - feeling lost
  - feeling neglected
  - feeling stuck
  - hate winter
  - no appetite
  - stop doom scrolling
  - suicidal ideation
  - suicidal, alone
  - unjust world

**Daily Life & Mental Struggles** (10 posts, 759 upvotes)
  - all or nothing
  - behavior uncertainty
  - constant mental noise
  - distracting thoughts
  - friendship difficulty
  - losing socks
  - perceived annoyingness
  - self-neglect
  - shower monotony
  - socializing feels bad

**Profound Despair and Suffering** (28 posts, 701 upvotes)
  - body disgust
  - can't escape suffering
  - constant sadness
  - extreme despair
  - failing at life
  - fear of life
  - feeling hopeless
  - hate everything
  - just existing
  - life is waste
  - life sucks
  - life wasted
  - lost to self-hate
  - memory, no interest
  - no hope
  - no support/love
  - no will to live
  - personal failure
  - profound despair
  - profound mental suffering
  - self-deprecating thoughts
  - suicidal thoughts
  - trapped, no escape
  - unbearable life
  - unbearable suffering
  - unjust suffering
  - want to die

**Profound Loneliness and In** (11 posts, 566 upvotes)
  - agony prolonged
  - family invalidation
  - feeling different
  - gay loneliness
  - invalidating sentiment
  - loneliness
  - mother's interference
  - no understanding
  - parents don't care
  - persistent emptiness
  - severe boredom

**ADHD Diagnosis and Treatment Struggles** (11 posts, 330 upvotes)
  - adhd narrative confusion
  - adhd work paralysis
  - learning methods ineffective
  - medication misunderstanding
  - meditation confusion
  - meds not working
  - not life-changing
  - parents deny adhd
  - parents deny meds
  - psychiatrist's dismissal
  - undiagnosed adhd

**Medication and Emotional Struggles** (6 posts, 141 upvotes)
  - evening crash
  - guilt over introversion
  - mirtazapine depression
  - new medication anxiety
  - shorted pills
  - weird lack of anger

**Medication Side Effects & Issues** (8 posts, 110 upvotes)
  - activities unrewarding
  - increased spending
  - intense side effects
  - losing track food
  - medication side effects
  - short vyvanse duration
  - unwanted hyperactivity
  - zyprexa side effects

**Workplace Insecurity and Doubt** (4 posts, 14 upvotes)
  - costly mistakes
  - fear job loss
  - job mismatch
  - questioning intelligence

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 53.5 |
| Parse + validation | 0.0 |
| **Total** | **53.5** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 Momentum Builder
**Pain point:** Individuals with ADHD and depression struggle with basic self-care, social interaction, and overcoming an 'all or nothing' mentality, leading to self-neglect and difficulty initiating tasks.
**Target user:** Individuals with ADHD, depression, or executive dysfunction who struggle with initiating and maintaining daily self-care routines and feel overwhelmed by tasks.
**Confidence:** high
**Core features:** micro-task breakdown, streak & progress visualizer, mood & energy check-ins, optional accountability buddies/groups
**Revenue model:** Freemium: Free for basic habit tracking (up to 3 habits, no groups). Premium subscription at $7.99/month or $69.99/year for unlimited habits, advanced analytics, accountability buddy matching, and access to curated support groups.
**Evidence:** 10 posts, 759 upvotes

### #2 FocusFlow
**Pain point:** Individuals, particularly those with ADHD, struggle with 'doom scrolling' and getting 'stuck in waiting mode,' leading to significant procrastination, digital overwhelm, and difficulty initiating productive tasks.
**Target user:** Individuals with ADHD, anxiety, or general executive dysfunction who struggle with digital distractions, procrastination, and feeling overwhelmed by digital tasks.
**Confidence:** high
**Core features:** doom scroll detector & interrupter, 'waiting mode' prompt, email inbox triage assistant, focus timer & task launcher
**Revenue model:** Freemium: Free browser extension with basic blocking and 3 custom prompts. Premium subscription at $9.99/month or $89.99/year for desktop app sync, unlimited custom prompts, advanced analytics on procrastination patterns, and integration with popular task managers.
**Evidence:** 17 posts, 1,051 upvotes

### #3 MyMedJourney
**Pain point:** Individuals with ADHD experience confusion and unmet expectations with medication, feeling like 'meds aren't working,' and face challenges in communicating their needs and experiences effectively to parents or psychiatrists.
**Target user:** Newly diagnosed ADHD individuals, those adjusting medication, or anyone struggling to understand and communicate their medication experience to healthcare providers or family.
**Confidence:** high
**Core features:** guided medication onboarding, symptom & side effect logger, medication effectiveness charting, doctor discussion guide generator
**Revenue model:** Subscription-based: $12.99/month or $119.99/year. Includes all features, unlimited data storage, and access to a curated library of expert-reviewed articles and FAQs.
**Evidence:** 11 posts, 330 upvotes

### #4 Empathy Circles
**Pain point:** Individuals experience profound loneliness, feeling misunderstood, and invalidated by family or society, especially when dealing with mental health issues or identity-specific struggles, leading to feelings of hopelessness and isolation.
**Target user:** Individuals experiencing profound loneliness, social isolation, family invalidation, or those seeking understanding and connection around specific mental health or identity challenges.
**Confidence:** high
**Core features:** curated support circles, guided discussion prompts, anonymous sharing & moderation, resource library
**Revenue model:** Subscription-based: $9.99/month or $99.99/year for access to unlimited circles, premium resources, and optional facilitated group sessions with trained peer mentors.
**Evidence:** 11 posts, 566 upvotes

### #5 SideEffect Sentinel
**Pain point:** Individuals taking mental health medications experience intense and unexpected side effects (e.g., rage, depression, short duration) and struggle with practical daily tasks like food management due to medication impact.
**Target user:** Individuals taking medications for ADHD, depression, or other mental health conditions who are experiencing side effects or struggling with medication-related daily challenges.
**Confidence:** medium
**Core features:** medication schedule & reminders, detailed side effect & mood logger, pattern analysis & doctor reports, proactive daily nudges
**Revenue model:** Subscription-based: $8.99/month or $79.99/year. Includes unlimited medication tracking, advanced analytics, custom reminder profiles, and secure data export for medical appointments.
**Evidence:** 8 posts, 110 upvotes

### Analysis Summary
The Reddit complaints reveal a pervasive and intense struggle with mental health, particularly ADHD and depression, manifesting as executive dysfunction, profound loneliness, digital overwhelm, and significant challenges in medication management. Users express deep frustration with self-care, focus, social connection, and the efficacy or side effects of their treatments, often feeling misunderstood or unsupported.

### Data Limitations
The dataset primarily reflects experiences within ADHD and depression communities on Reddit, potentially overrepresenting these specific mental health conditions. While upvotes and post counts indicate signal strength, they don't necessarily represent the full scope or prevalence of these issues across the general population. The data is self-reported and lacks clinical verification.
