"""
graffiti-plot: Interactive matplotlib figures with zoom, pan, curve fitting, and more.

Install from PyPI::

    pip install graffiti-plot

Usage::

    import graffiti_plot
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9], label="data")
    ax.legend()
    plt.show()

Importing graffiti_plot patches matplotlib figures so new axes get the interactive
toolbar (zoom, pan, link X, grid, log scale, curve fitting, etc.).
"""

__version__ = "0.1.0"

# Activate monkey-patches on import (patches Figure.add_subplot / add_axes)
from . import core

# Public API
from .core import set_footer, CONFIG, enable, disable, is_enabled
from .fits import register_fit, STANDARD_MODELS
from .save_load import save, load

__all__ = ["__version__", "set_footer", "CONFIG", "enable", "disable", "is_enabled", "register_fit", "STANDARD_MODELS", "save", "load"]
