# Trace: Reddit API Shutdown — User-Facing Banner

**Date:** 2026-05-29
**Trigger:** Reddit deprecated public JSON API endpoints (403/410). Data collection is offline pending Reddit data access request approval. Users visiting the live site would see failures with no explanation.

---

## Problem

After Reddit's API policy change (documented in `docs/traces/2026-05-29_reddit-api-shutdown-data-access-request.md`), the app's core data collection pipeline is non-functional. Any user who submits a topic query will encounter errors. There is no user-facing notice explaining the situation.

---

## Solution

Added a dismissible global banner to `MainLayout.tsx` that:

1. Informs users that data collection is temporarily offline
2. Links to Reddit's official API policy change announcement
3. Can be dismissed per-session (state resets on reload — appropriate for a temporary notice)
4. Renders on all pages, both mobile and desktop

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/components/layout/MainLayout.tsx` | Added amber warning banner below navbar |

### Changes to `MainLayout.tsx`

- Added `AlertTriangle` and `X` imports from `lucide-react` (already a project dependency)
- Added `bannerDismissed` state via `useState(false)`
- Inserted banner JSX between desktop navbar (line 96) and video player (line 97)

### Banner Design

- **Style**: Amber/yellow warning (`bg-amber-900/30`, `border-amber-700/40`, `text-amber-200`)
- **Content**: "Data collection is temporarily offline. We're redesigning our Reddit scraper following their API policy change (May 29, 2026)."
- **Link**: Opens Reddit's official announcement (`r/modnews` post) in a new tab
- **Dismiss**: X button sets `bannerDismissed = true` (component state, resets on reload)

---

## Why This Approach

| Consideration | Decision |
|---------------|----------|
| Component state vs localStorage | Component state — this is a temporary notice, not a user preference. Banner reappears on reload so returning users stay informed. |
| Global layout vs per-page | Global layout — the outage affects the entire app, not specific pages. |
| Amber/yellow vs red | Amber = "temporary service disruption." Red would imply a security or data-loss issue. |
| Inline SVG vs lucide-react | lucide-react already installed (`^0.468.0`) and used elsewhere. Consistent icon style. |

---

## Verification

- [ ] `npm run dev` compiles without errors
- [ ] Banner appears below navbar on all pages
- [ ] "API policy change" link opens Reddit post in new tab
- [ ] X button dismisses the banner for the current session
- [ ] Banner renders correctly on mobile viewport
- [ ] Banner does not push content below fold excessively

---

## Related Traces

- `docs/traces/2026-05-29_reddit-api-shutdown-data-access-request.md` — Root cause and data access request
