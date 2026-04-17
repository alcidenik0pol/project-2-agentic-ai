# Trace: Pipeline YouTube Video Player

**Date:** 2026-04-16
**Trigger:** Pipeline runs take several minutes. Users stare at a progress bar and log lines with nothing else to engage with.

---

## Problem

During the `running` phase, the UI shows:

- Step indicators (Collector → Analyst → Hypothesis)
- A progress bar
- Current activity text
- Recent log lines

There's a several-minute wait with no interactive or entertaining content. Users navigate away and may not return to see results.

---

## Solution

Added a YouTube video player that appears below the progress panel during pipeline execution. A random video from a curated list autoplays (muted) on loop while the pipeline runs. The player disappears when the pipeline completes or fails.

### Key design choices

1. **Video list in a standalone JSON file** (`frontend/config/videos.json`) — easy to edit without touching TypeScript. Add/remove video ID strings from the array.
2. **Random selection per run** — one video picked at random on mount, stays for the whole run.
3. **YouTube IFrame Player API** — loaded dynamically, no external NPM dependency needed.
4. **Autoplay + loop** — video starts muted (browser autoplay policy) and loops via the `playlist` parameter + `onStateChange` fallback.
5. **16:9 responsive container** — `paddingBottom: 56.25%` technique, consistent with card styling.

---

## Implementation

### Files created

| File | Purpose |
|------|---------|
| `frontend/config/videos.json` | Array of YouTube video IDs (user-editable) |
| `frontend/components/PipelineVideoPlayer.tsx` | Player component |

### Files modified

| File | Change |
|------|--------|
| `frontend/app/page.tsx` | Import `PipelineVideoPlayer` and `videos.json`; render between progress panel and collector pacing info when `phase === "running"` |

### PipelineVideoPlayer component

- Accepts `videoIds` prop (array of strings)
- `useEffect` picks a random index once on mount
- Second `useEffect` loads the YouTube IFrame API script (only once) and creates a `YT.Player` instance
- Cleanup destroys the player on unmount
- Returns `null` if no videos configured or no selection yet

### Integration guard

```tsx
{phase === "running" && PIPELINE_VIDEOS.length > 0 && (
  <PipelineVideoPlayer videoIds={PIPELINE_VIDEOS} />
)}
```

The `length > 0` check means the player is invisible until videos are added to the JSON file — zero-config default.

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/config/videos.json` | **NEW**: JSON array of 7 YouTube video IDs |
| `frontend/components/PipelineVideoPlayer.tsx` | **NEW**: YouTube IFrame player with autoplay/loop |
| `frontend/app/page.tsx` | Added imports and conditional render block |

---

## Design Decisions

- **JSON over TS for config**: A `.json` file requires no TypeScript syntax knowledge to edit — just add/remove quoted strings from the array. Imported natively by Next.js.
- **Dynamic script injection over NPM package**: The YouTube IFrame API is loaded via a `<script>` tag injected into `<head>`. No `react-youtube` or similar dependency to maintain.
- **`onYouTubeIframeAPIReady` global callback**: The YouTube API calls this function when ready. We assign it before injecting the script, and call it directly if the API was already loaded (e.g., hot reload).
- **`id="yt-player"` div**: The YouTube API replaces this div with an `<iframe>`. The `ref` is kept for future extensibility but the API targets the DOM ID directly.
- **Placement below logs, above collector pacing**: Users see the progress bar and latest logs first (operational), then the video (entertainment), then the collector pacing (operational detail).

---

## Related Traces

- `2026-04-14_fastapi-nextjs-frontend.md` — Original frontend setup where the running phase layout was established
- `2026-04-16_reddit-pacing-visual-tracker.md` — Collector pacing component that appears below the video player
