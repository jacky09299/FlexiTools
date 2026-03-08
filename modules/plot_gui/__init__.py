import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
from main import Module

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
    'Logarithmic': ['dB', 'dBm', 'dBW'],
}

class PlotGUIModule(Module):
    def __init__(self, master, shared_state, module_name, gui_manager):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state = shared_state
        self.gui_manager = gui_manager

        # Initialize instance variables
        self.df = None
        self.x_col = None
        self.curve_cols = []
        self.curve_colors = {}
        self.curve_markers = {}

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

        # New variables for plot style and saving
        self.var_save_path = tk.StringVar(value="plot_figure.png")
        self.var_marker_size = tk.DoubleVar(value=5.0)
        self.var_draw_points = tk.BooleanVar(value=True)
        self.var_draw_lines = tk.BooleanVar(value=False)
        self.var_marker_style = tk.StringVar(value='o (Point)')
        self.var_show_grid = tk.BooleanVar(value=False)
        self.var_x_scale_mode = tk.StringVar(value='Linear')
        self.var_y_scale_mode = tk.StringVar(value='Linear')
        self.var_custom_title = tk.StringVar()
        self.var_show_legend = tk.BooleanVar(value=True)
        self.var_line_width = tk.DoubleVar(value=1.0)

        self.fig, self.ax = plt.subplots(figsize=(6.4, 4.8))

        # Initialize widget references
        self.btn_load = None
        self.btn_plot = None
        self.btn_save = None
        self.lbl_title = None
        self.lbl_curves = None
        self.frame_y = None
        self.lbl_y_qty = None
        self.lbl_y_unit = None
        self.lbl_y_custom = None
        self.chk_y_use_qty = None
        self.chk_y_add_unit = None
        self.chk_y_replace_unit = None
        self.frame_save = None
        self.lbl_save_path = None
        self.btn_browse = None
        self.frame_style = None
        self.lbl_marker = None
        self.chk_points = None
        self.chk_lines = None
        self.lbl_linewidth = None
        self.chk_legend = None
        self.frame_grid = None
        self.chk_grid = None
        self.lbl_xscale = None
        self.lbl_yscale = None
        self.frame_x = None
        self.lbl_x_qty = None
        self.lbl_x_unit = None
        self.lbl_x_custom = None
        self.chk_x_use_qty = None
        self.chk_x_add_unit = None
        self.chk_x_replace_unit = None

        self.create_ui()
        self.update_language()

    def create_ui(self):
        # --- Create a canvas with scrollbars ---
        canvas = tk.Canvas(self.frame)
        scrollbar_y = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(self.frame, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)


        # --- Main layout frames ---
        self.frame_top = ttk.Frame(scrollable_frame)
        self.frame_top.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.frame_center = ttk.Frame(scrollable_frame)
        self.frame_center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.frame_left = ttk.Frame(self.frame_center)
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.frame_plot = ttk.Frame(self.frame_center)
        self.frame_plot.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame_bottom = ttk.Frame(scrollable_frame)
        self.frame_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        # --- Top controls ---
        frame_left_top = ttk.Frame(self.frame_top)
        frame_left_top.pack(side=tk.LEFT, anchor='n')

        self.btn_load = ttk.Button(frame_left_top, text="Load Excel", command=self.load_excel)
        self.btn_load.pack(side=tk.TOP, padx=2, anchor='w')

        self.btn_plot = ttk.Button(frame_left_top, text="Plot", command=self.plot_data)
        self.btn_plot.pack(side=tk.TOP, padx=2, pady=(2, 0), anchor='w')

        self.btn_save = ttk.Button(frame_left_top, text="Save Plot", command=self.save_plot)
        self.btn_save.pack(side=tk.TOP, padx=2, pady=(2, 6), anchor='w')


        frame_right_top = ttk.Frame(self.frame_top)
        frame_right_top.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))

        self.lbl_title = ttk.Label(frame_right_top, text="Custom Title:")
        self.lbl_title.pack(anchor='w', padx=2)
        self.entry_title = ttk.Entry(frame_right_top, textvariable=self.var_custom_title)
        self.entry_title.pack(fill=tk.X, padx=2, pady=(0, 5))

        self.lbl_curves = ttk.Label(frame_right_top, text="Select curves to plot:")
        self.lbl_curves.pack(anchor='w', padx=2)
        self.listbox = tk.Listbox(frame_right_top, selectmode=tk.MULTIPLE, exportselection=False, height=4)
        self.listbox.pack(fill=tk.X, padx=2, expand=True)

        frame_list_opts = ttk.Frame(frame_right_top)
        frame_list_opts.pack(fill=tk.X, padx=2, pady=2)
        self.btn_set_color = ttk.Button(frame_list_opts, text="Set Color ▾", command=self.show_color_menu)
        self.btn_set_color.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 1))
        self.btn_set_marker = ttk.Button(frame_list_opts, text="Set Marker ▾", command=self.show_marker_menu)
        self.btn_set_marker.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(1, 0))

        # --- Y axis controls ---
        self.frame_y = ttk.LabelFrame(self.frame_left, text="Y Axis")
        self.frame_y.pack(anchor='center', pady=0, expand=True)

        self.lbl_y_qty = ttk.Label(self.frame_y, text="Quantity:")
        self.lbl_y_qty.grid(row=0, column=0, sticky='e')
        self.om_y_qty = ttk.OptionMenu(self.frame_y, self.var_y_qty, 'None', *quantity_units.keys(), command=self.update_y_units)
        self.om_y_qty.grid(row=0, column=1, sticky='w')

        self.lbl_y_unit = ttk.Label(self.frame_y, text="Unit:")
        self.lbl_y_unit.grid(row=1, column=0, sticky='e')
        self.om_y_unit = ttk.OptionMenu(self.frame_y, self.var_y_unit, '')
        self.om_y_unit.grid(row=1, column=1, sticky='w')

        self.lbl_y_custom = ttk.Label(self.frame_y, text="Custom label:")
        self.lbl_y_custom.grid(row=2, column=0, sticky='e')
        self.entry_y_label = ttk.Entry(self.frame_y)
        self.entry_y_label.grid(row=2, column=1, sticky='we')

        self.chk_y_use_qty = ttk.Checkbutton(self.frame_y, text="Use Qty as Label", variable=self.var_y_use_qty)
        self.chk_y_use_qty.grid(row=3, column=0, columnspan=2, sticky='w')
        self.chk_y_add_unit = ttk.Checkbutton(self.frame_y, text="Append Unit", variable=self.var_y_add_unit)
        self.chk_y_add_unit.grid(row=4, column=0, columnspan=2, sticky='w')
        self.chk_y_replace_unit = ttk.Checkbutton(self.frame_y, text="Replace Unit", variable=self.var_y_replace_unit)
        self.chk_y_replace_unit.grid(row=5, column=0, columnspan=2, sticky='w')

        # --- Save options ---
        self.frame_save = ttk.LabelFrame(self.frame_left, text="Save Options")
        self.frame_save.pack(anchor='n', pady=5, fill=tk.X)
        self.lbl_save_path = ttk.Label(self.frame_save, text="Path:")
        self.lbl_save_path.grid(row=0, column=0, sticky='w')
        entry_save = ttk.Entry(self.frame_save, textvariable=self.var_save_path, width=20)
        entry_save.grid(row=1, column=0, sticky='ew')
        self.btn_browse = ttk.Button(self.frame_save, text="Browse...", command=self.select_save_path)
        self.btn_browse.grid(row=1, column=1, sticky='w', padx=(2,0))
        self.frame_save.columnconfigure(0, weight=1)

        # --- Plot style options ---
        self.frame_style = ttk.LabelFrame(self.frame_left, text="Plot Style")
        self.frame_style.pack(anchor='n', pady=5, fill=tk.X)
        self.lbl_marker = ttk.Label(self.frame_style, text="Marker Size:")
        self.lbl_marker.grid(row=0, column=0, sticky='w')
        ttk.Entry(self.frame_style, textvariable=self.var_marker_size, width=8).grid(row=0, column=1, sticky='e')
        
        self.lbl_marker_style = ttk.Label(self.frame_style, text="Marker Style:")
        self.lbl_marker_style.grid(row=1, column=0, sticky='w')
        self.om_marker = ttk.Combobox(self.frame_style, textvariable=self.var_marker_style, values=['o (Point)', 'x (Cross)', '^ (Triangle)', 's (Square)', '* (Star)'], width=10, state='readonly')
        self.om_marker.grid(row=1, column=1, sticky='e')

        self.chk_points = ttk.Checkbutton(self.frame_style, text="Draw Points", variable=self.var_draw_points)
        self.chk_points.grid(row=2, column=0, columnspan=2, sticky='w')
        self.chk_lines = ttk.Checkbutton(self.frame_style, text="Draw Lines", variable=self.var_draw_lines)
        self.chk_lines.grid(row=3, column=0, columnspan=2, sticky='w')
        self.lbl_linewidth = ttk.Label(self.frame_style, text="Line Width:")
        self.lbl_linewidth.grid(row=4, column=0, sticky='w')
        ttk.Entry(self.frame_style, textvariable=self.var_line_width, width=8).grid(row=4, column=1, sticky='e')
        self.chk_legend = ttk.Checkbutton(self.frame_style, text="Show Legend", variable=self.var_show_legend)
        self.chk_legend.grid(row=5, column=0, columnspan=2, sticky='w')

        # --- Grid and Scale options ---
        self.frame_grid = ttk.LabelFrame(self.frame_left, text="Grid & Scale")
        self.frame_grid.pack(anchor='n', pady=5, fill=tk.X)

        scale_modes = ['Linear', 'Logarithmic Axis']

        self.chk_grid = ttk.Checkbutton(self.frame_grid, text="Show Grid", variable=self.var_show_grid)
        self.chk_grid.grid(row=0, column=0, columnspan=2, sticky='w')

        self.lbl_xscale = ttk.Label(self.frame_grid, text="X Scale:")
        self.lbl_xscale.grid(row=1, column=0, sticky='w')
        om_x_scale = ttk.OptionMenu(self.frame_grid, self.var_x_scale_mode, self.var_x_scale_mode.get(), *scale_modes)
        om_x_scale.grid(row=1, column=1, sticky='ew')

        self.lbl_yscale = ttk.Label(self.frame_grid, text="Y Scale:")
        self.lbl_yscale.grid(row=2, column=0, sticky='w')
        om_y_scale = ttk.OptionMenu(self.frame_grid, self.var_y_scale_mode, self.var_y_scale_mode.get(), *scale_modes)
        om_y_scale.grid(row=2, column=1, sticky='ew')

        self.frame_grid.columnconfigure(1, weight=1)

        # --- Plot area ---
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_plot)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        # --- X axis controls ---
        self.frame_x = ttk.LabelFrame(self.frame_bottom, text="X Axis")
        self.frame_x.pack(anchor='center', pady=0)

        self.lbl_x_qty = ttk.Label(self.frame_x, text="Quantity:")
        self.lbl_x_qty.grid(row=0, column=0, sticky='e')
        self.om_x_qty = ttk.OptionMenu(self.frame_x, self.var_x_qty, 'None', *quantity_units.keys(), command=self.update_x_units)
        self.om_x_qty.grid(row=0, column=1, sticky='w')

        self.lbl_x_unit = ttk.Label(self.frame_x, text="Unit:")
        self.lbl_x_unit.grid(row=0, column=2, sticky='e')
        self.om_x_unit = ttk.OptionMenu(self.frame_x, self.var_x_unit, '')
        self.om_x_unit.grid(row=0, column=3, sticky='w')

        self.lbl_x_custom = ttk.Label(self.frame_x, text="Custom label:")
        self.lbl_x_custom.grid(row=1, column=0, sticky='e')
        self.entry_x_label = ttk.Entry(self.frame_x)
        self.entry_x_label.grid(row=1, column=1, sticky='we')

        self.chk_x_use_qty = ttk.Checkbutton(self.frame_x, text="Use Qty as Label", variable=self.var_x_use_qty)
        self.chk_x_use_qty.grid(row=2, column=0, columnspan=2, sticky='w')
        self.chk_x_add_unit = ttk.Checkbutton(self.frame_x, text="Append Unit", variable=self.var_x_add_unit)
        self.chk_x_add_unit.grid(row=2, column=2, columnspan=2, sticky='w')
        self.chk_x_replace_unit = ttk.Checkbutton(self.frame_x, text="Replace Unit", variable=self.var_x_replace_unit)
        self.chk_x_replace_unit.grid(row=3, column=0, columnspan=4, sticky='w')

        # Set initial values
        if not self.var_x_qty.get():
            self.var_x_qty.set(list(quantity_units.keys())[0])
            self.update_x_units(self.var_x_qty.get())
        if not self.var_y_qty.get():
            self.var_y_qty.set(list(quantity_units.keys())[0])
            self.update_y_units(self.var_y_qty.get())

    def update_language(self):
        super().update_language()
        if not getattr(self, 'btn_load', None): return

        self.btn_load.config(text=self.tr("module_plotgui_btn_load", "Load Excel"))
        self.btn_plot.config(text=self.tr("module_plotgui_btn_plot", "Plot"))
        self.btn_save.config(text=self.tr("module_plotgui_btn_save", "Save Plot"))
        self.lbl_title.config(text=self.tr("module_plotgui_lbl_title", "Custom Title:"))
        self.lbl_curves.config(text=self.tr("module_plotgui_lbl_curves", "Select curves to plot:"))
        if hasattr(self, 'btn_set_color'):
            self.btn_set_color.config(text=self.tr("module_plotgui_btn_set_color", "Set Color ▾"))
        if hasattr(self, 'btn_set_marker'):
            self.btn_set_marker.config(text=self.tr("module_plotgui_btn_set_marker", "Set Marker ▾"))

        self.frame_y.config(text=self.tr("module_plotgui_grp_y", "Y Axis"))
        self.lbl_y_qty.config(text=self.tr("module_plotgui_lbl_qty", "Quantity:"))
        self.lbl_y_unit.config(text=self.tr("module_plotgui_lbl_unit", "Unit:"))
        self.lbl_y_custom.config(text=self.tr("module_plotgui_lbl_custom", "Custom label:"))
        self.chk_y_use_qty.config(text=self.tr("module_plotgui_chk_use_qty", "Use Qty as Label"))
        self.chk_y_add_unit.config(text=self.tr("module_plotgui_chk_add_unit", "Append Unit"))
        self.chk_y_replace_unit.config(text=self.tr("module_plotgui_chk_replace_unit", "Replace Unit"))

        self.frame_save.config(text=self.tr("module_plotgui_grp_save", "Save Options"))
        self.lbl_save_path.config(text=self.tr("module_plotgui_lbl_path", "Path:"))
        self.btn_browse.config(text=self.tr("module_plotgui_btn_browse", "Browse..."))

        self.frame_style.config(text=self.tr("module_plotgui_grp_style", "Plot Style"))
        self.lbl_marker.config(text=self.tr("module_plotgui_lbl_marker", "Marker Size:"))
        if hasattr(self, 'lbl_marker_style'):
            self.lbl_marker_style.config(text=self.tr("module_plotgui_lbl_marker_style", "Marker Style:"))
        self.chk_points.config(text=self.tr("module_plotgui_chk_points", "Draw Points"))
        self.chk_lines.config(text=self.tr("module_plotgui_chk_lines", "Draw Lines"))
        self.lbl_linewidth.config(text=self.tr("module_plotgui_lbl_linewidth", "Line Width:"))
        self.chk_legend.config(text=self.tr("module_plotgui_chk_legend", "Show Legend"))

        self.frame_grid.config(text=self.tr("module_plotgui_grp_grid", "Grid & Scale"))
        self.chk_grid.config(text=self.tr("module_plotgui_chk_grid", "Show Grid"))
        self.lbl_xscale.config(text=self.tr("module_plotgui_lbl_xscale", "X Scale:"))
        self.lbl_yscale.config(text=self.tr("module_plotgui_lbl_yscale", "Y Scale:"))

        self.frame_x.config(text=self.tr("module_plotgui_grp_x", "X Axis"))
        self.lbl_x_qty.config(text=self.tr("module_plotgui_lbl_qty", "Quantity:"))
        self.lbl_x_unit.config(text=self.tr("module_plotgui_lbl_unit", "Unit:"))
        self.lbl_x_custom.config(text=self.tr("module_plotgui_lbl_custom", "Custom label:"))
        self.chk_x_use_qty.config(text=self.tr("module_plotgui_chk_use_qty", "Use Qty as Label"))
        self.chk_x_add_unit.config(text=self.tr("module_plotgui_chk_add_unit", "Append Unit"))
        self.chk_x_replace_unit.config(text=self.tr("module_plotgui_chk_replace_unit", "Replace Unit"))

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
        self.curve_colors.clear()
        self.curve_markers.clear()
        self.listbox.delete(0, tk.END)
        for i, col in enumerate(self.curve_cols):
            self.listbox.insert(tk.END, col)
            self.listbox.selection_set(i)

        # Set default quantities
        current_x_qty = self.var_x_qty.get()
        if not current_x_qty or current_x_qty == 'None':
            default_x_qty = list(quantity_units.keys())[0]
            if default_x_qty == 'None' and len(quantity_units.keys()) > 1:
                 default_x_qty = list(quantity_units.keys())[1]
            self.var_x_qty.set(default_x_qty)
            self.update_x_units(default_x_qty)

        current_y_qty = self.var_y_qty.get()
        if not current_y_qty or current_y_qty == 'None':
            default_y_qty = list(quantity_units.keys())[0]
            if default_y_qty == 'None' and len(quantity_units.keys()) > 1:
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

    def apply_color(self, color):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", self.tr("module_plotgui_msg_no_sel_color", "Please select at least one curve from the list to set its color."))
            return
        for idx in sel:
            col = self.curve_cols[idx]
            if color is None:
                self.curve_colors.pop(col, None)
            else:
                self.curve_colors[col] = color

    def apply_custom_color(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", self.tr("module_plotgui_msg_no_sel_color", "Please select at least one curve from the list to set its color."))
            return
        
        color_code = colorchooser.askcolor(title=self.tr("module_plotgui_title_color", "Choose Curve Color"))[1]
        if color_code:
            self.apply_color(color_code)

    def apply_marker(self, marker_style):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", self.tr("module_plotgui_msg_no_sel_marker", "Please select at least one curve from the list to set its marker."))
            return
        for idx in sel:
            col = self.curve_cols[idx]
            if marker_style is None:
                self.curve_markers.pop(col, None)
            else:
                self.curve_markers[col] = marker_style

    def show_color_menu(self):
        menu = tk.Menu(self.frame, tearoff=0)
        menu.add_command(label=self.tr("plotgui_color_auto", "Auto (Reset)"), command=lambda: self.apply_color(None))
        menu.add_separator()
        menu.add_command(label=self.tr("plotgui_color_red", "Red"), command=lambda: self.apply_color("red"))
        menu.add_command(label=self.tr("plotgui_color_blue", "Blue"), command=lambda: self.apply_color("blue"))
        menu.add_command(label=self.tr("plotgui_color_green", "Green"), command=lambda: self.apply_color("green"))
        menu.add_command(label=self.tr("plotgui_color_purple", "Purple"), command=lambda: self.apply_color("purple"))
        menu.add_command(label=self.tr("plotgui_color_orange", "Orange"), command=lambda: self.apply_color("orange"))
        menu.add_command(label=self.tr("plotgui_color_black", "Black"), command=lambda: self.apply_color("black"))
        menu.add_separator()
        menu.add_command(label=self.tr("plotgui_color_custom", "Custom..."), command=self.apply_custom_color)
        
        x = self.btn_set_color.winfo_rootx()
        y = self.btn_set_color.winfo_rooty() + self.btn_set_color.winfo_height()
        menu.tk_popup(x, y)

    def show_marker_menu(self):
        menu = tk.Menu(self.frame, tearoff=0)
        menu.add_command(label=self.tr("plotgui_marker_auto", "Auto (Global)"), command=lambda: self.apply_marker(None))
        menu.add_separator()
        menu.add_command(label="o (Point)", command=lambda: self.apply_marker("o"))
        menu.add_command(label="x (Cross)", command=lambda: self.apply_marker("x"))
        menu.add_command(label="^ (Triangle)", command=lambda: self.apply_marker("^"))
        menu.add_command(label="s (Square)", command=lambda: self.apply_marker("s"))
        menu.add_command(label="* (Star)", command=lambda: self.apply_marker("*"))
        menu.add_command(label="None", command=lambda: self.apply_marker("None"))
        
        x = self.btn_set_marker.winfo_rootx()
        y = self.btn_set_marker.winfo_rooty() + self.btn_set_marker.winfo_height()
        menu.tk_popup(x, y)

    def plot_data(self):
        if self.df is None:
            messagebox.showwarning("No Data", self.tr("module_plotgui_msg_no_data", "Please load an Excel file first."))
            return
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", self.tr("module_plotgui_msg_no_sel", "Please select at least one curve to plot."))
            return

        self.fig.clear()
        self.ax = self.fig.add_subplot(111)

        x_data = self.df[self.x_col]

        # --- Plotting logic ---
        linestyle = '-' if self.var_draw_lines.get() else 'None'
        actual_marker = self.var_marker_style.get().split(' ')[0]
        global_marker = actual_marker if self.var_draw_points.get() else 'None'
        markersize = self.var_marker_size.get()
        linewidth = self.var_line_width.get()

        for idx in sel:
            col = self.curve_cols[idx]
            y_data = self.df[col]
            color = self.curve_colors.get(col, None)
            marker = self.curve_markers.get(col, global_marker)
            
            kwargs = {
                'label': col,
                'marker': marker,
                'markersize': markersize,
                'linestyle': linestyle,
                'linewidth': linewidth
            }
            if color:
                kwargs['color'] = color
                
            self.ax.plot(x_data, y_data, **kwargs)

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
            elif add_selected_x_unit_to_label and selected_x_unit :
                 final_x_unit_text = selected_x_unit


        final_x_label_math = str(final_x_label_text).replace(' ', r'\ ')
        if final_x_unit_text:
            self.ax.set_xlabel(f"${final_x_label_math}$ $\\mathrm{{({final_x_unit_text})}}$")
        else:
            self.ax.set_xlabel(f"${final_x_label_math}$")


        # --- Y axis label logic ---
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
        else: # Use column header
            final_y_label_text = y_label_from_col_header
            if replace_col_header_y_unit_with_selected and add_selected_y_unit_to_label and selected_y_unit:
                final_y_unit_text = selected_y_unit
            elif y_unit_from_col_header:
                final_y_unit_text = y_unit_from_col_header
            elif add_selected_y_unit_to_label and selected_y_unit:
                final_y_unit_text = selected_y_unit


        final_y_label_math = str(final_y_label_text).replace(' ', r'\ ')
        if final_y_unit_text:
            self.ax.set_ylabel(f"${final_y_label_math}$ $\\mathrm{{({final_y_unit_text})}}$")
        else:
            self.ax.set_ylabel(f"${final_y_label_math}$")

        # --- Title Logic ---
        custom_title = self.var_custom_title.get().strip()
        if custom_title:
            custom_title_math = custom_title.replace(' ', r'\ ')
            self.ax.set_title(f"${custom_title_math}$")
        else:
            self.ax.set_title(f"${final_y_label_math}$ vs ${final_x_label_math}$")

        if self.var_show_legend.get():
            self.ax.legend()

        # --- Grid and Scale Logic ---
        x_scale_mode = self.var_x_scale_mode.get()
        y_scale_mode = self.var_y_scale_mode.get()

        if x_scale_mode == 'Logarithmic Axis':
            self.ax.set_xscale('log')
        else:
            self.ax.set_xscale('linear')

        if y_scale_mode == 'Logarithmic Axis':
            self.ax.set_yscale('log')
        else:
            self.ax.set_yscale('linear')

        if self.var_show_grid.get():
            self.ax.grid(True, which='both', linestyle='--', alpha=0.7)
        else:
            self.ax.grid(False)

        self.canvas.draw()

    def select_save_path(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg;*.jpeg"),
                ("SVG files", "*.svg"),
                ("PDF files", "*,pdf"),
                ("All files", "*.*"),
            ],
            initialfile=self.var_save_path.get(),
            title="Save Plot As"
        )
        if file_path:
            self.var_save_path.set(file_path)

    def save_plot(self):
        save_path = self.var_save_path.get()
        if not save_path:
            messagebox.showerror("Save Error", "No save path specified.")
            return

        try:
            self.fig.savefig(save_path, dpi=300, bbox_inches='tight')
            msg = self.tr("module_plotgui_msg_save_success", "Plot saved successfully to:\n{0}").format(save_path)
            messagebox.showinfo("Success", msg)
        except Exception as e:
            msg = self.tr("module_plotgui_msg_save_error", "Could not save plot to '{0}':\n{1}").format(save_path, e)
            messagebox.showerror("Save Plot Error", msg)
