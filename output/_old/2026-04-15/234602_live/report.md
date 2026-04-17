# Reddit Complaint Analysis Report

**Query:** find game ideas
**Mode:** test
**Provider:** gcloud (gemini-2.5-pro)
**Agents:** orchestrator -> analyst -> hypothesis
**Tool calls:** 5
**Generated:** 2026-04-15T23:54:23.736694

---

Here are the top 5 business ideas generated from the Reddit complaint data:

---

### **1. Digital Shelf Guardian**

*   **Pain Point:** Publishers are delisting games or shutting down servers, making games people paid for unplayable, with one post stating 'Ubisoft Wants Gamers To Destroy All Copies of A Game Once It Goes Offline'.
*   **Solution Description:** A dashboard that connects to a user's game libraries (Steam, Epic, GOG, etc.) via API. It continuously monitors the status of every game they own. If a publisher announces a server shutdown or a game is delisted, the user receives an immediate email alert with links to community resources, such as fan-run servers, preservation guides, or offline patches.
*   **Core Features:**
    *   Steam/Epic/GOG library integration
    *   Real-time game status monitoring (Live, At Risk, Delisted)
    *   Automated email alerts for status changes
    *   Curated database of community preservation resources
    *   Watchlist for un-owned games
*   **Revenue Model:** Freemium. Free: Monitor up to 50 games from one platform. Pro ($4/month): Unlimited games, multi-platform sync, instant SMS alerts, access to advanced preservation guides.
*   **First User Step:** User authenticates their Steam account. Within 30 seconds, their dashboard populates with their game library, automatically flagging any games that are already delisted or have announced shutdowns, like 'The Crew'.
*   **Target User:** Digital game collectors and long-time PC gamers with large libraries who are concerned about losing access to their purchases.
*   **Confidence:** High

---

### **2. FirstHour.gg**

*   **Pain Point:** Complex games are 'terrible at onboarding new players,' often overwhelming them and causing them to quit before they can get invested.
*   **Solution Description:** A website featuring curated, interactive 'First Hour' guides for popular but complex games. Instead of a dense wiki, it provides a simple, linear checklist for the first 60-90 minutes of gameplay. Each step includes a short text description ('Go to The Tower and speak to Zavala'), an optional 15-second video clip showing the action, and a 'What to Ignore' section to reduce overwhelm.
*   **Core Features:**
    *   Game-specific interactive checklists
    *   Embedded short video clips for each step
    *   Community-voted 'What to Ignore' tips
    *   Progress saving for returning users
    *   Mobile-friendly second-screen experience
*   **Revenue Model:** Ad-supported (non-intrusive banner ads). Premium guides created in partnership with content creators could be offered for a one-time fee of $1.99, with a revenue share.
*   **First User Step:** A user searches for 'Destiny 2' on the site. They immediately see a 'Start Your First Hour' button and are taken to a step-by-step guide, with the first step being 'Complete the 'A Guardian Rises' intro mission.'
*   **Target User:** New players trying to get into popular, long-running games like MMOs (Destiny 2, Warframe) or complex RPGs who feel overwhelmed by choice.
*   **Confidence:** High

---

### **3. PixelPricer**

*   **Pain Point:** Gamers are frustrated with high game prices, such as paying '$80 for games' or seeing a '3 year old, used game going for $59.99,' and want to know if they're getting good value for their money.
*   **Solution Description:** A game price comparison website that calculates a 'Value Score' for any given game. When a user searches for a game, the results page shows current prices across Steam, Epic, GOG, and console stores. Alongside the price, it displays a 1-100 Value Score calculated from the current price, historical low price, Metacritic rating, and 'HowLongToBeat' gameplay hours.
*   **Core Features:**
    *   Multi-store price tracking
    *   Historical price charts
    *   'Value Score' algorithm
    *   Integration with HowLongToBeat and Metacritic APIs
    *   Email alerts for price drops and when a game hits a target 'Value Score'
*   **Revenue Model:** Affiliate links on store purchase buttons. A Premium tier ($3/month) offers unlimited watchlist items, custom Value Score alerts, and an ad-free experience.
*   **First User Step:** User types 'The Last of Us Part II' into the search bar. The results page instantly loads, showing GameStop's price next to a low Value Score (e.g., 35/100) and the PlayStation Store's sale price next to a high Value Score (e.g., 85/100).
*   **Target User:** Budget-conscious gamers and backlog builders who want to maximize the value of their spending and avoid overpaying.
*   **Confidence:** High

---

### **4. GenAI Guard**

*   **Pain Point:** Gamers and game developers are skeptical of generative AI in games and want transparency, with many developers using 'AI free' as a sales pitch and workers wanting 'GenAI Disclosures'.
*   **Solution Description:** A browser extension for Chrome and Firefox that adds a small, clear badge next to a game's title on store pages like Steam and Epic Games Store. The badge indicates the game's AI status: 'Verified Human-Made', 'Contains GenAI', or 'Unknown'. Clicking the badge opens a pop-up with evidence, such as links to developer statements, news articles, or community-submitted proof.
*   **Core Features:**
    *   Automated badges on Steam/Epic store pages
    *   Community evidence submission and voting system
    *   Detailed evidence pop-up on click
    *   Watchlist for upcoming games' AI status
    *   Filtering store pages to hide games with GenAI
*   **Revenue Model:** Freemium. The extension is free to use. A 'Pro' version ($2/month) allows users to filter their Steam discovery queue to hide GenAI games and get alerts on their watchlist.
*   **First User Step:** User installs the browser extension. They navigate to the Steam page for 'Clair Obscur: Expedition 33', and a 'Contains GenAI' badge appears next to the title. They click it and see a link to the article about its disqualification from an awards show.
*   **Target User:** Indie game enthusiasts and developers who are ethically or artistically opposed to the use of generative AI in game development and want to make informed purchasing decisions.
*   **Confidence:** Medium

---

### **5. SubSlasher**

*   **Pain Point:** Users are 'scrambling to cancel' gaming subscriptions like Xbox Game Pass after price hikes, but the cancellation pages are crashing or are intentionally difficult to find.
*   **Solution Description:** A simple web app for managing gaming subscriptions. Users manually add their subscriptions (Game Pass, PS Plus, etc.). The app tracks renewal dates and sends reminders. Its key feature is a 'Cancellation Kit' for each service, which includes a direct deep-link to the exact cancellation page, a 3-step visual guide on what to click, and a pre-written cancellation request email template.
*   **Core Features:**
    *   Subscription tracking dashboard
    *   Renewal date reminders
    *   'Cancellation Kit' with direct links and visual guides
    *   Cost aggregation to show total monthly gaming spend
    *   Price hike news alerts
*   **Revenue Model:** Freemium. Free to track up to 3 subscriptions. Pro ($1.99/month) for unlimited subscriptions, access to all Cancellation Kits, and price hike alerts.
*   **First User Step:** User signs up and clicks 'Add Subscription'. They select 'Xbox Game Pass' from a dropdown, enter their monthly cost, and it appears on their dashboard. They then click the 'Cancellation Kit' button and see a direct link to the Microsoft account services page.
*   **Target User:** Gamers who use multiple subscription services and are frustrated by price hikes and intentionally obscure cancellation processes.
*   **Confidence:** Medium

---
