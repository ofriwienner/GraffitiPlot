import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.figure as mfigure
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.widgets import Cursor
from matplotlib.ticker import EngFormatter
import numpy as np
import time
import datetime
import math
import warnings
import csv

# =========================================================================
# macOS BACKEND FIX (AUTO-TRIGGER)
# =========================================================================
current_backend = mpl.get_backend().lower()
if current_backend == 'macosx':
    try:
        plt.switch_backend('TkAgg')
    except Exception as e:
        warnings.warn(f"[graffiti-plot] Could not auto-switch backend. Fit Window may crash. ({e})")

# --- Prevent default Matplotlib keymaps from double-firing ---
for kmap, keys in [
    ('keymap.yscale', ['l', 'L']),
    ('keymap.xscale', ['k', 'K']),
    ('keymap.grid', ['g', 'G']),
    ('keymap.home', ['h', 'H', 'r', 'R']),
    ('keymap.all_axes', ['a', 'A']),
    ('keymap.fullscreen', ['f', 'F']),
]:
    if kmap in mpl.rcParams:
        for k in keys:
            if k in mpl.rcParams[kmap]:
                mpl.rcParams[kmap].remove(k)

# =========================================================================
# CONSTANTS
# =========================================================================
_HOVER_PIXEL_THRESHOLD_ON = False   # Whether hover tooltips distance threshold should be enabled
_HOVER_PIXEL_THRESHOLD_SQ = 225    # Max pixel² distance for hover tooltip
_LEGEND_PICK_RADIUS_PX    = 5      # Pick radius for legend handles
_SCOPE_CLICK_TOLERANCE_PX = 5      # Max pixel movement to count as a click vs drag
_ZOOM_AXIS_RATIO           = 2.5   # Ratio threshold for H/V-only zoom detection
_ZOOM_PIXEL_MIN            = 10    # Minimum drag pixels before H/V mode locks
_ZOOM_FULL_RATIO           = 0.7   # Fraction of axis covered before snapping box to full extent
_BOTTOM_MARGIN_MIN         = 0.13  # Minimum bottom margin to keep axis labels above modebar
_MODEBAR_Y_POS             = 0.005 # Y position of modebar buttons (below footer)
_SCROLL_ZOOM_IN_FACTOR     = 0.9   # Scale factor when scrolling up (zoom in)
_SCROLL_ZOOM_OUT_FACTOR    = 1.1   # Scale factor when scrolling down (zoom out)
_AUTOY_PAD_FRACTION        = 0.05  # Padding fraction for auto-Y scaling
_DBL_CLICK_MAX_SEC         = 0.35  # Max seconds between clicks to count as double-click

# =========================================================================
# GLOBAL FOOTER & BUTTON CONFIGURATION
# =========================================================================
CONFIG = {
    'footer_enabled': False,
    'footer_text': None,
    'footer_prefix': '',
}

def set_footer(enabled=True, text=None, prefix=''):
    CONFIG['footer_enabled'] = enabled
    CONFIG['footer_text'] = text
    CONFIG['footer_prefix'] = prefix

def _apply_footer(fig):
    if not CONFIG['footer_enabled']: return
    if hasattr(fig, '_graffiti_footer'): return

    if CONFIG['footer_text'] is not None:
        final_text = CONFIG['footer_text']
    else:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_text = f"{CONFIG['footer_prefix']}{now_str}" if CONFIG['footer_prefix'] else now_str

    fig._graffiti_footer = fig.text(
        0.99, 0.03, final_text,
        color='gray', fontsize=8,
        ha='right', va='bottom', alpha=0.7, zorder=100
    )

# -------------------------------------------------------------------------
# MODEBAR BUTTON STYLES
# -------------------------------------------------------------------------
_MODEBAR_BTN_ACTIVE   = dict(boxstyle='round,pad=0.3', facecolor='#e8f4fd', edgecolor='dodgerblue', alpha=0.95)
_MODEBAR_BTN_INACTIVE = dict(boxstyle='round,pad=0.3', facecolor='white',   edgecolor='lightgray',  alpha=0.9)

def _make_btn(fig, x, y, text, action, ha='center'):
    """Create a single modebar button text-artist and register its action."""
    btn = fig.text(x, y, text, ha=ha, va='bottom', fontsize=8, color='gray',
                   picker=True, bbox=_MODEBAR_BTN_INACTIVE, zorder=2000)
    fig._graffiti_action_map[btn] = action
    return btn

# -------------------------------------------------------------------------
# GLOBAL MODEBAR (SINGLE TOOLBAR FOR THE ENTIRE FIGURE)
# -------------------------------------------------------------------------
def _apply_global_modebar(fig):
    if hasattr(fig, '_graffiti_modebar'): return
    fig._graffiti_modebar = True

    # Global States
    fig._menu_grid_state  = False
    fig._menu_autoy_state = False
    fig._menu_hover_state = True
    fig._graffiti_linked_x = False
    fig._graffiti_action_map = {}

    y = _MODEBAR_Y_POS

    # Left anchor: Export
    btns = {}
    btns['export'] = _make_btn(fig, 0.01, y, " ⬇ Export ", 'export', ha='left')

    # Centre buttons evenly distributed
    centre_labels = [
        (" Link X (X) ", 'link'),
        (" Grid (G) ", 'grid'),
        (" Auto Y (A) ", 'autoy'),
        (" Hover (H) ", 'hover'),
        (" Log X (K) ", 'logx'),
        (" Log Y (L) ", 'logy'),
        (" ← ([) ", 'back'),
        (" → (]) ", 'fwd'),
        (" Fit (F) ", 'fit'),
        (" Clear (C) ", 'clear'),
    ]
    x_positions = np.linspace(0.12, 0.88, len(centre_labels))
    for (text, action), x in zip(centre_labels, x_positions):
        btns[action] = _make_btn(fig, x, y, text, action)

    # Right anchor: Help
    btns['help'] = _make_btn(fig, 0.995, y, " ? ", 'help', ha='right')

    fig._graffiti_buttons_refs = btns

    fig.canvas.mpl_connect('pick_event', lambda event: (
        _handle_global_action(fig, fig._graffiti_action_map[event.artist])
        if event.artist in fig._graffiti_action_map else None
    ))

    _sync_global_button_visuals(fig)


def _set_btn_state(btn, active):
    """Apply active or inactive visual style to a modebar button."""
    btn.set_color('dodgerblue' if active else 'gray')
    btn.set_fontweight('bold' if active else 'normal')
    btn.set_bbox(_MODEBAR_BTN_ACTIVE if active else _MODEBAR_BTN_INACTIVE)


def _sync_global_button_visuals(fig):
    if not hasattr(fig, '_graffiti_buttons_refs'): return
    btns = fig._graffiti_buttons_refs

    _set_btn_state(btns['grid'],  fig._menu_grid_state)
    _set_btn_state(btns['link'],  fig._graffiti_linked_x)
    _set_btn_state(btns['autoy'], fig._menu_autoy_state)
    _set_btn_state(btns['hover'], fig._menu_hover_state)

    if fig.axes:
        _set_btn_state(btns['logx'], any(ax.get_xscale() == 'log' for ax in fig.axes))
        _set_btn_state(btns['logy'], any(ax.get_yscale() == 'log' for ax in fig.axes))

    has_back = any(
        len(getattr(getattr(ax, '_plotly_interactor', None), '_zoom_history', [])) > 0
        for ax in fig.axes
    )
    has_fwd = any(
        len(getattr(getattr(ax, '_plotly_interactor', None), '_zoom_future', [])) > 0
        for ax in fig.axes
    )
    _set_btn_state(btns['back'], has_back)
    _set_btn_state(btns['fwd'],  has_fwd)


def _handle_global_action(fig, action, caller_ax=None):
    if action == 'link':
        fig._graffiti_linked_x = not fig._graffiti_linked_x

    elif action == 'grid':
        fig._menu_grid_state = not fig._menu_grid_state
        for ax in fig.axes: ax.grid(fig._menu_grid_state)

    elif action == 'autoy':
        fig._menu_autoy_state = not fig._menu_autoy_state

    elif action == 'hover':
        fig._menu_hover_state = not fig._menu_hover_state
        if not fig._menu_hover_state:
            for ax in fig.axes:
                interactor = getattr(ax, '_plotly_interactor', None)
                if interactor and interactor._annot:
                    interactor._annot.set_visible(False)

    elif action == 'logx':
        target_axes = [caller_ax] if caller_ax else fig.axes
        is_log = any(ax.get_xscale() == 'log' for ax in target_axes)
        new_scale = 'linear' if is_log else 'log'
        for ax in target_axes:
            ax.set_xscale(new_scale)
            if new_scale == 'linear':
                interactor = getattr(ax, '_plotly_interactor', None)
                if interactor and interactor._si_unit_x:
                    ax.xaxis.set_major_formatter(EngFormatter(unit=''))

    elif action == 'logy':
        target_axes = [caller_ax] if caller_ax else fig.axes
        is_log = any(ax.get_yscale() == 'log' for ax in target_axes)
        new_scale = 'linear' if is_log else 'log'
        for ax in target_axes:
            ax.set_yscale(new_scale)
            if new_scale == 'linear':
                interactor = getattr(ax, '_plotly_interactor', None)
                if interactor and interactor._si_unit_y:
                    ax.yaxis.set_major_formatter(EngFormatter(unit=''))

    elif action == 'back':
        target_ax = caller_ax or (fig.axes[0] if fig.axes else None)
        if target_ax:
            interactor = getattr(target_ax, '_plotly_interactor', None)
            if interactor: interactor._zoom_back()

    elif action == 'fwd':
        target_ax = caller_ax or (fig.axes[0] if fig.axes else None)
        if target_ax:
            interactor = getattr(target_ax, '_plotly_interactor', None)
            if interactor: interactor._zoom_forward()

    elif action == 'fit':
        target_ax = caller_ax or (fig.axes[0] if fig.axes else None)
        if target_ax:
            interactor = getattr(target_ax, '_plotly_interactor', None)
            if interactor: interactor._trigger_fit_window()
    elif action == 'out':
        # Full zoom out: show all data (relim + autoscale), even when plot was drawn with xlim
        for ax in fig.axes:
            interactor = getattr(ax, '_plotly_interactor', None)
            if interactor and hasattr(interactor, '_scope_clear'):
                interactor._scope_clear()
        for ax in fig.axes:
            ax.relim()
            ax.autoscale()

    elif action == 'clear':
        for ax in fig.axes:
            interactor = getattr(ax, '_plotly_interactor', None)
            if interactor and hasattr(interactor, '_scope_clear'):
                interactor._scope_clear()

    elif action == 'export':
        _export_csv(fig)
        return  # skip redraw; file dialog handles it

    elif action == 'help':
        _show_help_dialog()
        return  # skip redraw

    _sync_global_button_visuals(fig)
    fig.canvas.draw_idle()


def _export_csv(fig):
    """Open a save-file dialog and write all visible line data to a CSV file."""
    try:
        import tkinter.filedialog as fd
        path = fd.asksaveasfilename(
            title="Export Data as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
    except Exception:
        warnings.warn("[graffiti-plot] Could not open file dialog for CSV export.")
        return

    if not path:
        return

    try:
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["# graffiti-plot export",
                             datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow([])
            for i, ax in enumerate(fig.axes):
                for line in ax.get_lines():
                    lbl = line.get_label()
                    if lbl.startswith('_'):
                        continue
                    section = f"{lbl} (subplot {i+1})" if len(fig.axes) > 1 else lbl
                    writer.writerow([f"# {section}"])
                    writer.writerow(["x", "y"])
                    for x, y in zip(line.get_xdata(), line.get_ydata()):
                        writer.writerow([x, y])
                    writer.writerow([])
    except Exception as e:
        warnings.warn(f"[graffiti-plot] CSV export failed: {e}")


def _show_help_dialog():
    """Open a small help window listing all keyboard shortcuts and mouse controls."""
    try:
        import customtkinter as ctk
    except ImportError:
        warnings.warn("[graffiti-plot] customtkinter not installed; cannot show help dialog.")
        return

    win = ctk.CTkToplevel()
    win.title("graffiti-plot — Help")
    win.geometry("340x430")
    win.resizable(False, False)
    win.lift()
    win.attributes('-topmost', True)
    win.after(500, lambda: win.attributes('-topmost', False))

    help_text = (
        "Keyboard Shortcuts\n"
        "──────────────────\n"
        "G        Toggle grid\n"
        "L        Toggle log Y\n"
        "K        Toggle log X\n"
        "A        Toggle auto Y\n"
        "H        Toggle hover tooltips\n"
        "X        Link / unlink X axes\n"
        "F        Open curve fit window\n"
        "[        Zoom back (undo)\n"
        "]        Zoom forward (redo)\n"
        "C / Esc  Clear scope cursors\n"
        "\n"
        "Mouse Controls\n"
        "──────────────\n"
        "Left drag    Zoom (box / H / V)\n"
        "Middle drag  Pan\n"
        "Scroll       Zoom in / out\n"
        "Dbl-click    Reset view\n"
        "Click plot   Place scope cursor\n"
    )

    ctk.CTkLabel(
        win, text=help_text,
        font=ctk.CTkFont(family="Courier", size=13),
        justify="left", anchor="w"
    ).pack(padx=20, pady=20, fill="both", expand=True)

    ctk.CTkButton(win, text="Close", command=win.destroy).pack(pady=(0, 15))


# =========================================================================
# CORE INTERACTIVITY CLASS
# =========================================================================
class PlotlyInteractivity:
    """Per-axes interactivity handler attached via monkey-patch.

    Manages zoom (box/H/V), pan (middle mouse), hover tooltips,
    dual-cursor measurement, legend toggling, and fit window launch.
    One instance is created per axes object.
    """

    def __init__(self, ax):
        self.ax = ax
        self.fig = ax.figure
        self._legend_mapping = {}
        self._cids = []       # all persistent event handler ids
        self._pick_cids = []  # pick-event ids reconnected on every ax.legend() call

        self._si_unit_x = None
        self._si_unit_y = None

        if self.fig.subplotpars.bottom < _BOTTOM_MARGIN_MIN:
            self.fig.subplots_adjust(bottom=_BOTTOM_MARGIN_MIN)

        self._toolbar = getattr(self.fig.canvas.manager, 'toolbar', None)
        if self._toolbar is not None:
            self._toolbar.zoom = lambda *args, **kwargs: None

        self._original_legend = self.ax.legend
        self.ax.legend = self._custom_legend

        self._is_dragging = False
        self._is_panning = False
        self._start_data = None
        self._start_px = None
        self._zoom_mode = None

        self._pan_start_xlim = None
        self._pan_start_ylim = None
        self._pan_start_px = None

        self._original_xlim = None
        self._original_ylim = None
        self._limits_captured = False

        # Zoom history for back/forward navigation
        self._zoom_history = []  # list of (xlim, ylim) tuples
        self._zoom_future  = []  # redo stack

        self._last_pick_time = 0
        self._last_picked_leg = None

        self._zoom_rect = Rectangle(
            (0, 0), 0, 0,
            facecolor='dodgerblue', alpha=0.3, edgecolor='blue',
            linewidth=1, visible=False, zorder=1000
        )
        self._zoom_rect.set_in_layout(False)
        self.ax.add_patch(self._zoom_rect)

        self._annot = self.ax.annotate(
            "", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3"), zorder=1005
        )
        self._annot.set_in_layout(False)
        self._annot.set_visible(False)

        self._cursor = Cursor(self.ax, useblit=True, color='gray', linewidth=0.8, linestyle=':', zorder=999)

        # Scope-style cursors: two points with Δx, Δy display
        self._scope_cursor_1 = None  # (x, y) or None
        self._scope_cursor_2 = None
        self._scope_vline1 = Line2D([0, 0], [0, 1], transform=self.ax.get_xaxis_transform(),
                                    color='crimson', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        self._scope_vline2 = Line2D([0, 0], [0, 1], transform=self.ax.get_xaxis_transform(),
                                    color='teal', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        self._scope_hline1 = Line2D([0, 1], [0, 0], transform=self.ax.get_yaxis_transform(),
                                    color='crimson', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        self._scope_hline2 = Line2D([0, 1], [0, 0], transform=self.ax.get_yaxis_transform(),
                                    color='teal', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        for line in (self._scope_vline1, self._scope_vline2, self._scope_hline1, self._scope_hline2):
            line.set_visible(False)
            self.ax.add_line(line)

        self._scope_annot = self.ax.text(
            0.02, 0.98, '', transform=self.ax.transAxes, fontsize=8,
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.35', facecolor='white', edgecolor='gray', alpha=0.95),
            zorder=1004
        )
        self._scope_annot.set_visible(False)
        self._scope_click_start = None  # (xdata, ydata, x_px, y_px) while waiting for release

        # Floating preview crosshair + snap point
        self._scope_preview_v  = Line2D([0, 0], [0, 1], transform=self.ax.get_xaxis_transform(),
                                        color='gray', linewidth=1, linestyle='-', alpha=0.5, zorder=997)
        self._scope_preview_h  = Line2D([0, 1], [0, 0], transform=self.ax.get_yaxis_transform(),
                                        color='gray', linewidth=1, linestyle='-', alpha=0.5, zorder=997)
        self._scope_preview_pt = Line2D([], [], linestyle='', marker='o', markersize=8,
                                        markeredgecolor='gray', markerfacecolor='white',
                                        markeredgewidth=1.5, alpha=0.95, zorder=1001)
        for art in (self._scope_preview_v, self._scope_preview_h, self._scope_preview_pt):
            art.set_visible(False)
            self.ax.add_line(art)

        self._setup_events()

    # ---------------------------------------------------------
    # SI UNIT INTEGRATION
    # ---------------------------------------------------------
    def set_si_units(self, x=None, y=None):
        """Attach SI unit labels to axes and enable EngFormatter tick formatting."""
        self._si_unit_x = x
        self._si_unit_y = y

        if x and self.ax.get_xscale() == 'linear':
            self.ax.xaxis.set_major_formatter(EngFormatter(unit=''))
            xlabel = self.ax.get_xlabel()
            if f"[{x}]" not in xlabel:
                self.ax.set_xlabel(f"{xlabel} [{x}]" if xlabel else f"[{x}]")

        if y and self.ax.get_yscale() == 'linear':
            self.ax.yaxis.set_major_formatter(EngFormatter(unit=''))
            ylabel = self.ax.get_ylabel()
            if f"[{y}]" not in ylabel:
                self.ax.set_ylabel(f"{ylabel} [{y}]" if ylabel else f"[{y}]")

        self.fig.canvas.draw_idle()

    def _format_si(self, val, unit):
        """Format a numeric value with the appropriate SI prefix for the given unit."""
        if unit is None: return f"{val:.3g}"
        if val == 0: return f"0 {unit}"
        mag = math.floor(math.log10(abs(val)) / 3.0) * 3
        mag = max(-15, min(mag, 12))
        prefixes = {12: 'T', 9: 'G', 6: 'M', 3: 'k', 0: '',
                    -3: 'm', -6: 'µ', -9: 'n', -12: 'p', -15: 'f'}
        return f"{val / (10 ** mag):.3g} {prefixes[mag]}{unit}"

    # ---------------------------------------------------------
    # SCOPE CURSOR
    # ---------------------------------------------------------
    def _scope_clear(self):
        """Remove both scope cursors and hide all associated visual elements."""
        self._scope_cursor_1 = None
        self._scope_cursor_2 = None
        self._scope_click_start = None
        for line in (self._scope_vline1, self._scope_vline2, self._scope_hline1, self._scope_hline2):
            line.set_visible(False)
        for art in (self._scope_preview_v, self._scope_preview_h, self._scope_preview_pt):
            art.set_visible(False)
        self._scope_annot.set_visible(False)
        self.fig.canvas.draw_idle()

    def _update_scope_preview(self, x_px, y_px, x_data=None):
        nearest = self._find_nearest_data_point(x_px, y_px, x_data_vertical=x_data)
        if nearest is None:
            self._scope_preview_v.set_visible(False)
            self._scope_preview_h.set_visible(False)
            self._scope_preview_pt.set_visible(False)
        else:
            x_snap, y_snap = nearest[0][0], nearest[0][1]
            self._scope_preview_v.set_xdata([x_snap, x_snap])
            self._scope_preview_v.set_ydata([0, 1])
            self._scope_preview_h.set_xdata([0, 1])
            self._scope_preview_h.set_ydata([y_snap, y_snap])
            self._scope_preview_pt.set_xdata([x_snap])
            self._scope_preview_pt.set_ydata([y_snap])
            self._scope_preview_v.set_visible(True)
            self._scope_preview_h.set_visible(True)
            self._scope_preview_pt.set_visible(True)
        self.fig.canvas.draw_idle()

    def _scope_place_point(self, x, y):
        """Place a scope cursor at the given data coordinates, cycling C1 → C2 → reset."""
        if self._scope_cursor_1 is None:
            self._scope_cursor_1 = (float(x), float(y))
        elif self._scope_cursor_2 is None:
            self._scope_cursor_2 = (float(x), float(y))
        else:
            self._scope_cursor_1 = (float(x), float(y))
            self._scope_cursor_2 = None
        self._scope_update_geometry()

    def _scope_update_geometry(self):
        p1, p2 = self._scope_cursor_1, self._scope_cursor_2

        for line in (self._scope_vline1, self._scope_vline2, self._scope_hline1, self._scope_hline2):
            line.set_visible(False)
        self._scope_annot.set_visible(False)

        if p1 is not None:
            self._scope_vline1.set_xdata([p1[0], p1[0]])
            self._scope_vline1.set_ydata([0, 1])
            self._scope_hline1.set_xdata([0, 1])
            self._scope_hline1.set_ydata([p1[1], p1[1]])
            self._scope_vline1.set_visible(True)
            self._scope_hline1.set_visible(True)

        if p2 is not None:
            self._scope_vline2.set_xdata([p2[0], p2[0]])
            self._scope_vline2.set_ydata([0, 1])
            self._scope_hline2.set_xdata([0, 1])
            self._scope_hline2.set_ydata([p2[1], p2[1]])
            self._scope_vline2.set_visible(True)
            self._scope_hline2.set_visible(True)

        if p1 is not None and p2 is not None:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            x1s = self._format_si(p1[0], self._si_unit_x)
            y1s = self._format_si(p1[1], self._si_unit_y)
            x2s = self._format_si(p2[0], self._si_unit_x)
            y2s = self._format_si(p2[1], self._si_unit_y)
            dxs = self._format_si(dx, self._si_unit_x)
            dys = self._format_si(dy, self._si_unit_y)
            self._scope_annot.set_text(
                f"C1: ({x1s}, {y1s})\nC2: ({x2s}, {y2s})\nΔx = {dxs}\nΔy = {dys}"
            )
            self._scope_annot.set_visible(True)

        self.fig.canvas.draw_idle()

    # ---------------------------------------------------------
    # ZOOM HISTORY
    # ---------------------------------------------------------
    def _push_zoom_state(self):
        """Save current axis limits to the zoom history stack and clear the redo stack."""
        self._zoom_history.append((self.ax.get_xlim(), self.ax.get_ylim()))
        self._zoom_future.clear()
        _sync_global_button_visuals(self.fig)

    def _zoom_back(self):
        """Restore the previous zoom state (undo)."""
        if not self._zoom_history:
            return
        self._zoom_future.append((self.ax.get_xlim(), self.ax.get_ylim()))
        xlim, ylim = self._zoom_history.pop()
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        _sync_global_button_visuals(self.fig)
        self.fig.canvas.draw_idle()

    def _zoom_forward(self):
        """Restore the next zoom state (redo)."""
        if not self._zoom_future:
            return
        self._zoom_history.append((self.ax.get_xlim(), self.ax.get_ylim()))
        xlim, ylim = self._zoom_future.pop()
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        _sync_global_button_visuals(self.fig)
        self.fig.canvas.draw_idle()

    # ---------------------------------------------------------
    # INTERACTIVE FIT TOOL UI
    # ---------------------------------------------------------
    def _trigger_fit_window(self):
        try:
            from .fit_ui import FitWindow
        except ImportError as e:
            warnings.warn(f"[graffiti-plot] Could not load GUI: {e}")
            return

        traces = {}
        for current_ax in self.fig.axes:
            xlim = current_ax.get_xlim()
            for line in current_ax.get_lines():
                lbl = line.get_label()
                if not line.get_visible() or lbl.startswith('_') or lbl.startswith('Fit:'):
                    continue

                x_f = np.asarray(line.get_xdata(), dtype=float)
                y_f = np.asarray(line.get_ydata(), dtype=float)
                mask = (x_f >= xlim[0]) & (x_f <= xlim[1]) & np.isfinite(y_f)

                if np.sum(mask) >= 3:
                    trace_name = (
                        f"{lbl} (Plot {self.fig.axes.index(current_ax)+1})"
                        if len(self.fig.axes) > 1 else lbl
                    )
                    traces[trace_name] = {
                        'x': x_f[mask], 'y': y_f[mask],
                        'color': line.get_color(), 'ax': current_ax
                    }

        if not traces:
            warnings.warn("[graffiti-plot] No valid data in view to fit. Zoom out and try again.")
            return

        def on_success(x_fit, y_fit, color, label, target_ax):
            if target_ax is None:
                target_ax = self.fig.axes[0] if self.fig.axes else None
            if target_ax is None:
                return
            target_ax.plot(x_fit, y_fit, linestyle='--', color=color, linewidth=2, alpha=0.85, label=label)
            target_ax.legend()
            self.fig.canvas.draw_idle()

        FitWindow(traces=traces, on_fit_success=on_success, format_si_func=self._format_si)

    # ---------------------------------------------------------
    # LEGEND INTERCEPT
    # ---------------------------------------------------------
    def _custom_legend(self, *args, **kwargs):
        leg = self._original_legend(*args, **kwargs)
        if leg is None: return leg

        # Only disconnect the previous pick handler — never touch the main _cids
        # (which hold mouse/keyboard/draw/scroll events).
        for cid in self._pick_cids:
            self.fig.canvas.mpl_disconnect(cid)
        self._pick_cids.clear()
        self._legend_mapping.clear()

        handles, labels = self.ax.get_legend_handles_labels()
        leg_handles = getattr(leg, 'legend_handles', getattr(leg, 'legendHandles', []))

        for leg_handle, orig_artist, label in zip(leg_handles, handles, labels):
            leg_handle.set_picker(True)
            leg_handle.set_pickradius(_LEGEND_PICK_RADIUS_PX)
            self._legend_mapping[leg_handle] = (orig_artist, label)

        self._pick_cids.append(self.fig.canvas.mpl_connect('pick_event', self._on_pick))
        return leg

    def _on_pick(self, event):
        if hasattr(self.fig, '_graffiti_action_map') and event.artist in self.fig._graffiti_action_map:
            return

        leg_handle = event.artist
        if leg_handle not in self._legend_mapping: return

        orig_artist, _ = self._legend_mapping[leg_handle]
        current_time = time.time()

        if current_time - self._last_pick_time < _DBL_CLICK_MAX_SEC and self._last_picked_leg == leg_handle:
            all_others_hidden = all(
                not art.get_visible()
                for lh, (art, _) in self._legend_mapping.items() if lh != leg_handle
            )
            for lh, (art, _) in self._legend_mapping.items():
                vis = True if all_others_hidden else (lh == leg_handle)
                art.set_visible(vis)
                lh.set_alpha(1.0 if vis else 0.2)
        else:
            vis = not orig_artist.get_visible()
            orig_artist.set_visible(vis)
            leg_handle.set_alpha(1.0 if vis else 0.2)

        self._last_pick_time = current_time
        self._last_picked_leg = leg_handle
        self.fig.canvas.draw_idle()

    def _setup_events(self):
        cid = self.fig.canvas.mpl_connect
        self._cids.extend([
            cid('button_press_event',   self._on_press),
            cid('motion_notify_event',  self._on_motion),
            cid('button_release_event', self._on_release),
            cid('scroll_event',         self._on_scroll),
            cid('key_press_event',      self._on_key),
            cid('draw_event',           self._on_draw),
            cid('close_event',          self._on_close),
        ])

    def _on_close(self, event):
        """Disconnect all event handlers when the figure is closed."""
        for cid in self._cids:
            self.fig.canvas.mpl_disconnect(cid)
        self._cids.clear()
        for cid in self._pick_cids:
            self.fig.canvas.mpl_disconnect(cid)
        self._pick_cids.clear()

    def _on_draw(self, event):
        if not self._limits_captured:
            self._original_xlim = self.ax.get_xlim()
            self._original_ylim = self.ax.get_ylim()
            self._limits_captured = True

        # Re-enforce bottom margin if tight_layout (or other calls) overrode it.
        # The flag prevents infinite recursion: subplots_adjust → draw → _on_draw → …
        if (not getattr(self.fig, '_graffiti_adjusting', False)
                and self.fig.subplotpars.bottom < _BOTTOM_MARGIN_MIN):
            self.fig._graffiti_adjusting = True
            self.fig.subplots_adjust(bottom=_BOTTOM_MARGIN_MIN)
            self.fig._graffiti_adjusting = False
            self.fig.canvas.draw_idle()

        leg = self.ax.get_legend()
        if leg and getattr(leg, '_loc', None) == 0:
            try:
                bbox = leg.get_window_extent()
                if bbox.width > 0 and bbox.height > 0:
                    bbox_axes = bbox.transformed(self.ax.transAxes.inverted())
                    leg.set_bbox_to_anchor((bbox_axes.x0, bbox_axes.y0, bbox_axes.width, bbox_axes.height))
                    leg._loc = 3
            except Exception: pass

    def _apply_xlim(self, xlim):
        if getattr(self.fig, '_graffiti_linked_x', False):
            for axis in self.fig.axes: axis.set_xlim(xlim)
        else:
            self.ax.set_xlim(xlim)

    def _on_key(self, event):
        if event.inaxes != self.ax: return
        key = event.key.lower() if event.key else ''
        if   key == 'l':      _handle_global_action(self.fig, 'logy',  self.ax)
        elif key == 'k':      _handle_global_action(self.fig, 'logx',  self.ax)
        elif key == 'g':      _handle_global_action(self.fig, 'grid',  self.ax)
        elif key == 'x':      _handle_global_action(self.fig, 'link',  self.ax)
        elif key == 'a':      _handle_global_action(self.fig, 'autoy', self.ax)
        elif key == 'h':      _handle_global_action(self.fig, 'hover', self.ax)
        elif key == 'f':      _handle_global_action(self.fig, 'fit',   self.ax)
        elif key == 'o':      _handle_global_action(self.fig, 'out')
        elif key == 'c':      _handle_global_action(self.fig, 'clear', self.ax)
        elif key == 'escape': _handle_global_action(self.fig, 'clear', self.ax)
        elif key == '[':      _handle_global_action(self.fig, 'back',  self.ax)
        elif key == ']':      _handle_global_action(self.fig, 'fwd',   self.ax)

    def _on_scroll(self, event):
        if event.inaxes != self.ax: return
        self._push_zoom_state()
        scale = _SCROLL_ZOOM_IN_FACTOR if event.button == 'up' else _SCROLL_ZOOM_OUT_FACTOR
        cur_xlim, cur_ylim = self.ax.get_xlim(), self.ax.get_ylim()

        if self.ax.get_xscale() == 'log' and event.xdata > 0:
            log_cur, log_x = np.log10(cur_xlim), np.log10(event.xdata)
            new_xlim = 10 ** np.array([log_x - (log_x - log_cur[0]) * scale,
                                       log_x + (log_cur[1] - log_x) * scale])
        else:
            new_xlim = [event.xdata - (event.xdata - cur_xlim[0]) * scale,
                        event.xdata + (cur_xlim[1] - event.xdata) * scale]

        if self.ax.get_yscale() == 'log' and event.ydata > 0:
            log_cur, log_y = np.log10(cur_ylim), np.log10(event.ydata)
            new_ylim = 10 ** np.array([log_y - (log_y - log_cur[0]) * scale,
                                       log_y + (log_cur[1] - log_y) * scale])
        else:
            new_ylim = [event.ydata - (event.ydata - cur_ylim[0]) * scale,
                        event.ydata + (cur_ylim[1] - event.ydata) * scale]

        self._apply_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.fig.canvas.draw_idle()

    def _on_press(self, event):
        if event.inaxes != self.ax: return

        leg = self.ax.get_legend()
        if leg is not None and leg.contains(event)[0]: return

        if event.button == 1 and event.dblclick:
            # Double-click: clear cursors and reset to original view
            for axis in self.fig.axes:
                interactor = getattr(axis, '_plotly_interactor', None)
                if interactor and hasattr(interactor, '_scope_clear'):
                    interactor._scope_clear()
            axes_to_reset = self.fig.axes if getattr(self.fig, '_graffiti_linked_x', False) else [self.ax]
            for axis in axes_to_reset:
                interactor = getattr(axis, '_plotly_interactor', None)
                if interactor and interactor._limits_captured:
                    axis.set_xlim(interactor._original_xlim)
                    axis.set_ylim(interactor._original_ylim)
                else:
                    axis.relim()
                    axis.autoscale()
            self.fig.canvas.draw_idle()
            return

        if event.button == 2:
            self._is_panning = True
            self._pan_start_px = (event.x, event.y)
            self._pan_start_xlim, self._pan_start_ylim = self.ax.get_xlim(), self.ax.get_ylim()
            self._annot.set_visible(False)
            self._cursor.visible = False
            return

        if event.button == 1:
            self._scope_click_start = (event.xdata, event.ydata, event.x, event.y)
            if self._toolbar and self._toolbar.mode != '': return
            self._is_dragging = True
            self._start_data, self._start_px = (event.xdata, event.ydata), (event.x, event.y)
            self._zoom_rect.set_visible(True)
            self._zoom_mode = 'box'
            self._annot.set_visible(False)

    def _on_motion(self, event):
        hover_enabled = getattr(self.fig, '_menu_hover_state', True)

        if not self._is_dragging and not self._is_panning:
            if event.inaxes == self.ax:
                self._update_scope_preview(event.x, event.y, getattr(event, 'xdata', None))
                if hover_enabled:
                    self._update_hover_tooltip(event)
            else:
                self._scope_preview_v.set_visible(False)
                self._scope_preview_h.set_visible(False)
                self._scope_preview_pt.set_visible(False)
                if not hover_enabled and self._annot.get_visible():
                    self._annot.set_visible(False)
                self.fig.canvas.draw_idle()
            return

        x_px = event.x if event.x is not None else self._start_px[0]
        y_px = event.y if event.y is not None else self._start_px[1]

        if self._is_panning:
            dx_px = x_px - self._pan_start_px[0]
            dy_px = y_px - self._pan_start_px[1]
            bbox = self.ax.get_window_extent()
            dx_data = dx_px * ((self._pan_start_xlim[1] - self._pan_start_xlim[0]) / bbox.width)
            dy_data = dy_px * ((self._pan_start_ylim[1] - self._pan_start_ylim[0]) / bbox.height)
            self._apply_xlim((self._pan_start_xlim[0] - dx_data, self._pan_start_xlim[1] - dx_data))
            self.ax.set_ylim(self._pan_start_ylim[0] - dy_data, self._pan_start_ylim[1] - dy_data)
            self.fig.canvas.draw_idle()
            return

        if self._is_dragging:
            bbox = self.ax.patch.get_window_extent()
            clamp_x_px = max(bbox.x0, min(x_px, bbox.x1))
            clamp_y_px = max(bbox.y0, min(y_px, bbox.y1))
            x1, y1 = self.ax.transData.inverted().transform((clamp_x_px, clamp_y_px))
            x0, y0 = self._start_data
            px_dx = abs(x_px - self._start_px[0])
            px_dy = abs(y_px - self._start_px[1])
            x_min_ax, x_max_ax = sorted(self.ax.get_xlim())
            y_min_ax, y_max_ax = sorted(self.ax.get_ylim())

            snap_x = px_dx >= _ZOOM_FULL_RATIO * bbox.width
            snap_y = px_dy >= _ZOOM_FULL_RATIO * bbox.height

            if not snap_x and not snap_y and px_dx > _ZOOM_AXIS_RATIO * px_dy and px_dx > _ZOOM_PIXEL_MIN:
                self._zoom_mode = 'h'
                self._zoom_rect.set_bounds(min(x0, x1), y_min_ax, abs(x1 - x0), y_max_ax - y_min_ax)
            elif not snap_x and not snap_y and px_dy > _ZOOM_AXIS_RATIO * px_dx and px_dy > _ZOOM_PIXEL_MIN:
                self._zoom_mode = 'v'
                self._zoom_rect.set_bounds(x_min_ax, min(y0, y1), x_max_ax - x_min_ax, abs(y1 - y0))
            else:
                self._zoom_mode = 'box'
                rx = x_min_ax if snap_x else min(x0, x1)
                rw = (x_max_ax - x_min_ax) if snap_x else abs(x1 - x0)
                ry = y_min_ax if snap_y else min(y0, y1)
                rh = (y_max_ax - y_min_ax) if snap_y else abs(y1 - y0)
                self._zoom_rect.set_bounds(rx, ry, rw, rh)
            self.fig.canvas.draw_idle()

    def _find_nearest_data_point(self, x_px, y_px, x_data_vertical=None):
        """Return (data_point, label, dist²) for the closest visible data point, or None."""
        if x_px is None or y_px is None:
            return None

        min_dist, closest_data, closest_label = float('inf'), None, None

        if x_data_vertical is not None:
            for line in self.ax.get_lines():
                if not line.get_visible(): continue
                label = line.get_label()
                if label.startswith('_'): continue
                xdata = np.asarray(line.get_xdata(), dtype=float)
                ydata = np.asarray(line.get_ydata(), dtype=float)
                if len(xdata) == 0: continue
                idx = np.argmin(np.abs(xdata - x_data_vertical))
                x_snap, y_snap = float(xdata[idx]), float(ydata[idx])
                pt_px = self.ax.transData.transform((x_snap, y_snap))
                dist_sq = (pt_px[0] - x_px)**2 + (pt_px[1] - y_px)**2
                if dist_sq < min_dist:
                    min_dist, closest_data, closest_label = dist_sq, (x_snap, y_snap), label
        else:
            for line in self.ax.get_lines():
                if not line.get_visible(): continue
                label = line.get_label()
                if label.startswith('_'): continue
                xdata, ydata = line.get_xdata(), line.get_ydata()
                if len(xdata) == 0: continue
                pts = self.ax.transData.transform(np.column_stack((xdata, ydata)))
                dists = (pts[:, 0] - x_px)**2 + (pts[:, 1] - y_px)**2
                idx = np.argmin(dists)
                if dists[idx] < min_dist:
                    min_dist, closest_data, closest_label = dists[idx], (xdata[idx], ydata[idx]), label

        if closest_data is None:
            return None
        return closest_data, closest_label, min_dist

    def _update_hover_tooltip(self, event):
        """Show an annotation near the nearest data point when within pixel threshold."""
        result = self._find_nearest_data_point(event.x, event.y, x_data_vertical=getattr(event, 'xdata', None))
        needs_redraw = False

        if result is not None:
            closest_data, closest_label, min_dist = result
        else:
            closest_data, closest_label, min_dist = None, None, float('inf')

        if closest_data is not None and (not _HOVER_PIXEL_THRESHOLD_ON or min_dist < _HOVER_PIXEL_THRESHOLD_SQ):
            x_str = self._format_si(closest_data[0], self._si_unit_x)
            y_str = self._format_si(closest_data[1], self._si_unit_y)
            new_text = f"{closest_label}\nX: {x_str}\nY: {y_str}"
            if not self._annot.get_visible() or self._annot.get_text() != new_text:
                self._annot.xy = closest_data
                self._annot.set_text(new_text)
                self._annot.set_visible(True)
                needs_redraw = True
        else:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                needs_redraw = True

        if needs_redraw:
            self.fig.canvas.draw_idle()

    def _on_release(self, event):
        if event.button == 2:
            self._is_panning = False
            self._cursor.visible = True
            return

        if getattr(self, '_scope_click_start', None) is not None and event.button == 1:
            xdata, ydata, x_px, y_px = self._scope_click_start
            small_move = (
                event.x is not None and event.y is not None
                and abs(event.x - x_px) < _SCOPE_CLICK_TOLERANCE_PX
                and abs(event.y - y_px) < _SCOPE_CLICK_TOLERANCE_PX
            )
            self._scope_click_start = None
            if small_move:
                x_data = getattr(event, 'xdata', None)
                nearest = self._find_nearest_data_point(event.x, event.y, x_data_vertical=x_data)
                if nearest is not None:
                    closest_data, _, _ = nearest
                    self._scope_place_point(closest_data[0], closest_data[1])
                self._is_dragging = False
                self._zoom_rect.set_visible(False)
                self.fig.canvas.draw_idle()
                return

        if not self._is_dragging: return
        self._is_dragging = False
        self._zoom_rect.set_visible(False)
        self.fig.canvas.draw_idle()

        x_px = event.x if event.x is not None else self._start_px[0]
        y_px = event.y if event.y is not None else self._start_px[1]

        if (abs(x_px - self._start_px[0]) < _SCOPE_CLICK_TOLERANCE_PX
                and abs(y_px - self._start_px[1]) < _SCOPE_CLICK_TOLERANCE_PX):
            return

        self._push_zoom_state()

        bbox = self.ax.patch.get_window_extent()
        clamp_x_px = max(bbox.x0, min(x_px, bbox.x1))
        clamp_y_px = max(bbox.y0, min(y_px, bbox.y1))
        x1, y1 = self.ax.transData.inverted().transform((clamp_x_px, clamp_y_px))
        x0, y0 = self._start_data
        new_xlim = [min(x0, x1), max(x0, x1)]
        new_ylim = [min(y0, y1), max(y0, y1)]

        autoy_enabled = getattr(self.fig, '_menu_autoy_state', False)

        if self._zoom_mode == 'h':
            self._apply_xlim(new_xlim)
            if autoy_enabled: self._autoscale_y_based_on_x(new_xlim)
        elif self._zoom_mode == 'v':
            self.ax.set_ylim(new_ylim)
        else:
            px_dx = abs(x_px - self._start_px[0])
            px_dy = abs(y_px - self._start_px[1])
            if px_dx >= _ZOOM_FULL_RATIO * bbox.width:
                new_xlim = sorted(self.ax.get_xlim())
            if px_dy >= _ZOOM_FULL_RATIO * bbox.height:
                new_ylim = sorted(self.ax.get_ylim())
            self._apply_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)
        self.fig.canvas.draw_idle()

    def _autoscale_y_based_on_x(self, xlim):
        """Auto-scale the Y axis to the data range visible within xlim, with padding."""
        min_y, max_y, has_data = float('inf'), float('-inf'), False
        is_log = self.ax.get_yscale() == 'log'
        for line in self.ax.get_lines():
            if not line.get_visible(): continue
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            if len(x) == 0 or len(y) == 0: continue

            mask = (x >= xlim[0]) & (x <= xlim[1]) & np.isfinite(y)
            if is_log: mask = mask & (y > 0)
            if np.any(mask):
                has_data = True
                min_y = min(min_y, np.min(y[mask]))
                max_y = max(max_y, np.max(y[mask]))

        if has_data and min_y != max_y and np.isfinite(min_y) and np.isfinite(max_y):
            if is_log:
                pad = (max_y / min_y) ** _AUTOY_PAD_FRACTION
                self.ax.set_ylim(min_y / pad, max_y * pad)
            else:
                pad = (max_y - min_y) * _AUTOY_PAD_FRACTION
                self.ax.set_ylim(min_y - pad, max_y + pad)


# =========================================================================
# ENABLE / DISABLE TOGGLE
# =========================================================================
_ENABLED = True  # default: on

def enable():
    """Re-enable graffiti-plot interactivity for all subsequently created figures."""
    global _ENABLED
    _ENABLED = True

def disable():
    """Disable graffiti-plot interactivity for all subsequently created figures.

    After calling this, new figures behave like plain matplotlib (no modebar,
    no zoom history, no cursor tools, etc.).  Figures already open keep
    whatever state they had.  Call ``enable()`` to turn it back on.
    """
    global _ENABLED
    _ENABLED = False

def is_enabled():
    """Return True if graffiti-plot interactivity is currently enabled."""
    return _ENABLED

# =========================================================================
# GLOBAL MONKEY-PATCH ACTIVATION
# =========================================================================
_original_add_subplot = mfigure.Figure.add_subplot
_original_add_axes    = mfigure.Figure.add_axes

def _patched_add_subplot(self, *args, **kwargs):
    ax = _original_add_subplot(self, *args, **kwargs)
    if not _ENABLED: return ax
    if getattr(self, '_is_graffiti_ui', False): return ax
    if not hasattr(ax, '_plotly_interactor'):
        ax._plotly_interactor = PlotlyInteractivity(ax)
    _apply_footer(self.figure)
    _apply_global_modebar(self.figure)
    return ax

def _patched_add_axes(self, *args, **kwargs):
    ax = _original_add_axes(self, *args, **kwargs)
    if not _ENABLED: return ax
    if getattr(self, '_is_graffiti_ui', False): return ax
    if not hasattr(ax, '_plotly_interactor'):
        ax._plotly_interactor = PlotlyInteractivity(ax)
    _apply_footer(self.figure)
    _apply_global_modebar(self.figure)
    return ax

mfigure.Figure.add_subplot = _patched_add_subplot
mfigure.Figure.add_axes    = _patched_add_axes
mpl.axes.Axes.set_si_units = (
    lambda self, x=None, y=None:
    getattr(self, '_plotly_interactor').set_si_units(x, y)
    if hasattr(self, '_plotly_interactor') else None
)

# -------------------------------------------------------------------------
# Savefig wrapper: hide graffiti UI buttons in exported images
# -------------------------------------------------------------------------
_original_savefig = mfigure.Figure.savefig

def _patched_savefig(self, *args, **kwargs):
    # Hide the modebar buttons (fig.text artists) during save so they don't
    # appear in the output image (and so bbox_inches='tight' ignores them).
    btns = getattr(self, '_graffiti_buttons_refs', None)
    if not btns:
        return _original_savefig(self, *args, **kwargs)

    # Store current visibilities to restore even if savefig fails.
    old_vis = {}
    for _, btn in btns.items():
        try:
            old_vis[btn] = btn.get_visible()
            btn.set_visible(False)
        except Exception:
            # If an artist doesn't support the expected API, just skip it.
            pass

    try:
        # Mark for debugging/testing (non-public).
        old_hidden_flag = getattr(self, '_graffiti_modebar_hidden_for_save', False)
        setattr(self, '_graffiti_modebar_hidden_for_save', True)
        return _original_savefig(self, *args, **kwargs)
    finally:
        for btn, vis in old_vis.items():
            try:
                btn.set_visible(vis)
            except Exception:
                pass
        setattr(self, '_graffiti_modebar_hidden_for_save', old_hidden_flag)

mfigure.Figure.savefig = _patched_savefig
