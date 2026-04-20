# Workflow Report
_Generated: 2026-04-19T21:16:34.525507+00:00_

## 1. Subreddit Selection

**Topic:** health
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> Selected subreddits include direct mental and physical health communities, general support/venting forums where health complaints are common, and communities where health issues significantly impact finances, family, or relationships.

### Selected Subreddits
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/offmychest
- r/trueoffmychest
- r/parenting
- r/mommit
- r/daddit
- r/beyondthebump
- r/personalfinance
- r/povertyfinance
- r/debtfree
- r/30PlusSkinCare
- r/workreform
- r/lonely
- r/relationship_advice
- r/relationships
- r/dating
- r/datingoverthirty

## 2. Data Fetching

**Topic:** health
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 112.4s

### Subreddits Queried
- r/ADHD
- r/depression
- r/anxiety
- r/socialanxiety
- r/offmychest
- r/trueoffmychest
- r/parenting
- r/mommit
- r/daddit
- r/beyondthebump
- r/personalfinance
- r/povertyfinance
- r/debtfree
- r/30PlusSkinCare
- r/workreform
- r/lonely
- r/relationship_advice
- r/relationships
- r/dating
- r/datingoverthirty

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 40.4s
**Throughput:** 2.5 posts/s
**Unique themes:** 96

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 370.8 | 100.0 calls, avg 3.708s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 94
- Non-complaints: 6

### Intensity Distribution
- high: 80
- medium: 14
- low: 6

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Feeling stuck | 3 |
| 2 | Suicidal ideation | 2 |
| 3 | Feeling hopeless | 2 |
| 4 | Stuck, can't act | 1 |
| 5 | Expected more | 1 |
| 6 | Casual drinking confusion | 1 |
| 7 | Being annoying | 1 |
| 8 | Parental denial | 1 |
| 9 | Self-regulation struggle | 1 |
| 10 | Shower chore | 1 |
| 11 | Caffeine overstimulation | 1 |
| 12 | Lack of focus | 1 |
| 13 | Forgetting fridge food | 1 |
| 14 | Medication necessity | 1 |
| 15 | Vyvanse side effects | 1 |
| 16 | Socializing feels bad | 1 |
| 17 | Medication failure | 1 |
| 18 | Misunderstanding change | 1 |
| 19 | Lectures ineffective | 1 |
| 20 | Forgetting faces | 1 |

## 4. Clustering EDA

**Original themes:** 90
**Canonical themes:** 90
**Deduplication ratio:** 1.000
**Final clusters:** 8
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 97.6s
**Total posts in clusters:** 94
**Total upvotes in clusters:** 3,581

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 74.7 | 76.6% |
| Theme Expansion Llm | 74.7 | 76.5% |
| Embedding Generation | 8.1 | 8.3% |
| Kmeans Clustering | 1.0 | 1.0% |
| Cluster Naming | 13.6 | 13.9% |

### Cluster Size Stats
- Min posts: 4
- Max posts: 25
- Mean posts: 11.8

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 1 | Deep Emotional Pain and Isolation | 17 | 19 | 1,211 | 63.7 |
| 6 | Overwhelming Inner Struggles | 5 | 5 | 683 | 136.6 |
| 4 | Profound Hopelessness and Despair | 23 | 25 | 553 | 22.1 |
| 0 | Sudden Loss and Frustration | 7 | 7 | 393 | 56.1 |
| 2 | Medication Problems and Side Effects | 12 | 12 | 250 | 20.8 |
| 3 | Overwhelm, burnout, and inaction | 10 | 10 | 209 | 20.9 |
| 7 | Internal & External Struggles | 12 | 12 | 203 | 16.9 |
| 5 | Memory and Cognitive Decline | 4 | 4 | 79 | 19.8 |

### Theme Breakdown by Cluster

**Deep Emotional Pain and Isolation** (19 posts, 1,211 upvotes)
  - addiction ruined life
  - childhood pain, anger
  - denied mercy
  - extreme nostalgia
  - family invalidation
  - feeling stuck
  - feeling worthless
  - gay loneliness
  - harder to connect
  - hate winter
  - loneliness
  - loss of self
  - nicotine addiction
  - profound loneliness
  - severe understimulation
  - stuck, no progress
  - suicidal, no support

**Overwhelming Inner Struggles** (5 posts, 683 upvotes)
  - being annoying
  - compulsive biting
  - constant mental noise
  - shower chore
  - socializing feels bad

**Profound Hopelessness and Despair** (25 posts, 553 upvotes)
  - disappointed waking up
  - efforts always fail
  - extreme despair
  - extreme hopelessness
  - fear of dying
  - feeling hopeless
  - hate everything
  - hate own body
  - hopelessness
  - life is awful
  - life is hopeless
  - life is suffering
  - life is unfair
  - loss of hope
  - no hope
  - no one cares
  - parental indifference
  - persistent sadness
  - personal inadequacy
  - suicidal ideation
  - unending depression
  - unworthy of affection
  - utter defeat

**Sudden Loss and Frustration** (7 posts, 393 upvotes)
  - all or nothing
  - delete account/payment
  - forgetting fridge food
  - immediate access loss
  - losing socks
  - misunderstanding change
  - unfair suffering

**Medication Problems and Side Effects** (12 posts, 250 upvotes)
  - caffeine overstimulation
  - emotional blunting
  - evening crash
  - expected more
  - medication failure
  - medication harm
  - medication problems
  - medication side effects
  - meds not working
  - unwanted medication change
  - vyvanse not lasting
  - vyvanse side effects

**Overwhelm, burnout, and inaction** (10 posts, 209 upvotes)
  - email overwhelm
  - gaming impairs focus
  - overwhelmed by suffering
  - self-regulation struggle
  - simple tasks overwhelming
  - stuck, can't act
  - student burnout
  - suicidal pressure
  - unsuitable career
  - unsure how to support

**Internal & External Struggles** (12 posts, 203 upvotes)
  - adhd narrative confusion
  - adhd struggle
  - casual drinking confusion
  - friend's negativity
  - job loss fear
  - lectures ineffective
  - medication necessity
  - meditation uncertainty
  - parental denial
  - questioning intelligence
  - unexplained stimming
  - unwanted hyperfocus

**Memory and Cognitive Decline** (4 posts, 79 upvotes)
  - cognitive decline
  - cognitive impairment
  - forgetting faces
  - missing medication

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 45.5 |
| Parse + validation | 0.0 |
| **Total** | **45.5** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 MedTrack Pro: ADHD & Depression Meds
**Pain point:** Users experience unexpected and severe side effects, inconsistent medication efficacy, and difficulty tracking their response to mental health medications like Vyvanse, Concerta, and Zyprexa.
**Target user:** Individuals with ADHD or depression who are currently on medication and experiencing side effects, inconsistent efficacy, or difficulty managing their treatment.
**Confidence:** high
**Core features:** medication schedule reminders, time-stamped symptom/side effect logging (severity scale), mood tracking with customizable tags, visual efficacy graphs (e.g., 'Vyvanse crash' timing), shareable PDF reports for doctors
**Revenue model:** Subscription: $7.99/month or $69.99/year for unlimited medication tracking, advanced analytics, and secure data sharing. Free tier allows tracking of one medication with basic logging.
**Evidence:** 12 posts, 250 upvotes

### #2 TaskFlow for Neurodivergents
**Pain point:** Individuals with ADHD and similar conditions struggle with executive dysfunction, making simple daily tasks like showering or managing food feel overwhelming, leading to inaction and self-criticism.
**Target user:** Adults and young adults with ADHD, executive dysfunction, or depression who struggle with initiating and completing daily self-care, household, or work-related tasks.
**Confidence:** high
**Core features:** micro-task breakdown and sequencing, customizable gentle reminders (visual, haptic, audio cues), virtual 'body doubling' sessions (silent co-working), visual progress tracking and streaks, 'reset' button for overwhelm/skipped tasks
**Revenue model:** Freemium: Basic task management and reminders are free. Premium ($9.99/month or $89.99/year) unlocks unlimited body doubling, advanced customization for reminders, and detailed progress analytics.
**Evidence:** 5 posts, 683 upvotes

### #3 SoberPath: Addiction Recovery Companion
**Pain point:** Individuals struggling with addiction feel isolated, lack consistent support, and need structured tools to manage cravings, identify triggers, and prevent relapse, often feeling their lives are ruined.
**Target user:** Individuals actively seeking to overcome addiction (e.g., gambling, substance abuse) and maintain sobriety, who need structured support and tools for relapse prevention.
**Confidence:** high
**Core features:** daily check-in (mood, craving intensity, triggers), personalized coping strategy library (e.g., guided meditations, distraction exercises), anonymous moderated peer support groups, progress tracking (days sober, goals met), emergency contact quick-dial and crisis resources
**Revenue model:** Subscription: $14.99/month or $129.99/year for full access to all coping strategies, unlimited group sessions, and advanced progress analytics. A free tier offers basic daily check-ins and limited access to resources.
**Evidence:** 19 posts, 1,211 upvotes

### #4 NeuroLearn: Adaptive Study Companion
**Pain point:** Neurodivergent individuals (e.g., with ADHD) find traditional learning methods ineffective, struggle with information retention, and feel frustrated by lectures and standard study techniques.
**Target user:** Students and professionals with ADHD or other neurodivergent conditions who struggle with traditional learning methods and information retention.
**Confidence:** medium
**Core features:** content import (text, audio, video), AI-powered summarization and rephrasing, interactive flashcards and quizzes, visual mind-mapping tools, customizable learning pace and reminder system, multi-modal output options (audio narration, visual aids)
**Revenue model:** Subscription: $12.99/month or $119.99/year for unlimited content uploads, advanced AI features, and personalized learning path recommendations. A free trial allows processing of 3 short documents.
**Evidence:** 12 posts, 203 upvotes

### #5 SafeHarbor: Moderated Peer Support
**Pain point:** Individuals experiencing profound hopelessness, despair, and suicidal ideation lack immediate, empathetic, and safe peer support channels, often feeling isolated and unheard.
**Target user:** Individuals experiencing severe depression, anxiety, loneliness, hopelessness, or suicidal ideation who are seeking immediate, safe, and anonymous peer support.
**Confidence:** high
**Core features:** anonymous 1:1 chat with trained peer supporters, moderated group support sessions (themed discussions), curated library of crisis resources (hotlines, local services), mood check-in with private journaling, 'safe space' content filters and reporting tools
**Revenue model:** Freemium: Basic anonymous chat and limited group access are free. Premium ($19.99/month or $199.99/year) offers priority access to 1:1 peer support, unlimited group sessions, and advanced journaling features. Partnerships with mental health organizations could also provide funding.
**Evidence:** 25 posts, 553 upvotes

### Analysis Summary
The Reddit complaints reveal significant and often severe mental health challenges, particularly related to ADHD and depression. Key themes include struggles with medication efficacy and side effects, executive dysfunction impacting daily tasks, profound emotional pain and isolation, and the critical need for structured support in addiction recovery and mental health crises. Many users express feelings of overwhelm, hopelessness, and a desire for practical, empathetic solutions.

### Data Limitations
This dataset primarily captures self-reported experiences from Reddit users, which may not be representative of the broader population or clinical diagnoses. The data is limited to specific subreddits (ADHD, depression, anxiety, daddit) and may not cover the full spectrum of health complaints. Upvote counts indicate community resonance but not necessarily the prevalence or severity of a problem in a clinical sense. The short timeframe of the posts (likely a single crawl) means trends are not observable.
