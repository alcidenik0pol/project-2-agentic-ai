# Workflow Report
_Generated: 2026-04-20T00:26:34.929305+00:00_

## 1. Subreddit Selection

**Topic:** health
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> The selected subreddits cover direct mental and physical health conditions (depression, anxiety, ADHD, socialanxiety, 30PlusSkinCare), general emotional support and venting (offmychest, trueoffmychest, lonely), and health-related aspects of parenting (parenting, mommit, beyondthebump). Additionally, subreddits addressing relationship issues (relationships, relationship_advice, deadbedrooms) are included due to their significant impact on mental well-being. Systemic issues affecting health, such as healthcare access and costs (workreform, povertyfinance), public health (fuckcars), and work-related stress (antiwork), are also represented. Finally, general conflict (amitheasshole) and financial burdens (studentloans, potentially from medical debt) are included as they can lead to significant health complaints.

### Selected Subreddits
- r/depression
- r/anxiety
- r/ADHD
- r/socialanxiety
- r/offmychest
- r/trueoffmychest
- r/lonely
- r/parenting
- r/mommit
- r/beyondthebump
- r/30PlusSkinCare
- r/relationships
- r/relationship_advice
- r/deadbedrooms
- r/workreform
- r/povertyfinance
- r/fuckcars
- r/antiwork
- r/amitheasshole
- r/studentloans

## 2. Data Fetching

**Topic:** health
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 123.0s

### Subreddits Queried
- r/depression
- r/anxiety
- r/ADHD
- r/socialanxiety
- r/offmychest
- r/trueoffmychest
- r/lonely
- r/parenting
- r/mommit
- r/beyondthebump
- r/30PlusSkinCare
- r/relationships
- r/relationship_advice
- r/deadbedrooms
- r/workreform
- r/povertyfinance
- r/fuckcars
- r/antiwork
- r/amitheasshole
- r/studentloans

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 43.6s
**Throughput:** 2.3 posts/s
**Unique themes:** 95

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 387.0 | 100.0 calls, avg 3.870s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 94
- Non-complaints: 6

### Intensity Distribution
- high: 85
- medium: 12
- low: 3

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Feeling worthless | 2 |
| 2 | Mirtazapine depression | 2 |
| 3 | Debilitating anxiety | 2 |
| 4 | Anxiety attacks | 2 |
| 5 | New job anxiety | 2 |
| 6 | Parental indifference | 1 |
| 7 | No one cares | 1 |
| 8 | Done suffering | 1 |
| 9 | Social isolation | 1 |
| 10 | Suicidal and alone | 1 |
| 11 | Body disgust | 1 |
| 12 | Life's overwhelming fear | 1 |
| 13 | Weary of life | 1 |
| 14 | Memory and interest | 1 |
| 15 | Life's unfairness | 1 |
| 16 | Self-neglect | 1 |
| 17 | Suffering from addiction | 1 |
| 18 | Zyprexa ruined me | 1 |
| 19 | Always sad | 1 |
| 20 | Hate everything | 1 |

## 4. Clustering EDA

**Original themes:** 89
**Canonical themes:** 89
**Deduplication ratio:** 1.000
**Final clusters:** 15
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 136.3s
**Total posts in clusters:** 94
**Total upvotes in clusters:** 1,566

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 84.5 | 62.0% |
| Theme Expansion Llm | 84.5 | 62.0% |
| Embedding Generation | 16.7 | 12.3% |
| Kmeans Clustering | 0.9 | 0.7% |
| Cluster Naming | 34.0 | 24.9% |

### Cluster Size Stats
- Min posts: 1
- Max posts: 18
- Mean posts: 6.3

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 7 | Profound Despair and Isolation | 17 | 18 | 609 | 33.8 |
| 9 | Inability to Improve | 2 | 2 | 251 | 125.5 |
| 2 | Past Regrets and Wasted Life | 5 | 5 | 216 | 43.2 |
| 4 | Nighttime Anxiety and Panic | 8 | 8 | 189 | 23.6 |
| 1 | Severe, Debilitating Life Anxiety | 12 | 13 | 84 | 6.5 |
| 10 | Profound Hopelessness and Weariness | 7 | 7 | 48 | 6.9 |
| 14 | Emotional Pain and Neglect | 5 | 5 | 46 | 9.2 |
| 0 | Persistent Sadness and Depression | 9 | 9 | 45 | 5.0 |
| 6 | Anxiety and Panic Symptoms | 5 | 6 | 21 | 3.5 |
| 11 | Love Life Challenges | 2 | 2 | 19 | 9.5 |
| 3 | Medication Side Effects & Harm | 5 | 6 | 16 | 2.7 |
| 5 | Overwhelming Personal Distress | 5 | 5 | 13 | 2.6 |
| 8 | Anxiety Mental and Physical Symptoms | 4 | 4 | 4 | 1.0 |
| 12 | Anxiety about new tasks | 2 | 3 | 3 | 1.0 |
| 13 | Coping with Sadness | 1 | 1 | 2 | 2.0 |

### Theme Breakdown by Cluster

**Profound Despair and Isolation** (18 posts, 609 upvotes)
  - body disgust
  - done suffering
  - feeling hopeless
  - feeling worthless
  - gay loneliness
  - hopeless depression
  - life is terrible
  - life is unfair
  - life's unfairness
  - lost the fight
  - no one cares
  - overwhelming guilt
  - personal failure
  - profound loneliness
  - self-hatred
  - suicidal and alone
  - unjust world, anger

**Inability to Improve** (2 posts, 251 upvotes)
  - can't get better
  - feeling stuck

**Past Regrets and Wasted Life** (5 posts, 216 upvotes)
  - disturbing past thoughts
  - extreme nostalgia
  - life is waste
  - memory and interest
  - wasted life

**Nighttime Anxiety and Panic** (8 posts, 189 upvotes)
  - anxiety at night
  - anxiety prevents sleep
  - awakening panic attacks
  - escaping anxiety
  - fear of dying
  - night anxiety
  - night panic attacks
  - physical anxiety symptoms

**Severe, Debilitating Life Anxiety** (13 posts, 84 upvotes)
  - anxiety ruins life
  - debilitating anxiety
  - disabled by anxiety
  - fear of scolding
  - future anxiety
  - future worry
  - life's overwhelming fear
  - overwhelming anxiety
  - persistent anxiety
  - public speaking fear
  - severe anxiety
  - surgery anxiety

**Profound Hopelessness and Weariness** (7 posts, 48 upvotes)
  - always tired
  - constant neglect
  - denied mercy
  - hate everything
  - lost enjoyment
  - profound hopelessness
  - weary of life

**Emotional Pain and Neglect** (5 posts, 46 upvotes)
  - failing at life
  - hurt, isolation, anxiety
  - no understanding
  - parental indifference
  - self-neglect

**Persistent Sadness and Depression** (9 posts, 45 upvotes)
  - always sad
  - constant sadness
  - feeling depressed
  - low mood
  - negative mindset
  - passive ideations
  - persistent emptiness
  - seasonal depression
  - social isolation

**Anxiety and Panic Symptoms** (6 posts, 21 upvotes)
  - always panicking
  - anxiety attacks
  - ongoing panic attacks
  - overthinking
  - persistent dizziness

**Love Life Challenges** (2 posts, 19 upvotes)
  - friend's crush
  - unprepared for marriage

**Medication Side Effects & Harm** (6 posts, 16 upvotes)
  - caffeine anxiety
  - horrid anxiety
  - mirtazapine depression
  - propranolol side effects
  - zyprexa ruined me

**Overwhelming Personal Distress** (5 posts, 13 upvotes)
  - fear for father
  - feeling lost
  - mental health crisis
  - overwhelming life struggles
  - suffering from addiction

**Anxiety Mental and Physical Symptoms** (4 posts, 4 upvotes)
  - anxiety sensations
  - intrusive thoughts
  - leg tingling
  - mental anxiety

**Anxiety about new tasks** (3 posts, 3 upvotes)
  - mopping anxiety
  - new job anxiety

**Coping with Sadness** (1 posts, 2 upvotes)
  - sadness coping

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 38.5 |
| Parse + validation | 0.0 |
| **Total** | **38.5** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 NightCalm Companion
**Pain point:** Users experience debilitating anxiety and panic attacks at night, preventing sleep and causing fear, often related to death or physical symptoms.
**Target user:** Individuals suffering from nocturnal anxiety, sleep-onset insomnia due to anxiety, or those who experience panic attacks during the night.
**Confidence:** high
**Core features:** Guided sleep meditations, Panic Attack 'First Aid' audio, Personalized calming soundscapes, Pre-sleep worry journal, Sleep pattern tracker integration
**Revenue model:** Subscription: Free tier with basic meditations and panic first aid. Premium tier at $9.99/month or $79.99/year for unlimited access to all content, personalized soundscapes, advanced sleep tracking insights, and detailed journaling features.
**Evidence:** 8 posts, 189 upvotes

### #2 MedInsight Tracker
**Pain point:** Users are concerned about medication side effects, how different substances interact, and the overall impact of their prescriptions on their mental and physical well-being.
**Target user:** Individuals taking prescription medications for mental health or other conditions, who are concerned about side effects, interactions, or want to better understand their medication's impact.
**Confidence:** medium
**Core features:** Medication logging & reminders, Symptom tracking (customizable), Side effect database with user reports, Interaction checker (basic), Doctor discussion report generator
**Revenue model:** Freemium: Basic medication logging and symptom tracking are free. Premium features at $7.99/month or $69.99/year include advanced analytics, personalized insights, access to a larger community data pool for comparison, and exportable detailed reports for doctors.
**Evidence:** 6 posts, 16 upvotes

### #3 MoodFlow Daily
**Pain point:** Individuals experience persistent sadness, emptiness, and low mood, seeking practical ways to improve their emotional state and overall well-being.
**Target user:** Anyone experiencing persistent low mood, sadness, or mild to moderate depression who is looking for self-help tools and structured exercises to improve their emotional well-being.
**Confidence:** high
**Core features:** Daily mood check-ins, Guided gratitude journaling, Thought record exercises (CBT), Activity scheduling for mood, Progress visualization & insights
**Revenue model:** Subscription: Free trial for 7 days. Then $8.99/month or $74.99/year for full access to all exercises, unlimited journaling, personalized recommendations, and advanced progress reports.
**Evidence:** 9 posts, 45 upvotes

### #4 FearLadder Pro
**Pain point:** Users experience severe, debilitating anxiety that prevents them from enjoying life, often triggered by specific fears like social situations, new tasks, or future uncertainties.
**Target user:** Individuals with specific phobias, social anxiety, performance anxiety, or generalized anxiety that manifests around particular situations or tasks, who are looking for structured self-help to manage their fears.
**Confidence:** high
**Core features:** Customizable 'Fear Ladder' creation, Guided exposure exercises, Real-time coping tools (breathing, grounding), Thought challenging prompts, Progress tracking & insights
**Revenue model:** Subscription: Free tier for one basic fear ladder. Premium tier at $12.99/month or $99.99/year for unlimited fear ladders, advanced coping techniques, detailed progress analytics, and access to a library of expert-led workshops.
**Evidence:** 13 posts, 84 upvotes

### #5 Momentum Builder
**Pain point:** Users feel paralyzed, stuck, and unable to motivate themselves to initiate or complete tasks, often due to executive dysfunction or overwhelming feelings.
**Target user:** Individuals struggling with executive dysfunction, ADHD, anxiety-induced procrastination, or general feelings of being 'stuck' and unable to start or complete tasks.
**Confidence:** high
**Core features:** Task breakdown into micro-steps, Gamified progress tracking, 'Momentum Prompt' system, Customizable reward system, Accountability partner integration (optional)
**Revenue model:** Subscription: Free tier for managing 3 tasks. Premium tier at $6.99/month or $59.99/year for unlimited tasks, advanced analytics, custom reward options, and the ability to invite and track progress with accountability partners.
**Evidence:** 2 posts, 251 upvotes

### Analysis Summary
The Reddit complaints reveal a significant and pervasive struggle with various forms of mental health issues, primarily anxiety and depression. Users express deep feelings of sadness, debilitating anxiety, fear, and an inability to function or improve, often exacerbated by sleep disturbances or concerns about medication. The desire for practical, self-help tools to manage these conditions is evident across multiple clusters.

### Data Limitations
The data primarily consists of self-reported experiences on Reddit, which may not be representative of the broader population or clinical diagnoses. The sample sizes for some clusters are small, and while upvotes indicate resonance, they don't necessarily reflect the severity or prevalence of the issue. The nature of Reddit posts means solutions must be carefully designed to avoid exacerbating distress, especially for severe mental health concerns like suicidal ideation, which were present in some clusters but not directly addressed by product ideas due to the 3-6 month build constraint for safe, effective solutions.
