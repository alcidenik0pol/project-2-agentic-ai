# Reddit Complaint Analysis Report

**Query:** find game ideas
**Mode:** test
**Provider:** gcloud (gemini-2.5-pro)
**Agents:** orchestrator -> analyst -> hypothesis
**Tool calls:** 5
**Generated:** 2026-04-15T23:39:37.228141

---

Here are the top 5 business ideas generated from the complaint data:

---

### **1. Sunset Sentinel**

*   **Pain Point:** Gamers are losing access to games they paid for when publishers shut down servers, as seen with complaints like 'Ubisoft Wants Gamers To Destroy All Copies of A Game Once It Goes Offline'.
*   **Product Description:** A web service that tracks game server shutdown announcements. Users follow games in their library, and the service sends an email or push notification weeks or months before a game becomes unplayable. The dashboard shows a 'sunset date' for each tracked game. For each sunsetting game, we host a dedicated community forum for users to share methods for personal data archival, discuss private server projects, and preserve community history.
*   **Target User:** Digital game collectors and players of online-only or live-service games who have invested significant time and money into their libraries.
*   **Evidence:** This idea is supported by the "Publisher/Developer Negative Actions" cluster, with 14 posts and 107,334 upvotes, highlighting user frustration with actions taken by game publishers and developers.
*   **Confidence Level:** High
    *   **Core Features:**
        *   Game shutdown date tracking database
        *   User-followed game list
        *   Email/Push notification alerts for shutdowns
        *   Community forums for preservation efforts
        *   Public API for shutdown data
    *   **Revenue Model:** Freemium. Free: Track up to 10 games with email alerts. Pro ($3/mo): Unlimited game tracking, push notifications, access to advanced archival guides, and a vote on which games get dedicated preservation support.
    *   **First User Step:** User signs up and is prompted to connect their Steam account or manually add games. They search for 'The Crew', add it to their watchlist, and immediately see its status as 'Offline' with a link to community discussions on the shutdown.

---

### **2. PricePerPlay.io**

*   **Pain Point:** Gamers feel new games are overpriced for the content they offer, stating 'No Way Im Paying 80$ For Games When There Are Better Games With More Content That Came Out For Less'.
*   **Product Description:** A browser extension that injects a 'Value Score' widget onto major game store pages (Steam, PSN, Xbox). The widget displays the game's average playtime (from HowLongToBeat), its historical lowest price, and calculates the current 'cost per hour of gameplay'. It includes a chart of the game's price history to help users decide if they should buy now or wait for a sale.
*   **Target User:** Budget-conscious gamers and backlog-builders who want to maximize the value of their spending and avoid buyer's remorse on expensive new titles.
*   **Evidence:** This idea is supported by the "High Gaming Costs" cluster, with 8 posts and 101,620 upvotes, pointing to concerns about the expense associated with gaming.
*   **Confidence Level:** High
    *   **Core Features:**
        *   Browser extension for Steam/PSN/Xbox
        *   Cost-per-hour calculation
        *   Historical price tracking chart
        *   Average playtime data integration
        *   Sale notification watchlist
    *   **Revenue Model:** Free for users. Monetization through affiliate links on 'buy' buttons and partnerships with key-seller sites. Potential for a 'Pro' version ($1/mo) that offers cross-platform wishlist syncing and more advanced analytics.
    *   **First User Step:** User installs the Chrome extension. They browse to a new $70 game on the Steam store. A widget automatically appears below the price, showing: 'Current Value: $4.67/hr (15hr avg). Best Value: $1.33/hr (at historical low of $20). Add to Waitlist for price drop alert.'

---

### **3. Onboard.gg**

*   **Pain Point:** Players struggle with complex games that have poor onboarding, sometimes 'accidentally played the wrong way for hours before realizing it'.
*   **Product Description:** A platform for creating and sharing concise, visual 'First Hour' guides for complex games. Unlike dense wikis, guides on Onboard.gg use a standardized, step-by-step format with screenshots and GIFs to explain crucial early-game choices, mechanics to master, and common new-player traps to avoid. The top-voted, spoiler-free guide for each game is surfaced for new players looking for essential starting tips without wading through long videos.
*   **Target User:** New players starting complex MMOs, RPGs, or strategy games (e.g., Destiny 2, Path of Exile, Crusader Kings) who feel overwhelmed by walls of text or long video tutorials.
*   **Evidence:** This idea is supported by the "Confusing User Experience" cluster, with 3 posts and 29,285 upvotes, highlighting difficulties with game interfaces or usability.
*   **Confidence Level:** High
    *   **Core Features:**
        *   Standardized visual guide creator
        *   Community voting and ranking system
        *   Spoiler-tagging functionality
        *   Game-specific quick-start pages
        *   Search by 'common mistakes' or 'best starting path'
    *   **Revenue Model:** Free to use. Revenue from non-intrusive display ads. Potential for a 'Creator's Program' where popular guide-makers can get a share of ad revenue or receive tips, encouraging high-quality content.
    *   **First User Step:** User searches for 'Destiny 2'. The top result is a guide titled 'Your First 3 Hours in the Cosmodrome'. The first step says 'IGNORE the main quest for 20 mins. Go to the Tower first and pick up these specific bounties to level up faster. Here's a GIF showing you where.'

---

### **4. Mechanic Matcher**

*   **Pain Point:** Gamers are tired of misleading genres and repetitive gameplay formulas, often feeling disappointed that a game they were looking forward to is unoriginal or not what they expected.
*   **Product Description:** A game discovery engine that focuses on specific gameplay mechanics instead of broad genres. Users can search for games by including mechanics they love (e.g., 'deep crafting system', 'satisfying parry') and excluding mechanics they hate (e.g., 'procedurally generated fetch quests', 'unskippable cutscenes'). The results show games ranked by their 'mechanic match' score, with user reviews that specifically mention the queried mechanics.
*   **Target User:** Experienced gamers who know what specific gameplay loops they enjoy and are frustrated with generic marketing and genre tags when trying to find new games.
*   **Evidence:** This idea is supported by the "Unsatisfying and Repetitive Gameplay" cluster, with 14 posts and 215,350 upvotes, indicating strong dissatisfaction with game mechanics and replayability.
*   **Confidence Level:** Medium
    *   **Core Features:**
        *   Mechanic-based search engine (include/exclude tags)
        *   Community-sourced mechanic tagging
        *   User reviews filterable by mechanic
        *   'Gameplay DNA' comparison between two games
        *   'Surprise Me' feature based on liked mechanics
    *   **Revenue Model:** Freemium. Free search and discovery. A 'Pro' tier ($4/mo) could offer unlimited saved searches, personalized recommendations based on play history (via Steam integration), and alerts for new games that match complex mechanic profiles.
    *   **First User Step:** User lands on the site. They type 'Love: player-driven economy, complex skill trees' and 'Hate: forced PvP, timed missions'. The site returns a list including 'Eve Online' and 'Path of Exile' at the top, while explicitly filtering out games like 'The Division'.

---

### **5. GamePass Guardian**

*   **Pain Point:** Cancelling gaming subscriptions is intentionally difficult, and pages can crash during mass cancellation events after price hikes, trapping users in subscriptions they no longer want.
*   **Product Description:** A subscription management service that issues single-purpose virtual credit cards for each of your gaming subscriptions (Game Pass, PS Plus, etc.). From a central dashboard, you can pause, unpause, or set spending limits on any subscription with a single click, effectively cancelling the service by cutting off payment without ever needing to visit the provider's confusing cancellation page. It also allows setting up 'trial cards' that automatically decline after one month.
*   **Target User:** Gamers who subscribe to multiple services (Game Pass, PS Plus, Ubisoft+, etc.) and want a simple, powerful way to manage costs and avoid cancellation 'dark patterns'.
*   **Evidence:** This idea is supported by the "Expensive and difficult cancellation" cluster, with 2 posts and 22,733 upvotes, suggesting problems with cancelling subscriptions or services.
*   **Confidence Level:** Medium
    *   **Core Features:**
        *   One-click virtual card generation
        *   Centralized dashboard of all gaming subscriptions
        *   'Freeze Card' button for instant cancellation
        *   Monthly spending limits per subscription
        *   Auto-expiring cards for free trials
    *   **Revenue Model:** Subscription. $5/month for unlimited virtual cards and management. This is a premium service for users who value convenience and control over their recurring gaming expenses.
    *   **First User Step:** User signs up and clicks 'Add Subscription'. They name it 'Xbox Game Pass' and the service generates a unique Visa card number. The user is instructed to use this new card number on the Xbox website. The subscription now appears on their GamePass Guardian dashboard with a 'Freeze' button.

---
