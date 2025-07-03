import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
from main import Module # Added import

# Configuration: Add physical quantities and corresponding units here
quantity_units = {
    'None': [''],
    'Length': ['pm', 'nm', 'μm', 'mm', 'cm', 'dm', 'm', 'km', 'Mm', 'Gm'],
    'Area': ['nm²', 'μm²', 'mm²', 'cm²', 'm²', 'km²'],
    'Volume': ['nm³', 'μm³', 'mm³', 'cm³', 'm³', 'km³', 'L', 'mL', 'μL', 'nL'],
    'Mass': ['fg', 'pg', 'ng', 'μg', 'mg', 'g', 'kg', 't'],
    'Time': ['fs', 'ps', 'ns', 'μs', 'ms', 's', 'min', 'h', 'day', 'yr'],
    'Frequency': ['Hz', 'kHz', 'MHz', 'GHz', 'THz'],
    'Current': ['fA', 'pA', 'nA', 'μA', 'mA', 'A', 'kA'],
    'Voltage': ['μV', 'mV', 'V', 'kV', 'MV'],
    'Resistance': ['μΩ', 'mΩ', 'Ω', 'kΩ', 'MΩ', 'GΩ'],
    'Conductance': ['μS', 'mS', 'S'],
    'Capacitance': ['aF', 'fF', 'pF', 'nF', 'μF', 'mF', 'F'],
    'Inductance': ['pH', 'nH', 'μH', 'mH', 'H'],
    'Power': ['nW', 'μW', 'mW', 'W', 'kW', 'MW', 'GW'],
    'Energy': ['eV', 'meV', 'keV', 'MeV', 'J', 'kJ', 'MJ', 'Wh', 'kWh'],
    'Pressure': ['Pa', 'kPa', 'MPa', 'GPa', 'bar', 'atm', 'mmHg', 'Torr'],
    'Temperature': ['K', '°C', '°F'],
    'Force': ['μN', 'mN', 'N', 'kN', 'MN'],
    'Magnetic Field': ['nT', 'μT', 'mT', 'T'],
    'Luminous Intensity': ['cd', 'mcd', 'μcd'],
    'Amount of Substance': ['mol', 'mmol', 'μmol', 'nmol'],
    'Data Size': ['bit', 'B', 'kB', 'MB', 'GB', 'TB'],
    # 你可以根據需要繼續擴充
}

class PlotGUIModule(Module): # Changed class definition
    def __init__(self, master, shared_state, module_name, gui_manager): # Modified __init__ signature
        super().__init__(master, shared_state, module_name, gui_manager) # Call super
        self.shared_state = shared_state
        self.gui_manager = gui_manager

        # Initialize instance variables
        self.df = None
        self.x_col = None
        self.curve_cols = []

        self.var_x_qty = tk.StringVar()
        self.var_x_unit = tk.StringVar()
        self.var_x_use_qty = tk.BooleanVar(value=False)
        self.var_x_add_unit = tk.BooleanVar(value=True)
        self.var_x_replace_unit = tk.BooleanVar(value=False)

        self.var_y_qty = tk.StringVar()
        self.var_y_unit = tk.StringVar()
        self.var_y_use_qty = tk.BooleanVar(value=True)
        self.var_y_add_unit = tk.BooleanVar(value=True)
        self.var_y_replace_unit = tk.BooleanVar(value=False)

        self.fig, self.ax = plt.subplots(figsize=(6.4, 4.8)) # Keep this early for canvas

        self.create_ui() # Call create_ui

    def create_ui(self): # New method for UI creation
        # --- Main layout frames ---
        # self.frame is provided by the Module base class
        self.frame_top = ttk.Frame(self.frame) # Parent to self.frame
        self.frame_top.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.frame_center = ttk.Frame(self.frame) # Parent to self.frame
        self.frame_center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.frame_left = ttk.Frame(self.frame_center)
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.frame_plot = ttk.Frame(self.frame_center)
        self.frame_plot.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame_bottom = ttk.Frame(self.frame) # Parent to self.frame
        self.frame_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        # --- Top controls: Load (左), Plot (左下), 曲線選擇 (右) ---
        frame_left_top = ttk.Frame(self.frame_top)
        frame_left_top.pack(side=tk.LEFT, anchor='n')

        self.btn_load = ttk.Button(frame_left_top, text="Load Excel", command=self.load_excel)
        self.btn_load.pack(side=tk.TOP, padx=2, anchor='w')

        self.btn_plot = ttk.Button(frame_left_top, text="Plot (Scatter)", command=self.plot_data)
        self.btn_plot.pack(side=tk.TOP, padx=2, pady=(2, 6), anchor='w')

        frame_curve = ttk.Frame(self.frame_top)
        frame_curve.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(frame_curve, text="Select curves to plot:").pack(anchor='w', padx=2)
        self.listbox = tk.Listbox(frame_curve, selectmode=tk.MULTIPLE, exportselection=False, height=4)
        self.listbox.pack(fill=tk.X, padx=2, expand=True)

        # --- Y axis controls (left, vertically centered) ---
        frame_y = ttk.LabelFrame(self.frame_left, text="Y Axis")
        frame_y.pack(anchor='center', pady=0, expand=True)
        ttk.Label(frame_y, text="Quantity:").grid(row=0, column=0, sticky='e')
        self.om_y_qty = ttk.OptionMenu(frame_y, self.var_y_qty, 'None', *quantity_units.keys(), command=self.update_y_units) # Added 'None' as initial
        self.om_y_qty.grid(row=0, column=1, sticky='w')
        ttk.Label(frame_y, text="Unit:").grid(row=1, column=0, sticky='e')
        self.om_y_unit = ttk.OptionMenu(frame_y, self.var_y_unit, '')
        self.om_y_unit.grid(row=1, column=1, sticky='w')
        ttk.Label(frame_y, text="Custom label:").grid(row=2, column=0, sticky='e')
        self.entry_y_label = ttk.Entry(frame_y)
        self.entry_y_label.grid(row=2, column=1, sticky='we')
        self.chk_y_use_qty = ttk.Checkbutton(frame_y, text="以Quantity為標籤", variable=self.var_y_use_qty)
        self.chk_y_use_qty.grid(row=3, column=0, columnspan=2, sticky='w')
        self.chk_y_add_unit = ttk.Checkbutton(frame_y, text="附加單位", variable=self.var_y_add_unit)
        self.chk_y_add_unit.grid(row=4, column=0, columnspan=2, sticky='w')
        self.chk_y_replace_unit = ttk.Checkbutton(frame_y, text="取代單位", variable=self.var_y_replace_unit)
        self.chk_y_replace_unit.grid(row=5, column=0, columnspan=2, sticky='w')

        # --- Plot area (center) ---
        # self.fig, self.ax are initialized in __init__
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_plot) # Parent to self.frame_plot
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        # --- X axis controls (bottom, horizontally centered) ---
        frame_x = ttk.LabelFrame(self.frame_bottom, text="X Axis")
        frame_x.pack(anchor='center', pady=0)
        ttk.Label(frame_x, text="Quantity:").grid(row=0, column=0, sticky='e')
        self.om_x_qty = ttk.OptionMenu(frame_x, self.var_x_qty, 'None', *quantity_units.keys(), command=self.update_x_units) # Added 'None' as initial
        self.om_x_qty.grid(row=0, column=1, sticky='w')
        ttk.Label(frame_x, text="Unit:").grid(row=0, column=2, sticky='e')
        self.om_x_unit = ttk.OptionMenu(frame_x, self.var_x_unit, '')
        self.om_x_unit.grid(row=0, column=3, sticky='w')
        ttk.Label(frame_x, text="Custom label:").grid(row=1, column=0, sticky='e')
        self.entry_x_label = ttk.Entry(frame_x)
        self.entry_x_label.grid(row=1, column=1, sticky='we')
        self.chk_x_use_qty = ttk.Checkbutton(frame_x, text="以Quantity為標籤", variable=self.var_x_use_qty)
        self.chk_x_use_qty.grid(row=2, column=0, columnspan=2, sticky='w')
        self.chk_x_add_unit = ttk.Checkbutton(frame_x, text="附加單位", variable=self.var_x_add_unit)
        self.chk_x_add_unit.grid(row=2, column=2, columnspan=2, sticky='w')
        self.chk_x_replace_unit = ttk.Checkbutton(frame_x, text="取代單位", variable=self.var_x_replace_unit)
        self.chk_x_replace_unit.grid(row=3, column=0, columnspan=4, sticky='w')

        # Set initial values for OptionMenus if not already set by load_excel
        if not self.var_x_qty.get():
            self.var_x_qty.set(list(quantity_units.keys())[0])
            self.update_x_units(self.var_x_qty.get())
        if not self.var_y_qty.get():
            self.var_y_qty.set(list(quantity_units.keys())[0])
            self.update_y_units(self.var_y_qty.get())


    def load_excel(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx;*.xls")]
        )
        if not file_path:
            return
        try:
            self.df = pd.read_excel(file_path)
        except Exception as e:
            messagebox.showerror("Load Failed", str(e))
            return
        cols = list(self.df.columns)
        self.x_col = cols[0]
        self.curve_cols = cols[1:]
        self.listbox.delete(0, tk.END)
        for i, col in enumerate(self.curve_cols):
            self.listbox.insert(tk.END, col)
            self.listbox.selection_set(i)

        # Set default quantities if not already set, which might trigger unit updates
        # This ensures that even if create_ui sets a default, load_excel can override
        # or set it if it was still empty.
        current_x_qty = self.var_x_qty.get()
        if not current_x_qty or current_x_qty == 'None': # Check if it's 'None' or empty
            default_x_qty = list(quantity_units.keys())[0]
            if default_x_qty == 'None' and len(quantity_units.keys()) > 1: # Prefer not 'None' if others exist
                 default_x_qty = list(quantity_units.keys())[1]
            self.var_x_qty.set(default_x_qty)
            self.update_x_units(default_x_qty)

        current_y_qty = self.var_y_qty.get()
        if not current_y_qty or current_y_qty == 'None': # Check if it's 'None' or empty
            default_y_qty = list(quantity_units.keys())[0]
            if default_y_qty == 'None' and len(quantity_units.keys()) > 1: # Prefer not 'None' if others exist
                default_y_qty = list(quantity_units.keys())[1]
            self.var_y_qty.set(default_y_qty)
            self.update_y_units(default_y_qty)


    def update_x_units(self, selected_qty):
        units = quantity_units.get(selected_qty, [])
        menu = self.om_x_unit['menu']
        menu.delete(0, 'end')
        for u in units:
            menu.add_command(label=u, command=lambda value=u: self.var_x_unit.set(value))
        if units:
            self.var_x_unit.set(units[0])
        else:
            self.var_x_unit.set('')

    def update_y_units(self, selected_qty):
        units = quantity_units.get(selected_qty, [])
        menu = self.om_y_unit['menu']
        menu.delete(0, 'end')
        for u in units:
            menu.add_command(label=u, command=lambda value=u: self.var_y_unit.set(value))
        if units:
            self.var_y_unit.set(units[0])
        else:
            self.var_y_unit.set('')

    def plot_data(self):
        if self.df is None:
            messagebox.showwarning("No Data", "Please load an Excel file first.")
            return
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select at least one curve to plot.")
            return

        self.fig.clear()
        self.ax = self.fig.add_subplot(111)

        x_data_column = self.df[self.x_col]

        for idx in sel:
            col = self.curve_cols[idx]
            y_data_column = self.df[col]
            self.ax.scatter(x_data_column, y_data_column, label=col)

        # --- X axis label logic ---
        x_label_from_col_header = re.sub(r"\s*\(.*?\)", "", self.x_col).strip()
        x_unit_match_from_col_header = re.search(r"\((.*?)\)", self.x_col)
        x_unit_from_col_header = x_unit_match_from_col_header.group(1) if x_unit_match_from_col_header else ''

        selected_x_qty_name = self.var_x_qty.get()
        selected_x_unit = self.var_x_unit.get()
        use_selected_x_qty_as_label = self.var_x_use_qty.get()
        add_selected_x_unit_to_label = self.var_x_add_unit.get()
        replace_col_header_x_unit_with_selected = self.var_x_replace_unit.get()
        custom_x_axis_label = self.entry_x_label.get().strip()

        final_x_label_text = ""
        final_x_unit_text = ""

        if custom_x_axis_label:
            final_x_label_text = custom_x_axis_label
            # If custom label, units depend on checkboxes
            if add_selected_x_unit_to_label and selected_x_unit:
                final_x_unit_text = selected_x_unit
        elif use_selected_x_qty_as_label and selected_x_qty_name != 'None':
            final_x_label_text = selected_x_qty_name
            if add_selected_x_unit_to_label and selected_x_unit:
                final_x_unit_text = selected_x_unit
        else: # Use column header
            final_x_label_text = x_label_from_col_header
            if replace_col_header_x_unit_with_selected and add_selected_x_unit_to_label and selected_x_unit:
                final_x_unit_text = selected_x_unit
            elif x_unit_from_col_header:
                final_x_unit_text = x_unit_from_col_header
            elif add_selected_x_unit_to_label and selected_x_unit : # Fallback if col header has no unit
                 final_x_unit_text = selected_x_unit


        if final_x_unit_text:
            self.ax.set_xlabel(f"${final_x_label_text} \\, ({final_x_unit_text})$")
        else:
            self.ax.set_xlabel(f"${final_x_label_text}$")


        # --- Y axis label logic ---
        # Default Y label to first selected curve name if not using quantity/custom
        first_selected_y_col_name = self.curve_cols[sel[0]] if sel else "Y"
        y_label_from_col_header = re.sub(r"\s*\(.*?\)", "", first_selected_y_col_name).strip()
        y_unit_match_from_col_header = re.search(r"\((.*?)\)", first_selected_y_col_name)
        y_unit_from_col_header = y_unit_match_from_col_header.group(1) if y_unit_match_from_col_header else ''
        
        selected_y_qty_name = self.var_y_qty.get()
        selected_y_unit = self.var_y_unit.get()
        use_selected_y_qty_as_label = self.var_y_use_qty.get()
        add_selected_y_unit_to_label = self.var_y_add_unit.get()
        replace_col_header_y_unit_with_selected = self.var_y_replace_unit.get()
        custom_y_axis_label = self.entry_y_label.get().strip()

        final_y_label_text = ""
        final_y_unit_text = ""

        if custom_y_axis_label:
            final_y_label_text = custom_y_axis_label
            if add_selected_y_unit_to_label and selected_y_unit:
                final_y_unit_text = selected_y_unit
        elif use_selected_y_qty_as_label and selected_y_qty_name != 'None':
            final_y_label_text = selected_y_qty_name
            if add_selected_y_unit_to_label and selected_y_unit:
                final_y_unit_text = selected_y_unit
        else: # Use (first selected) column header
            final_y_label_text = y_label_from_col_header
            if replace_col_header_y_unit_with_selected and add_selected_y_unit_to_label and selected_y_unit:
                final_y_unit_text = selected_y_unit
            elif y_unit_from_col_header:
                final_y_unit_text = y_unit_from_col_header
            elif add_selected_y_unit_to_label and selected_y_unit: # Fallback if col header has no unit
                final_y_unit_text = selected_y_unit


        if final_y_unit_text:
            self.ax.set_ylabel(f"${final_y_label_text} \\, ({final_y_unit_text})$")
        else:
            self.ax.set_ylabel(f"${final_y_label_text}$")


        self.ax.set_title(f"${final_y_label_text}$ vs ${final_x_label_text}$")
        self.ax.legend()
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.canvas.draw()
        
        try:
            self.fig.savefig("plot_figure.png", dpi=150)
        except Exception as e:
            messagebox.showerror("Save Plot Error", f"Could not save plot: {e}")

# Removed __main__ block