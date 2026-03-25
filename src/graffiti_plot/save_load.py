"""
Save and load GraffitiPlot figure state.

File format: .gfp  (JSON)
Companion data files: .npz (numpy) or .csv (pandas) when embed_data=False.
"""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import matplotlib.figure
    import matplotlib.axes

_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save(fig, path, embed_data: bool = True, data_file=None):
    """Save a GraffitiPlot figure to a ``.gfp`` file.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure to save.
    path : str or Path
        Destination ``.gfp`` file path.
    embed_data : bool, optional
        If ``True`` (default) all series data is embedded as JSON arrays inside
        the ``.gfp`` file.  If ``False`` data is written to a separate
        companion file referenced by the ``.gfp``.
    data_file : str, Path or pandas.DataFrame, optional
        Only used when ``embed_data=False``.

        * ``None``  – auto-name companion as ``<stem>.npz`` (numpy binary).
        * ``"name.npz"`` – write numpy NPZ to the given path.
        * ``"name.csv"`` – write CSV (via pandas if available, else numpy).
        * ``pandas.DataFrame`` – match series arrays to DataFrame columns and
          save the DataFrame as ``<stem>.csv``; unmatched series fall back to
          embedding.
    """
    path = Path(path)

    # Collect external arrays (key → ndarray) while serializing
    ext_arrays: dict[str, np.ndarray] = {}
    # Mapping of (ax_idx, series_idx) → DataFrame column names, used for df mode
    df_col_map: dict[tuple, tuple[str, str]] = {}

    # --- Resolve DataFrame reference up front ---
    df_ref = None
    df_save_path: Path | None = None
    is_df_mode = False
    try:
        import pandas as pd
        if isinstance(data_file, pd.DataFrame):
            is_df_mode = True
            df_ref = data_file
            df_save_path = path.with_suffix('.csv')
    except ImportError:
        pass

    doc = {
        "version": _SCHEMA_VERSION,
        "figure": _serialize_figure(fig),
        "axes": [],
    }

    for i, ax in enumerate(fig.axes):
        if _is_graffiti_internal_axes(ax):
            continue
        ax_data = _serialize_axes(ax, i, embed_data, ext_arrays, df_ref, df_col_map)
        doc["axes"].append(ax_data)

    if not embed_data:
        companion_path = _resolve_companion_path(path, data_file, is_df_mode)
        _write_external_file(companion_path, ext_arrays, data_file, is_df_mode, df_ref, df_save_path)
        _update_file_refs(doc, companion_path.name)

    path.write_text(json.dumps(doc, indent=2))


def load(path):
    """Load a ``.gfp`` file and return ``(fig, axes_list)``.

    The returned figure is fully interactive (GraffitiPlot features active).

    Parameters
    ----------
    path : str or Path

    Returns
    -------
    fig : matplotlib.figure.Figure
    axes_list : list of matplotlib.axes.Axes
        One entry per saved axes, in order.

    Example
    -------
    >>> import graffiti_plot, matplotlib.pyplot as plt
    >>> fig, axes = graffiti_plot.load("experiment.gfp")
    >>> plt.show()
    """
    import matplotlib.pyplot as plt

    path = Path(path)
    doc = json.loads(path.read_text())

    ext_data = _load_external_data(path, doc)

    fig_data = doc["figure"]
    figsize = fig_data.get("figsize", [10, 6])
    fig = plt.figure(figsize=figsize)

    sp = fig_data.get("subplotpars", {})
    if sp:
        fig.subplots_adjust(
            left=sp.get("left"),
            right=sp.get("right"),
            bottom=sp.get("bottom"),
            top=sp.get("top"),
            wspace=sp.get("wspace"),
            hspace=sp.get("hspace"),
        )

    axes_list = []
    for ax_data in doc.get("axes", []):
        pos = ax_data["position"]
        ax = fig.add_axes([pos["x0"], pos["y0"], pos["width"], pos["height"]])
        _restore_axes(ax, ax_data, ext_data)
        axes_list.append(ax)

    _restore_modebar_state(fig, fig_data.get("modebar", {}))
    return fig, axes_list


# ---------------------------------------------------------------------------
# Internal: called from modebar "Save" button
# ---------------------------------------------------------------------------

def _save_with_dialog(fig):
    """Open a file-save dialog and save the figure."""
    try:
        import tkinter.filedialog as fd
        path = fd.asksaveasfilename(
            title="Save GraffitiPlot Figure",
            defaultextension=".gfp",
            filetypes=[("GraffitiPlot files", "*.gfp"), ("All files", "*.*")],
        )
    except Exception:
        path = None

    if not path:
        return

    try:
        save(fig, path)
    except Exception as exc:
        warnings.warn(f"graffiti_plot: failed to save figure – {exc}")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_figure(fig) -> dict:
    w, h = fig.get_size_inches()
    sp = fig.subplotpars
    return {
        "figsize": [float(w), float(h)],
        "modebar": {
            "grid":   bool(getattr(fig, "_menu_grid_state",  False)),
            "auto_y": bool(getattr(fig, "_menu_autoy_state", False)),
            "hover":  bool(getattr(fig, "_menu_hover_state", True)),
            "link_x": bool(getattr(fig, "_graffiti_linked_x", False)),
        },
        "subplotpars": {
            "left":   sp.left,
            "right":  sp.right,
            "bottom": sp.bottom,
            "top":    sp.top,
            "wspace": sp.wspace,
            "hspace": sp.hspace,
        },
    }


def _is_graffiti_internal_axes(ax) -> bool:
    # Modebar lives in figure.texts, not in a separate axes; no internal axes to exclude.
    return False


def _serialize_axes(ax, index: int, embed_data: bool,
                    ext_arrays: dict, df_ref, df_col_map: dict) -> dict:
    pos = ax.get_position()

    # Legend
    legend_data = None
    leg = ax.get_legend()
    if leg is not None and leg.get_visible():
        legend_data = {
            "visible": True,
            "loc": int(getattr(leg, "_loc", 0)),
        }

    # SI units from PlotlyInteractivity
    pi = getattr(ax, "_plotly_interactor", None)
    si_x = getattr(pi, "_si_unit_x", None) if pi else None
    si_y = getattr(pi, "_si_unit_y", None) if pi else None

    series = []
    s_idx = 0
    for line in ax.get_lines():
        label = line.get_label()
        if label.startswith("_"):  # skip internal matplotlib / graffiti lines
            continue
        s = _serialize_line(line, index, s_idx, embed_data, ext_arrays, df_ref, df_col_map)
        series.append(s)
        s_idx += 1

    return {
        "index": index,
        "position": {
            "x0":     pos.x0,
            "y0":     pos.y0,
            "width":  pos.width,
            "height": pos.height,
        },
        "title":  ax.get_title(),
        "xlabel": ax.get_xlabel(),
        "ylabel": ax.get_ylabel(),
        "xlim":   list(ax.get_xlim()),
        "ylim":   list(ax.get_ylim()),
        "xscale": ax.get_xscale(),
        "yscale": ax.get_yscale(),
        "grid":   bool(getattr(ax.get_figure(), "_menu_grid_state", False)),
        "si_units": {"x": si_x, "y": si_y},
        "legend": legend_data,
        "series": series,
    }


def _serialize_line(line, ax_idx: int, s_idx: int, embed_data: bool,
                    ext_arrays: dict, df_ref, df_col_map: dict) -> dict:
    x = np.asarray(line.get_xdata(), dtype=float)
    y = np.asarray(line.get_ydata(), dtype=float)
    alpha = line.get_alpha()

    # Try DataFrame column matching first
    if df_ref is not None and not embed_data:
        col_x, col_y = _match_df_columns(df_ref, x, y)
        if col_x is not None:
            df_col_map[(ax_idx, s_idx)] = (col_x, col_y)
            data_block = {
                "mode":   "external_csv",
                "file":   None,   # filled later
                "x_col":  col_x,
                "y_col":  col_y,
            }
        else:
            # DataFrame provided but no matching columns – fall back to embed
            data_block = {"mode": "embedded", "x": _safe_tolist(x), "y": _safe_tolist(y)}
    elif embed_data:
        data_block = {"mode": "embedded", "x": _safe_tolist(x), "y": _safe_tolist(y)}
    else:
        x_key = f"ax{ax_idx}_s{s_idx}_x"
        y_key = f"ax{ax_idx}_s{s_idx}_y"
        ext_arrays[x_key] = x
        ext_arrays[y_key] = y
        data_block = {
            "mode":  "external_npz",  # corrected to actual type by _update_file_refs
            "file":  None,            # filled later
            "x_key": x_key,
            "y_key": y_key,
        }

    return {
        "label":      line.get_label(),
        "color":      line.get_color(),
        "linewidth":  float(line.get_linewidth()),
        "linestyle":  line.get_linestyle(),
        "marker":     str(line.get_marker()),
        "markersize": float(line.get_markersize()),
        "alpha":      float(alpha) if alpha is not None else None,
        "visible":    bool(line.get_visible()),
        "data":       data_block,
    }


def _match_df_columns(df, x: np.ndarray, y: np.ndarray):
    """Return (x_col_name, y_col_name) if arrays match df columns, else (None, None)."""
    col_x = None
    col_y = None
    for col in df.columns:
        arr = np.asarray(df[col])
        if col_x is None and arr.shape == x.shape:
            try:
                if np.array_equal(arr, x, equal_nan=True):
                    col_x = str(col)
            except TypeError:
                if np.array_equal(arr, x):
                    col_x = str(col)
        if col_y is None and arr.shape == y.shape:
            try:
                if np.array_equal(arr, y, equal_nan=True):
                    col_y = str(col)
            except TypeError:
                if np.array_equal(arr, y):
                    col_y = str(col)
        if col_x is not None and col_y is not None:
            break
    if col_x is None or col_y is None:
        return None, None
    return col_x, col_y


def _safe_tolist(arr: np.ndarray) -> list:
    """Convert float array to JSON list, replacing NaN/Inf with None."""
    out = []
    for v in arr.tolist():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out.append(None)
        else:
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# External file helpers
# ---------------------------------------------------------------------------

def _resolve_companion_path(gfp_path: Path, data_file, is_df_mode: bool) -> Path:
    if data_file is None:
        return gfp_path.with_suffix(".npz")
    if is_df_mode:
        return gfp_path.with_suffix(".csv")
    return Path(data_file)


def _write_external_file(companion_path: Path, ext_arrays: dict,
                          data_file, is_df_mode: bool, df_ref, df_save_path):
    """Write the companion data file (NPZ or CSV)."""
    suffix = companion_path.suffix.lower()

    if suffix == ".npz" or (data_file is None and not is_df_mode):
        if ext_arrays:
            np.savez(companion_path, **ext_arrays)
        # (if no ext_arrays everything was embedded – nothing to write)

    elif suffix == ".csv" or is_df_mode:
        if is_df_mode and df_ref is not None:
            # Save the user's DataFrame directly (all columns preserved)
            try:
                df_ref.to_csv(companion_path, index=False)
            except Exception as exc:
                warnings.warn(f"graffiti_plot: could not save DataFrame – {exc}")
        elif ext_arrays:
            # Build a DataFrame from the extracted arrays and save as CSV
            # Each array may have a different length; pad with NaN
            max_len = max(len(v) for v in ext_arrays.values())
            csv_data = {}
            for key, arr in ext_arrays.items():
                padded = np.full(max_len, np.nan)
                padded[:len(arr)] = arr
                csv_data[key] = padded
            try:
                import pandas as pd
                pd.DataFrame(csv_data).to_csv(companion_path, index=False)
            except ImportError:
                # Fallback: write manually
                _write_csv_without_pandas(companion_path, csv_data, max_len)
    else:
        # Unknown extension – default to NPZ
        if ext_arrays:
            np.savez(companion_path, **ext_arrays)


def _write_csv_without_pandas(path: Path, data: dict, n_rows: int):
    headers = list(data.keys())
    with path.open("w") as f:
        f.write(",".join(headers) + "\n")
        for i in range(n_rows):
            row = []
            for key in headers:
                v = float(data[key][i])
                row.append("" if math.isnan(v) else f"{v:.17g}")
            f.write(",".join(row) + "\n")


def _update_file_refs(doc: dict, filename: str):
    """Fill in the ``file`` field of all external data blocks."""
    suffix = Path(filename).suffix.lower()
    mode = "external_csv" if suffix == ".csv" else "external_npz"
    for ax_data in doc.get("axes", []):
        for series in ax_data.get("series", []):
            blk = series.get("data", {})
            if blk.get("mode") in ("external_npz", "external_csv"):
                blk["file"] = filename
                if mode == "external_csv" and "x_key" in blk:
                    # CSV column names = the same keys used in the NPZ/CSV header
                    blk["x_col"] = blk.pop("x_key")
                    blk["y_col"] = blk.pop("y_key")
                blk["mode"] = mode


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def _load_external_data(gfp_path: Path, doc: dict):
    """Load companion data file if any series references external storage."""
    # Find the first external file reference
    ext_file = None
    ext_mode = None
    for ax_data in doc.get("axes", []):
        for series in ax_data.get("series", []):
            blk = series.get("data", {})
            if blk.get("mode") in ("external_npz", "external_csv") and blk.get("file"):
                ext_file = blk["file"]
                ext_mode = blk["mode"]
                break
        if ext_file:
            break

    if ext_file is None:
        return None

    companion = gfp_path.parent / ext_file
    if not companion.exists():
        raise FileNotFoundError(
            f"graffiti_plot: companion data file not found: {companion}"
        )

    if ext_mode == "external_npz":
        return {"mode": "npz", "data": np.load(companion)}
    else:  # external_csv
        try:
            import pandas as pd
            df = pd.read_csv(companion)
            return {"mode": "csv_df", "data": df}
        except ImportError:
            arr = np.genfromtxt(companion, delimiter=",", names=True)
            return {"mode": "csv_np", "data": arr}


def _load_series_xy(blk: dict, ext_data) -> tuple[np.ndarray, np.ndarray]:
    mode = blk.get("mode", "embedded")

    if mode == "embedded":
        x = np.array([v if v is not None else np.nan for v in blk["x"]])
        y = np.array([v if v is not None else np.nan for v in blk["y"]])
        return x.astype(float), y.astype(float)

    if ext_data is None:
        raise ValueError("graffiti_plot: external data required but not loaded")

    if mode == "external_npz":
        raw = ext_data["data"]
        return np.asarray(raw[blk["x_key"]], dtype=float), \
               np.asarray(raw[blk["y_key"]], dtype=float)

    if mode == "external_csv":
        x_col = blk["x_col"]
        y_col = blk["y_col"]
        if ext_data["mode"] == "csv_df":
            df = ext_data["data"]
            return np.asarray(df[x_col], dtype=float), np.asarray(df[y_col], dtype=float)
        else:  # csv_np (numpy structured array)
            arr = ext_data["data"]
            return np.asarray(arr[x_col], dtype=float), np.asarray(arr[y_col], dtype=float)

    raise ValueError(f"graffiti_plot: unknown data mode '{mode}'")


def _restore_axes(ax, data: dict, ext_data):
    """Recreate all series and styling for one axes."""
    for series in data.get("series", []):
        x, y = _load_series_xy(series["data"], ext_data)

        kwargs = {
            "label":     series.get("label"),
            "color":     series.get("color"),
            "linewidth": series.get("linewidth"),
            "linestyle": series.get("linestyle"),
            "markersize": series.get("markersize"),
            "visible":   series.get("visible", True),
        }
        marker = series.get("marker", "None")
        if marker and marker not in ("None", "none"):
            kwargs["marker"] = marker

        alpha = series.get("alpha")
        if alpha is not None:
            kwargs["alpha"] = alpha

        ax.plot(x, y, **kwargs)

    ax.set_title(data.get("title", ""))
    ax.set_xlabel(data.get("xlabel", ""))
    ax.set_ylabel(data.get("ylabel", ""))

    # Scale before limits (critical for log)
    ax.set_xscale(data.get("xscale", "linear"))
    ax.set_yscale(data.get("yscale", "linear"))

    if data.get("xlim"):
        ax.set_xlim(data["xlim"])
    if data.get("ylim"):
        ax.set_ylim(data["ylim"])

    if data.get("grid"):
        ax.grid(True)

    si = data.get("si_units", {})
    si_x = si.get("x") if si else None
    si_y = si.get("y") if si else None
    if (si_x or si_y) and hasattr(ax, "set_si_units"):
        ax.set_si_units(x=si_x or None, y=si_y or None)

    legend_data = data.get("legend")
    if legend_data and legend_data.get("visible"):
        ax.legend(loc=legend_data.get("loc", 0))


def _restore_modebar_state(fig, modebar: dict):
    """Apply saved modebar toggle states to a freshly loaded figure."""
    if not hasattr(fig, "_graffiti_modebar"):
        return

    from .core import _handle_global_action, _sync_global_button_visuals

    if modebar.get("grid"):
        _handle_global_action(fig, "grid")
    if modebar.get("link_x"):
        fig._graffiti_linked_x = True
    if modebar.get("auto_y"):
        fig._menu_autoy_state = True
    if not modebar.get("hover", True):
        fig._menu_hover_state = False

    _sync_global_button_visuals(fig)
