# Workflow Report
_Generated: 2026-04-20T03:48:19.698086+00:00_

## 1. Subreddit Selection

**Topic:** love
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> The selected subreddits directly address love, relationships, and dating, or provide platforms for emotional complaints and struggles that frequently involve love-related issues, family dynamics, or personal well-being impacted by relationships. General complaint forums are included for broader applicability.

### Selected Subreddits
- r/relationship_advice
- r/relationships
- r/dating
- r/datingoverthirty
- r/breakups
- r/deadbedrooms
- r/offmychest
- r/trueoffmychest
- r/lonely
- r/amitheasshole
- r/parenting
- r/mommit
- r/daddit
- r/beyondthebump
- r/depression
- r/anxiety
- r/socialanxiety
- r/ChildFree
- r/adulting
- r/ADHD

## 2. Data Fetching

**Topic:** love
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 140.2s

### Subreddits Queried
- r/relationship_advice
- r/relationships
- r/dating
- r/datingoverthirty
- r/breakups
- r/deadbedrooms
- r/offmychest
- r/trueoffmychest
- r/lonely
- r/amitheasshole
- r/parenting
- r/mommit
- r/daddit
- r/beyondthebump
- r/depression
- r/anxiety
- r/socialanxiety
- r/ChildFree
- r/adulting
- r/ADHD

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 40.0s
**Throughput:** 2.5 posts/s
**Unique themes:** 98

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 378.0 | 100.0 calls, avg 3.780s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 99
- Non-complaints: 1

### Intensity Distribution
- high: 79
- medium: 21
- low: 0

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Sexual incompatibility | 2 |
| 2 | Lack of intimacy | 2 |
| 3 | Boyfriend's disrespect | 1 |
| 4 | Boyfriend's overreaction | 1 |
| 5 | Ignoring preferences | 1 |
| 6 | Boyfriend's manipulation | 1 |
| 7 | Teasing causes rejection | 1 |
| 8 | Partner's disbelief | 1 |
| 9 | Unsolicited religious push | 1 |
| 10 | Recycled trip | 1 |
| 11 | Sexless, unaffectionate | 1 |
| 12 | Negative comparison | 1 |
| 13 | Cleaning disagreement | 1 |
| 14 | Porn addiction impact | 1 |
| 15 | Porn affecting intimacy | 1 |
| 16 | Relationship on autopilot | 1 |
| 17 | Feeling used | 1 |
| 18 | Sudden breakup | 1 |
| 19 | Feeling overwhelmed | 1 |
| 20 | Girlfriend distant | 1 |

## 4. Clustering EDA

**Original themes:** 97
**Canonical themes:** 97
**Deduplication ratio:** 1.000
**Final clusters:** 14
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 141.8s
**Total posts in clusters:** 99
**Total upvotes in clusters:** 5,179

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 107.0 | 75.5% |
| Theme Expansion Llm | 107.0 | 75.5% |
| Embedding Generation | 8.4 | 5.9% |
| Kmeans Clustering | 0.9 | 0.6% |
| Cluster Naming | 25.2 | 17.8% |

### Cluster Size Stats
- Min posts: 2
- Max posts: 17
- Mean posts: 7.1

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 3 | Partner Behavior and Conflict | 17 | 17 | 2,124 | 124.9 |
| 10 | Deep Personal Emotional Struggles | 3 | 3 | 837 | 279.0 |
| 13 | Interpersonal Stress and Annoyances | 7 | 7 | 753 | 107.6 |
| 9 | Relationship Betrayal and Neglect | 10 | 10 | 381 | 38.1 |
| 6 | Partner Unsupportive & Unco | 7 | 7 | 316 | 45.1 |
| 4 | Unmet Sexual and Intimacy Needs | 12 | 14 | 264 | 18.9 |
| 2 | Partner Betrayal and Cheating | 5 | 5 | 232 | 46.4 |
| 1 | Relationship Struggles and Anxiety | 10 | 10 | 113 | 11.3 |
| 12 | Unwanted Personal Interference | 2 | 2 | 69 | 34.5 |
| 0 | Uncertain Relationship Dynamics | 8 | 8 | 54 | 6.8 |
| 8 | Unhealthy Relationship Dynamics | 5 | 5 | 14 | 2.8 |
| 7 | Unhealthy Friendship Struggles | 5 | 5 | 8 | 1.6 |
| 5 | Ghosting and Relationship Ruin | 4 | 4 | 7 | 1.8 |
| 11 | Price and Noise Issues | 2 | 2 | 7 | 3.5 |

### Theme Breakdown by Cluster

**Partner Behavior and Conflict** (17 posts, 2,124 upvotes)
  - bf lied
  - boyfriend lying
  - boyfriend wants space
  - boyfriend's disrespect
  - boyfriend's manipulation
  - boyfriend's overreaction
  - cleaning disagreement
  - excluded from grief
  - forgotten birthday effort
  - lack of commitment
  - negative comparison
  - partner's disbelief
  - porn addiction impact
  - rude in sleep
  - situationship disrespect
  - trip conflict
  - unreasonable boundaries

**Deep Personal Emotional Struggles** (3 posts, 837 upvotes)
  - girlfriend distant
  - recycled trip
  - reveal father's abuse

**Interpersonal Stress and Annoyances** (7 posts, 753 upvotes)
  - dog's bad behavior
  - feeling overwhelmed
  - gf overreaction
  - girlfriend's accusations
  - teasing causes rejection
  - unwanted food sharing
  - wife's post-sex crying

**Relationship Betrayal and Neglect** (10 posts, 381 upvotes)
  - depression's toll
  - ex-husband's exploitation
  - feeling used
  - husband's betrayal
  - husband's irresponsibility
  - husband's neglect
  - husband's selfishness
  - mother rejects housing
  - toxic relationship
  - unjust exclusion

**Partner Unsupportive & Unco** (7 posts, 316 upvotes)
  - ex holding stuff
  - fiancé unsupportive
  - ignoring preferences
  - medication non-support
  - postpone engagement
  - refusal to discuss
  - vacation resistance

**Unmet Sexual and Intimacy Needs** (14 posts, 264 upvotes)
  - lack of intimacy
  - less intense sex
  - low social battery
  - nagging girlfriends
  - no desire shown
  - no new experiences
  - porn affecting intimacy
  - sexless, unaffectionate
  - sexual dissatisfaction
  - sexual incompatibility
  - time/energy mismatch
  - unmet sexual needs

**Partner Betrayal and Cheating** (5 posts, 232 upvotes)
  - boyfriend cheated
  - cheating ex
  - financial betrayal
  - partner's betrayal
  - trapped with cheater

**Relationship Struggles and Anxiety** (10 posts, 113 upvotes)
  - communication insecurity
  - communication struggle
  - debilitating relationship anxiety
  - ending relationship kindly
  - ex feelings
  - missed experiences
  - partner's decline
  - partner's issues
  - self-love issues
  - trust broken

**Unwanted Personal Interference** (2 posts, 69 upvotes)
  - dad's spying
  - unsolicited religious push

**Uncertain Relationship Dynamics** (8 posts, 54 upvotes)
  - emotional instability
  - fear of rejection
  - friend likes bf
  - inconsistent feelings
  - lack of clarity
  - mixed signals
  - roommate phase
  - unclear intentions

**Unhealthy Relationship Dynamics** (5 posts, 14 upvotes)
  - lost attraction
  - relationship on autopilot
  - sudden breakup
  - unhealthy relationship patterns
  - unsafe, uncommitted

**Unhealthy Friendship Struggles** (5 posts, 8 upvotes)
  - friend ignoring me
  - friendship is draining
  - lost best friend
  - one-sided friendship
  - trauma from friendship

**Ghosting and Relationship Ruin** (4 posts, 7 upvotes)
  - ghosted, confused
  - ghosting behavior
  - man unavailable
  - ruined relationship

**Price and Noise Issues** (2 posts, 7 upvotes)
  - cost complaining
  - date too loud

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 48.3 |
| Parse + validation | 0.0 |
| **Total** | **48.3** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 ConvoFlow: Guided Relationship Dialogue
**Pain point:** Partners struggle with effective communication, leading to unresolved conflicts, feelings of disrespect, and a lack of support, often exacerbated by one partner's unwillingness to discuss issues.
**Target user:** Couples (M/F, M/M, F/F) experiencing communication breakdowns, frequent arguments, or difficulty addressing sensitive topics, particularly those where one partner avoids discussion.
**Confidence:** high
**Core features:** Guided conversation templates for sensitive topics, AI-powered sentiment analysis during text-based discussions, conflict resolution frameworks, agreement tracking and reminders, 'cooling off' timer for breaks.
**Revenue model:** Freemium: Basic templates and 3 agreement tracks free. Premium subscription at $9.99/month or $99/year for unlimited templates, AI sentiment analysis, advanced conflict resolution tools, and unlimited agreement tracking.
**Evidence:** 17 posts, 2,124 upvotes

### #2 DesireMap: Intimacy Explorer
**Pain point:** Couples experience sexual dissatisfaction, lack of intimacy, and difficulty communicating desires, leading to feelings of being 'sexually incompatible' or unfulfilled.
**Target user:** Couples (all orientations) experiencing a decline in intimacy, sexual incompatibility, or difficulty discussing their sexual and emotional needs openly.
**Confidence:** high
**Core features:** Anonymous individual intimacy preference quizzes, AI-generated compatibility insights and discussion points, guided intimacy exercises (communication-focused), private shared 'desire list' for partners, progress tracking for intimacy goals.
**Revenue model:** Subscription: $14.99/month or $149/year for couples, offering full access to all quizzes, insights, exercises, and sharing features. Free trial for 7 days.
**Evidence:** 14 posts, 264 upvotes

### #3 HealPath: Post-Betrayal Support
**Pain point:** Individuals are devastated by partner betrayal and cheating, struggling with emotional processing, trust issues, and the path to recovery or moving on.
**Target user:** Individuals (all genders, ages 20+) who have recently experienced or are currently dealing with partner betrayal (cheating, financial infidelity, etc.) and are seeking structured support for recovery.
**Confidence:** high
**Core features:** Structured recovery modules (e.g., 'Processing Anger,' 'Rebuilding Self-Trust'), moderated peer support groups, expert Q&A sessions (therapists, legal advisors), journaling and emotional tracking tools, personalized action plans.
**Revenue model:** Subscription: $29.99/month for full access to all modules, groups, and expert content, with a 7-day free trial. Optional premium 1:1 coaching sessions available at an additional cost.
**Evidence:** 5 posts, 232 upvotes

### #4 SignalSense: Relationship Decoder
**Pain point:** Individuals struggle with uncertainty in relationships, interpreting mixed signals, understanding 'normal' communication patterns, and navigating the early stages of romantic interest, leading to anxiety and confusion.
**Target user:** Young adults (17-30) and individuals new to dating or relationships, experiencing anxiety, confusion, or uncertainty about mixed signals, communication norms, or the intentions of others.
**Confidence:** medium
**Core features:** AI-powered analysis of user-inputted (anonymized) conversation snippets for mixed signals, guided journaling prompts for self-reflection, 'What if' scenario builder for relationship decisions, curated articles/advice on common relationship uncertainties, personalized interpretation feedback.
**Revenue model:** Freemium: Basic signal analysis (e.g., 5 analyses/month) and 3 journaling prompts free. Premium for unlimited analysis, advanced scenario building, access to expert content, and deeper AI insights at $7.99/month or $79/year.
**Evidence:** 8 posts, 54 upvotes

### #5 FriendshipFlow: Navigate & Nurture
**Pain point:** Individuals struggle with unhealthy, one-sided, or draining friendships, feeling like 'the problem' or finding it difficult to set boundaries or end friendships respectfully.
**Target user:** Individuals (all ages, but particularly young adults) struggling with platonic relationships, feeling drained by friends, or unsure how to address issues or end friendships.
**Confidence:** medium
**Core features:** Friendship health assessment quizzes, guided conversation scripts for setting boundaries, moderated peer support community, resources for healthy friendship building, tools for respectfully ending friendships.
**Revenue model:** Subscription: $5.99/month or $59/year for full access to all assessments, scripts, community forums, and resources. Basic assessment and 1 script template available for free.
**Evidence:** 5 posts, 8 upvotes

### Analysis Summary
The Reddit complaint clusters reveal a pervasive struggle with communication, trust, and emotional navigation across various types of 'love' relationships, including romantic partnerships and friendships. Users frequently express pain points related to unresolved conflicts, unmet intimacy needs, the aftermath of betrayal, and general uncertainty about relationship dynamics, highlighting a strong demand for tools that facilitate healthier interactions and personal healing.

### Data Limitations
This dataset primarily captures self-reported complaints and requests for advice, which may overrepresent negative experiences and not reflect the full spectrum of relationship dynamics. The sample size for some clusters is small, and upvote counts, while indicative of resonance, do not necessarily equate to market size or willingness to pay for a solution. Additionally, the data is text-based and lacks demographic diversity beyond age and gender mentioned in posts, limiting deeper insights into specific user segments.
