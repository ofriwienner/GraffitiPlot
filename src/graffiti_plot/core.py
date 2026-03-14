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

# =========================================================================
# macOS BACKEND FIX (AUTO-TRIGGER)
# =========================================================================
current_backend = mpl.get_backend().lower()
if current_backend == 'macosx':
    try:
        plt.switch_backend('TkAgg')
    except Exception as e:
        print(f"[graffiti] WARNING: Could not auto-switch backend. Fit Window may crash. ({e})")

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
# GLOBAL FOOTER & GLOBAL BUTTON CONFIGURATION
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
        0.99, 0.01, final_text, 
        color='gray', fontsize=8, 
        ha='right', va='bottom', alpha=0.7, zorder=100
    )

# -------------------------------------------------------------------------
# GLOBAL MODEBAR (SINGLE TOOLBAR FOR THE ENTIRE FIGURE)
# -------------------------------------------------------------------------
def _apply_global_modebar(fig):
    if hasattr(fig, '_graffiti_modebar'): return
    fig._graffiti_modebar = True

    # Global States
    fig._menu_grid_state = False
    fig._menu_autoy_state = False
    fig._menu_hover_state = True
    fig._graffiti_linked_x = False

    bbox_style = dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='lightgray', alpha=0.9)
    # FIX: Pushed buttons further down the screen
    y_pos = 0.02  
    x_pos = np.linspace(0.1, 0.9, 9)

    btns = {}
    labels = [(" Link X (X) ", 'link'), (" Grid (G) ", 'grid'), (" Auto Y (A) ", 'autoy'),
              (" Hover (H) ", 'hover'), (" Log X (K) ", 'logx'), (" Log Y (L) ", 'logy'),
              (" Fit (F) ", 'fit'), (" Out (O) ", 'out'), (" Clear (C) ", 'clear')]

    fig._graffiti_action_map = {}
    for (i, (text, action)) in enumerate(labels):
        btn = fig.text(x_pos[i], y_pos, text, ha='center', va='bottom', fontsize=8, color='gray', picker=True, bbox=bbox_style, zorder=2000)
        btns[action] = btn
        fig._graffiti_action_map[btn] = action

    fig._graffiti_buttons_refs = btns

    def global_pick(event):
        if event.artist in fig._graffiti_action_map:
            action = fig._graffiti_action_map[event.artist]
            _handle_global_action(fig, action)

    fig.canvas.mpl_connect('pick_event', global_pick)
    _sync_global_button_visuals(fig)

def _sync_global_button_visuals(fig):
    if not hasattr(fig, '_graffiti_buttons_refs'): return
    btns = fig._graffiti_buttons_refs

    btns['grid'].set_color('dodgerblue' if fig._menu_grid_state else 'gray')
    btns['grid'].set_fontweight('bold' if fig._menu_grid_state else 'normal')

    btns['link'].set_color('dodgerblue' if fig._graffiti_linked_x else 'gray')
    btns['link'].set_fontweight('bold' if fig._graffiti_linked_x else 'normal')

    btns['autoy'].set_color('dodgerblue' if fig._menu_autoy_state else 'gray')
    btns['autoy'].set_fontweight('bold' if fig._menu_autoy_state else 'normal')

    btns['hover'].set_color('dodgerblue' if fig._menu_hover_state else 'gray')
    btns['hover'].set_fontweight('bold' if fig._menu_hover_state else 'normal')

    if fig.axes:
        is_log_x = any(ax.get_xscale() == 'log' for ax in fig.axes)
        btns['logx'].set_color('dodgerblue' if is_log_x else 'gray')
        btns['logx'].set_fontweight('bold' if is_log_x else 'normal')

        is_log_y = any(ax.get_yscale() == 'log' for ax in fig.axes)
        btns['logy'].set_color('dodgerblue' if is_log_y else 'gray')
        btns['logy'].set_fontweight('bold' if is_log_y else 'normal')

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
                if interactor and interactor._annot: interactor._annot.set_visible(False)
    elif action == 'logx':
        target_axes = [caller_ax] if caller_ax else fig.axes
        is_log = any(ax.get_xscale() == 'log' for ax in target_axes)
        new_scale = 'linear' if is_log else 'log'
        for ax in target_axes:
            ax.set_xscale(new_scale)
            if new_scale == 'linear':
                interactor = getattr(ax, '_plotly_interactor', None)
                if interactor and interactor._si_unit_x: ax.xaxis.set_major_formatter(EngFormatter(unit=''))
    elif action == 'logy':
        target_axes = [caller_ax] if caller_ax else fig.axes
        is_log = any(ax.get_yscale() == 'log' for ax in target_axes)
        new_scale = 'linear' if is_log else 'log'
        for ax in target_axes:
            ax.set_yscale(new_scale)
            if new_scale == 'linear':
                interactor = getattr(ax, '_plotly_interactor', None)
                if interactor and interactor._si_unit_y: ax.yaxis.set_major_formatter(EngFormatter(unit=''))
    elif action == 'fit':
        target_ax = caller_ax if caller_ax else (fig.axes[0] if fig.axes else None)
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

    _sync_global_button_visuals(fig)
    fig.canvas.draw_idle()


# =========================================================================
# CORE INTERACTIVITY CLASS
# =========================================================================
class PlotlyInteractivity:
    def __init__(self, ax):
        self.ax = ax
        self.fig = ax.figure
        self._legend_mapping = {}
        self._cids = []
        
        self._si_unit_x = None
        self._si_unit_y = None
        
        # FIX: Increased bottom margin to prevent overlap with axis labels
        if self.fig.subplotpars.bottom < 0.20:
            self.fig.subplots_adjust(bottom=0.20)
        
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
        
        self._last_pick_time = 0
        self._last_picked_leg = None
        
        self._zoom_rect = Rectangle((0, 0), 0, 0, facecolor='dodgerblue', alpha=0.3, edgecolor='blue', linewidth=1, visible=False, zorder=1000)
        self._zoom_rect.set_in_layout(False)
        self.ax.add_patch(self._zoom_rect)
        
        self._annot = self.ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9), arrowprops=dict(arrowstyle="->", connectionstyle="arc3"), zorder=1005)
        self._annot.set_in_layout(False)
        self._annot.set_visible(False)
        
        self._cursor = Cursor(self.ax, useblit=True, color='gray', linewidth=0.8, linestyle=':', zorder=999)

        # Scope-style cursors: two points with Δx, Δy display
        self._scope_cursor_1 = None  # (x, y) or None
        self._scope_cursor_2 = None
        self._scope_vline1 = Line2D([0, 0], [0, 1], transform=self.ax.get_xaxis_transform(), color='crimson', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        self._scope_vline2 = Line2D([0, 0], [0, 1], transform=self.ax.get_xaxis_transform(), color='teal', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        self._scope_hline1 = Line2D([0, 1], [0, 0], transform=self.ax.get_yaxis_transform(), color='crimson', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        self._scope_hline2 = Line2D([0, 1], [0, 0], transform=self.ax.get_yaxis_transform(), color='teal', linewidth=1.2, linestyle='--', alpha=0.9, zorder=998)
        for line in (self._scope_vline1, self._scope_vline2, self._scope_hline1, self._scope_hline2):
            line.set_visible(False)
            self.ax.add_line(line)
        self._scope_annot = self.ax.text(0.02, 0.98, '', transform=self.ax.transAxes, fontsize=8, verticalalignment='top',
                                         bbox=dict(boxstyle='round,pad=0.35', facecolor='white', edgecolor='gray', alpha=0.95), zorder=1004)
        self._scope_annot.set_visible(False)
        self._scope_click_start = None  # (xdata, ydata, x_px, y_px) when waiting for release to place cursor

        # Floating preview: half-transparent crosshair + highlighted point at snap-to position
        self._scope_preview_v = Line2D([0, 0], [0, 1], transform=self.ax.get_xaxis_transform(), color='gray', linewidth=1, linestyle='-', alpha=0.5, zorder=997)
        self._scope_preview_h = Line2D([0, 1], [0, 0], transform=self.ax.get_yaxis_transform(), color='gray', linewidth=1, linestyle='-', alpha=0.5, zorder=997)
        self._scope_preview_pt = Line2D([], [], linestyle='', marker='o', markersize=8, markeredgecolor='gray', markerfacecolor='white', markeredgewidth=1.5, alpha=0.95, zorder=1001)
        for art in (self._scope_preview_v, self._scope_preview_h, self._scope_preview_pt):
            art.set_visible(False)
            self.ax.add_line(art)

        self._setup_events()

    # ---------------------------------------------------------
    # SI UNIT INTEGRATION
    # ---------------------------------------------------------
    def set_si_units(self, x=None, y=None):
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
        if unit is None: return f"{val:.3g}"
        if val == 0: return f"0 {unit}"
        mag = math.floor(math.log10(abs(val)) / 3.0) * 3
        mag = max(-15, min(mag, 12))
        prefixes = {12: 'T', 9: 'G', 6: 'M', 3: 'k', 0: '', -3: 'm', -6: 'µ', -9: 'n', -12: 'p', -15: 'f'}
        return f"{val / (10 ** mag):.3g} {prefixes[mag]}{unit}"

    def _scope_clear(self):
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
        if self._scope_cursor_1 is None:
            self._scope_cursor_1 = (float(x), float(y))
        elif self._scope_cursor_2 is None:
            self._scope_cursor_2 = (float(x), float(y))
        else:
            self._scope_cursor_1 = (float(x), float(y))
            self._scope_cursor_2 = None
        self._scope_update_geometry()

    def _scope_update_geometry(self):
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        p1, p2 = self._scope_cursor_1, self._scope_cursor_2

        self._scope_vline1.set_visible(False)
        self._scope_vline2.set_visible(False)
        self._scope_hline1.set_visible(False)
        self._scope_hline2.set_visible(False)
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
            self._scope_annot.set_text(f"C1: ({x1s}, {y1s})\nC2: ({x2s}, {y2s})\nΔx = {dxs}\nΔy = {dys}")
            self._scope_annot.set_visible(True)

        self.fig.canvas.draw_idle()

    # ---------------------------------------------------------
    # INTERACTIVE FIT TOOL UI
    # ---------------------------------------------------------
    def _trigger_fit_window(self):
        print("[graffiti] Fit button clicked! Preparing data...")
        try:
            from .fit_ui import FitWindow
        except ImportError as e:
            print(f"[graffiti] ERROR: Could not load GUI. {e}")
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
                    trace_name = f"{lbl} (Plot {self.fig.axes.index(current_ax)+1})" if len(self.fig.axes) > 1 else lbl
                    traces[trace_name] = {'x': x_f[mask], 'y': y_f[mask], 'color': line.get_color(), 'ax': current_ax}
                    
        if not traces:
            print("[graffiti] ERROR: No valid data in view to fit. Please zoom out.")
            return

        def on_success(x_fit, y_fit, color, label, target_ax):
            if target_ax is None:
                target_ax = self.fig.axes[0] if self.fig.axes else None
            if target_ax is None:
                return
            target_ax.plot(x_fit, y_fit, linestyle='--', color=color, linewidth=2, alpha=0.85, label=label)
            target_ax.legend()
            self.fig.canvas.draw_idle()

        app = FitWindow(traces=traces, on_fit_success=on_success, format_si_func=self._format_si)

    # ---------------------------------------------------------
    # LEGEND INTERCEPT
    # ---------------------------------------------------------
    def _custom_legend(self, *args, **kwargs):
        leg = self._original_legend(*args, **kwargs)
        if leg is None: return leg

        for cid in self._cids: self.fig.canvas.mpl_disconnect(cid)
        self._cids.clear()
        self._legend_mapping.clear()
        
        handles, labels = self.ax.get_legend_handles_labels()
        leg_handles = getattr(leg, 'legend_handles', getattr(leg, 'legendHandles', []))

        for leg_handle, orig_artist, label in zip(leg_handles, handles, labels):
            leg_handle.set_picker(True)
            leg_handle.set_pickradius(5)
            self._legend_mapping[leg_handle] = (orig_artist, label)

        self._cids.append(self.fig.canvas.mpl_connect('pick_event', self._on_pick))
        return leg

    def _on_pick(self, event):
        if hasattr(self.fig, '_graffiti_action_map') and event.artist in self.fig._graffiti_action_map: return

        leg_handle = event.artist
        if leg_handle not in self._legend_mapping: return
            
        orig_artist, _ = self._legend_mapping[leg_handle]
        current_time = time.time()
        
        if current_time - self._last_pick_time < 0.35 and self._last_picked_leg == leg_handle:
            all_others_hidden = all(not art.get_visible() for lh, (art, _) in self._legend_mapping.items() if lh != leg_handle)
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
        self.fig.canvas.mpl_connect('button_press_event', self._on_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key)
        self.fig.canvas.mpl_connect('draw_event', self._on_draw)

    def _on_draw(self, event):
        if not self._limits_captured:
            self._original_xlim = self.ax.get_xlim()
            self._original_ylim = self.ax.get_ylim()
            self._limits_captured = True

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
        else: self.ax.set_xlim(xlim)

    def _on_key(self, event):
        if event.inaxes != self.ax: return
        key = event.key.lower() if event.key else ''
        if key == 'l': _handle_global_action(self.fig, 'logy', self.ax)
        elif key == 'k': _handle_global_action(self.fig, 'logx', self.ax)
        elif key == 'g': _handle_global_action(self.fig, 'grid', self.ax)
        elif key == 'x': _handle_global_action(self.fig, 'link', self.ax)
        elif key == 'a': _handle_global_action(self.fig, 'autoy', self.ax)
        elif key == 'h': _handle_global_action(self.fig, 'hover', self.ax)
        elif key == 'f': _handle_global_action(self.fig, 'fit', self.ax)
        elif key == 'o': _handle_global_action(self.fig, 'out')
        elif key == 'c': _handle_global_action(self.fig, 'clear', self.ax)
        elif key == 'escape': _handle_global_action(self.fig, 'clear', self.ax)

    def _on_scroll(self, event):
        if event.inaxes != self.ax: return
        scale = 0.9 if event.button == 'up' else 1.1
        cur_xlim, cur_ylim = self.ax.get_xlim(), self.ax.get_ylim()
        
        if self.ax.get_xscale() == 'log' and event.xdata > 0:
            log_cur, log_x = np.log10(cur_xlim), np.log10(event.xdata)
            new_xlim = 10 ** np.array([log_x - (log_x - log_cur[0]) * scale, log_x + (log_cur[1] - log_x) * scale])
        else: new_xlim = [event.xdata - (event.xdata - cur_xlim[0]) * scale, event.xdata + (cur_xlim[1] - event.xdata) * scale]
                        
        if self.ax.get_yscale() == 'log' and event.ydata > 0:
            log_cur, log_y = np.log10(cur_ylim), np.log10(event.ydata)
            new_ylim = 10 ** np.array([log_y - (log_y - log_cur[0]) * scale, log_y + (log_cur[1] - log_y) * scale])
        else: new_ylim = [event.ydata - (event.ydata - cur_ylim[0]) * scale, event.ydata + (cur_ylim[1] - event.ydata) * scale]
                    
        self._apply_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.fig.canvas.draw_idle()

    def _on_press(self, event):
        if event.inaxes != self.ax: return
        
        leg = self.ax.get_legend()
        if leg is not None and leg.contains(event)[0]: return
            
        if event.button == 1 and event.dblclick:
            # Double-click to reset view: also clear scope cursors so no new cursor is left behind
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
            dx_px, dy_px = x_px - self._pan_start_px[0], y_px - self._pan_start_px[1]
            bbox = self.ax.get_window_extent()
            dx_data = dx_px * ((self._pan_start_xlim[1] - self._pan_start_xlim[0]) / bbox.width)
            dy_data = dy_px * ((self._pan_start_ylim[1] - self._pan_start_ylim[0]) / bbox.height)
            
            self._apply_xlim((self._pan_start_xlim[0] - dx_data, self._pan_start_xlim[1] - dx_data))
            self.ax.set_ylim(self._pan_start_ylim[0] - dy_data, self._pan_start_ylim[1] - dy_data)
            self.fig.canvas.draw_idle()
            return
            
        if self._is_dragging:
            bbox = self.ax.patch.get_window_extent()
            clamp_x_px, clamp_y_px = max(bbox.x0, min(x_px, bbox.x1)), max(bbox.y0, min(y_px, bbox.y1))
            x1, y1 = self.ax.transData.inverted().transform((clamp_x_px, clamp_y_px))
            x0, y0 = self._start_data
            px_dx, px_dy = abs(x_px - self._start_px[0]), abs(y_px - self._start_px[1])
            x_min_ax, x_max_ax = sorted(self.ax.get_xlim())
            y_min_ax, y_max_ax = sorted(self.ax.get_ylim())
            
            ratio = 2.5 
            if px_dx > ratio * px_dy and px_dx > 10:
                self._zoom_mode = 'h'
                self._zoom_rect.set_bounds(min(x0, x1), y_min_ax, abs(x1 - x0), y_max_ax - y_min_ax)
            elif px_dy > ratio * px_dx and px_dy > 10:
                self._zoom_mode = 'v'
                self._zoom_rect.set_bounds(x_min_ax, min(y0, y1), x_max_ax - x_min_ax, abs(y1 - y0))
            else:
                self._zoom_mode = 'box'
                self._zoom_rect.set_bounds(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            self.fig.canvas.draw_idle()

    def _find_nearest_data_point(self, x_px, y_px, x_data_vertical=None):
        if x_px is None or y_px is None:
            return None

        min_dist, closest_data, closest_label = float('inf'), None, None

        if x_data_vertical is not None:
            # Snap to point on same x (vertical): for each line take point with x closest to x_data_vertical, then pick by screen distance
            for line in self.ax.get_lines():
                if not line.get_visible():
                    continue
                label = line.get_label()
                if label.startswith('_'):
                    continue
                xdata = np.asarray(line.get_xdata(), dtype=float)
                ydata = np.asarray(line.get_ydata(), dtype=float)
                if len(xdata) == 0:
                    continue
                idx = np.argmin(np.abs(xdata - x_data_vertical))
                x_snap, y_snap = float(xdata[idx]), float(ydata[idx])
                pt_px = self.ax.transData.transform((x_snap, y_snap))
                dist_sq = (pt_px[0] - x_px)**2 + (pt_px[1] - y_px)**2
                if dist_sq < min_dist:
                    min_dist, closest_data, closest_label = dist_sq, (x_snap, y_snap), label
        else:
            # Nearest point by 2D pixel distance (e.g. for hover)
            for line in self.ax.get_lines():
                if not line.get_visible():
                    continue
                label = line.get_label()
                if label.startswith('_'):
                    continue
                xdata, ydata = line.get_xdata(), line.get_ydata()
                if len(xdata) == 0:
                    continue
                pts = self.ax.transData.transform(np.column_stack((xdata, ydata)))
                dists = (pts[:, 0] - x_px)**2 + (pts[:, 1] - y_px)**2
                idx = np.argmin(dists)
                if dists[idx] < min_dist:
                    min_dist, closest_data, closest_label = dists[idx], (xdata[idx], ydata[idx]), label

        if closest_data is None:
            return None
        return closest_data, closest_label, min_dist

    def _update_hover_tooltip(self, event):
        result = self._find_nearest_data_point(event.x, event.y)
        needs_redraw = False

        if result is not None:
            closest_data, closest_label, min_dist = result
        else:
            closest_data, closest_label, min_dist = None, None, float('inf')

        if closest_data is not None and min_dist < 225:
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
            small_move = event.x is not None and event.y is not None and abs(event.x - x_px) < 5 and abs(event.y - y_px) < 5
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

        if abs(x_px - self._start_px[0]) < 5 and abs(y_px - self._start_px[1]) < 5: return

        bbox = self.ax.patch.get_window_extent()
        clamp_x_px, clamp_y_px = max(bbox.x0, min(x_px, bbox.x1)), max(bbox.y0, min(y_px, bbox.y1))
        x1, y1 = self.ax.transData.inverted().transform((clamp_x_px, clamp_y_px))
        x0, y0 = self._start_data
        new_xlim, new_ylim = [min(x0, x1), max(x0, x1)], [min(y0, y1), max(y0, y1)]

        autoy_enabled = getattr(self.fig, '_menu_autoy_state', False)

        if self._zoom_mode == 'h':
            self._apply_xlim(new_xlim)
            if autoy_enabled: self._autoscale_y_based_on_x(new_xlim)
        elif self._zoom_mode == 'v':
            self.ax.set_ylim(new_ylim)
        else:
            self._apply_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)
        self.fig.canvas.draw_idle()

    def _autoscale_y_based_on_x(self, xlim):
        min_y, max_y, has_data, is_log = float('inf'), float('-inf'), False, self.ax.get_yscale() == 'log'
        for line in self.ax.get_lines():
            if not line.get_visible(): continue
            x, y = np.asarray(line.get_xdata(), dtype=float), np.asarray(line.get_ydata(), dtype=float)
            if len(x) == 0 or len(y) == 0: continue
            
            mask = (x >= xlim[0]) & (x <= xlim[1]) & np.isfinite(y)
            if is_log: mask = mask & (y > 0) 
            if np.any(mask):
                has_data, min_y, max_y = True, min(min_y, np.min(y[mask])), max(max_y, np.max(y[mask]))
                
        if has_data and min_y != max_y and np.isfinite(min_y) and np.isfinite(max_y):
            if is_log:
                pad = (max_y / min_y) ** 0.05
                self.ax.set_ylim(min_y / pad, max_y * pad)
            else:
                pad = (max_y - min_y) * 0.05
                self.ax.set_ylim(min_y - pad, max_y + pad)

# =========================================================================
# GLOBAL MONKEY-PATCH ACTIVATION
# =========================================================================
_original_add_subplot = mfigure.Figure.add_subplot
_original_add_axes = mfigure.Figure.add_axes

def _patched_add_subplot(self, *args, **kwargs):
    ax = _original_add_subplot(self, *args, **kwargs)
    if getattr(self, '_is_graffiti_ui', False): return ax
    if not hasattr(ax, '_plotly_interactor'): ax._plotly_interactor = PlotlyInteractivity(ax)
    _apply_footer(self.figure) 
    _apply_global_modebar(self.figure)
    return ax

def _patched_add_axes(self, *args, **kwargs):
    ax = _original_add_axes(self, *args, **kwargs)
    if getattr(self, '_is_graffiti_ui', False): return ax
    if not hasattr(ax, '_plotly_interactor'): ax._plotly_interactor = PlotlyInteractivity(ax)
    _apply_footer(self.figure) 
    _apply_global_modebar(self.figure)
    return ax

mfigure.Figure.add_subplot = _patched_add_subplot
mfigure.Figure.add_axes = _patched_add_axes
mpl.axes.Axes.set_si_units = lambda self, x=None, y=None: getattr(self, '_plotly_interactor').set_si_units(x, y) if hasattr(self, '_plotly_interactor') else None
