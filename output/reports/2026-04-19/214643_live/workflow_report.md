# Workflow Report
_Generated: 2026-04-19T21:56:02.440478+00:00_

## 1. Subreddit Selection

**Topic:** health
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> Selected subreddits include direct mental and physical health communities, general venting forums where health complaints are common, and communities where health issues significantly impact finances, relationships, work, or family life.

### Selected Subreddits
- r/offmychest
- r/trueoffmychest
- r/depression
- r/anxiety
- r/ADHD
- r/socialanxiety
- r/parenting
- r/mommit
- r/beyondthebump
- r/workreform
- r/fuckcars
- r/30PlusSkinCare
- r/povertyfinance
- r/personalfinance
- r/deadbedrooms
- r/relationships
- r/relationship_advice
- r/antiwork
- r/adulting
- r/lonely

## 2. Data Fetching

**Topic:** health
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 285.6s

### Subreddits Queried
- r/offmychest
- r/trueoffmychest
- r/depression
- r/anxiety
- r/ADHD
- r/socialanxiety
- r/parenting
- r/mommit
- r/beyondthebump
- r/workreform
- r/fuckcars
- r/30PlusSkinCare
- r/povertyfinance
- r/personalfinance
- r/deadbedrooms
- r/relationships
- r/relationship_advice
- r/antiwork
- r/adulting
- r/lonely

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 43.2s
**Throughput:** 2.3 posts/s
**Unique themes:** 98

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 411.6 | 100.0 calls, avg 4.116s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 96
- Non-complaints: 4

### Intensity Distribution
- high: 90
- medium: 6
- low: 4

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Profound grief | 2 |
| 2 | Father's abuse | 2 |
| 3 | Denied oral sex | 1 |
| 4 | Rape sites exist | 1 |
| 5 | Men's voyeurism | 1 |
| 6 | Soulless decline | 1 |
| 7 | Lost human progress | 1 |
| 8 | Breast size burden | 1 |
| 9 | Life is a lie | 1 |
| 10 | Racist society | 1 |
| 11 | Incestuous family dynamic | 1 |
| 12 | Virginity shaming | 1 |
| 13 | Feeling stuck | 1 |
| 14 | Guilt, lost cat | 1 |
| 15 | Social emptiness | 1 |
| 16 | Dick size obsession | 1 |
| 17 | Tired of life | 1 |
| 18 | Birthday not special | 1 |
| 19 | Longing for him | 1 |
| 20 | Coworker manipulation | 1 |

## 4. Clustering EDA

**Original themes:** 94
**Canonical themes:** 94
**Deduplication ratio:** 1.000
**Final clusters:** 14
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 147.8s
**Total posts in clusters:** 96
**Total upvotes in clusters:** 35,251

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 90.1 | 61.0% |
| Theme Expansion Llm | 90.1 | 61.0% |
| Embedding Generation | 22.9 | 15.5% |
| Kmeans Clustering | 1.1 | 0.7% |
| Cluster Naming | 33.4 | 22.6% |

### Cluster Size Stats
- Min posts: 3
- Max posts: 14
- Mean posts: 6.9

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 11 | Gendered Discomfort and Dismissal | 12 | 12 | 14,616 | 1218.0 |
| 10 | Unfulfilled Desires and Longings | 5 | 5 | 7,106 | 1421.2 |
| 6 | Profound Emotional Despair and Isolation | 13 | 14 | 5,196 | 371.1 |
| 3 | Extreme Family Betrayal | 4 | 4 | 4,234 | 1058.5 |
| 13 | Child Skincare Safety Concerns | 3 | 3 | 1,196 | 398.7 |
| 4 | Family and Relationship Trauma | 9 | 10 | 680 | 68.0 |
| 2 | Threats to Personal Safety | 4 | 4 | 564 | 141.0 |
| 7 | Societal Decline and Delusion | 4 | 4 | 419 | 104.8 |
| 12 | Profound Loss and Trauma | 5 | 5 | 374 | 74.8 |
| 8 | Betrayal and Communication Breakdown | 6 | 6 | 372 | 62.0 |
| 1 | Self-Worth and Rejection | 10 | 10 | 231 | 23.1 |
| 9 | Personal Failure and Regret | 10 | 10 | 177 | 17.7 |
| 0 | Personal Harm and Distress | 5 | 5 | 52 | 10.4 |
| 5 | Hostile Coworker Workplace | 4 | 4 | 34 | 8.5 |

### Theme Breakdown by Cluster

**Gendered Discomfort and Dismissal** (12 posts, 14,616 upvotes)
  - breast size burden
  - denied oral sex
  - dick size obsession
  - disappointment with men
  - doctor downplays risk
  - ignored male discomfort
  - inappropriate pda
  - making a big deal
  - men hijack spaces
  - men's dating issues
  - men's voyeurism
  - nude request discomfort

**Unfulfilled Desires and Longings** (5 posts, 7,106 upvotes)
  - bts obsession
  - cat obsession problem
  - longing for him
  - miss mom's cooking
  - unmet desires

**Profound Emotional Despair and Isolation** (14 posts, 5,196 upvotes)
  - extreme pain
  - feeling excluded
  - feeling unloved
  - giving up hope
  - lack of support
  - no one cares
  - parental indifference
  - profound grief
  - social emptiness
  - soulless decline
  - tired of life
  - ugliness ruining life
  - unbearable loss

**Extreme Family Betrayal** (4 posts, 4,234 upvotes)
  - incestuous family dynamic
  - mom enables pervert
  - sister killed niece
  - sister's hypocrisy

**Child Skincare Safety Concerns** (3 posts, 1,196 upvotes)
  - kids retinol misuse
  - lost on eye care
  - parents ignore safety

**Family and Relationship Trauma** (10 posts, 680 upvotes)
  - childhood depression resurfaces
  - dad's jealousy
  - dad's shaming
  - father's abuse
  - husband's unforgiveness
  - life is a lie
  - parental interference
  - unloved by parents
  - unreliable husband

**Threats to Personal Safety** (4 posts, 564 upvotes)
  - bedbug spread risk
  - rape sites exist
  - rape trauma
  - unprovoked attack

**Societal Decline and Delusion** (4 posts, 419 upvotes)
  - cynicism and ignorance
  - fiction vs. reality
  - lost human progress
  - racist society

**Profound Loss and Trauma** (5 posts, 374 upvotes)
  - forced painful sacrifice
  - missed dad's call
  - overdose crisis
  - paternity shock
  - pets killed

**Betrayal and Communication Breakdown** (6 posts, 372 upvotes)
  - cutting people off
  - false accusation
  - hurtful words
  - lack of closure
  - partner's infidelity
  - poor communication

**Self-Worth and Rejection** (10 posts, 231 upvotes)
  - always 'almost'
  - birthday not special
  - can't love self
  - celebration hassle
  - feeling deprioritized
  - female friendship struggles
  - minor selfie guilt
  - mother's rejection
  - virginity shaming
  - weight prevents love

**Personal Failure and Regret** (10 posts, 177 upvotes)
  - bad teachers
  - ed ruined life
  - embarrassing stupidity
  - feeling like failure
  - feeling overwhelmed
  - feeling uneducated
  - guilt, lost cat
  - life stagnation
  - marital failure
  - no independence

**Personal Harm and Distress** (5 posts, 52 upvotes)
  - assault and betrayal
  - drug-induced trauma
  - feeling stuck
  - friend's neglect
  - professor gossips

**Hostile Coworker Workplace** (4 posts, 34 upvotes)
  - coworker interference
  - coworker manipulation
  - hostile work environment
  - work despair

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 41.5 |
| Parse + validation | 0.0 |
| **Total** | **41.5** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 SafeSpace Connect
**Pain point:** Users express profound emotional despair, feelings of being 'done with life,' worsening depression, and a lack of support, indicating an urgent need for accessible mental health intervention.
**Target user:** Individuals experiencing acute emotional distress, depression, profound grief, or suicidal ideation who need immediate, anonymous support.
**Confidence:** high
**Core features:** anonymous chat with trained peer supporters, guided breathing exercises, emergency hotline directory, daily mood check-ins, mood trend tracking
**Revenue model:** Freemium: Basic anonymous chat and guided breathing exercises are free. A Premium subscription costs $9.99/month or $99/year, offering access to certified crisis counselors (limited sessions), advanced mood tracking analytics, and personalized coping strategies.
**Evidence:** 14 posts, 5,196 upvotes

### #2 KidSkin Guardian
**Pain point:** Parents are unaware or dismissive of the risks associated with certain skincare products for children, leading to potential harm (e.g., retinol misuse), and there's a need for reliable, accessible information.
**Target user:** Parents and guardians concerned about the safety and appropriateness of skincare products for their children, especially those influenced by social media trends or seeking reliable information.
**Confidence:** high
**Core features:** product barcode scanner for safety rating, ingredient checker with age-appropriate warnings, educational articles on child skin health, moderated 'Ask an Expert' forum, personalized child profile
**Revenue model:** Freemium: Basic ingredient checker and general educational articles are free. A Premium subscription costs $4.99/month or $49.99/year for full access to the product scanner, expert forum, and premium, in-depth articles.
**Evidence:** 3 posts, 1,196 upvotes

### #3 Resilience Path
**Pain point:** Individuals experience severe trauma from family abuse, betrayal, assault, or profound loss, leading to a need for specialized, trauma-informed support and resources, with many posts mentioning needing therapy or feeling stuck.
**Target user:** Individuals who have experienced significant trauma (e.g., abuse, assault, profound loss, betrayal) and are seeking specialized, compassionate support for their healing journey.
**Confidence:** high
**Core features:** trauma-informed therapist directory, moderated peer support group matching, guided trauma-sensitive meditations, curated resource library, secure journaling
**Revenue model:** Freemium: Basic resource library and limited peer group access are free. A Premium subscription costs $19.99/month or $199/year for unlimited peer groups, an advanced meditation library, and discounted rates for therapist consultations (platform takes a small booking fee from therapists).
**Evidence:** 10 posts, 680 upvotes

### #4 Patient Voice Pro
**Pain point:** Patients feel their medical concerns are being downplayed or dismissed by doctors, leading to frustration, potential misdiagnosis, or inadequate care, as highlighted by 'I think my doctor might be downplaying a medical issue'.
**Target user:** Patients who feel unheard or dismissed by their healthcare providers, are seeking a second opinion, or want to better advocate for themselves in medical settings.
**Confidence:** medium
**Core features:** secure medical record storage, AI-powered symptom question generator, guided appointment templates, second opinion specialist matching, symptom tracking
**Revenue model:** Freemium: Basic record storage and appointment templates are free. A Premium subscription costs $14.99/month or $149/year for advanced symptom tracking, AI-generated question prompts, and access to the 'Second Opinion Match' service (platform takes a 15-20% fee from specialist consultations).
**Evidence:** 12 posts, 14,616 upvotes

### #5 Inner Spark
**Pain point:** Individuals struggle with low self-worth, body image issues, feelings of failure, and an inability to love themselves, impacting their mental well-being and relationships, as seen in posts like 'I've been trying to learn to love myself for almost a year and it's not working'.
**Target user:** Individuals struggling with low self-esteem, negative body image, self-doubt, or feelings of inadequacy, seeking structured guidance to improve their self-perception and mental well-being.
**Confidence:** high
**Core features:** daily guided affirmations, personalized self-worth exercises, self-compassion journaling prompts, progress tracking for self-esteem, 1:1 coaching session booking
**Revenue model:** Subscription: A subscription costs $9.99/month or $99/year for full access to all exercises, journaling, and progress tracking. 1:1 coaching sessions are an additional cost ($50-$150/session), with the platform taking a 20% commission.
**Evidence:** 10 posts, 231 upvotes

### Analysis Summary
The complaints reveal a significant unmet need for mental health support, ranging from acute crisis intervention and trauma recovery to foundational self-esteem and body image work. There's also a clear demand for reliable, accessible information and advocacy in specific physical health areas, particularly concerning child safety and patient empowerment in medical settings.

### Data Limitations
This dataset is limited to Reddit 'offmychest' and 'TrueOffMyChest' type subreddits, which primarily capture highly emotional, personal, and often traumatic experiences. While providing strong signals for mental health and personal safety issues, it may underrepresent other common health complaints (e.g., chronic illness management, preventative care) that are discussed in different online forums or in less emotionally charged contexts. The upvote counts can also be skewed by sensational or highly relatable stories, not necessarily indicating the most widespread or financially viable pain points.
