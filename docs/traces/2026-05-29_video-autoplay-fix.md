# Trace: Fix Video Autoplay on Page Load

**Date:** 2026-05-29
**Trigger:** Video plays audio on page load even when no workflow is active.

---

## Problem

When the page loads, the YouTube player initialized with `autoplay: 1` starts playing immediately — even if no pipeline workflow is running. The `useEffect` that pauses based on the `active` prop only fires on prop *changes*, not on mount, so it never pauses the initial autoplay.

Result: unexpected audio on page load with no user interaction.

---

## Root Cause

Two contributing factors:

1. **`autoplay: 1` in player config** — `PipelineVideoPlayer.tsx:47` unconditionally told YouTube to autoplay.
2. **`useEffect([active])` misses mount** — The play/pause effect at line 80-87 only reacts to *changes* in `active`. If `active` is `false` on mount and never changes, the effect body never runs, so the autoplay is never countered.

---

## Solution

Changed from "autoplay always, pause if inactive" to "never autoplay, play only if active".

### Changes

| Location | Change |
|----------|--------|
| `PipelineVideoPlayer.tsx:21-22` | Added `activeRef` to track current `active` value across render cycles |
| `PipelineVideoPlayer.tsx:49` | Changed `autoplay: 1` → `autoplay: 0` |
| `PipelineVideoPlayer.tsx:56-60` | Added `onReady` handler that calls `playVideo()` only if `activeRef.current` is true |

### Why `activeRef`

The `onReady` callback is a closure created once when the player initializes. Without a ref, it would capture the initial `active` value (potentially stale). `activeRef.current` always holds the latest value because it's updated synchronously on every render.

---

## Behavior After Fix

| Scenario | Before | After |
|----------|--------|-------|
| Page load, no workflow | Audio plays immediately | Video loads silently |
| Workflow starts | No change — `useEffect` calls `playVideo()` | No change — same `useEffect` |
| Workflow ends | `useEffect` calls `pauseVideo()` | No change — same `useEffect` |

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/components/PipelineVideoPlayer.tsx` | Added `activeRef`, disabled autoplay, added `onReady` handler |

---

## Related Traces

- `2026-04-16_pipeline-video-player.md` — Original video player implementation that introduced the autoplay behavior
