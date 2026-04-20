# Workflow Report
_Generated: 2026-04-20T03:25:53.184865+00:00_

## 1. Subreddit Selection

**Topic:** flowers
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> Flowers are often central to personal relationships, dating, and emotional well-being, leading to complaints about gifts, gestures, or their absence. They can also be the subject of general grievances, business-related issues (florists), or financial concerns.

### Selected Subreddits
- r/relationship_advice
- r/relationships
- r/dating
- r/datingoverthirty
- r/breakups
- r/amitheasshole
- r/mildlyinfuriating
- r/offmychest
- r/trueoffmychest
- r/entrepreneur
- r/smallbusiness
- r/depression
- r/anxiety
- r/socialanxiety
- r/deadbedrooms
- r/lonely
- r/personalfinance
- r/povertyfinance
- r/assholedesign
- r/adulting

## 2. Data Fetching

**Topic:** flowers
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 191.9s

### Subreddits Queried
- r/relationship_advice
- r/relationships
- r/dating
- r/datingoverthirty
- r/breakups
- r/amitheasshole
- r/mildlyinfuriating
- r/offmychest
- r/trueoffmychest
- r/entrepreneur
- r/smallbusiness
- r/depression
- r/anxiety
- r/socialanxiety
- r/deadbedrooms
- r/lonely
- r/personalfinance
- r/povertyfinance
- r/assholedesign
- r/adulting

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 39.6s
**Throughput:** 2.5 posts/s
**Unique themes:** 98

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 359.4 | 100.0 calls, avg 3.594s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 100
- Non-complaints: 0

### Intensity Distribution
- high: 80
- medium: 19
- low: 1

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Unclear intentions | 2 |
| 2 | Husband's betrayal | 2 |
| 3 | Boyfriend's disrespect | 1 |
| 4 | Boyfriend's anger | 1 |
| 5 | Ring preferences ignored | 1 |
| 6 | Toxic communication | 1 |
| 7 | Sexual teasing hurts | 1 |
| 8 | Partner invalidates experience | 1 |
| 9 | Unwanted religious gift | 1 |
| 10 | Recycled trip | 1 |
| 11 | Appearance doubts | 1 |
| 12 | Sexless, unaffectionate | 1 |
| 13 | Cleaning disagreement | 1 |
| 14 | Addiction & betrayal | 1 |
| 15 | Porn affecting sex | 1 |
| 16 | Relationship autopilot | 1 |
| 17 | Feeling used | 1 |
| 18 | Ex's behavior | 1 |
| 19 | Girlfriend overwhelmed me | 1 |
| 20 | GF distant | 1 |

## 4. Clustering EDA

**Original themes:** 98
**Canonical themes:** 98
**Deduplication ratio:** 1.000
**Final clusters:** 11
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 126.8s
**Total posts in clusters:** 100
**Total upvotes in clusters:** 5,028

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 97.7 | 77.1% |
| Theme Expansion Llm | 97.7 | 77.0% |
| Embedding Generation | 8.8 | 6.9% |
| Kmeans Clustering | 0.9 | 0.7% |
| Cluster Naming | 19.2 | 15.2% |

### Cluster Size Stats
- Min posts: 3
- Max posts: 16
- Mean posts: 9.1

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 9 | Relationship & Trust Issues | 6 | 6 | 1,769 | 294.8 |
| 0 | Relationship Conflict & Disrespect | 14 | 14 | 1,433 | 102.4 |
| 8 | Relationship Insecurity & Conflict | 16 | 16 | 897 | 56.1 |
| 5 | Intimacy and Sexual Dissatisfaction | 13 | 13 | 344 | 26.5 |
| 2 | Partner Betrayal and Neglect | 14 | 15 | 323 | 21.5 |
| 1 | Personal Distress and Discomfort | 3 | 3 | 113 | 37.7 |
| 4 | Social Discomfort and Anxiety | 7 | 7 | 71 | 10.1 |
| 7 | Relationship Emotional Turmoil | 4 | 4 | 40 | 10.0 |
| 10 | Unclear, Uncommitted Relationships | 10 | 11 | 19 | 1.7 |
| 6 | Difficult Relationship Aftermath | 6 | 6 | 11 | 1.8 |
| 3 | Declining Relationship Connection | 5 | 5 | 8 | 1.6 |

### Theme Breakdown by Cluster

**Relationship & Trust Issues** (6 posts, 1,769 upvotes)
  - addiction & betrayal
  - appearance doubts
  - gf distant
  - porn affecting sex
  - privacy invasion
  - recycled trip

**Relationship Conflict & Disrespect** (14 posts, 1,433 upvotes)
  - boyfriend's anger
  - boyfriend's disrespect
  - cleaning disagreement
  - dog's behavior
  - feeling used
  - girlfriend opposes meds
  - low effort birthday
  - mother housing crisis
  - not wanted there
  - ring preferences ignored
  - sleep anger
  - unjust exclusion
  - unsupportive fiancé
  - vacation refusal

**Relationship Insecurity & Conflict** (16 posts, 897 upvotes)
  - communication difficulty
  - communication insecurity
  - food boundaries ignored
  - girlfriend overwhelmed me
  - insecurity broke us
  - insecurity projection
  - mismatched schedules
  - mom repeats details
  - partner changed negatively
  - partner invalidates experience
  - partner's jealousy
  - refuses discussion
  - relationship insecurity
  - toxic communication
  - unfair blame
  - unreasonable boundaries

**Intimacy and Sexual Dissatisfaction** (13 posts, 344 upvotes)
  - dating inexperience
  - no initiation
  - no sexual desire
  - relationship autopilot
  - relationship problems
  - sex less intense
  - sexless, unaffectionate
  - sexual deprivation
  - sexual dishonesty
  - sexual dissatisfaction
  - sexual incompatibility
  - sexual teasing hurts
  - unsatisfying intimacy

**Partner Betrayal and Neglect** (15 posts, 323 upvotes)
  - betrayal, abuse
  - boyfriend cheated
  - boyfriend lying
  - cheating betrayal
  - husband's betrayal
  - husband's cheating
  - husband's irresponsibility
  - husband's neglect
  - husband's secret life
  - husband's selfishness
  - lack of progress
  - partner's neglect
  - reveal father's abuse
  - trust broken

**Personal Distress and Discomfort** (3 posts, 113 upvotes)
  - complaining about bill
  - duty sex distress
  - embarrassing loudness

**Social Discomfort and Anxiety** (7 posts, 71 upvotes)
  - anxiety prevents relationships
  - boring weekends
  - fear ruined relationship
  - low social battery
  - relationship anxiety
  - relationships annoying
  - unwanted religious gift

**Relationship Emotional Turmoil** (4 posts, 40 upvotes)
  - confused about feelings
  - fear of rejection
  - friend likes bf
  - jonathan's inconsistency

**Unclear, Uncommitted Relationships** (11 posts, 19 upvotes)
  - boundary disrespect
  - constant ghosting
  - friend ignoring me
  - ghosted and confused
  - lack of commitment
  - mixed signals
  - one-sided friendship
  - roommate phase
  - situationship disrespect
  - unclear intentions

**Difficult Relationship Aftermath** (6 posts, 11 upvotes)
  - difficult breakup
  - draining friendship
  - ex refuses items
  - ex's behavior
  - lost best friend
  - trauma triggered

**Declining Relationship Connection** (5 posts, 8 upvotes)
  - bf wants space
  - gf's behavior changed
  - girlfriend's disapproval
  - no attraction
  - staying too long

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 30.4 |
| Parse + validation | 0.0 |
| **Total** | **30.4** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 ThoughtfulBloom: Personalized Gifting for Milestones
**Pain point:** Partners feel unappreciated or that not enough effort is put into special occasions like birthdays.
**Target user:** Individuals in relationships (M/F 20-40) who struggle with consistently showing appreciation or planning thoughtful gestures, often leading to complaints of 'low effort'.
**Confidence:** high
**Core features:** Calendar integration for relationship milestones, partner preference profile builder, AI-driven personalized flower/gift suggestions, automated reminder system, curated local florist network for delivery.
**Revenue model:** Freemium: Basic reminders and suggestions are free. Premium subscription ($9.99/month or $99/year) unlocks advanced personalization, unlimited event tracking, and exclusive florist discounts. Transactional commission (10-15%) on flower and gift orders placed through the platform.
**Evidence:** 14 posts, 1,433 upvotes

### #2 CarePetal: Sympathy & Support Flower Service
**Pain point:** Partners struggle to show support or care during difficult, stressful, or grieving periods, sometimes leading to emotional distance or feeling 'not wanted there'.
**Target user:** Individuals whose partners or loved ones are experiencing difficult life events (e.g., loss, illness, high stress) and want to show support but are unsure how, or fear being intrusive.
**Confidence:** medium
**Core features:** Event-based suggestion engine (e.g., 'grief', 'stress', 'recovery'), curated selection of sympathy and support-appropriate flowers, pre-written customizable message templates, discreet and timely delivery options, integration with local florists.
**Revenue model:** Transactional model with tiered pricing for different care packages and flower arrangements (e.g., 'Comfort Bouquet' $50, 'Deep Sympathy Arrangement' $120). Optional expedited delivery fee ($15-25).
**Evidence:** 14 posts, 1,433 upvotes

### #3 ReconcileBloom: Apology & Repair Kits
**Pain point:** Individuals struggle to effectively apologize or initiate reconciliation after significant relationship conflicts or betrayals, often leading to prolonged silence or unresolved issues.
**Target user:** Individuals who have caused pain or conflict in a relationship and are seeking a structured, thoughtful way to apologize and initiate repair, especially when direct communication is difficult.
**Confidence:** medium
**Core features:** Severity-based apology kit suggestions, flower symbolism guide, customizable apology message templates, optional add-ons (e.g., a journal for reflection, a 'discussion prompt' card), discreet delivery with optional 'read receipt' for delivery confirmation.
**Revenue model:** Transactional model with tiered apology kits (e.g., 'Minor Misstep Kit' $60, 'Serious Repair Kit' $150, 'Betrayal Atonement Kit' $250). Optional premium message crafting assistance ($20).
**Evidence:** 15 posts, 323 upvotes

### #4 SparkBloom: Relationship Connection Boosters
**Pain point:** Relationships experience declining connection, attraction, or communication, leading to feelings of distance or 'autopilot'.
**Target user:** Couples in established relationships (25-50) who feel their connection is waning or has entered 'autopilot', and want proactive ways to maintain intimacy and appreciation.
**Confidence:** low
**Core features:** Relationship 'spark level' assessment, personalized gesture prompts (including 'surprise' flower deliveries), curated selection of small, non-overwhelming flower options, integration with local florists for spontaneous delivery, 'relationship health check-ins' to adapt suggestions.
**Revenue model:** Subscription service: $19.99/month for weekly prompts and curated suggestions, plus discounted flower deliveries. Higher tiers ($39.99/month) include one small flower delivery per month and premium date ideas.
**Evidence:** 5 posts, 8 upvotes

### #5 SignalBloom: Subtle Interest & Appreciation Gestures
**Pain point:** Individuals in new or ambiguous relationships (situationships, friendships with romantic interest) struggle to convey interest or appreciation without sending 'mixed signals' or being overly intense.
**Target user:** Young adults (18-30) navigating the early stages of relationships, friendships with potential, or 'situationships' who want to express feelings or appreciation without miscommunication.
**Confidence:** low
**Core features:** 'Signal Strength' guide for flower choices (e.g., a single stem vs. a small bouquet), non-committal message templates, anonymous or discreet delivery options, advice on timing and frequency of gestures, curated selection of local florists for subtle arrangements.
**Revenue model:** Transactional model for individual flower/gift orders (e.g., a single rose for $25, a small plant for $40). Premium advice package ($10 for 3 consultations) for personalized guidance on gesture selection and messaging.
**Evidence:** 11 posts, 19 upvotes

### Analysis Summary
The provided Reddit complaint clusters are overwhelmingly focused on various forms of relationship distress, betrayal, communication issues, and personal discomfort, with no explicit mention of 'flowers'. To fulfill the request, the proposed business opportunities interpret 'flowers' as a symbolic gesture within relationships, aiming to address emotional pain points by facilitating thoughtful communication, appreciation, support, apology, or subtle signaling through floral gifts.

### Data Limitations
The primary limitation is the complete absence of the keyword 'flowers' or any related complaints within the provided dataset. All proposed ideas are based on inferring how floral gestures could hypothetically address the emotional and relational pain points described in the clusters, rather than directly responding to complaints about flowers themselves (e.g., quality, delivery, cost of flowers). This required a significant interpretive leap to connect the user's specific request to the available data.
