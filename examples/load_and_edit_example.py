"""
load_and_edit_example.py
========================
Demonstrates how to:

1. Save a GraffitiPlot figure to a .gfp file
2. Load it back and display in an interactive window
3. Programmatically edit the loaded figure

Run from the terminal:
    python examples/load_and_edit_example.py

Or, once the file is saved, re-open it at any time with:
    gfp-open experiment.gfp          # interactive shell
    python -c "import graffiti_plot; graffiti_plot.view('experiment.gfp')"
"""

import numpy as np
import matplotlib.pyplot as plt
import graffiti_plot

# ── Step 1: Create and save a figure ─────────────────────────────────────────

t = np.linspace(0, 10e-9, 2000)  # 10 ns

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
fig.suptitle("Fiber Optics – Pulse Propagation")

# Subplot 1: clean input pulse
input_pulse = np.exp(-((t - 3e-9) / 0.5e-9) ** 2) * 5e-3
ax1.plot(t, input_pulse, label="Input Pulse", color="dodgerblue", linewidth=2)
ax1.set_title("Transmitter")
ax1.set_ylabel("Optical Power")
ax1.set_si_units(x="s", y="W")
ax1.legend()

# Subplot 2: dispersed + noisy output
rng = np.random.default_rng(42)
noise = rng.normal(0, 1.5e-4, len(t))
output = np.exp(-((t - 6e-9) / 1.2e-9) ** 2) * 1.5e-3 + noise
ax2.plot(t, output, label="Output (after 50 km)", color="darkorange", linewidth=1.5)
ax2.set_title("Receiver")
ax2.set_xlabel("Time")
ax2.set_ylabel("Optical Power")
ax2.set_si_units(x="s", y="W")
ax2.legend()

plt.tight_layout()

# Save to .gfp (all data + styling embedded in one file)
save_path = "experiment.gfp"
graffiti_plot.save(fig, save_path)
print(f"Saved to '{save_path}'")

plt.close(fig)

# ── Step 2: Load it back and show in interactive window ───────────────────────

# This opens the graph AND drops you into a Python shell where
# fig, axes, ax, plt, np are all available for live editing.
#
# Try in the shell:
#   axes[0].set_title("My New Title")
#   fig.canvas.draw_idle()
#
#   axes[1].set_yscale('log')
#   fig.canvas.draw_idle()
#
#   import graffiti_plot
#   graffiti_plot.save(fig, "experiment_v2.gfp")   # save edits

graffiti_plot.view(save_path)
