# PRD: China Tech Intelligence Newsletter

---

## Why This Is Worth Building

Most US founders and investors are flying blind on China. The people who should care — early-stage VCs, consumer founders, operators building in competitive markets — are reading TechCrunch and missing the country that is 3 to 5 years ahead on consumer behavior, super app mechanics, logistics density, and AI application layers.

The gap is not interest. It is access. Chinese tech media is in Mandarin, fragmented across WeChat public accounts, paywalled platforms, and social feeds that require being on the ground to navigate. The few English-language bridges (Technode, KrAsia) are digestible but thin — they translate the news, not the pattern underneath it.

The core product insight is that this access problem is now solvable without a translation pipeline. LLMs read Chinese natively. There is no intermediate step where a human reads Mandarin and converts it to English — the model ingests the source directly and produces English output. This means primary Chinese sources (36kr, Huxiu, WeChat public accounts) can be processed at the same speed and cost as English ones. The bottleneck shifts entirely to judgment: which signals matter, which patterns are real, which ideas travel.

This newsletter does not translate news. It applies venture pattern recognition to Chinese tech signals and produces a replication thesis: what is working in China, why it works structurally, and what a US founder would need to build the analog. It is written by someone with 7 years of venture experience who has been tracking Southeast Asian and Chinese tech markets for years, from primary sources.

It is not public. It is not for everyone. That is intentional.

---

## Project Goals

1. Maintain active visibility with a curated audience of founders and investors without transactional networking
2. Produce a weekly artifact that demonstrates pattern recognition, not just information access
3. Build a proof-of-work corpus that compounds over time and can support consulting, fund roles, or co-founder conversations
4. Keep operational overhead low enough that the author spends time thinking, not processing

---

## Non-Goals

- Mass audience growth
- SEO or content marketing
- Charging subscribers (at least in v1)
- Video or audio formats
- Covering Southeast Asia (prior newsletter covered this; this is China-focused)
- Opinion or commentary without evidential grounding

---

## Audience

**Primary:** 50 to 100 people, invitation or referral only. No public subscribe button.

**Profile:**
- Early-stage VCs (pre-seed to Series B) with consumer, fintech, or SaaS focus
- Founders building in markets where China has a structural lead (payments, logistics, social commerce, AI applications)
- Operators at growth-stage companies who run competitive intelligence or strategy

**What they have in common:** They are China-curious but cannot read the sources. They trust pattern recognition over hot takes. They forward things when the insight is genuine.

**Explicitly excluded:** Journalists, policy people, generalist tech readers, anyone who would be satisfied by KrAsia.

---

## Product Description

A weekly email. Invitation only. Typically one to two ideas per issue. No filler.

Each idea follows the pattern recognition framework (see Editorial Framework below). The author only writes about something when a genuine pattern has been observed across multiple data points — not because something is interesting, novel, or trending.

---

## Editorial Framework: Pattern Recognition vs Opinion

The distinction that governs every editorial decision:

**Opinion:** "I think this is interesting." No evidentiary basis. Author-dependent. Not reproducible.

**Pattern recognition:** "I have seen this mechanic N times across different companies and markets. Here is what they have in common structurally. Here is what it predicts."

### The Three Gates

Every item must pass all three before it is written up:

**Gate 1 — Evidence of recurrence**

You need at least two data points, ideally three, that show the same underlying mechanic appearing independently within the past 6 to 12 months. Not the same company iterating. Different companies, same solution to the same problem. The time window matters: a pattern from three years ago may no longer be relevant, and a pattern that took three years to accumulate is not a current signal.

Ask yourself: have I seen this mechanic appear independently 2+ times within the past 6 to 12 months? Where? What happened?

If you cannot answer that, it is news. Move on.

**Gate 2 — Structural explanation**

Why does this mechanic work in China specifically? What combination of infrastructure, regulation, consumer behavior, or market structure makes it viable there?

This is the most important gate because it forces you to understand the conditions, not just the pattern. And it is what tells you whether the US replication is realistic or fantasy.

Common structural factors in China worth mapping:
- Fragmented offline retail vs consolidated
- WeChat as distribution layer
- Lower labor costs enabling human-in-the-loop models
- Regulatory arbitrage windows before enforcement
- Super app behavior vs single-purpose app behavior

If the mechanic only works because of a China-specific condition that does not exist in the US, say that explicitly. That is still valuable — it is telling your reader not to waste time.

**Gate 3 — The translation question**

What would need to be true in the US for this to work? Not "could someone do this" but specifically:
- Which US structural condition substitutes for the Chinese one
- Which customer segment is the analog
- What is the wedge — where does it start before it scales

If you cannot answer this concretely, you do not have a replication thesis yet. You have an observation. Keep thinking or drop it.

### Output Format Per Issue

Every piece follows this skeleton. If any section cannot be written with specificity, the idea is dropped.

**The pattern** — I have seen this mechanic X times, here is the thread across them. At least two instances named and dated.

**Why it works there** — the structural conditions in China that enable it (regulatory, behavioral, infrastructural, distributional).

**Why now** — what changed that made this pattern emerge or accelerate.

**The US translation** — what the analog looks like, where it starts, what the bet is. Named segment, named wedge.

**The open question** — what the author does not know yet, what would change the thesis.

The open question is what separates pattern recognition from opinion. Opinions do not have open questions. Genuine analysis does.

---

## Data Sources and Infrastructure

### Tier 1: Automated

| Source | Method | Cadence | Coverage |
|---|---|---|---|
| 36kr | RSSHub `/36kr/:category` | Daily pull | Startups, VC, consumer tech |
| Huxiu | RSSHub `/huxiu/channel/:id` | Daily pull | Analysis, longer-form |
| WeChat (tracked accounts) | RSSHub via Sogou search | Daily pull, last ~10 articles per account | 20 to 30 curated public accounts |

**Infrastructure:** Self-hosted RSSHub instance on a $5/month VPS. One-time Docker setup. Stable, no ongoing maintenance.

### Tier 2: Manual Curation

The author follows 20 to 30 WeChat public accounts directly on Android. Discovery happens through normal reading. When an article is worth processing:

1. Copy link or open in browser within WeChat
2. Share URL to processing queue (Telegram bot or Airtable form)
3. Claude API processes overnight: translate, summarize, score for US replication potential (1 to 10) with one-line reason

This manual layer is not a failure of automation. It is where editorial judgment lives. No tool selects which accounts to follow.

#### WeChat Account Selection Criteria

Initial accounts are selected based on:
- **Follower count:** Minimum 50,000 followers (indicates established publication)
- **Publication frequency:** At least 2-3 articles per week (ensures active signal flow)
- **Sector relevance:** Focus on consumer tech, fintech, AI applications, logistics, or startup/VC coverage
- **Source quality:** Original reporting or analysis preferred over aggregation

#### Account Evaluation Process

**Adding new accounts:**
1. Discover through reading, referrals, or cross-references in existing accounts
2. Monitor for 2-4 weeks before adding to tracked list
3. Evaluate signal-to-noise ratio: does this account consistently produce articles that score 6+ on replication potential?
4. Add to RSSHub tracking if accessible; otherwise add to manual Android reading list

**Pruning inactive or low-signal accounts:**
- Review tracked accounts quarterly
- Remove accounts that have not published in 60+ days
- Remove accounts where <10% of articles score 4+ on replication potential over a 3-month period
- Target range remains 20-30 accounts to maintain manageable reading load

### Tier 3: Processing Pipeline

```
RSSHub feeds (daily)
    → filter by category tags
    → Claude API per article: translate + 3-sentence summary + replication score + reason
    → Airtable or Notion editorial queue
    → author reviews 2x per week
    → selects 1 to 2 items that pass the three gates
    → writes the issue
    → sends via Substack (private/invite-only setting)
```

**Estimated cost:** $10 to 20/month (VPS + API calls). No third-party data services.

#### Replication Scoring Rubric

Every processed article receives a replication potential score from 1 to 10, with a required one-line reason. The rubric:

| Score | Meaning | Characteristics |
|-------|---------|-----------------|
| **1-3** | Low replication potential | China-specific infrastructure dependency (e.g., WeChat-only mechanics), regulatory arbitrage with no US analog, or consumer behavior deeply tied to Chinese cultural context. No viable US wedge. |
| **4-6** | Moderate replication potential | Pattern has structural parallels in the US but requires significant adaptation. May have unclear customer segment or wedge. Worth tracking but not ready for issue write-up. |
| **7-10** | High replication potential | Clear structural analog exists in US, identifiable customer segment, and plausible wedge. The pattern is actionable for a US founder today. Higher scores (9-10) indicate urgency or strong supporting evidence. |

**One-line reason requirement:** Every score must include a single sentence explaining the key factor. Examples:
- "3: Relies entirely on Alipay integration with no US payment equivalent"
- "6: Interesting social commerce mechanic but unclear which US platform would serve as distribution layer"
- "8: Clear wedge in independent creator monetization, TikTok Shop creates structural analog"

### WeChat Discovery Constraint

WeChat's closed ecosystem means programmatic account discovery is not possible without authentication. The Sogou RSS route gives partial coverage of followed accounts. For accounts the author reads natively on Android:

- Google Tap to Translate handles in-app reading triage
- One manual step (copy link → queue) per article worth saving
- This friction is acceptable and by design: it forces a minimum quality bar before anything enters the pipeline

---

## Compounding Module: Quarterly Sector Reports

Individual issues are weekly artifacts. But the corpus they build over time has a second use.

Every article that enters the pipeline — whether published in an issue or not — is tagged by sector at the processing stage. The Claude API prompt includes a sector classification alongside the summary and replication score. Sectors are kept broad initially: robotics, social commerce, fintech, logistics, AI applications, consumer hardware, enterprise SaaS.

After one quarter, all items tagged to a given sector are compiled automatically into a sector report. This is not a manually written document. It is a structured output from the accumulated pipeline data: all the patterns observed, all the structural conditions noted, all the open questions that remain open, and a summary of which signals appeared more than once (indicating a real trend vs a one-off).

The output is a 3 to 5 page PDF or markdown document per sector, produced quarterly, distributed to the same private list.

**Why this matters:** A reader who has been following the newsletter for a quarter gets confirmation of what they half-noticed across issues. A new reader who joins gets access to the back-catalogue in condensed form. And the author has a body of work that is legible as a research product, not just a newsletter — something that can be shared in a VC meeting or attached to a consulting proposal.

**What the stacking mechanism requires technically:**
- Every pipeline item tagged with sector at processing time (one additional field in the Claude API prompt, costs nothing)
- Items stored in Airtable or Notion with that tag, regardless of whether they were published
- A quarterly script or prompt that pulls all items by sector and generates the report structure
- The author reviews and adds a one-paragraph synthesis at the top

The quarterly report is the proof-of-work artifact that the weekly issue cannot be. Issues show judgment in real time. Reports show pattern recognition over time. Both are needed.

---

This newsletter does not optimize for subscriber count, open rate, or revenue. It optimizes for inbound.

**Primary KPI:** Unsolicited contact from people the author wants to work with — replies, introductions, "I read your newsletter" as a meeting opener from someone the author did not send it to directly.

**Secondary KPI:** Forward rate. If an issue travels beyond the original send list without the author initiating it, the content is working.

**Negative signal:** High open rates with zero replies. Means the content is being consumed passively, which is the digest trap the previous newsletter fell into.

**Review cadence:** Qualitative, monthly. Is anything interesting happening as a result of sending this?

---

## Distribution

**Platform:** Substack, set to private. No public archive. No SEO.

**List management:** Manual. The author controls who is on the list. Getting on the list requires either a direct invitation or a referral from an existing reader. There is no public subscribe link.

**Initial list:** The author's existing network from venture, Columbia, and the previous newsletter — filtered to people who fit the audience profile. Target: 40 to 60 people at launch.

**Growth:** Only through reader referrals. No growth hacking. If a reader wants to add someone, they ask the author. This keeps the list legible — the author knows roughly who every reader is.

---

## Constraints and Risks

**Editorial discipline risk:** The three-gate framework is only as good as the author's willingness to drop ideas that don't pass. The failure mode is publishing because an issue is due, not because a genuine pattern was identified. Mitigation: no fixed cadence obligation. Skip a week if nothing passes the gates.

**Source reliability risk:** RSSHub routes for 36kr and Huxiu can break when sites update their structure. Mitigation: self-hosted instance makes debugging faster; Sogou as fallback for WeChat; the manual layer provides redundancy.

**WeChat coverage risk:** The Sogou RSS route is limited and potentially fragile. Mitigation: treat automated WeChat coverage as supplementary, not primary. The author's own reading on the platform is the primary WeChat input.

**Audience drift risk:** Keeping a private list small and curated requires active management. Mitigation: the author reviews the list quarterly and removes people who have become irrelevant to the goal.

---

## Version 1 Scope

**In scope:**
- RSSHub self-hosted setup for 36kr and Huxiu
- Telegram bot or Airtable form for manual article queuing
- Claude API processing pipeline (translate, summarize, score)
- Substack private list setup
- Initial send list curation (40 to 60 people)
- First 4 issues to establish format and editorial voice

**Out of scope for v1:**
- Bilibili or Douyin video source ingestion
- Automated WeChat account discovery
- Any monetization mechanism
- Public-facing web presence
- Analytics beyond manual tracking

---

## Success at 6 Months

At least three instances of inbound contact from people the author did not initiate with, where the newsletter was the reason they reached out. These contacts should be with people who fit the target audience profile: early-stage VCs, relevant founders, or operators in competitive markets.

If this has not happened by month 6, the content is not differentiated enough or the list is wrong. Both are fixable. Neither requires changing the infrastructure.

---

## Appendix: Claude API Prompt Example

The following is a template prompt for processing individual articles through the Claude API. This prompt is sent with each article's full text (after extraction from RSS or URL).

```
You are processing a Chinese tech article for a US-focused venture intelligence newsletter.

TASK: Analyze the following article and return structured output.

ARTICLE TEXT:
[article text here]

OUTPUT FORMAT (return as JSON):
{
  "title_translated": "English translation of the article title",
  "summary": "3-sentence summary of the article's key points in English",
  "sector": "One of: robotics, social_commerce, fintech, logistics, ai_applications, consumer_hardware, enterprise_saas, other",
  "sector_notes": "If 'other', specify the sector",
  "replication_score": <integer 1-10>,
  "replication_reason": "One sentence explaining the key factor in this score",
  "key_companies_mentioned": ["Company A", "Company B"],
  "structural_factors": ["List any China-specific conditions mentioned or implied"],
  "potential_us_analog": "If score >= 6, describe the potential US equivalent; if score < 6, explain why"
}

SCORING GUIDANCE:
- 1-3: China-specific with no viable US replication path
- 4-6: Possible replication but significant barriers or unclear wedge
- 7-10: Clear US replication opportunity with identifiable segment and wedge
```

**Notes on prompt usage:**
- Article text should be extracted and cleaned before sending (strip navigation, ads, etc.)
- For paywalled content, use the excerpt available and note limitations in output
- Sector classification can be expanded over time as patterns emerge
- The prompt can be iterated based on scoring consistency across processed articles
