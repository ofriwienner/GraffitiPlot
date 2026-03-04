# graffiti-plot

Interactive matplotlib figures: zoom, pan, curve fitting, SI units, and more.

**PyPI name:** `graffiti-plot` (the name "graffiti" is already taken on PyPI).

## Install

```bash
pip install graffiti-plot
```

## Usage

```python
import graffiti_plot
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9], label="data")
ax.legend()
plt.show()
```

Importing `graffiti_plot` patches matplotlib so new figures get the interactive toolbar (zoom, pan, link X, grid, log scale, curve fitting, hover tooltips, etc.).

### Optional: footer and SI units

```python
import graffiti_plot
graffiti_plot.set_footer(enabled=True)

import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.set_si_units(x="s", y="V")  # SI prefixes (m, k, M, …) on axes
ax.plot(t, v, label="signal")
plt.show()
```

## Development

```bash
pip install -e .
```