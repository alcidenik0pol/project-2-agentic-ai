# Workflow Report
_Generated: 2026-04-19T02:52:26.552232+00:00_

## 1. Subreddit Selection

**Topic:** artificial intelligence
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> The selected subreddits cover direct complaints about AI malfunctions, unethical design, and its impact on specific processes like recruitment and tech support. They also include broader discussions on AI's influence on the job market, various industries (gaming, music, small business), personal finance, and career development. Subreddits like 'antiwork' and 'workreform' are highly relevant for complaints regarding AI-driven job displacement and labor issues. 'Softwaregore' and 'assholedesign' are ideal for capturing complaints about poorly implemented or ethically questionable AI systems. Industry-specific subreddits like 'gamedev' and 'WeAreTheMusicMakers' are included for complaints about AI's role in content creation and its competitive implications.

### Selected Subreddits
- r/softwaregore
- r/assholedesign
- r/recruitinghell
- r/talesfromtechsupport
- r/antiwork
- r/workreform
- r/cscareerquestions
- r/gamedev
- r/entrepreneur
- r/smallbusiness
- r/careerguidance
- r/jobs
- r/personalfinance
- r/productivity
- r/WeAreTheMusicMakers
- r/freelance
- r/gaming
- r/pcgaming
- r/Steam
- r/selfhosted

## 2. Data Fetching

**Topic:** artificial intelligence
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 266.9s

### Subreddits Queried
- r/softwaregore
- r/assholedesign
- r/recruitinghell
- r/talesfromtechsupport
- r/antiwork
- r/workreform
- r/cscareerquestions
- r/gamedev
- r/entrepreneur
- r/smallbusiness
- r/careerguidance
- r/jobs
- r/personalfinance
- r/productivity
- r/WeAreTheMusicMakers
- r/freelance
- r/gaming
- r/pcgaming
- r/Steam
- r/selfhosted

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-flash
**Processing time:** 36.7s
**Throughput:** 2.7 posts/s
**Unique themes:** 97

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 348.1 | 100.0 calls, avg 3.481s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 100
- Non-complaints: 0

### Intensity Distribution
- high: 52
- medium: 38
- low: 10

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | Software glitch | 3 |
| 2 | Software gore | 2 |
| 3 | Software broken | 1 |
| 4 | Time bug | 1 |
| 5 | Broken ad | 1 |
| 6 | Pinterest broken | 1 |
| 7 | Display error | 1 |
| 8 | Random date text | 1 |
| 9 | No preferences | 1 |
| 10 | Incorrect information | 1 |
| 11 | Missing hint | 1 |
| 12 | Android TV sucks | 1 |
| 13 | Software bug | 1 |
| 14 | Terminal failed | 1 |
| 15 | Equalizer broken | 1 |
| 16 | Wrong clock options | 1 |
| 17 | Login paradox | 1 |
| 18 | Camera glitch | 1 |
| 19 | Squished time | 1 |
| 20 | Not complete | 1 |

## 4. Clustering EDA

**Original themes:** 97
**Canonical themes:** 97
**Deduplication ratio:** 1.000
**Final clusters:** 8
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 108.9s
**Total posts in clusters:** 100
**Total upvotes in clusters:** 170,153

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 85.1 | 78.1% |
| Theme Expansion Llm | 85.0 | 78.1% |
| Embedding Generation | 8.7 | 8.0% |
| Kmeans Clustering | 0.8 | 0.7% |
| Cluster Naming | 14.2 | 13.0% |

### Cluster Size Stats
- Min posts: 4
- Max posts: 20
- Mean posts: 12.5

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 6 | Intrusive and excessive ads | 17 | 17 | 66,330 | 3901.8 |
| 5 | Deceptive Charges and Practices | 7 | 7 | 26,170 | 3738.6 |
| 0 | Forced Actions and Restrictions | 17 | 17 | 23,329 | 1372.3 |
| 4 | Poor Streaming Experience | 4 | 4 | 21,220 | 5305.0 |
| 1 | System and Feature Malfunctions | 19 | 19 | 14,702 | 773.8 |
| 7 | Unfair Process Requirements | 4 | 4 | 14,096 | 3524.0 |
| 3 | Software Bugs and Glitches | 17 | 20 | 3,615 | 180.8 |
| 2 | Poor Interface and Usability | 12 | 12 | 691 | 57.6 |

### Theme Breakdown by Cluster

**Intrusive and excessive ads** (17 posts, 66,330 upvotes)
  - ads block reflection
  - annoying ads
  - broken ad
  - cookie consent dark patterns
  - fish in scratcher
  - forced ads
  - forced video fullscreen
  - intrusive ads
  - keyboard ad overlay
  - maps getting ads
  - planned obsolescence
  - pop-up redundancy
  - scanner ads
  - unclosable pop-up
  - unskippable ad
  - unskippable long ads
  - unwanted contact

**Deceptive Charges and Practices** (7 posts, 26,170 upvotes)
  - dark pattern tipping
  - forced tip
  - forced tipping
  - hidden cancel button
  - hidden fee
  - undisclosed fee
  - unpayable tiny bill

**Forced Actions and Restrictions** (17 posts, 23,329 upvotes)
  - ai privacy breach
  - app blocking
  - bank app gambling
  - blocking ineffective
  - excessive verification
  - fastboot restriction
  - forced data collection
  - forced launcher download
  - forced price hike
  - forced sign-in
  - forced unreviewed update
  - id requirement unsafe
  - login paradox
  - mandatory data sharing
  - mental health scam
  - no standalone brick
  - opt-out billing

**Poor Streaming Experience** (4 posts, 21,220 upvotes)
  - android tv sucks
  - forced tv ads
  - locked 720p quality
  - netflix anger

**System and Feature Malfunctions** (19 posts, 14,702 upvotes)
  - apps inaccessible
  - bad autocorrect
  - bad prediction
  - display error
  - empty offer
  - forced ai spying
  - forced copilot
  - glitched title
  - incorrect information
  - large system storage
  - missing hint
  - no content
  - notification spam
  - ram speed error
  - random date text
  - tedious notification settings
  - terminal failed
  - translator broken
  - unwanted dnd notifications

**Unfair Process Requirements** (4 posts, 14,096 upvotes)
  - experience catch-22
  - mandatory interview
  - required drugs
  - unfair pay

**Software Bugs and Glitches** (20 posts, 3,615 upvotes)
  - blank screen
  - camera glitch
  - equalizer broken
  - icon color issue
  - inaccurate step count
  - os glitch
  - pinterest broken
  - privacy settings reset
  - redemption broken
  - screen cropped
  - software broken
  - software bug
  - software glitch
  - software gore
  - time bug
  - ui duplicated
  - visual glitch

**Poor Interface and Usability** (12 posts, 691 upvotes)
  - asshole design
  - bad web design
  - confusing menu
  - gibberish name
  - invalid date
  - no preferences
  - not complete
  - squished time
  - system bloated
  - taskbar overflow
  - unclear graph labels
  - wrong clock options

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 51.6 |
| Parse + validation | 0.0 |
| **Total** | **51.6** |
| **Model:** gcloud:gemini-2.5-flash | |

**Total ideas generated:** 5

### #1 AI Data Guardian
**Pain point:** Users are frustrated by companies automatically using their data to train AI models and forcing unwanted AI features with difficult-to-manage opt-out processes or deceptive billing.
**Target user:** Privacy-conscious individuals, small business owners, and users concerned about their data being used for AI training without clear consent.
**Confidence:** high
**Core features:** Browser extension for policy scanning, Centralized dashboard for opt-out management, Automated opt-out assistant, Billing monitor for AI-related charges
**Revenue model:** Freemium: Free for basic scanning and manual opt-out guidance. Premium subscription: $5/month or $50/year for automated opt-out assistance, billing monitoring, and advanced privacy reports.
**Evidence:** 17 posts, 23,329 upvotes

### #2 AI ToggleMaster
**Pain point:** Users are frustrated by AI features (like Copilot, Meta AI) being forced into their software, often displacing core functionality, being difficult to disable, or feeling intrusive ('spying').
**Target user:** Power users, privacy advocates, and professionals who rely on productivity software but are frustrated by intrusive or performance-impacting AI integrations.
**Confidence:** high
**Core features:** AI feature scanner, Centralized toggle dashboard, Forced AI blocker, Resource monitor for AI components
**Revenue model:** One-time purchase: $29.99 for the desktop application. Optional annual updates/support subscription: $9.99/year.
**Evidence:** 19 posts, 14,702 upvotes

### #3 AI Quality Guard
**Pain point:** Developers and product managers struggle to consistently monitor the real-world performance and accuracy of their AI-powered features (e.g., autocorrect, translation, prediction engines), leading to user frustration and negative reviews.
**Target user:** Software development teams, AI/ML engineers, and product managers responsible for AI-powered features in consumer or enterprise applications.
**Confidence:** medium
**Core features:** SDK/API integration for data collection, AI-powered error detection and categorization, Performance dashboards with accuracy trends, Alerting system for performance degradation
**Revenue model:** Subscription-based for development teams. Tiered pricing based on data volume (e.g., number of AI interactions monitored per month) and number of users/projects: Starter ($99/month for up to 100k interactions), Pro ($499/month for up to 1M interactions), Enterprise (Custom pricing).
**Evidence:** 19 posts, 14,702 upvotes

### #4 BioConsent Hub
**Pain point:** Users are increasingly required to provide biometric data (e.g., face scans, fingerprints) for access to services, often without clear understanding of how this data is stored, used, or protected, leading to significant privacy concerns.
**Target user:** Individuals concerned about biometric privacy, users of services requiring face/fingerprint ID, and privacy-conscious consumers.
**Confidence:** high
**Core features:** Biometric consent registry, Policy analyzer for biometric clauses, Revocation assistant for data deletion requests, Secure encrypted vault for documentation
**Revenue model:** Freemium: Free for tracking up to 3 services. Premium subscription: $3/month or $30/year for unlimited service tracking, automated policy updates, and priority support for revocation requests.
**Evidence:** 17 posts, 23,329 upvotes

### #5 Deceptive UI Shield
**Pain point:** Users are constantly exposed to dark patterns, some potentially enhanced by AI, that trick them into unwanted actions like signing up for subscriptions, sharing data, or accepting hidden charges, including 'opt-out billing' for AI features.
**Target user:** Everyday internet users, online shoppers, and anyone frustrated by manipulative website designs and deceptive practices, especially those related to AI features.
**Confidence:** high
**Core features:** Real-time dark pattern detection, AI feature opt-out flagging, User guidance and warnings, Community-driven pattern library
**Revenue model:** Freemium: Free for basic detection and warnings. Premium subscription: $4/month or $40/year for advanced blocking features, automated opt-out attempts, and priority access to new pattern definitions.
**Evidence:** 17 posts, 23,329 upvotes

### Analysis Summary
The complaints highlight a strong user desire for greater control, transparency, and reliability regarding AI features, particularly concerning data privacy, forced integrations, and performance accuracy. Users are frustrated by AI being imposed without consent, difficult to disable, or performing poorly, indicating a market need for tools that empower users and developers to manage AI more effectively and ethically.

### Data Limitations
This dataset primarily captures consumer-facing frustrations and software glitches, offering limited insight into enterprise-level AI challenges or specific technical implementation pain points for AI developers. The 'artificial intelligence' mentions are often from the user's perspective of being affected by AI, rather than deep technical issues within AI development itself.
