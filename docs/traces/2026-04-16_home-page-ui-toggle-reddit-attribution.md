# Trace: Home Page UI — Mode Toggle & Reddit Attribution

**Date:** 2026-04-16
**Session:** Replace test mode checkbox with a styled toggle button, restructure ChatInterface layout, enhance Reddit attribution visibility.

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/components/ChatInterface.tsx` | Added `ModeToggle` component; restructured layout into 3 rows (input+button, toggle, attribution); updated Reddit text/sizing/opacity |

## Architecture

```
Before:
┌──────────────────────────────────────────────────┐
│ [Input field]              [Pan it] [☑ Test Mode] │
│                              Panned from 📡       │
└──────────────────────────────────────────────────┘

After:
┌──────────────────────────────────────────────────┐
│ [Input field]                           [Pan it]  │
│                                🟢 Scraping on     │
│                       Panned from Reddit 📡       │
└──────────────────────────────────────────────────┘
```

### Layout Structure

1. **Row 1:** Input field + Submit/Cancel button (simplified, no checkbox)
2. **Row 2:** `ModeToggle` component, right-aligned
3. **Row 3:** "Panned from Reddit" + logo, right-aligned, larger text/icon

### ModeToggle Component

- Inline component in ChatInterface.tsx (lines 13-37)
- Props: `mode`, `setMode`, `isRunning`
- States:
  - **Live (default):** Green bg/border/text, green dot indicator, label "Scraping on"
  - **Test:** Muted gray bg/border/text, gray dot indicator, label "Static data"
- Disabled during analysis (`isRunning`): opacity-50, cursor-not-allowed
- Keyboard accessible via native `<button>` element

## Design Decisions

1. **Pill-shaped button instead of iOS toggle switch.** A full toggle switch (sliding track) requires more CSS and aria attributes for accessibility. The pill button with colored indicator dot gives the same visual feedback with simpler implementation and native `<button>` semantics (keyboard, focus, disabled all free).

2. **Green for "on" state.** Conventional color for active/enabled. The muted gray for "Static data" de-emphasizes the test mode, which matches our intent: live scraping is the primary workflow.

3. **Right-aligned both toggle and attribution.** Creates visual hierarchy — the primary action (input + button) is the focal point, secondary controls recede to the right. Also avoids cluttering the input row.

4. **Reddit attribution sized up (11px→13px text, 14px→18px icon, 40%→60% opacity).** The previous sizing was nearly invisible at typical viewing distances. The new values remain subtle but legible.

5. **No separate file for ModeToggle.** Single-use component, ~25 lines. Not worth a separate file — keeps the change minimal and the import graph unchanged.

## Changes Detail

### Removed
- Checkbox `<input type="checkbox">` and its `<label>` wrapper from the main controls row
- Wrapper `<div>` around the button + checkbox group

### Added
- `ModeToggle` component (lines 13-37)
- Toggle row: `<div className="flex justify-end mt-2">` containing `<ModeToggle />`
- Updated attribution row with new text, sizing, and opacity

### Unchanged
- All state management (`query`, `mode`, `isRunning`)
- `handleSubmit` and `handleKeyDown` logic
- Input field styling and behavior
- Submit/Cancel button logic
- `onSubmit` prop interface — still passes `(query, mode)` where mode is `"test" | "live"`

## Verification Performed

- [x] TypeScript compiles with no errors (`npx tsc --noEmit`)
- [x] Toggle states: "Scraping on" (green) ↔ "Static data" (gray)
- [x] Toggle disabled during `isRunning` state
- [x] Reddit text reads "Panned from Reddit" (was "Panned from")
- [x] Reddit icon 18px (was 14px), text 13px (was 11px), opacity 60% (was 40%)
- [x] No changes to component props or external interfaces

## What Was NOT Done

- **No visual regression testing** (requires browser runtime)
- **No new CSS classes or Tailwind extensions** — all styling via existing utility classes
- **No changes to test data flow** — `mode` state still passes `"test" | "live"` to `onSubmit`
