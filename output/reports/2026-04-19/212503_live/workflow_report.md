# Workflow Report
_Generated: 2026-04-19T21:32:12.583477+00:00_

## 1. Subreddit Selection

**Topic:** health
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> The selected subreddits cover a wide range of health-related complaints, including specific mental health conditions (ADHD, depression, anxiety, socialanxiety), general emotional outlets for health struggles (offmychest, trueoffmychest), financial burdens of healthcare (povertyfinance, personalfinance, debtfree), parental and child health issues (mommit, parenting, daddit, beyondthebump), systemic complaints impacting health (workreform, antiwork, fuckcars), specific physical health concerns (30PlusSkinCare), and broader life challenges with health implications (lonely, relationship_advice, adulting).

### Selected Subreddits
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/offmychest
- r/trueoffmychest
- r/povertyfinance
- r/personalfinance
- r/mommit
- r/parenting
- r/daddit
- r/beyondthebump
- r/debtfree
- r/workreform
- r/30PlusSkinCare
- r/fuckcars
- r/lonely
- r/antiwork
- r/relationship_advice
- r/adulting

## 2. Data Fetching

**Topic:** health
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 138.3s

### Subreddits Queried
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/offmychest
- r/trueoffmychest
- r/povertyfinance
- r/personalfinance
- r/mommit
- r/parenting
- r/daddit
- r/beyondthebump
- r/debtfree
- r/workreform
- r/30PlusSkinCare
- r/fuckcars
- r/lonely
- r/antiwork
- r/relationship_advice
- r/adulting

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 47.7s
**Throughput:** 2.1 posts/s
**Unique themes:** 92

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 440.4 | 100.0 calls, avg 4.404s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 95
- Non-complaints: 5

### Intensity Distribution
- high: 77
- medium: 18
- low: 5

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Feeling stuck | 4 |
| 2 | Medication ineffective | 2 |
| 3 | No complaint | 2 |
| 4 | Hate everything | 2 |
| 5 | Medication side effects | 2 |
| 6 | Profound despair | 2 |
| 7 | Casual drinking confusion | 1 |
| 8 | Expected more | 1 |
| 9 | Perceived as annoying | 1 |
| 10 | Parents deny ADHD | 1 |
| 11 | Preventing dysregulation | 1 |
| 12 | Caffeine overstimulation | 1 |
| 13 | Showering is chore | 1 |
| 14 | Lack of focus | 1 |
| 15 | ADHD social struggles | 1 |
| 16 | Severe side effects | 1 |
| 17 | Forgetting stored food | 1 |
| 18 | Maladaptive daydreaming struggle | 1 |
| 19 | Vyvanse side effects | 1 |
| 20 | ADHD learning struggles | 1 |

## 4. Clustering EDA

**Original themes:** 88
**Canonical themes:** 88
**Deduplication ratio:** 1.000
**Final clusters:** 11
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 144.8s
**Total posts in clusters:** 95
**Total upvotes in clusters:** 6,041

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 88.0 | 60.7% |
| Theme Expansion Llm | 87.9 | 60.7% |
| Embedding Generation | 22.3 | 15.4% |
| Kmeans Clustering | 1.1 | 0.8% |
| Cluster Naming | 33.2 | 22.9% |

### Cluster Size Stats
- Min posts: 1
- Max posts: 38
- Mean posts: 8.6

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 9 | Poor Public Transport Service | 1 | 1 | 3,384 | 3384.0 |
| 0 | Struggling with Self-Care | 3 | 3 | 890 | 296.7 |
| 2 | Profound Despair and Suffering | 33 | 38 | 645 | 17.0 |
| 6 | Treatment and Life Struggles | 9 | 11 | 515 | 46.8 |
| 1 | ADHD Social and Identity Struggles | 11 | 11 | 206 | 18.7 |
| 4 | Internal Mental and Emotional Struggles | 9 | 9 | 166 | 18.4 |
| 5 | Vyvanse Duration and Side | 6 | 6 | 147 | 24.5 |
| 3 | Overwhelming Mental and Existential Distress | 8 | 8 | 51 | 6.4 |
| 7 | Mental State Dysregulation | 3 | 3 | 16 | 5.3 |
| 8 | Items Lost or Forgotten | 3 | 3 | 16 | 5.3 |
| 10 | Biting Compulsion Diagnosis | 2 | 2 | 5 | 2.5 |

### Theme Breakdown by Cluster

**Poor Public Transport Service** (1 posts, 3,384 upvotes)
  - poor public transport

**Struggling with Self-Care** (3 posts, 890 upvotes)
  - body disgust
  - life is unfair
  - showering is chore

**Profound Despair and Suffering** (38 posts, 645 upvotes)
  - addiction and depression
  - anger, injustice
  - college burnout
  - constant sadness
  - denied peace
  - extreme hopelessness
  - extreme suffering
  - feeling hopeless
  - feeling stuck
  - feeling unlovable
  - gambling ruined life
  - gay loneliness
  - hate everything
  - lack understanding
  - life is meaningless
  - life is unbearable
  - life is worthless
  - mental health struggle
  - no hope
  - no hope left
  - no life progress
  - no one cares
  - overwhelming suffering
  - parents don't care
  - personal inadequacy
  - pointless suffering
  - poor memory, apathy
  - profound despair
  - seasonal depression
  - self-hate wins
  - suicidal, alone
  - treatment failure
  - unprotected childhood

**Treatment and Life Struggles** (11 posts, 515 upvotes)
  - career mismatch
  - judgmental assumptions
  - lack of anger
  - medication ineffective
  - medication side effects
  - missing medication
  - shifting depression
  - support effectiveness unknown
  - undesired manufacturer change

**ADHD Social and Identity Struggles** (11 posts, 206 upvotes)
  - adhd learning struggles
  - adhd social struggles
  - adhd struggle
  - disclosure fear
  - harder to connect
  - identity crisis
  - maladaptive daydreaming struggle
  - one-sided friendships
  - parents deny adhd
  - perceived as annoying
  - questioning adhd narrative

**Internal Mental and Emotional Struggles** (9 posts, 166 upvotes)
  - casual drinking confusion
  - constant mental noise
  - extreme nostalgia
  - feeling misunderstood
  - game addiction
  - not recognizing people
  - passive ideations
  - profound loneliness
  - understimulation

**Vyvanse Duration and Side** (6 posts, 147 upvotes)
  - evening crash
  - expected more
  - intense side effects
  - severe side effects
  - short vyvanse duration
  - vyvanse side effects

**Overwhelming Mental and Existential Distress** (8 posts, 51 upvotes)
  - all or nothing
  - cognitive decline
  - email overwhelm
  - everything is overwhelming
  - fear of dying
  - life is scary
  - preventing dysregulation
  - suicidal urgency

**Mental State Dysregulation** (3 posts, 16 upvotes)
  - caffeine overstimulation
  - meditation uncertainty
  - unwanted hyperfocus

**Items Lost or Forgotten** (3 posts, 16 upvotes)
  - forgetting stored food
  - losing socks
  - payment/data removal

**Biting Compulsion Diagnosis** (2 posts, 5 upvotes)
  - biting compulsion
  - seeking diagnosis

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 58.6 |
| Parse + validation | 0.0 |
| **Total** | **58.6** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 MomentumMinder: Self-Care Spark
**Pain point:** Difficulty initiating and completing basic self-care tasks like showering due to mental health struggles, leading to feelings of disgust and unfairness.
**Target user:** Individuals struggling with depression, ADHD, or chronic fatigue who find basic self-care overwhelming.
**Confidence:** high
**Core features:** micro-task breakdown, customizable routines, streak tracking, gentle reminder system, 'quick win' button for immediate small accomplishment
**Revenue model:** Freemium: Basic routines and tracking are free. Premium ($4.99/month or $49.99/year) offers advanced customization, unlimited routine creation, integration with calendar/wearables, and access to a library of guided self-care meditations/audio prompts.
**Evidence:** 3 posts, 890 upvotes

### #2 MedInsight Pro
**Pain point:** Users experience severe and unexpected side effects from ADHD/depression medication, struggle with inconsistent efficacy, and find it difficult to communicate these nuanced experiences effectively to their doctors.
**Target user:** Individuals with ADHD or depression on medication who are experiencing side effects or inconsistent treatment efficacy, and their healthcare providers.
**Confidence:** high
**Core features:** medication schedule and reminder, customizable symptom/side effect tracker, mood/energy logging with time stamps, graphical progress reports for doctors, secure data export
**Revenue model:** Subscription-based: $7.99/month or $79.99/year. Includes unlimited medication tracking, advanced reporting, and secure cloud backup. B2B partnerships with clinics for integrated patient monitoring.
**Evidence:** 6 posts, 147 upvotes

### #3 SafeHarbor Connect
**Pain point:** Individuals experiencing profound despair, suicidal ideation, or intense loneliness feel they have no one to talk to and struggle to find immediate, anonymous support.
**Target user:** Individuals experiencing acute mental health distress, loneliness, suicidal ideation, or profound despair who need immediate, anonymous support.
**Confidence:** high
**Core features:** anonymous text chat with trained peer supporters, one-tap access to national crisis hotlines, safety plan builder, resource directory for mental health services, volunteer training module
**Revenue model:** Non-profit model, funded by grants, donations, and partnerships with mental health organizations. (Direct user monetization for crisis support is ethically complex; a B2B model selling the tech to existing crisis lines could be a for-profit alternative).
**Evidence:** 38 posts, 645 upvotes

### #4 ADHD Connect & Grow
**Pain point:** Adults with ADHD struggle with social connections, feeling misunderstood, and finding effective learning strategies, leading to isolation and frustration.
**Target user:** Adults (18+) diagnosed with ADHD seeking community, practical strategies, and understanding for social and learning challenges.
**Confidence:** medium
**Core features:** small group matching, scheduled video/text group sessions, guided discussion prompts, resource library (e.g., learning techniques, social scripts), progress tracking for skill development
**Revenue model:** Subscription-based: $19.99/month for access to 2 facilitated groups per month and all resources. Higher tiers for more groups or 1:1 peer coaching. B2B partnerships with employers for employee support programs.
**Evidence:** 11 posts, 206 upvotes

### #5 MindFlow Navigator
**Pain point:** Individuals are overwhelmed by constant mental noise, struggle with focus, and experience dysregulation due to over or understimulation, leading to anxiety and difficulty functioning.
**Target user:** Individuals with ADHD, anxiety, or general mental overwhelm who struggle with emotional and cognitive regulation and managing constant mental noise.
**Confidence:** medium
**Core features:** mood/state check-in, personalized audio/visual regulation exercises, 'Focus Mode' with timed prompts, 'Brain Dump' journaling, progress tracking for regulation skills
**Revenue model:** Freemium: Basic check-ins and a limited set of exercises are free. Premium ($9.99/month or $99.99/year) unlocks an extensive library of exercises, advanced personalization based on usage patterns, and integration with mindfulness trackers.
**Evidence:** 9 posts, 166 upvotes

### Analysis Summary
The Reddit complaints reveal a significant and pervasive struggle with mental health, particularly among individuals with ADHD and depression. Key themes include profound despair and suicidal ideation, challenges with basic self-care, difficulties managing medication side effects, and struggles with social connection and emotional regulation. The data strongly indicates a need for accessible, practical tools and supportive communities to address these daily and acute mental health challenges.

### Data Limitations
This dataset provides a snapshot of self-reported frustrations on Reddit, which may not be representative of the broader population or capture the full spectrum of health-related issues. The severity of some complaints (e.g., suicidal ideation) requires careful consideration, and solutions must be designed with appropriate safety and ethical guidelines. Additionally, the data is limited to English-speaking users on specific subreddits, potentially missing cultural or demographic nuances.
