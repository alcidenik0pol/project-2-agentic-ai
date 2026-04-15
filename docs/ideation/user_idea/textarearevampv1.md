Problems:

The textarea and the Cancel button + Test Mode checkbox are not vertically aligned to each other's center
"Cancel" button takes too much visual weight for what should be a secondary action (it's bright red, which typically signals destructive/primary)
"Test Mode" checkbox label group is crammed with no breathing room from the button
The "Powered by Reddit" label floats awkwardly below, disconnected from the control group


Instructions for the engineer:
1. Container layout
Make the top row a single flex row with align-items: center and gap: 12px. All three elements (textarea, Cancel button, Test Mode group) should sit on the same horizontal axis, baseline-aligned to center.
2. Textarea
Remove any fixed height forcing it taller than a single-line input. Use min-height: 48px and let it grow. Set flex: 1 so it takes all remaining space.
3. Cancel button
This should NOT be red. Red is reserved for destructive irreversible actions. Change it to a neutral secondary style (e.g. outlined or ghost, border: 1px solid #555, background transparent, white/grey text). Same height as the textarea row, height: 48px, padding: 0 20px.
4. Test Mode checkbox group
Wrap the checkbox and its label in a <label> element with display: flex; align-items: center; gap: 6px; white-space: nowrap. Do not let it wrap or collapse. Give it min-width: fit-content.
5. "Powered by Reddit" label
Move it inside the container row, right-aligned, either as a small position: absolute bottom-right of the textarea, or tucked as the last item in the flex row at reduced opacity. It should not occupy its own line and orphan below.
Resulting flex structure:
[textarea flex:1] [Cancel button] [☐ Test Mode] [Powered by Reddit]
All on one line, vertically centered, no wrapping.