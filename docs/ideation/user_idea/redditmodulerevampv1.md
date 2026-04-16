The public API surface is minimal on purpose:
jsawait RedditRL.fire();    // call before every Reddit fetch — blocks if limit hit
RedditRL.reset();         // call on 429 or manual window expiry
RedditRL.getStatus();     // { used, remaining, queued, resetIn }
One thing worth flagging: the queue uses a Promise-based slot system, but the _resolve hook in the current code is wired for the demo flow. In production you'd want flushQueue() to actually call req._resolve() after incrementing used, then let your caller proceed to fetch(). The integration comment at the bottom of the file spells out the exact swap.
Also, Reddit's API responses include X-Ratelimit-Remaining and X-Ratelimit-Reset headers — you should sync your local used and windowStart against those rather than trusting purely client-side counting, since other tabs or server-side calls share the same quota.