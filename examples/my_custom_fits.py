"""
my_custom_fits.py — Example custom fit library for GraffitiPlot.

Users create a file like this and import it before plt.show().
Each function decorated with @register_fit will automatically appear
in the GraffitiPlot Fit window.

Use hidden=True to register a function without showing it in the UI.
"""

import numpy as np
from graffiti_plot import register_fit


@register_fit(
    name='Power Law',
    param_names=['a', 'n'],
    default_guesses=[1.0, 2.0],
    equation_string='a * x**n'
)
def power_law(x, a, n):
    return a * x**n


@register_fit(
    name='Damped Sine',
    param_names=['a', 'b', 'c', 'tau'],
    default_guesses=[1.0, 1.0, 0.0, 1.0],
    equation_string='a * np.sin(b * x + c) * np.exp(-x / tau)'
)
def damped_sine(x, a, b, c, tau):
    return a * np.sin(b * x + c) * np.exp(-x / tau)


@register_fit(
    name='Logistic',
    param_names=['L', 'k', 'x0'],
    default_guesses=[1.0, 1.0, 0.0],
    equation_string='L / (1 + np.exp(-k * (x - x0)))'
)
def logistic(x, L, k, x0):
    return L / (1 + np.exp(-k * (x - x0)))


# hidden=True: registered internally but will NOT appear in the Fit UI.
# Useful for helper functions or models you only use programmatically.
@register_fit(
    name='_helper_offset',
    param_names=['c'],
    default_guesses=[0.0],
    equation_string='c',
    hidden=True
)
def _helper_offset(x, c):
    return np.full_like(x, c, dtype=float)
