# graffiti-plot

Interactive matplotlib figures: zoom, pan, curve fitting, SI units, and more.

**PyPI name:** `graffiti-plot` (the name "graffiti" is already taken on PyPI).

## Install

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you do not have it yet.

### Tcl/Tk (required for the GUI)

`graffiti-plot` uses **tkinter** (via `customtkinter` and matplotlib’s Tk backends). That needs Tcl/Tk to be available for your Python interpreter. Pip cannot install it; use your OS or Python installer.

- **Debian / Ubuntu:** `sudo apt install python3-tk`
- **Fedora:** `sudo dnf install python3-tkinter`
- **macOS (Homebrew):** `brew install python-tk` (use the Homebrew Python that matches this install, or ensure your interpreter can see Tcl/Tk)
- **Windows:** When installing Python from [python.org](https://www.python.org/downloads/), enable **“tcl/tk and IDLE”** (or run the installer’s *Modify* step and add that component)

If you see `No module named '_tkinter'`, Tcl/Tk is still missing for the Python you are using.

### From PyPI

```bash
uv pip install graffiti-plot
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

From the repository root, with Tcl/Tk installed for your Python (see above):

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e .
```