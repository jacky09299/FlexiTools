import tkinter as tk
from tkinter import ttk, filedialog
from main import Module
import logging
import os # For os.path.basename

try:
    import pandas as pd
    # Also try to import an engine to ensure pandas can read xlsx/xls
    try:
        import openpyxl
    except ImportError:
        # xlrd might be needed for .xls, openpyxl for .xlsx
        # Pandas will raise an error if the appropriate engine is missing for a given file type.
        pass # Let pandas handle engine errors at read_excel time
except ImportError:
    pd = None # Placeholder if pandas is not installed

class ReportModule(Module):
    def __init__(self, master, shared_state, module_name="Report", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.dataframe = None # To store the loaded pandas DataFrame
        self.tree = None
        self.excel_filepath = ""
        self.sheet_names = []
        self.current_sheet_name = None

        if pd is None:
            self.shared_state.log("Pandas library not found. Excel loading will not be available.", logging.ERROR)

        self.create_ui()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Top frame for controls
        controls_frame = ttk.Frame(self.frame)
        controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        load_button = ttk.Button(controls_frame, text="Load Excel File", command=self.load_excel_file_dialog)
        load_button.pack(side=tk.LEFT, padx=(0, 5))

        self.sheet_label = ttk.Label(controls_frame, text="Sheet:")
        self.sheet_label.pack(side=tk.LEFT, padx=(5,0))
        self.sheet_var = tk.StringVar()
        self.sheet_selector = ttk.Combobox(controls_frame, textvariable=self.sheet_var, state="readonly", width=15)
        self.sheet_selector.pack(side=tk.LEFT, padx=5)
        self.sheet_selector.bind("<<ComboboxSelected>>", self.on_sheet_selected)

        # Frame for Treeview and Scrollbars
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=(0,5))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, show="headings")

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        if pd is None:
            # Display message if pandas is not available, in the tree_frame area
            # Destroy tree and scrollbars if pandas not found, to make space for label
            self.tree.destroy()
            vsb.destroy()
            hsb.destroy()
            status_label = ttk.Label(tree_frame, text="Pandas library not installed.\nExcel display unavailable.", justify=tk.CENTER)
            status_label.grid(row=0, column=0, sticky="nsew")
            self.sheet_label.pack_forget()
            self.sheet_selector.pack_forget()
            load_button.config(state=tk.DISABLED)


        # Status label (replaces old info_label)
        self.status_info_label = ttk.Label(controls_frame, text="No Excel file loaded.")
        self.status_info_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Update shared state
        self.shared_state.set(f"{self.module_name}_initialized", True)
        self.shared_state.log(f"UI for {self.module_name} created.")
        # self.shared_state.add_observer("system_status", self.on_system_status_change) # Removed for this example

    def load_excel_file_dialog(self):
        if pd is None:
            self.shared_state.log("Pandas is not installed, cannot load Excel.", logging.ERROR)
            self.status_info_label.config(text="Error: Pandas library not found.")
            return

        filepath = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=(("Excel files", "*.xlsx *.xls"),
                       ("All files", "*.*"))
        )
        if not filepath:
            return

        self.excel_filepath = filepath
        try:
            # Get sheet names
            xls = pd.ExcelFile(self.excel_filepath)
            self.sheet_names = xls.sheet_names
            self.sheet_selector['values'] = self.sheet_names
            if self.sheet_names:
                self.current_sheet_name = self.sheet_names[0]
                self.sheet_var.set(self.current_sheet_name)
                self.load_sheet_data(self.current_sheet_name)
                self.sheet_selector.config(state="readonly" if len(self.sheet_names) > 0 else tk.DISABLED) # Allow selection if multiple sheets
            else:
                self.shared_state.log(f"No sheets found in Excel file: {self.excel_filepath}", logging.WARNING)
                self.status_info_label.config(text=f"No sheets in: {os.path.basename(self.excel_filepath)}")
                self.sheet_selector.config(state=tk.DISABLED)
                self.clear_treeview()


        except Exception as e:
            self.shared_state.log(f"Error reading Excel file '{self.excel_filepath}': {e}", logging.ERROR)
            self.status_info_label.config(text=f"Error loading: {os.path.basename(self.excel_filepath)}. See console.")
            self.clear_treeview()
            self.sheet_selector.config(state=tk.DISABLED)
            self.sheet_selector['values'] = []


    def on_sheet_selected(self, event=None):
        selected_sheet = self.sheet_var.get()
        if selected_sheet and selected_sheet != self.current_sheet_name: # Ensure it's a new selection
            self.current_sheet_name = selected_sheet
            self.load_sheet_data(selected_sheet)

    def load_sheet_data(self, sheet_name):
        if not self.excel_filepath or pd is None:
            return

        try:
            self.dataframe = pd.read_excel(self.excel_filepath, sheet_name=sheet_name)
            self.populate_treeview()
            self.status_info_label.config(text=f"Loaded: {os.path.basename(self.excel_filepath)} [{sheet_name}]")
            self.shared_state.log(f"Sheet '{sheet_name}' from '{self.excel_filepath}' loaded.", logging.INFO)
        except Exception as e:
            self.shared_state.log(f"Error loading sheet '{sheet_name}': {e}", logging.ERROR)
            self.status_info_label.config(text=f"Error loading sheet: {sheet_name}. See console.")
            self.clear_treeview()

    def clear_treeview(self):
        if self.tree and self.tree.winfo_exists(): # Check if tree exists
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.tree["columns"] = ()

    def populate_treeview(self):
        self.clear_treeview()
        if self.dataframe is None or self.dataframe.empty:
            # self.status_info_label.config(text="No data to display.") # Optional: update status
            return

        df = self.dataframe

        # Define columns
        self.tree["columns"] = list(df.columns)
        self.tree["show"] = "headings"

        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, minwidth=50, anchor=tk.W)

        rows = df.to_numpy().tolist()
        for i, row in enumerate(rows):
            str_row = [str(val) if pd.notna(val) else "" for val in row] # Handle NaN values
            self.tree.insert("", "end", iid=i, values=str_row)

        self.shared_state.log(f"Treeview populated with {len(df)} rows from sheet '{self.current_sheet_name}'.", logging.DEBUG)

    def on_destroy(self):
        super().on_destroy()
        # No specific observer to remove from this version
        self.shared_state.set(f"{self.module_name}_initialized", False)
        self.shared_state.log(f"{self.module_name} instance destroyed.")

# Standalone test (optional) - Requires pandas and openpyxl/xlrd
if __name__ == '__main__':
    try:
        from main import Module as MainModule
    except ImportError:
        class MainModule:
            def __init__(self, master, shared_state, module_name="Test", gui_manager=None):
                self.master = master; self.shared_state = shared_state; self.module_name = module_name; self.gui_manager = gui_manager
                self.frame = ttk.Frame(master)
                # self.frame.pack(fill=tk.BOTH, expand=True)
                self.shared_state.log(f"MockModule '{self.module_name}' initialized.")
            def get_frame(self): return self.frame
            def create_ui(self): ttk.Label(self.frame, text=f"Content for {self.module_name}").pack()
            def on_destroy(self): self.shared_state.log(f"MockModule '{self.module_name}' destroyed.")
        globals()['Module'] = MainModule

    class MockSharedState:
        def __init__(self): self.vars = {}
        def log(self, message, level=logging.INFO): print(f"LOG ({logging.getLevelName(level)}): {message}")
        def get(self, key, default=None): return self.vars.get(key, default)
        def set(self, key, value): self.vars[key] = value; print(f"STATE SET: {key} = {value}")
        def add_observer(self,key,cb):pass
        def remove_observer(self,key,cb):pass


    root = tk.Tk()
    root.title("Report Module Test")
    root.geometry("600x400")

    mock_shared_state = MockSharedState()

    module_container_frame = ttk.Frame(root, padding=10)
    module_container_frame.pack(fill=tk.BOTH, expand=True)

    report_module_instance = None
    if pd is None:
        ttk.Label(module_container_frame, text="Pandas not installed. ReportModule cannot be fully tested.").pack(expand=True)
    else:
        report_module_instance = ReportModule(module_container_frame, mock_shared_state, gui_manager=None)
        report_module_instance.get_frame().pack(fill=tk.BOTH, expand=True)
        # Example: Create a dummy Excel file for testing
        # try:
        #     dummy_df = pd.DataFrame({'ColA': [1, 2, 3], 'ColB': ['apple', 'banana', 'cherry']})
        #     dummy_excel_file = "test_report_data.xlsx"
        #     dummy_df.to_excel(dummy_excel_file, index=False, sheet_name="TestDataSheet")
        #     report_module_instance.excel_filepath = dummy_excel_file
        #     report_module_instance.sheet_names = ["TestDataSheet"]
        #     report_module_instance.current_sheet_name = "TestDataSheet"
        #     report_module_instance.sheet_var.set("TestDataSheet")
        #     report_module_instance.sheet_selector['values'] = ["TestDataSheet"]
        #     report_module_instance.sheet_selector.config(state="readonly")
        #     report_module_instance.load_sheet_data("TestDataSheet")
        # except Exception as e_test:
        #     print(f"Error creating test excel: {e_test}")


    root.mainloop()

    if report_module_instance:
         report_module_instance.on_destroy()
        # if 'dummy_excel_file' in locals() and os.path.exists(dummy_excel_file):
        #     os.remove(dummy_excel_file)
