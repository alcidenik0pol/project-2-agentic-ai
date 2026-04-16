# Workflow Report
_Generated: 2026-04-16T16:00:18.985977+00:00_

## 1. Subreddit Selection

**Topic:** gaming
**Method:** llm
**Fallback used:** False
**Subreddits available:** 75
**Subreddits selected:** 20

### LLM Reasoning
> Selected subreddits include direct gaming communities, subreddits for game development and specific platforms, general complaint forums, and communities discussing the impact of gaming on personal life, relationships, and mental well-being.

### Selected Subreddits
- r/gaming
- r/pcgaming
- r/Steam
- r/gamedev
- r/patientgamers
- r/indiegaming
- r/softwaregore
- r/assholedesign
- r/mildlyinfuriating
- r/talesfromtechsupport
- r/amitheasshole
- r/relationship_advice
- r/relationships
- r/offmychest
- r/trueoffmychest
- r/parenting
- r/dating
- r/personalfinance
- r/productivity
- r/ADHD

## 2. Data Fetching

**Topic:** gaming
**Mode:** live
**Total posts:** 100
**Subreddits queried:** 20
**Time:** 240.6s

### Subreddits Queried
- r/gaming
- r/pcgaming
- r/Steam
- r/gamedev
- r/patientgamers
- r/indiegaming
- r/softwaregore
- r/assholedesign
- r/mildlyinfuriating
- r/talesfromtechsupport
- r/amitheasshole
- r/relationship_advice
- r/relationships
- r/offmychest
- r/trueoffmychest
- r/parenting
- r/dating
- r/personalfinance
- r/productivity
- r/ADHD

## 3. Classification EDA

**Total posts:** 100
**Successful:** 100
**Failed:** 0
**Success rate:** 100.0%
**Model:** gcloud:gemini-2.5-pro
**Processing time:** 70.7s
**Throughput:** 1.4 posts/s
**Unique themes:** 71

### Timing Breakdown

| Step | Duration (s) | Notes |
|------|-------------|-------|
| LLM calls | 657.7 | 100.0 calls, avg 6.577s/call |
| Serialization/overhead | 0.0 | Rate limiting delays + serialization |

### Complaint vs Non-Complaint
- Complaints: 36
- Non-complaints: 64

### Intensity Distribution
- high: 6
- medium: 22
- low: 72

### Top 20 Themes

| # | Theme | Count |
|---|-------|-------|
| 1 | No complaint | 28 |
| 2 | Game delayed | 2 |
| 3 | Too expensive | 2 |
| 4 | Director praises games | 1 |
| 5 | 3DS finds | 1 |
| 6 | Game character customization | 1 |
| 7 | Constant demands | 1 |
| 8 | Game sales | 1 |
| 9 | Lost game | 1 |
| 10 | PSN Down | 1 |
| 11 | Changing game opinion | 1 |
| 12 | Time constraints | 1 |
| 13 | Game ideas | 1 |
| 14 | Nuisance enemies | 1 |
| 15 | Small active fandoms | 1 |
| 16 | Performance issues | 1 |
| 17 | Bad icon | 1 |
| 18 | Loss of freedom | 1 |
| 19 | EGS user retention | 1 |
| 20 | Controller not working | 1 |

## 4. Clustering EDA

**Original themes:** 34
**Canonical themes:** 34
**Deduplication ratio:** 1.000
**Final clusters:** 14
**Embedding model:** text-embedding-004
**Provider:** gcloud
**Processing time:** 73.7s
**Total posts in clusters:** 36
**Total upvotes in clusters:** 72,704

### Timing Breakdown

| Step | Duration (s) | % of Total |
|------|-------------|------------|
| Theme Expansion | 42.6 | 57.9% |
| Theme Expansion Llm | 42.6 | 57.8% |
| Embedding Generation | 3.4 | 4.6% |
| Kmeans Clustering | 0.3 | 0.4% |
| Cluster Naming | 27.3 | 37.1% |

### Cluster Size Stats
- Min posts: 1
- Max posts: 6
- Mean posts: 2.6

### Cluster Details

| # | Name | Themes | Posts | Upvotes | Avg Upvotes |
|---|------|--------|-------|---------|-------------|
| 1 | Poor EGS User Retention | 2 | 2 | 17,454 | 8727.0 |
| 2 | article misinformation | 5 | 6 | 14,104 | 2350.7 |
| 12 | data breach threat | 1 | 1 | 9,028 | 9028.0 |
| 4 | ea games unfinished | 6 | 6 | 8,639 | 1439.8 |
| 13 | lack monster games | 2 | 2 | 6,840 | 3420.0 |
| 6 | absurd requirement | 1 | 1 | 6,153 | 6153.0 |
| 7 | bad icon | 2 | 2 | 3,970 | 1985.0 |
| 8 | Game development and availability | 3 | 4 | 2,681 | 670.2 |
| 3 | Difficult Setup Experience | 1 | 1 | 1,604 | 1604.0 |
| 0 | flawed original trailer | 2 | 2 | 977 | 488.5 |
| 9 | unrealistic self-assessment | 1 | 1 | 596 | 596.0 |
| 5 | Game Progress Loss & Burden | 4 | 4 | 408 | 102.0 |
| 11 | quiz too hard | 1 | 1 | 172 | 172.0 |
| 10 | Game Performance and Access | 3 | 3 | 78 | 26.0 |

### Theme Breakdown by Cluster

**Poor EGS User Retention** (2 posts, 17,454 upvotes)
  - egs user retention
  - poor egs retention

**article misinformation** (6 posts, 14,104 upvotes)
  - article misinformation
  - destroying videogames
  - memory price increase
  - psn down
  - too expensive

**data breach threat** (1 posts, 9,028 upvotes)
  - data breach threat

**ea games unfinished** (6 posts, 8,639 upvotes)
  - ea games unfinished
  - game mischaracterization
  - games too violent
  - loss of freedom
  - no build quickswap
  - time constraints

**lack monster games** (2 posts, 6,840 upvotes)
  - lack monster games
  - nuisance enemies

**absurd requirement** (1 posts, 6,153 upvotes)
  - absurd requirement

**bad icon** (2 posts, 3,970 upvotes)
  - bad icon
  - controller not working

**Game development and availability** (4 posts, 2,681 upvotes)
  - disney delists games
  - game delayed
  - slow development

**Difficult Setup Experience** (1 posts, 1,604 upvotes)
  - setup difficulty

**flawed original trailer** (2 posts, 977 upvotes)
  - flawed original trailer
  - game series decline

**unrealistic self-assessment** (1 posts, 596 upvotes)
  - unrealistic self-assessment

**Game Progress Loss & Burden** (4 posts, 408 upvotes)
  - constant demands
  - game state concern
  - game waste guilt
  - lost game

**quiz too hard** (1 posts, 172 upvotes)
  - quiz too hard

**Game Performance and Access** (3 posts, 78 upvotes)
  - new games struggle
  - no pc version
  - performance issues

## 5. Hypothesis Summary

### Timing Breakdown

| Step | Duration (s) |
|------|-------------|
| Table preparation | 0.0 |
| LLM generation | 75.2 |
| Parse + validation | 0.0 |
| **Total** | **75.2** |
| **Model:** gcloud:gemini-2.5-pro | |

**Total ideas generated:** 5

### #1 Epic Storefront Enhancer
**Pain point:** Users claim free games on the Epic Games Store but immediately return to Steam, implying a lack of compelling features on the EGS platform.
**Target user:** PC gamers who claim free games on EGS but primarily use Steam for its community features.
**Confidence:** high
**Core features:** Steam review integration, HowLongToBeat playtime data, ProtonDB compatibility scores, Price history chart
**Revenue model:** Freemium: Core data injection is free. A Pro subscription ($3/mo) adds advanced features like price drop email alerts, cross-platform library management, and custom filters.
**Evidence:** 2 posts, 17,454 upvotes

### #2 Delist Watch
**Pain point:** Gamers are frustrated and concerned when publishers permanently remove games from digital storefronts, preventing future purchases.
**Target user:** Digital game collectors, game preservation advocates, and any gamer who fears missing out on buying a game before it disappears forever.
**Confidence:** high
**Core features:** Steam/GOG wishlist synchronization, Email and push notification alerts for at-risk games, Public dashboard of recently delisted games, Historical delisting database for research
**Revenue model:** Freemium: Free to monitor up to 20 games from a wishlist. Pro subscription ($4/mo or $40/yr) for unlimited game monitoring, SMS alerts, and access to advanced historical data.
**Evidence:** 4 posts, 2,681 upvotes

### #3 Steam Deck RetroLoader
**Pain point:** It is overly complicated and difficult to install older, non-Steam games (especially from physical media) onto modern gaming hardware like the Steam Deck.
**Target user:** Steam Deck owners and Linux gamers who want to play their existing library of older PC games without complex manual configuration.
**Confidence:** medium
**Core features:** Game-specific installation script generation, Community-sourced compatibility configurations, Automated dependency management (Proton/Wine), One-click 'Add to Steam' shortcut creation
**Revenue model:** One-time purchase: $19.99 for the full application with lifetime updates. A free version allows for the installation of up to 3 games.
**Evidence:** 1 posts, 1,604 upvotes

### #4 Weekend Warrior Planner
**Pain point:** Time-constrained gamers are unsure how to budget their limited playing time to complete games, leading to questions like 'Is it possible to beat both RE 2 storylines in a weekend?'.
**Target user:** Adult gamers (25-45) with jobs, families, and other commitments who want to make the most of their limited gaming sessions.
**Confidence:** medium
**Core features:** Integration with HowLongToBeat API, Personalized schedule generation, Main Story vs. Completionist tracks, Progress tracking checklist
**Revenue model:** Free to use. Monetized via affiliate links on game store pages. A potential Pro tier ($2/mo) could offer calendar integration and multi-game planning.
**Evidence:** 6 posts, 8,639 upvotes

### #5 LowSpec Index
**Pain point:** Gamers with low-performance PCs struggle to find games that will run well on their specific hardware.
**Target user:** Gamers using non-gaming laptops, older desktops, or other budget hardware.
**Confidence:** low
**Core features:** Filter games by specific GPU/CPU, Real-world performance benchmarks submitted by users, 'Plays like X but runs on a potato' recommendations, Price comparison across stores
**Revenue model:** Free for users, monetized through affiliate links on game store pages. Anonymized performance data could be a potential B2B revenue stream for market research.
**Evidence:** 3 posts, 78 upvotes

### Analysis Summary
The most significant frustrations revolve around the user experience of game platforms and the lifecycle of games themselves. Users are vocal about feature gaps in newer storefronts like EGS (vs. Steam) and show significant anxiety about games being delisted or becoming inaccessible. These represent clear opportunities for third-party tools that enhance existing platforms or provide valuable meta-services like monitoring and planning.

### Data Limitations
This dataset is a small snapshot of Reddit conversations and may not be representative of all gamers. Upvote counts can be influenced by post timing and subreddit culture, not just the severity of the problem. Furthermore, the clusters often group diverse themes, so a high upvote count for a cluster might not apply to every individual pain point within it.
