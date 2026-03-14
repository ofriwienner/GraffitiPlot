"""
custom_fits_example.py — Demonstrates how to use a custom fit library with GraffitiPlot.

Steps:
  1. Create a file (e.g. my_custom_fits.py) with functions decorated by @register_fit.
  2. Import graffiti_plot first, then import your custom fits file.
  3. The custom fits will automatically appear alongside the built-in models
     in the Fit window (press F or click the "Fit" button).

Try pressing F to open the Fit window — you should see Power Law, Damped Sine,
and Logistic listed in the sidebar in addition to the built-in models.
"""

import graffiti_plot          # Must be imported first to set up the library
import my_custom_fits         # Importing this registers Power Law, Damped Sine, Logistic

import matplotlib.pyplot as plt
import numpy as np

np.random.seed(42)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# ==========================================
# Subplot 1: Power Law data
# ==========================================
x1 = np.linspace(0.5, 10, 80)
y1 = 2.5 * x1**1.7 + np.random.normal(0, 1.5, len(x1))

ax1.plot(x1, y1, 'o', label='Measured (Power Law)', color='royalblue', markersize=4)
ax1.set_title("Power Law Data  —  try fitting with 'Power Law' in the Fit window (F)")
ax1.set_xlabel("x")
ax1.set_ylabel("y")
ax1.legend()

# ==========================================
# Subplot 2: Damped Sine data
# ==========================================
x2 = np.linspace(0, 10, 300)
y2 = 3.0 * np.sin(2.0 * x2 + 0.5) * np.exp(-x2 / 4.0) + np.random.normal(0, 0.1, len(x2))

ax2.plot(x2, y2, label='Measured (Damped Sine)', color='darkorange', linewidth=1.5)
ax2.set_title("Damped Sine Data  —  try fitting with 'Damped Sine' in the Fit window (F)")
ax2.set_xlabel("x")
ax2.set_ylabel("y")
ax2.legend()

plt.tight_layout()

# PRO TIP: Press F (or click the Fit button) to open the Fit window.
# Your custom fits (Power Law, Damped Sine, Logistic) appear alongside built-ins!
plt.show()
