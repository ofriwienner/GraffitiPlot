"""
GraffitiPlot viewer: load a .gfp file and open it in an interactive window.

Public API
----------
    graffiti_plot.view("my_plot.gfp")

CLI (after ``pip install graffiti-plot``)
-----------------------------------------
    gfp-open my_plot.gfp          # show + interactive shell
    gfp-open                       # file-open dialog if no argument
    gfp-open my_plot.gfp --view-only   # show only, no shell
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Public: view()
# ---------------------------------------------------------------------------

def view(path, *, interactive: bool = True):
    """Load a ``.gfp`` file and show it in a live, editable window.

    After the window appears the function drops into an IPython (or
    standard Python) interactive shell so you can edit the figure
    immediately::

        axes[0].set_title("Better title")
        axes[0].set_xlim(0, 5e-9)
        fig.canvas.draw_idle()

    Parameters
    ----------
    path : str or Path
        Path to the ``.gfp`` file.
    interactive : bool, optional
        If ``True`` (default) an interactive shell is started after the
        window opens.  Set ``False`` to just display and return.

    Returns
    -------
    fig : matplotlib.figure.Figure
    axes : list of matplotlib.axes.Axes
    """
    from .save_load import load
    import matplotlib.pyplot as plt
    import numpy as np

    path = Path(path)

    print(f"Loading '{path.name}' …")
    fig, axes = load(path)

    # Set a descriptive window title
    try:
        fig.canvas.manager.set_window_title(f"GraffitiPlot – {path.name}")
    except Exception:
        pass

    plt.ion()         # non-blocking: GUI events run alongside the shell
    plt.show()
    plt.pause(0.05)   # give the window time to appear

    if not interactive:
        return fig, axes

    _start_shell(fig, axes, path)
    return fig, axes


# ---------------------------------------------------------------------------
# CLI entry point (gfp-open)
# ---------------------------------------------------------------------------

def main():
    """Entry point for the ``gfp-open`` command installed by pip."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="gfp-open",
        description="Open a GraffitiPlot .gfp file with an interactive window + Python shell.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  gfp-open experiment.gfp\n"
            "  gfp-open experiment.gfp --view-only\n"
            "  gfp-open                       # file-open dialog\n"
        ),
    )
    parser.add_argument("file", nargs="?", help="Path to .gfp file")
    parser.add_argument(
        "--view-only", action="store_true",
        help="Show the graph without dropping into an interactive shell",
    )
    args = parser.parse_args()

    # Resolve path: argument → dialog
    gfp_path = _resolve_path(args.file)
    if gfp_path is None:
        parser.print_help()
        sys.exit(1)

    # If launched without a terminal (e.g. double-click), respawn in one
    if not sys.stdin.isatty() and not args.view_only:
        if _relaunch_in_terminal(gfp_path):
            sys.exit(0)
        # Could not find a terminal emulator – fall back to view-only
        print(
            "Warning: could not find a terminal emulator. "
            "Showing graph without interactive shell.",
            file=sys.stderr,
        )
        args.view_only = True

    # Set an interactive backend before importing matplotlib
    _ensure_interactive_backend()

    import graffiti_plot  # ensure patches are active
    view(gfp_path, interactive=not args.view_only)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_path(arg) -> str | None:
    """Return a path string: use `arg` if given, else open a file dialog."""
    if arg is not None:
        return arg
    try:
        import tkinter.filedialog as fd
        path = fd.askopenfilename(
            title="Open GraffitiPlot Figure",
            filetypes=[("GraffitiPlot files", "*.gfp"), ("All files", "*.*")],
        )
        return path if path else None
    except Exception:
        return None


def _ensure_interactive_backend():
    """Switch matplotlib away from Agg to an interactive backend if needed."""
    try:
        import matplotlib
        backend = matplotlib.get_backend().lower()
        if backend == "agg":
            for candidate in ("TkAgg", "Qt5Agg", "Qt6Agg", "MacOSX", "WxAgg"):
                try:
                    matplotlib.use(candidate)
                    break
                except Exception:
                    pass
    except Exception:
        pass


def _start_shell(fig, axes, path: Path):
    """Start an IPython or standard-Python interactive shell with fig/axes in scope."""
    import matplotlib.pyplot as plt
    import numpy as np

    namespace = {
        "fig":   fig,
        "axes":  axes,
        "ax":    axes[0] if len(axes) == 1 else axes,
        "plt":   plt,
        "np":    np,
    }

    ax_hint = "axes[0]" if len(axes) > 1 else "ax"
    banner = (
        f"\n{'─' * 56}\n"
        f"  GraffitiPlot – '{path.name}'\n"
        f"{'─' * 56}\n"
        f"  fig    → matplotlib Figure ({len(axes)} subplot{'s' if len(axes) != 1 else ''})\n"
        f"  axes   → list of Axes  (axes[0], axes[1], …)\n"
        f"  ax     → shortcut for {ax_hint}\n"
        f"  plt    → matplotlib.pyplot\n"
        f"  np     → numpy\n"
        f"\n"
        f"  Edit the graph, then call:\n"
        f"    fig.canvas.draw_idle()   ← refresh the window\n"
        f"    plt.savefig('out.png')   ← export image\n"
        f"\n"
        f"  All GraffitiPlot modebar features are active.\n"
        f"  Close the window or press Ctrl-D / Ctrl-Z to exit.\n"
        f"{'─' * 56}\n"
    )

    # IPython is strongly preferred because it handles the matplotlib event
    # loop automatically (the GUI window stays responsive).
    try:
        import IPython
        IPython.embed(user_ns=namespace, banner1=banner, colors="Neutral")
        return
    except ImportError:
        pass

    # Fallback: stdlib code.interact  (window may freeze between commands –
    # call plt.pause(0.1) if that happens)
    banner += "\nNote: install IPython for a better interactive experience.\n"
    import code
    code.interact(banner=banner, local=namespace)


def _relaunch_in_terminal(gfp_path: str) -> bool:
    """Spawn a terminal emulator that runs ``gfp-open <gfp_path>``.

    Returns True if a terminal was successfully launched.
    """
    import shutil
    import subprocess

    # Build the command the terminal will execute
    py_args = [
        sys.executable, "-c",
        (
            "import graffiti_plot.viewer as v, sys; "
            f"sys.argv=['gfp-open',{gfp_path!r}]; "
            "v.main()"
        ),
    ]
    cmd_str = " ".join(py_args)   # for single-string terminal flags

    # ── macOS ──────────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        # Escape for AppleScript double-quote context
        safe = cmd_str.replace("\\", "\\\\").replace('"', '\\"')
        os.system(f'osascript -e \'tell app "Terminal" to do script "{safe}"\'')
        return True

    # ── Windows ────────────────────────────────────────────────────────────
    if sys.platform == "win32":
        subprocess.Popen(["cmd", "/k"] + py_args, creationflags=0x00000010)
        return True

    # ── Linux / other POSIX ────────────────────────────────────────────────
    # Terminals that accept `-- command args…` (exec style)
    exec_style = [
        "gnome-terminal", "xfce4-terminal", "lxterminal",
        "mate-terminal", "tilix",
    ]
    # Terminals that accept `-e command args…`
    e_style = ["xterm", "rxvt", "urxvt", "alacritty", "kitty"]
    # Terminals that accept `--command` or similar
    konsole_style = ["konsole"]

    for term in exec_style:
        if shutil.which(term):
            subprocess.Popen([term, "--"] + py_args)
            return True

    for term in konsole_style:
        if shutil.which(term):
            subprocess.Popen([term, "-e"] + py_args)
            return True

    for term in e_style:
        if shutil.which(term):
            subprocess.Popen([term, "-e"] + py_args)
            return True

    return False
