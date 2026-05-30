# Reddit Data Access Request - Answers

Copy-paste these answers into the form.

---

## What do you need assistance with?
> Data Access Request

---

## Your email address
> [YOUR COLUMBIA EMAIL HERE]

---

## Which role best describes your reason for requesting data access?
> I'm a developer

---

## What is your inquiry?
> I'm a developer and want to build a Reddit App that does not work in the Devvit ecosystem.

---

## Reddit account name
> [YOUR REDDIT USERNAME HERE]

---

## What benefit/purpose will the bot/app have for Redditors?

```
This is a non-commercial educational project for my graduate coursework at Columbia University. The app helps identify common pain points and recurring complaints within niche communities by analyzing public Reddit discussions.

Benefits to Redditors:
- Surfaces real, unaddressed problems that community members frequently discuss
- Helps aspiring entrepreneurs understand what solutions Redditors actually want
- All insights trace back to real posts (with links), amplifying genuine community voices rather than replacing them with AI-generated content
- Read-only analysis - the app does not post, comment, or interact with Reddit in any way
```

---

## Provide a detailed description of what the Bot/App will be doing on the Reddit platform.

```
This is a read-only analysis tool built for a Columbia University graduate course on Agentic AI systems.

How it works:
1. A user enters a topic or niche (e.g., "home espresso machines")
2. The app identifies relevant subreddits for that topic
3. It fetches recent public posts and comments via the Reddit API
4. An AI agent clusters complaints by theme, counts frequency, and checks if existing solutions are mentioned
5. The output is a ranked report of pain points with links to the original Reddit posts

Technical details:
- Read-only: The app only uses GET endpoints. It never posts, comments, votes, or modifies any Reddit content.
- Low volume: This is a classroom project with a single user (me). Expected usage is ~10-20 queries total over the semester.
- Caching: Results are cached locally to minimize redundant API calls. The same topic is never queried twice.
- Attribution: Every finding in the report links back to the original Reddit post.

Example use case:
I enter "mechanical keyboards" as a topic. The app finds r/MechanicalKeyboards, fetches recent posts, and returns: "Top complaint: keycap legends fading (mentioned 47 times, 2.3k total upvotes). Existing solutions mentioned: doubleshot PBT keycaps." Each finding includes links to the actual Reddit threads.
```

---

## What is missing from Devvit that prevents building on that platform?

```
Devvit is designed for apps that run within Reddit (subreddit widgets, interactive posts, moderation tools). My project is an external analysis tool that:

1. Runs outside Reddit as a standalone web application
2. Analyzes data across multiple subreddits for a given topic (not scoped to a single community)
3. Processes data with external AI services (Claude/OpenAI) for complaint clustering
4. Generates reports in a separate frontend, not within Reddit's UI

Devvit's architecture assumes the app lives inside Reddit and serves a specific subreddit. My use case is cross-subreddit, read-only research that produces external reports - which falls outside Devvit's design scope.
```

---

## Provide a link to source code or platform that will access the API.

```
https://github.com/alcidenik0pol/project-2-agentic-ai

The repository is for a Columbia University course project. I'm happy to make it public or grant access for review upon request.
```

---

## What subreddits do you intend to use the bot/app in?

```
The app dynamically identifies relevant subreddits based on user-entered topics. It does not target specific subreddits in advance.

Example subreddits that might be queried (depending on topics I explore for coursework):
- r/espresso, r/Coffee (if analyzing coffee equipment pain points)
- r/MechanicalKeyboards (if analyzing keyboard hobby pain points)
- r/homelab, r/selfhosted (if analyzing home server pain points)

The app is read-only and low-volume. I expect to query perhaps 5-10 different topic areas total over the course of the semester, with results cached to avoid repeat queries.
```

---

## If applicable, what username will you be operating this bot/app under? (optional)

```
[YOUR REDDIT USERNAME] (same as my personal account - this is a solo student project)
```

---

## Attachments (optional)

Consider attaching:
- Screenshot of your Columbia student portal/enrollment
- Course syllabus mentioning the project (if available)
- Architecture diagram of the app (optional, shows professionalism)
