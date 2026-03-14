import customtkinter as ctk
import numpy as np


class FitWindow(ctk.CTkToplevel):
    def __init__(self, traces, on_fit_success, format_si_func):
        super().__init__()
        self.traces = traces
        self.on_fit_success = on_fit_success
        self.format_si = format_si_func

        try:
            import scipy.optimize
            from . import fits
            self.models = fits.STANDARD_MODELS
        except ImportError as e:
            self.title("graffiti-plot — Error")
            self.geometry("360x140")
            ctk.CTkLabel(
                self,
                text=f"Missing dependency:\n{e}",
                text_color="red",
                font=ctk.CTkFont(size=13),
            ).pack(pady=30, padx=20)
            ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=(0, 20))
            return

        # Window Config
        self.title("graffiti-plot — Curve Fitting")
        self.geometry("950x600")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.lift()
        self.attributes('-topmost', True)
        self.after(500, lambda: self.attributes('-topmost', False))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -----------------------------------
        # LEFT SIDEBAR (scrollable to handle many models)
        # -----------------------------------
        self.sidebar = ctk.CTkScrollableFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Trace Selection
        ctk.CTkLabel(
            self.sidebar, text="1. Select Trace",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(20, 10), padx=20, anchor="w")
        self.trace_var = ctk.StringVar(value=list(self.traces.keys())[0])

        # Group traces visually by plot number if present in label (e.g. "... (Plot 1)")
        prev_plot = None
        for label, data in self.traces.items():
            plot_id = None
            if label.endswith(")") and " (Plot " in label:
                base, rest = label.rsplit(" (Plot ", 1)
                if rest.endswith(")"):
                    num_str = rest[:-1]
                    if num_str.isdigit():
                        plot_id = int(num_str)

            if plot_id is not None and plot_id != prev_plot:
                sep_text = f"Plot {plot_id}"
                ctk.CTkLabel(
                    self.sidebar,
                    text=sep_text,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color="gray"
                ).pack(pady=(12, 2) if prev_plot is not None else (4, 2), padx=20, anchor="w")
                prev_plot = plot_id

            rb = ctk.CTkRadioButton(self.sidebar, text=label, variable=self.trace_var, value=label)
            rb.configure(text_color=data['color'])
            rb.pack(pady=5, padx=20, anchor="w")

        # Model Selection (hidden models are filtered out)
        ctk.CTkLabel(
            self.sidebar, text="2. Select Model",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(25, 10), padx=20, anchor="w")
        self.model_var = ctk.StringVar(value="Gaussian")
        visible_models = [m for m, entry in self.models.items() if not entry[4]]
        for m in visible_models + ["Custom..."]:
            rb = ctk.CTkRadioButton(
                self.sidebar, text=m,
                variable=self.model_var, value=m,
                command=self._on_model_change
            )
            rb.pack(pady=5, padx=20, anchor="w")

        # -----------------------------------
        # MAIN CONTENT AREA
        # -----------------------------------
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Model name label (row 0, above the equation entry)
        self.lbl_model_name = ctk.CTkLabel(
            self.main_frame, text="",
            font=ctk.CTkFont(weight="bold", size=14),
            text_color="#1a73e8",
            anchor="w",
        )
        self.lbl_model_name.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="w")

        # Equation (read-only for built-in models, editable for Custom)
        ctk.CTkLabel(
            self.main_frame, text="Equation:",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=1, column=0, padx=10, pady=(2, 10), sticky="e")
        self.entry_eq = ctk.CTkEntry(self.main_frame)
        self.entry_eq.grid(row=1, column=1, padx=10, pady=(2, 10), sticky="ew")

        # Guesses
        ctk.CTkLabel(
            self.main_frame, text="Guesses (p0):",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")
        self.entry_guess = ctk.CTkEntry(self.main_frame)
        self.entry_guess.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")

        # Execute Button
        self.btn_exec = ctk.CTkButton(
            self.main_frame, text="Execute Fit",
            command=self._execute_fit,
            font=ctk.CTkFont(weight="bold", size=14), height=40
        )
        self.btn_exec.grid(row=3, column=0, columnspan=2, pady=15)

        # Estimation Results
        self.lbl_result = ctk.CTkLabel(
            self.main_frame,
            text="(Run a fit to see estimates...)",
            text_color="gray",
            font=ctk.CTkFont(weight="bold", size=14),
            wraplength=680,
        )
        self.lbl_result.grid(row=4, column=0, columnspan=2, pady=(5, 15))

        # Code Snippet Area
        self.code_frame = ctk.CTkFrame(self.main_frame)
        self.code_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=10)
        self.code_frame.grid_columnconfigure(0, weight=1)
        self.code_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(5, weight=1)

        header_frame = ctk.CTkFrame(self.code_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame, text="Auto-Generated Code:",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.btn_copy = ctk.CTkButton(
            header_frame, text="Copy Code", width=90,
            fg_color="gray", hover_color="darkgray",
            command=self._copy_code
        )
        self.btn_copy.grid(row=0, column=1, sticky="e")

        self.textbox_code = ctk.CTkTextbox(
            self.code_frame,
            font=ctk.CTkFont(family="Courier", size=13),
            activate_scrollbars=True
        )
        self.textbox_code.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.textbox_code.insert("0.0", "# Run a fit to generate the curve_fit code...")

        self._on_model_change()

    def _on_model_change(self):
        m = self.model_var.get()
        if m != "Custom...":
            self.lbl_model_name.configure(text=m)
            _, _, defaults, eq_str, _ = self.models[m]
            self.entry_guess.delete(0, 'end')
            self.entry_guess.insert(0, ", ".join(map(str, defaults)))
            self.entry_eq.delete(0, 'end')
            self.entry_eq.insert(0, eq_str)
            self.entry_eq.configure(state="disabled", fg_color="#e0e0e0", text_color="gray")
        else:
            self.lbl_model_name.configure(text="Custom")
            # Match the other entry (Guesses) so Equation looks identical when editable
            self.entry_eq.configure(
                state="normal",
                fg_color=self.entry_guess.cget("fg_color"),
                text_color=self.entry_guess.cget("text_color"),
            )

        self.lbl_result.configure(text="(Run a fit to see estimates...)", text_color="gray")
        self.textbox_code.delete("0.0", "end")
        self.textbox_code.insert("0.0", "# Run a fit to generate the curve_fit code...")
        self.btn_copy.configure(text="Copy Code")

    def _copy_code(self):
        text = self.textbox_code.get("0.0", "end").strip()
        if text and not text.startswith("# Run"):
            self.clipboard_clear()
            self.clipboard_append(text)
            self.btn_copy.configure(text="Copied!")

    def _parse_si_guess(self, val_str):
        val_str = val_str.strip().replace(' ', '')
        if not val_str: return None
        suffixes = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'k': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}
        last_char = val_str[-1]
        if last_char in suffixes:
            return float(val_str[:-1]) * suffixes[last_char]
        return float(val_str)

    def _execute_fit(self):
        from scipy.optimize import curve_fit

        self.btn_copy.configure(text="Copy Code")
        trace_name = self.trace_var.get()
        model_name = self.model_var.get()

        data = self.traces[trace_name]
        x_data, y_data, line_color = data['x'], data['y'], data['color']
        target_ax = data.get('ax')

        try:
            raw_guesses = [val for val in self.entry_guess.get().split(',') if val.strip()]
            p0 = [self._parse_si_guess(val) for val in raw_guesses] if raw_guesses else None
        except ValueError:
            p0 = None

        if model_name == 'Custom...':
            eq = self.entry_eq.get()
            def custom_func(x, a=1, b=1, c=1, d=1, e=1):
                return eval(eq, {"__builtins__": {}}, {"np": np, "x": x, "a": a, "b": b, "c": c, "d": d, "e": e})
            func = custom_func
            param_names = ['a', 'b', 'c', 'd', 'e'][:len(p0)] if p0 else ['a', 'b', 'c']
        else:
            func, param_names, default_p0, _, _ = self.models[model_name]
            if not p0: p0 = default_p0

        try:
            popt, pcov = curve_fit(func, x_data, y_data, p0=p0)
        except Exception as e:
            self.lbl_result.configure(text=f"Fit failed — check initial guesses.\n{e}",
                                      text_color="#ff4a4a")
            self.textbox_code.delete("0.0", "end")
            self.textbox_code.insert("0.0", f"# Fit failed\n# {e}")
            return

        # Compute ± uncertainty from covariance diagonal
        try:
            perr = np.sqrt(np.diag(pcov))
        except Exception:
            perr = [float('nan')] * len(popt)

        x_fit = np.linspace(min(x_data), max(x_data), 500)
        y_fit = func(x_fit, *popt)

        # Build result string with ±
        parts = []
        for n, v, e in zip(param_names, popt, perr):
            if np.isfinite(e):
                parts.append(f"{n} = {self.format_si(v, None)} ± {e:.2g}")
            else:
                parts.append(f"{n} = {self.format_si(v, None)}")
        param_str = ",  ".join(parts)
        fit_label = f"Fit: {model_name} ({', '.join(f'{n}={v:.3g}' for n, v in zip(param_names, popt))})"

        self.lbl_result.configure(text=param_str, text_color="#00b548")
        self.on_fit_success(x_fit, y_fit, line_color, fit_label, target_ax)

        # Generate code snippet
        p0_formatted = ", ".join([f"{v:.5g}" for v in p0])
        unpack_str = ", ".join(param_names)

        if model_name == 'Custom...':
            code_snippet  = f"# 1. Define custom equation\n"
            code_snippet += f"def custom_fit_func(x, {unpack_str}):\n"
            code_snippet += f"    return {self.entry_eq.get()}\n\n"
            code_snippet += f"# 2. Execute Fit\n"
            code_snippet += f"p0 = [{p0_formatted}]  # Initial Guesses\n"
            code_snippet += f"popt, pcov = curve_fit(custom_fit_func, x, y, p0=p0)\n"
            code_snippet += f"perr = np.sqrt(np.diag(pcov))  # ±1σ uncertainty\n"
            code_snippet += f"{unpack_str} = popt\n"
            code_snippet += f"y_fit = custom_fit_func(x, *popt)"
        else:
            code_snippet  = f"p0 = [{p0_formatted}]  # Guesses for: {unpack_str}\n"
            code_snippet += f"popt, pcov = curve_fit({func.__name__}, x, y, p0=p0)\n"
            code_snippet += f"perr = np.sqrt(np.diag(pcov))  # ±1σ uncertainty\n"
            code_snippet += f"{unpack_str} = popt\n"
            code_snippet += f"y_fit = {func.__name__}(x, *popt)"

        self.textbox_code.delete("0.0", "end")
        self.textbox_code.insert("0.0", code_snippet)
