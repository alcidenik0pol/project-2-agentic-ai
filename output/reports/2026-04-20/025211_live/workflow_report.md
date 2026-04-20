# Workflow Report
_Generated: 2026-04-20T02:57:58.468860+00:00_

## 1. Subreddit Selection

**Topic:** health
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> The selected subreddits cover direct health conditions (mental and physical), the impact of relationships and social issues on well-being, and systemic or financial factors that contribute to health-related complaints. General complaint/support subreddits are included as they often contain personal health struggles.

### Selected Subreddits
- r/depression
- r/anxiety
- r/ADHD
- r/socialanxiety
- r/30PlusSkinCare
- r/parenting
- r/mommit
- r/beyondthebump
- r/relationships
- r/relationship_advice
- r/offmychest
- r/trueoffmychest
- r/lonely
- r/deadbedrooms
- r/personalfinance
- r/povertyfinance
- r/debtfree
- r/antiwork
- r/workreform
- r/fuckcars

## 2. Data Fetching

**Topic:** health
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 93.9s

### Subreddits Queried
- r/depression
- r/anxiety
- r/ADHD
- r/socialanxiety
- r/30PlusSkinCare
- r/parenting
- r/mommit
- r/beyondthebump
- r/relationships
- r/relationship_advice
- r/offmychest
- r/trueoffmychest
- r/lonely
- r/deadbedrooms
- r/personalfinance
- r/povertyfinance
- r/debtfree
- r/antiwork
- r/workreform
- r/fuckcars

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 36.8s
**Throughput:** 2.7 posts/s
**Unique themes:** 89

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 345.6 | 100.0 calls, avg 3.456s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 93
- Non-complaints: 7

### Intensity Distribution
- high: 85
- medium: 8
- low: 7

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Suicidal thoughts | 3 |
| 2 | Constant sadness | 3 |
| 3 | No complaint | 3 |
| 4 | Suicidal ideation | 2 |
| 5 | Life is unbearable | 2 |
| 6 | Profound hopelessness | 2 |
| 7 | Debilitating anxiety | 2 |
| 8 | Anxiety attacks | 2 |
| 9 | Wanting to die | 1 |
| 10 | Parents don't care | 1 |
| 11 | Tired of life | 1 |
| 12 | No one cares | 1 |
| 13 | Profound loneliness | 1 |
| 14 | Suicidal, alone | 1 |
| 15 | Body disgust | 1 |
| 16 | Fear of life | 1 |
| 17 | Overwhelming guilt | 1 |
| 18 | Mental anguish | 1 |
| 19 | Constant neglect | 1 |
| 20 | Memory and apathy | 1 |

## 4. Clustering EDA

**Original themes:** 84
**Canonical themes:** 84
**Deduplication ratio:** 1.000
**Final clusters:** 15
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 103.4s
**Total posts in clusters:** 93
**Total upvotes in clusters:** 1,437

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 70.8 | 68.5% |
| Theme Expansion Llm | 70.8 | 68.4% |
| Embedding Generation | 8.0 | 7.8% |
| Kmeans Clustering | 0.9 | 0.9% |
| Cluster Naming | 23.6 | 22.8% |

### Cluster Size Stats
- Min posts: 1
- Max posts: 24
- Mean posts: 6.2

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 14 | Unfulfilled Life and Regret | 6 | 6 | 457 | 76.2 |
| 1 | Profound Despair and Suicidal Thoughts | 18 | 24 | 317 | 13.2 |
| 4 | Nighttime Sleep Panic Attacks | 8 | 8 | 204 | 25.5 |
| 10 | Profound Despair and Isolation | 8 | 9 | 99 | 11.0 |
| 2 | Severe Debilitating Anxiety | 13 | 15 | 94 | 6.3 |
| 0 | Phone Use Anxiety | 1 | 1 | 86 | 86.0 |
| 6 | Intense Self-Loathing and Despair | 3 | 3 | 50 | 16.7 |
| 8 | Husband's Betrayal | 1 | 1 | 34 | 34.0 |
| 3 | Fear and Anxiety Triggers | 6 | 6 | 22 | 3.7 |
| 13 | Anxiety, Mood, Overthinking Struggles | 6 | 6 | 20 | 3.3 |
| 11 | Life Disarray and Neglect | 6 | 6 | 19 | 3.2 |
| 5 | Medication Side Effect Concerns | 5 | 5 | 16 | 3.2 |
| 12 | Missing past fun | 1 | 1 | 10 | 10.0 |
| 9 | Memory Loss and Apathy | 1 | 1 | 6 | 6.0 |
| 7 | Chronic Dizziness Complaints | 1 | 1 | 3 | 3.0 |

### Theme Breakdown by Cluster

**Unfulfilled Life and Regret** (6 posts, 457 upvotes)
  - extreme nostalgia
  - forced waiting
  - gay loneliness
  - life wasted
  - looksmaxing ruined life
  - lost potential

**Profound Despair and Suicidal Thoughts** (24 posts, 317 upvotes)
  - can't die
  - constant sadness
  - denied peace
  - existential dread
  - fear of life
  - hate everything
  - hate life
  - life is hopeless
  - life is pointless
  - life is unbearable
  - mother's interference
  - no motivation
  - no one cares
  - parents don't care
  - suicidal ideation
  - suicidal thoughts
  - tired of life
  - wanting to die

**Nighttime Sleep Panic Attacks** (8 posts, 204 upvotes)
  - bedtime anxiety
  - fear sleep death
  - flu-like symptoms
  - medication wears off
  - nighttime panic
  - panicky chest
  - sleep anxiety
  - waking panic attacks

**Profound Despair and Isolation** (9 posts, 99 upvotes)
  - constant suffering
  - failing at life
  - mental anguish
  - profound depression
  - profound hopelessness
  - profound loneliness
  - social rejection
  - suicidal, alone

**Severe Debilitating Anxiety** (15 posts, 94 upvotes)
  - anxiety attack fear
  - anxiety attacks
  - anxiety controls life
  - compulsive worrying
  - debilitating anxiety
  - disabled by anxiety
  - overwhelming anxiety
  - physical anxiety fear
  - severe anxiety symptoms
  - surgery anxiety
  - teaching fear
  - uncomfortable eye contact
  - unrelenting anxiety

**Phone Use Anxiety** (1 posts, 86 upvotes)
  - anxiety phone habit

**Intense Self-Loathing and Despair** (3 posts, 50 upvotes)
  - body disgust
  - overwhelming guilt
  - self-destructive fantasies

**Husband's Betrayal** (1 posts, 34 upvotes)
  - husband's betrayal

**Fear and Anxiety Triggers** (6 posts, 22 upvotes)
  - anxious about heart
  - fear of emotions
  - fear of recurrence
  - fear of scolding
  - loud alerts distress
  - uncontrolled anxiety

**Anxiety, Mood, Overthinking Struggles** (6 posts, 20 upvotes)
  - anxious overthinking
  - everything feels off
  - friendship anxiety
  - low mood
  - mood swings
  - overthinking struggle

**Life Disarray and Neglect** (6 posts, 19 upvotes)
  - constant neglect
  - feeling lost
  - life falling apart
  - no time
  - self-neglect
  - struggling to change

**Medication Side Effect Concerns** (5 posts, 16 upvotes)
  - fear of side effects
  - lithium weight gain
  - propranolol side effects
  - worsening anxiety
  - zyprexa side effects

**Missing past fun** (1 posts, 10 upvotes)
  - forgotten fun

**Memory Loss and Apathy** (1 posts, 6 upvotes)
  - memory and apathy

**Chronic Dizziness Complaints** (1 posts, 3 upvotes)
  - chronic dizziness

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 47.2 |
| Parse + validation | 0.0 |
| **Total** | **47.2** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 SafeSpace Connect
**Pain point:** Users express profound despair, suicidal thoughts, and a desperate need for someone to talk to, feeling isolated and alone.
**Target user:** Individuals experiencing profound despair, suicidal ideation, severe loneliness, or mental health crises who are seeking immediate, non-clinical support and human connection.
**Confidence:** high
**Core features:** anonymous 1:1 peer chat, guided emotional journaling, quick crisis hotline access, curated coping resource library, daily mood check-ins
**Revenue model:** Freemium: Basic features (journaling, resources, limited peer chat sessions) are free. A premium subscription at $9.99/month or $99/year offers unlimited peer chat, advanced mood analytics, and specialized guided programs.
**Evidence:** 24 posts, 317 upvotes

### #2 Serene Slumber
**Pain point:** Users experience nighttime panic attacks, fear of falling asleep, and physical anxiety symptoms that severely disrupt their sleep.
**Target user:** Individuals who regularly experience anxiety, panic attacks, or intense fear specifically around bedtime or during the night, leading to significant sleep disruption and distress.
**Confidence:** high
**Core features:** emergency panic button, personalized sleep stories/meditations, CBT-I modules for anxiety, optional sleep tracking, anxiety symptom progress tracking
**Revenue model:** Subscription: $7.99/month or $69.99/year, with a 7-day free trial.
**Evidence:** 8 posts, 204 upvotes

### #3 Anxiety Navigator
**Pain point:** Users report debilitating, never-ending anxiety that feels like agony and significantly impairs their daily functioning.
**Target user:** Individuals suffering from chronic, severe, or debilitating anxiety that significantly impacts their daily functioning, social interactions, and overall quality of life.
**Confidence:** high
**Core features:** real-time anxiety check-in, guided coping strategies, personalized skill builder modules, trigger journaling, progress dashboard
**Revenue model:** Subscription: $12.99/month or $119.99/year. A free tier provides access to basic check-ins and one introductory skill module.
**Evidence:** 15 posts, 94 upvotes

### #4 MedInsight Connect
**Pain point:** Users are concerned about or experiencing side effects from mental health medications, seeking peer experiences and reliable information beyond what doctors provide.
**Target user:** Individuals currently taking mental health medications (e.g., antidepressants, anxiolytics, mood stabilizers) who are concerned about or experiencing side effects and desire peer insights and better tools for managing their treatment.
**Confidence:** medium
**Core features:** personalized medication tracker, anonymous peer reviews/ratings, community forums, side effect trend visualization, doctor discussion guide generator
**Revenue model:** Freemium: Basic medication tracking and limited community access are free. A premium subscription at $5.99/month or $59.99/year offers advanced analytics, unlimited forum access, and personalized doctor discussion guides.
**Evidence:** 5 posts, 16 upvotes

### #5 Mindful Momentum
**Pain point:** Users express regret over unfulfilled lives, struggle with digital distraction (phone use anxiety), and desire to proactively improve their mental well-being and self-care habits.
**Target user:** Individuals who feel their life is unfulfilled, struggle with digital addiction or phone-induced anxiety, or proactively seek to improve their mental well-being, self-care habits, and overall life satisfaction.
**Confidence:** high
**Core features:** personalized mental wellness goal setting, digital usage insights & nudges, daily self-care prompts, guided reflection & journaling, curated mental health resource library
**Revenue model:** Subscription: $8.99/month or $89.99/year. A free tier provides basic goal setting and limited digital usage insights.
**Evidence:** 6 posts, 457 upvotes

### Analysis Summary
The complaints predominantly highlight severe mental health challenges, including profound despair, suicidal ideation, debilitating anxiety, and specific issues like nighttime panic attacks and medication side effect concerns. There's a strong underlying theme of feeling overwhelmed, isolated, and a desire for effective coping mechanisms and support to improve overall well-being and life satisfaction.

### Data Limitations
The dataset is limited to Reddit complaints, which may overrepresent individuals actively seeking support or expressing distress online, potentially skewing the perception of prevalence. The data also lacks demographic information, making it difficult to target specific user segments beyond the expressed pain points. Furthermore, the short-form nature of Reddit posts may not capture the full nuance or complexity of users' health issues.
