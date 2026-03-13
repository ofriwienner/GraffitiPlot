# GraffitiPlot — Test Plan

Run all tests with:
```bash
cd /path/to/GraffitiPlot
python examples/plot_example.py
```

Each section below describes one feature, how to trigger it, and what to verify.

---

## 1. Enable / Disable Toggle

**How to test:**
```python
import graffiti_plot
import matplotlib.pyplot as plt

# Default: ON
print(graffiti_plot.is_enabled())   # True
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
plt.show()
# → Modebar buttons visible at the bottom; zoom/pan/cursors work

# Disable
graffiti_plot.disable()
print(graffiti_plot.is_enabled())   # False
fig2, ax2 = plt.subplots()
ax2.plot([1, 2, 3], [4, 5, 6])
plt.show()
# → Plain matplotlib figure; no modebar, no interactivity

# Re-enable
graffiti_plot.enable()
fig3, ax3 = plt.subplots()
ax3.plot([1, 2, 3], [4, 5, 6])
plt.show()
# → Modebar returns; all features active again
```

**Pass criteria:**
- [ ] `is_enabled()` returns `True` on import, before any call
- [ ] After `disable()`, new figures have no modebar and no graffiti key bindings
- [ ] Figures created before `disable()` are unaffected (keep their modebar)
- [ ] After `enable()`, new figures have the full modebar again
- [ ] `disable()` / `enable()` can be toggled multiple times without error

---

## 2. Modebar Layout — Bottom Bar Below Axis Labels

**How to test:**
Open `examples/plot_example.py` (uses `plt.tight_layout()` and two subplots).

**Pass criteria:**
- [ ] Modebar buttons appear at the very bottom of the figure window
- [ ] Footer timestamp (if enabled) appears above the modebar
- [ ] Bottom subplot's X-axis label is fully visible above the footer
- [ ] No visual overlap between the modebar and any axis label or tick
- [ ] Resizing the figure window does not cause overlap to reappear
- [ ] Works with a single subplot as well as 2+ subplots

---

## 3. Modebar — Active Button Visual State

**How to test:**
Open any figure and click the **Grid**, **Hover**, **Log Y**, etc. buttons.

**Pass criteria:**
- [ ] Inactive buttons: gray text, white background, light-gray border
- [ ] Active buttons: blue bold text, light-blue (`#e8f4fd`) background, blue border
- [ ] State visually updates immediately on every click
- [ ] Keyboard shortcuts (G, H, L, K, X, A) also update the button visuals
- [ ] After `disable()` + `enable()`, new figures respect the same styling

---

## 4. Help Dialog (`?` Button)

**How to test:**
Click the **`?`** button at the far right of the modebar.

**Pass criteria:**
- [ ] A small window titled "graffiti-plot — Help" opens
- [ ] Window lists all keyboard shortcuts: G, L, K, A, H, X, F, `[`, `]`, C / Esc
- [ ] Window lists all mouse controls: left-drag, middle-drag, scroll, dbl-click, click
- [ ] "Close" button closes the dialog
- [ ] Closing the dialog does not affect the figure
- [ ] Dialog can be opened and closed multiple times without error

---

## 5. CSV Export (`⬇ Export` Button)

**How to test:**
1. Open `examples/plot_example.py` (two traces visible)
2. Click the **`⬇ Export`** button at the far left of the modebar
3. A save-file dialog appears — choose a path and save

**Pass criteria:**
- [ ] File dialog opens when the button is clicked
- [ ] Cancelling the dialog does nothing (no file written, no error)
- [ ] Saved CSV contains a header row with timestamp
- [ ] Each visible trace has a `# <trace name>` comment, then `x,y` header, then data rows
- [ ] Hidden traces (toggled off via legend click) are **not** exported
- [ ] Fit curves (dashed `Fit:` lines) are included if visible
- [ ] Works with subplots: each subplot's traces are exported with `(subplot N)` suffix
- [ ] Re-zooming and exporting exports **all** data, not just the current view
  *(note: export currently writes full line data, not just the visible X range)*

---

## 6. Zoom History — Back / Forward

**How to test:**
1. Open any figure with plotted data
2. Drag-zoom in several times (3–4 zoom operations)
3. Press `[` or click **← Back** to undo each zoom step
4. Press `]` or click **→ Fwd** to redo a zoom step

**Pass criteria:**
- [ ] Each drag-zoom pushes a state onto the history stack
- [ ] Each scroll-zoom pushes a state onto the history stack
- [ ] `[` key / **← Back** button restores the previous xlim + ylim
- [ ] `]` key / **→ Fwd** button re-applies a previously undone zoom
- [ ] **← Back** button is visually active (blue) when history is available
- [ ] **→ Fwd** button is visually active (blue) when redo stack is available
- [ ] After a fresh zoom, the redo stack clears (can no longer go forward)
- [ ] Panning (middle-mouse drag) does **not** push to zoom history
- [ ] Double-click reset does **not** use the zoom history stacks
- [ ] Zoom history is per-subplot (each axes has its own stacks)

---

## 7. Curve Fit Window — Parameter Uncertainty

**How to test:**
1. Plot data that fits a known model (e.g., the Gaussian in `plot_example.py`)
2. Press **F** or click **Fit (F)** in the modebar
3. Select a trace and model, then click **Execute Fit**

**Pass criteria:**
- [ ] Fit window opens at size 950×600 (wider than before)
- [ ] Result label shows `param = value ± uncertainty` for each parameter
- [ ] Uncertainty values are formatted to 2 significant figures
- [ ] Generated code snippet includes `perr = np.sqrt(np.diag(pcov))`
- [ ] Generated code unpacks parameters by name (`a, mu, sigma = popt`)
- [ ] If fit fails (bad guesses), an inline error message appears in red — no crash
- [ ] If scipy is missing, the window shows a readable error label instead of closing silently
- [ ] Fitted curve is overlaid on the plot as a dashed line after a successful fit

---

## 8. Scope Cursors — Existing Behaviour (Regression)

Verify that the cursor feature still works correctly after all refactoring.

**How to test:**
Click on a plotted line to place C1, then click again to place C2.

**Pass criteria:**
- [ ] First click places crimson cursor lines (vertical + horizontal)
- [ ] Second click places teal cursor lines
- [ ] Annotation box shows C1, C2 coordinates and Δx, Δy with SI formatting
- [ ] Third click replaces C1 and removes C2
- [ ] `C` key and **Clear (C)** button remove all cursors
- [ ] Floating preview crosshair follows the mouse and snaps to the nearest data point
- [ ] Double-click resets the view and clears all cursors

---

## 9. Legend Interactivity — Regression

**How to test:**
Plot multiple labelled lines and call `ax.legend()`.

**Pass criteria:**
- [ ] Single-click a legend entry → that line toggles visibility (dimmed handle = hidden)
- [ ] Double-click a legend entry → isolates that line (all others hidden)
- [ ] Double-click the isolated line again → all lines become visible
- [ ] Visibility state is preserved across zoom/pan operations

---

## 10. SI Units — Regression

**How to test:**
```python
ax.set_si_units(x='s', y='W')
```

**Pass criteria:**
- [ ] X-axis ticks display with SI prefixes (e.g., `1 ns`, `500 ps`)
- [ ] Y-axis ticks display with SI prefixes (e.g., `1 mW`, `500 µW`)
- [ ] Hover tooltip shows SI-formatted values
- [ ] Scope cursor annotation shows SI-formatted values
- [ ] Log X / Log Y toggling does not break SI formatting on return to linear

---

## Notes

- All tests should be run with both a **single subplot** and **multiple subplots**
- Test on the default matplotlib backend for your OS (TkAgg / Qt5Agg / MacOSX)
- When `disable()` is active, none of the features in sections 3–10 should appear on new figures
