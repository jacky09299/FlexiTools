import tkinter as tk
from tkinter import ttk, messagebox
from main import Module
import math
from scipy.constants import e, h, hbar

__version__ = "1.0.0"

class QuantumCircuitToolsModule(Module):
    def __init__(self, master, shared_state, module_name="Quantum Circuit Tools", gui_manager=None):
        self.header_label = None
        self.lf_ec = None
        self.lf_el = None
        self.lf_tr = None
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

        # --- Section 3: Transmon Solver ---
        lf_tr = ttk.LabelFrame(main_frame, text="Transmon Solver (E_C, E_J, f)", padding=10)
        lf_tr.pack(fill=tk.X, pady=5)
        
        ttk.Label(lf_tr, text="Input any TWO values and click Calculate. All units are in GHz.", font=("Helvetica", 9, "italic")).grid(row=0, column=0, columnspan=7, padx=5, pady=(0, 10), sticky=tk.W)

        ttk.Label(lf_tr, text="EC (GHz):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.tr_ec_var = tk.StringVar()
        ttk.Entry(lf_tr, textvariable=self.tr_ec_var, width=12).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(lf_tr, text="EJ (GHz):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.tr_ej_var = tk.StringVar()
        ttk.Entry(lf_tr, textvariable=self.tr_ej_var, width=12).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(lf_tr, text="f (GHz):").grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)
        self.tr_f_var = tk.StringVar()
        ttk.Entry(lf_tr, textvariable=self.tr_f_var, width=12).grid(row=1, column=5, padx=5, pady=5)

        ttk.Button(lf_tr, text="Calculate", command=self.calc_transmon).grid(row=1, column=6, padx=15, pady=5)

        # Version label
        ttk.Label(main_frame, text=f"v{__version__}", foreground="gray").pack(side=tk.BOTTOM, anchor=tk.SE)

        self.lf_ec = lf_ec
        self.lf_el = lf_el
        self.lf_tr = lf_tr

    def update_language(self):
        super().update_language()
        if getattr(self, 'header_label', None) is None:
            return
            
        self.header_label.config(text=self.tr("module_qc_title", "Quantum Circuit Tools"))
        self.lf_ec.config(text=self.tr("module_qc_ec_frame", "Capacitance / Charging Energy (C <-> EC)"))
        self.lf_el.config(text=self.tr("module_qc_el_frame", "Inductance / Inductive Energy (L <-> EL)"))
        self.lf_tr.config(text=self.tr("module_qc_tr_frame", "Transmon Solver (E_C, E_J, f)"))

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

    def calc_transmon(self):
        ec_str = self.tr_ec_var.get().strip()
        ej_str = self.tr_ej_var.get().strip()
        f_str = self.tr_f_var.get().strip()
        
        vals = {}
        if ec_str: vals['EC'] = float(ec_str)
        if ej_str: vals['EJ'] = float(ej_str)
        if f_str: vals['f'] = float(f_str)
        
        if len(vals) != 2:
            self.shared_state.log("QuantumCircuitTools: Please input exactly TWO values.")
            return
            
        try:
            if 'EC' in vals and 'EJ' in vals:
                ans_f = math.sqrt(8 * vals['EC'] * vals['EJ']) - vals['EC']
                self.tr_f_var.set(f"{ans_f:.6f}")
            elif 'EC' in vals and 'f' in vals:
                ans_ej = ((vals['f'] + vals['EC']) ** 2) / (8 * vals['EC'])
                self.tr_ej_var.set(f"{ans_ej:.6f}")
            elif 'EJ' in vals and 'f' in vals:
                inner = 4 * (vals['EJ'] ** 2) - 2 * vals['f'] * vals['EJ']
                if inner < 0:
                    self.shared_state.log("QuantumCircuitTools: No real solution for transmon regime (requires EJ > f / 2).")
                    return
                ans_ec = 4 * vals['EJ'] - vals['f'] - 2 * math.sqrt(inner)
                self.tr_ec_var.set(f"{ans_ec:.6f}")
        except Exception as ex:
            self.shared_state.log(f"QuantumCircuitTools: Calculation error: {ex}")
