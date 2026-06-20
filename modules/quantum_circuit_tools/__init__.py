import tkinter as tk
from tkinter import ttk, messagebox
from main import Module
import math
from scipy.constants import e, h, hbar

__version__ = "1.2.0"

class QuantumCircuitToolsModule(Module):
    def __init__(self, master, shared_state, module_name="Quantum Circuit Tools", gui_manager=None):
        self.header_label = None
        self.lf_ec = None
        self.lf_el = None
        self.lf_reso = None
        self.lf_tr = None
        self.transmon_tabs = []
        self.transmon_counter = 0
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"QuantumCircuitTools '{self.module_name}' initialized.")
        
        self.create_ui()
        self.update_language()

    def create_ui(self):
        main_frame = ttk.Frame(self.frame, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        self.header_label = ttk.Label(main_frame, text="Quantum Circuit Tools", font=("Helvetica", 14, "bold"))
        self.header_label.pack(pady=(0, 15))

        # --- Section 1: C <-> EC ---
        lf_ec = ttk.LabelFrame(main_frame, text="Capacitance / Charging Energy (C <-> EC)", padding=10)
        lf_ec.pack(fill=tk.X, pady=5)

        ttk.Label(lf_ec, text="C (fF):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.c_var = tk.StringVar()
        ttk.Entry(lf_ec, textvariable=self.c_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(lf_ec, text="C ➔ EC", command=self.calc_c_to_ec).grid(row=0, column=2, padx=10, pady=5)
        ttk.Button(lf_ec, text="EC ➔ C", command=self.calc_ec_to_c).grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(lf_ec, text="EC (GHz):").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.ec_var = tk.StringVar()
        ttk.Entry(lf_ec, textvariable=self.ec_var, width=15).grid(row=0, column=5, padx=5, pady=5)

        # --- Section 2: L <-> EL ---
        lf_el = ttk.LabelFrame(main_frame, text="Inductance / Inductive Energy (L <-> EL)", padding=10)
        lf_el.pack(fill=tk.X, pady=10)

        ttk.Label(lf_el, text="L (nH):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.l_var = tk.StringVar()
        ttk.Entry(lf_el, textvariable=self.l_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(lf_el, text="L ➔ EL", command=self.calc_l_to_el).grid(row=0, column=2, padx=10, pady=5)
        ttk.Button(lf_el, text="EL ➔ L", command=self.calc_el_to_l).grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(lf_el, text="EL (GHz):").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.el_var = tk.StringVar()
        ttk.Entry(lf_el, textvariable=self.el_var, width=15).grid(row=0, column=5, padx=5, pady=5)

        # --- Section 3: LC Resonator Solver ---
        lf_reso = ttk.LabelFrame(main_frame, text="LC Resonator Solver (L, C, f, Z0)", padding=10)
        lf_reso.pack(fill=tk.X, pady=10)
        
        ttk.Label(lf_reso, text="Input any TWO values to solve for the others. C(fF), L(nH), f(GHz), Z0(Ω)", font=("Helvetica", 9, "italic")).grid(row=0, column=0, columnspan=9, padx=5, pady=(0, 5), sticky=tk.W)

        ttk.Label(lf_reso, text="L (nH):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.reso_l_var = tk.StringVar()
        ttk.Entry(lf_reso, textvariable=self.reso_l_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(lf_reso, text="C (fF):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.reso_c_var = tk.StringVar()
        ttk.Entry(lf_reso, textvariable=self.reso_c_var, width=10).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(lf_reso, text="f (GHz):").grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)
        self.reso_f_var = tk.StringVar()
        ttk.Entry(lf_reso, textvariable=self.reso_f_var, width=10).grid(row=1, column=5, padx=5, pady=5)

        ttk.Label(lf_reso, text="Z0 (Ω):").grid(row=1, column=6, padx=5, pady=5, sticky=tk.W)
        self.reso_z0_var = tk.StringVar()
        ttk.Entry(lf_reso, textvariable=self.reso_z0_var, width=10).grid(row=1, column=7, padx=5, pady=5)

        ttk.Button(lf_reso, text="Calculate", command=self.calc_resonator).grid(row=1, column=8, padx=15, pady=5)

        # --- Section 4: Transmon Solvers ---
        lf_tr = ttk.LabelFrame(main_frame, text="Transmon Solvers (E_C, E_J, f_01, f_12)", padding=10)
        lf_tr.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(lf_tr, text="Input any TWO values to solve for the other two. All units are in GHz.", font=("Helvetica", 9, "italic")).pack(padx=5, pady=(0, 5), anchor=tk.W)

        btn_frame = ttk.Frame(lf_tr)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="+ Add Transmon Solver", command=self.add_transmon_tab).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Plot Energy Levels", command=self.plot_energy_levels).pack(side=tk.LEFT, padx=5)

        self.tr_notebook = ttk.Notebook(lf_tr)
        self.tr_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.add_transmon_tab()

        # Version label
        ttk.Label(main_frame, text=f"v{__version__}", foreground="gray").pack(side=tk.BOTTOM, anchor=tk.SE)

        self.lf_ec = lf_ec
        self.lf_el = lf_el
        self.lf_reso = lf_reso
        self.lf_tr = lf_tr

    def update_language(self):
        super().update_language()
        if getattr(self, 'header_label', None) is None:
            return
            
        self.header_label.config(text=self.tr("module_qc_title", "Quantum Circuit Tools"))
        self.lf_ec.config(text=self.tr("module_qc_ec_frame", "Capacitance / Charging Energy (C <-> EC)"))
        self.lf_el.config(text=self.tr("module_qc_el_frame", "Inductance / Inductive Energy (L <-> EL)"))
        self.lf_reso.config(text=self.tr("module_qc_reso_frame", "LC Resonator Solver (L, C, f, Z0)"))
        self.lf_tr.config(text=self.tr("module_qc_tr_frame", "Transmon Solvers (E_C, E_J, f_01, f_12)"))

    # --- Math & Logic Functions ---
    def calc_c_to_ec(self):
        try:
            val = float(self.c_var.get())
            if val <= 0: raise ValueError
            C_F = val * 1e-15
            EC_J = (e ** 2) / (2 * C_F)
            EC_Hz = EC_J / h
            self.ec_var.set(f"{EC_Hz * 1e-9:.6f}")
        except Exception:
            self.shared_state.log("QuantumCircuitTools: Invalid C value.")

    def calc_ec_to_c(self):
        try:
            val = float(self.ec_var.get())
            if val <= 0: raise ValueError
            EC_Hz = val * 1e9
            EC_J = EC_Hz * h
            C_F = (e ** 2) / (2 * EC_J)
            self.c_var.set(f"{C_F * 1e15:.4f}")
        except Exception:
            self.shared_state.log("QuantumCircuitTools: Invalid EC value.")

    def calc_l_to_el(self):
        try:
            val = float(self.l_var.get())
            if val <= 0: raise ValueError
            L_H = val * 1e-9
            flux_quantum_reduced = hbar / (2 * e)
            EL_J = (flux_quantum_reduced ** 2) / L_H
            EL_Hz = EL_J / h
            self.el_var.set(f"{EL_Hz * 1e-9:.6f}")
        except Exception:
            self.shared_state.log("QuantumCircuitTools: Invalid L value.")

    def calc_el_to_l(self):
        try:
            val = float(self.el_var.get())
            if val <= 0: raise ValueError
            EL_Hz = val * 1e9
            EL_J = EL_Hz * h
            flux_quantum_reduced = hbar / (2 * e)
            L_H = (flux_quantum_reduced ** 2) / EL_J
            self.l_var.set(f"{L_H * 1e9:.4f}")
        except Exception:
            self.shared_state.log("QuantumCircuitTools: Invalid EL value.")

    def calc_resonator(self):
        l_str = self.reso_l_var.get().strip()
        c_str = self.reso_c_var.get().strip()
        f_str = self.reso_f_var.get().strip()
        z0_str = self.reso_z0_var.get().strip()
        
        vals = {}
        if l_str: vals['L'] = float(l_str)
        if c_str: vals['C'] = float(c_str)
        if f_str: vals['f'] = float(f_str)
        if z0_str: vals['Z0'] = float(z0_str)
        
        if len(vals) != 2:
            self.shared_state.log("QuantumCircuitTools: Please input exactly TWO values for resonator.")
            messagebox.showerror("Error", "Please input exactly TWO values for the resonator.", parent=self.frame)
            return
            
        try:
            if 'L' in vals and 'C' in vals:
                ans_f = 1000.0 / (2 * math.pi * math.sqrt(vals['L'] * vals['C']))
                ans_z0 = 1000.0 * math.sqrt(vals['L'] / vals['C'])
                self.reso_f_var.set(f"{ans_f:.6f}")
                self.reso_z0_var.set(f"{ans_z0:.6f}")
            elif 'L' in vals and 'f' in vals:
                ans_c = 1e6 / (4 * (math.pi**2) * (vals['f']**2) * vals['L'])
                ans_z0 = 2 * math.pi * vals['f'] * vals['L']
                self.reso_c_var.set(f"{ans_c:.6f}")
                self.reso_z0_var.set(f"{ans_z0:.6f}")
            elif 'C' in vals and 'f' in vals:
                ans_l = 1e6 / (4 * (math.pi**2) * (vals['f']**2) * vals['C'])
                ans_z0 = 1e6 / (2 * math.pi * vals['f'] * vals['C'])
                self.reso_l_var.set(f"{ans_l:.6f}")
                self.reso_z0_var.set(f"{ans_z0:.6f}")
            elif 'L' in vals and 'Z0' in vals:
                ans_c = 1e6 * vals['L'] / (vals['Z0']**2)
                ans_f = vals['Z0'] / (2 * math.pi * vals['L'])
                self.reso_c_var.set(f"{ans_c:.6f}")
                self.reso_f_var.set(f"{ans_f:.6f}")
            elif 'C' in vals and 'Z0' in vals:
                ans_l = vals['C'] * (vals['Z0']**2) / 1e6
                ans_f = 1e6 / (2 * math.pi * vals['Z0'] * vals['C'])
                self.reso_l_var.set(f"{ans_l:.6f}")
                self.reso_f_var.set(f"{ans_f:.6f}")
            elif 'f' in vals and 'Z0' in vals:
                ans_l = vals['Z0'] / (2 * math.pi * vals['f'])
                ans_c = 1e6 / (2 * math.pi * vals['f'] * vals['Z0'])
                self.reso_l_var.set(f"{ans_l:.6f}")
                self.reso_c_var.set(f"{ans_c:.6f}")
        except Exception as ex:
            self.shared_state.log(f"QuantumCircuitTools: Calculation error: {ex}")
            messagebox.showerror("Error", f"Calculation error: {ex}", parent=self.frame)

    def add_transmon_tab(self):
        self.transmon_counter += 1
        name = f"Transmon {self.transmon_counter}"
        tab_frame = ttk.Frame(self.tr_notebook, padding=10)
        self.tr_notebook.add(tab_frame, text=name)
        
        vars_dict = {
            'name': name,
            'frame': tab_frame,
            'ec': tk.StringVar(),
            'ej': tk.StringVar(),
            'f01': tk.StringVar(),
            'f12': tk.StringVar()
        }
        self.transmon_tabs.append(vars_dict)
        
        # Row 1
        ttk.Label(tab_frame, text="EC (GHz):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(tab_frame, textvariable=vars_dict['ec'], width=12).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(tab_frame, text="EJ (GHz):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(tab_frame, textvariable=vars_dict['ej'], width=12).grid(row=1, column=3, padx=5, pady=5)

        # Row 2
        ttk.Label(tab_frame, text="f_01 (GHz):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(tab_frame, textvariable=vars_dict['f01'], width=12).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(tab_frame, text="f_12 (GHz):").grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(tab_frame, textvariable=vars_dict['f12'], width=12).grid(row=2, column=3, padx=5, pady=5)

        # Calculate & Delete Buttons
        calc_cmd = lambda v=vars_dict: self.calc_transmon_instance(v)
        del_cmd = lambda v=vars_dict: self.remove_transmon_tab(v)
        
        btn_subframe = ttk.Frame(tab_frame)
        btn_subframe.grid(row=1, column=4, rowspan=2, padx=15, pady=5)
        ttk.Button(btn_subframe, text="Calculate", command=calc_cmd).pack(fill=tk.X, pady=2)
        ttk.Button(btn_subframe, text="Delete", command=del_cmd).pack(fill=tk.X, pady=2)

    def calc_transmon_instance(self, v_dict):
        ec_str = v_dict['ec'].get().strip()
        ej_str = v_dict['ej'].get().strip()
        f01_str = v_dict['f01'].get().strip()
        f12_str = v_dict['f12'].get().strip()
        
        vals = {}
        if ec_str: vals['EC'] = float(ec_str)
        if ej_str: vals['EJ'] = float(ej_str)
        if f01_str: vals['f01'] = float(f01_str)
        if f12_str: vals['f12'] = float(f12_str)
        
        if len(vals) != 2:
            self.shared_state.log("QuantumCircuitTools: Please input exactly TWO values.")
            messagebox.showerror("Error", "Please input exactly TWO values.", parent=self.frame)
            return
            
        try:
            # 1. (EC, EJ)
            if 'EC' in vals and 'EJ' in vals:
                ans_f01 = math.sqrt(8 * vals['EC'] * vals['EJ']) - vals['EC']
                ans_f12 = ans_f01 - vals['EC']
                v_dict['f01'].set(f"{ans_f01:.6f}")
                v_dict['f12'].set(f"{ans_f12:.6f}")
                
            # 2. (EC, f01)
            elif 'EC' in vals and 'f01' in vals:
                ans_ej = ((vals['f01'] + vals['EC']) ** 2) / (8 * vals['EC'])
                ans_f12 = vals['f01'] - vals['EC']
                v_dict['ej'].set(f"{ans_ej:.6f}")
                v_dict['f12'].set(f"{ans_f12:.6f}")

            # 3. (EC, f12)
            elif 'EC' in vals and 'f12' in vals:
                ans_f01 = vals['f12'] + vals['EC']
                ans_ej = ((ans_f01 + vals['EC']) ** 2) / (8 * vals['EC'])
                v_dict['f01'].set(f"{ans_f01:.6f}")
                v_dict['ej'].set(f"{ans_ej:.6f}")

            # 4. (EJ, f01)
            elif 'EJ' in vals and 'f01' in vals:
                inner = 4 * (vals['EJ'] ** 2) - 2 * vals['f01'] * vals['EJ']
                if inner < 0:
                    raise ValueError("No real solution for standard transmon regime (EJ > f01/2 required).")
                ans_ec = 4 * vals['EJ'] - vals['f01'] - 2 * math.sqrt(inner)
                ans_f12 = vals['f01'] - ans_ec
                v_dict['ec'].set(f"{ans_ec:.6f}")
                v_dict['f12'].set(f"{ans_f12:.6f}")

            # 5. (EJ, f12)
            elif 'EJ' in vals and 'f12' in vals:
                inner = vals['EJ']**2 - vals['f12'] * vals['EJ']
                if inner < 0:
                    raise ValueError("No real solution for standard transmon regime (EJ > f12 required).")
                ans_ec = vals['EJ'] - vals['f12']/2 - math.sqrt(inner)
                ans_f01 = vals['f12'] + ans_ec
                v_dict['ec'].set(f"{ans_ec:.6f}")
                v_dict['f01'].set(f"{ans_f01:.6f}")

            # 6. (f01, f12)
            elif 'f01' in vals and 'f12' in vals:
                ans_ec = vals['f01'] - vals['f12']
                if ans_ec <= 0:
                    raise ValueError("f01 must be greater than f12 for a transmon (negative anharmonicity).")
                ans_ej = ((vals['f01'] + ans_ec) ** 2) / (8 * ans_ec)
                v_dict['ec'].set(f"{ans_ec:.6f}")
                v_dict['ej'].set(f"{ans_ej:.6f}")
                
        except Exception as ex:
            self.shared_state.log(f"QuantumCircuitTools: Calculation error: {ex}")
            messagebox.showerror("Error", f"Calculation error: {ex}", parent=self.frame)

    def remove_transmon_tab(self, v_dict):
        self.tr_notebook.forget(v_dict['frame'])
        if v_dict in self.transmon_tabs:
            self.transmon_tabs.remove(v_dict)

    def plot_energy_levels(self):
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            messagebox.showerror("Dependency Error", "Matplotlib is required for plotting.\nPlease run 'pip install matplotlib'.", parent=self.frame)
            return

        qubits_data = []
        for v_dict in self.transmon_tabs:
            name = v_dict['name']
            f01_str = v_dict['f01'].get().strip()
            ec_str = v_dict['ec'].get().strip()
            if not f01_str or not ec_str:
                continue
            try:
                f01 = float(f01_str)
                ec = float(ec_str)
                qubits_data.append((name, f01, ec))
            except ValueError:
                continue

        if not qubits_data:
            messagebox.showerror("Error", "No calculated transmon data available to plot.\nPlease ensure you have calculated EC and f_01 for at least one transmon.", parent=self.frame)
            return

        plot_win = tk.Toplevel(self.frame)
        plot_win.title("Transmon Energy Data")
        plot_win.geometry("900x500")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

        # --- Subplot 1: Energy Level Diagram ---
        for idx, (name, f01, ec) in enumerate(qubits_data):
            x = idx
            levels = [0, f01, 2 * f01 - ec, 3 * f01 - 3 * ec]
            labels = ['|0>', '|1>', '|2>', '|3>']
            for freq, lbl in zip(levels, labels):
                ax1.hlines(freq, x - 0.3, x + 0.3, colors='b', linestyles='solid', lw=2)
                ax1.text(x + 0.35, freq, lbl, va='center', color='darkred', fontweight='bold')

        ax1.set_xticks(range(len(qubits_data)))
        ax1.set_xticklabels([d[0] for d in qubits_data], rotation=15)
        ax1.set_ylabel("Absolute Energy (GHz)", fontsize=11)
        ax1.set_title("Energy Level Diagram", fontsize=13)
        ax1.grid(True, axis='y', linestyle='--', alpha=0.7)

        # --- Subplot 2: Transition Frequencies ---
        import numpy as np
        x_indices = np.arange(len(qubits_data))
        width = 0.35
        
        f01_vals = [d[1] for d in qubits_data]
        f12_vals = [d[1] - d[2] for d in qubits_data]
        
        ax2.bar(x_indices - width/2, f01_vals, width, label='$f_{01}$', color='royalblue')
        ax2.bar(x_indices + width/2, f12_vals, width, label='$f_{12}$', color='darkorange')
        
        ax2.set_xticks(x_indices)
        ax2.set_xticklabels([d[0] for d in qubits_data], rotation=15)
        ax2.set_ylabel("Transition Frequency (GHz)", fontsize=11)
        ax2.set_title("Transitions: $f_{01}$ vs $f_{12}$", fontsize=13)
        ax2.legend()
        ax2.grid(True, axis='y', linestyle='--', alpha=0.7)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=plot_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
