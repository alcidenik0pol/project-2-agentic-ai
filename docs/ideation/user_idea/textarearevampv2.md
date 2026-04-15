
---

**Issue 1: Textarea is too tall and misaligned**
The textarea is roughly 2x the height of the button, so nothing aligns. It should be a single-line input (`<input type="text">`), not a `<textarea>`. If multiline is required, cap it at `min-height: 48px` and vertically center the placeholder text. The button and checkbox group must share the same `48px` height.

**Issue 2: "Powered by Reddit" is inline with Test Mode**
It reads as one run-on label: "Test Mode Powered by Reddit". Separate it visually. Either move it outside the control row entirely (small muted text below the whole bar, right-aligned), or add a clear visual divider and reduce its font size to ~11px with lower opacity (~40%).

**Issue 3: Cancel button color is wrong**
It's now a dark/neutral style but still labeled "Cancel" with heavy presence. If the page is in an active running state, "Cancel" is the primary action and should stand out, but with a danger-appropriate red or at least a more distinct color so it doesn't blend into the dark background. Right now it's nearly invisible against the dark card.

**Issue 4: The entire top bar has no container/card treatment**
The textarea and controls float on a raw dark background with no grouping. Wrap the entire row in a card with `border-radius: 8px`, a subtle border (`1px solid rgba(255,255,255,0.1)`), and `padding: 12px 16px`. This visually groups the input area and separates it from the pipeline steps below.

**Issue 5: No submit/run button**
There is no primary action button to actually trigger analysis. "Cancel" should never be the only button. There needs to be an "Analyze" or "Run" button as the primary CTA, styled prominently (solid accent color), with Cancel as secondary next to it.

---

**Target structure in one line:**

```
[card wrapper padding:12px 16px]
  [input flex:1 height:48px] [Analyze button primary] [Cancel button ghost] [☐ Test Mode]
  [Powered by Reddit - bottom right of card, muted, 11px]
```
