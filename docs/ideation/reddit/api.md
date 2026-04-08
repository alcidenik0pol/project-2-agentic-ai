Free: 1000 API requests per 10 minutes with OAuth; 100 per 10 minutes without. Note this is for your whole API key, not per-end-user. So if you made an app/website used by a thousand people, they would all be sharing the 1000 requests per 10 minutes, which adds up quickly.
Paid: requires Reddit to explicitly grant you access, which happens rarely. If granted, it’s $0.24 per 1000 API calls, unless it changed recently.

---

The honest solutions
Option 1: Cache aggressively
Don't re-fetch Reddit for the same niche twice. Store results, refresh once a day max. Most users searching "productivity apps" get the same cached analysis. This stretches your API budget dramatically and is actually the right architecture anyway.
Option 2: Pre-compute popular niches
Run the analysis nightly on 50-100 common niches. Users browsing those get instant results. Only live API calls happen for novel queries. This is how every real data product works.
Option 3: Don't build a live query product
Build a weekly digest instead. You run the scraper on a schedule, not on user request. Zero concurrency problem.