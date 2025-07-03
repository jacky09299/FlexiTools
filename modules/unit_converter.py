import tkinter as tk
from tkinter import ttk
import logging

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class UnitConverterModule(Module):
    def __init__(self, master, shared_state, module_name="UnitConverter", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.conversion_types = {
            "Length": {
                "Meters to Feet": lambda m: m * 3.28084,
                "Feet to Meters": lambda ft: ft / 3.28084,
                "Kilometers to Miles": lambda km: km * 0.621371,
                "Miles to Kilometers": lambda mi: mi / 0.621371,
            },
            "Temperature": {
                "Celsius to Fahrenheit": lambda c: (c * 9/5) + 32,
                "Fahrenheit to Celsius": lambda f: (f - 32) * 5/9,
            },
            "Weight": {
                "Kilograms to Pounds": lambda kg: kg * 2.20462,
                "Pounds to Kilograms": lambda lb: lb / 2.20462,
                "Grams to Ounces": lambda g: g * 0.035274,
                "Ounces to Grams": lambda oz: oz / 0.035274,
            }
        }

        # UI Elements
        self.category_var = tk.StringVar()
        self.conversion_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()

        self.category_selector = None
        self.conversion_selector = None
        self.input_entry = None
        self.output_label = None # Changed from Entry to Label for output
        self.input_unit_label = None
        self.output_unit_label = None

        self.create_ui()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        content_frame = ttk.Frame(self.frame, padding="10")
        content_frame.pack(expand=True, fill=tk.BOTH)
        content_frame.columnconfigure(1, weight=1) # Allow entry/label widgets to expand

        # Category Selector
        ttk.Label(content_frame, text="Category:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        categories = list(self.conversion_types.keys())
        self.category_selector = ttk.Combobox(content_frame, textvariable=self.category_var, values=categories, state="readonly", width=15)
        self.category_selector.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.category_selector.bind("<<ComboboxSelected>>", self.on_category_selected)
        if categories:
            self.category_var.set(categories[0]) # Set default category

        # Conversion Type Selector
        ttk.Label(content_frame, text="Conversion:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.conversion_selector = ttk.Combobox(content_frame, textvariable=self.conversion_var, state="readonly", width=25)
        self.conversion_selector.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.conversion_selector.bind("<<ComboboxSelected>>", self.on_conversion_selected)

        # Input Area
        ttk.Label(content_frame, text="Input:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.input_entry = ttk.Entry(content_frame, textvariable=self.input_var, width=15)
        self.input_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.input_unit_label = ttk.Label(content_frame, text="", width=10) # Unit for input
        self.input_unit_label.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.input_var.trace_add("write", self.perform_conversion)

        # Output Area
        ttk.Label(content_frame, text="Output:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.output_label = ttk.Label(content_frame, textvariable=self.output_var, relief="sunken", padding=2, width=15, anchor="w") # Output as a label
        self.output_label.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.output_unit_label = ttk.Label(content_frame, text="", width=10) # Unit for output
        self.output_unit_label.grid(row=3, column=2, padx=5, pady=5, sticky="w")

        self.on_category_selected() # Populate initial conversion types and units
        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def on_category_selected(self, event=None):
        selected_category = self.category_var.get()
        if selected_category in self.conversion_types:
            conversions = list(self.conversion_types[selected_category].keys())
            self.conversion_selector['values'] = conversions
            if conversions:
                self.conversion_var.set(conversions[0])
            else:
                self.conversion_var.set("")
            self.on_conversion_selected() # Update units and clear values
        else:
            self.conversion_selector['values'] = []
            self.conversion_var.set("")
            self.on_conversion_selected()

    def on_conversion_selected(self, event=None):
        self.input_var.set("")
        self.output_var.set("")
        self._update_unit_labels()
        self.perform_conversion()

    def _update_unit_labels(self):
        selected_category = self.category_var.get()
        selected_conversion_name = self.conversion_var.get()

        if selected_category and selected_conversion_name:
            # Derive units from the conversion name string "UnitA to UnitB"
            try:
                parts = selected_conversion_name.split(" to ")
                input_unit = parts[0].strip()
                output_unit = parts[1].strip()
                self.input_unit_label.config(text=input_unit)
                self.output_unit_label.config(text=output_unit)
            except IndexError:
                self.input_unit_label.config(text="")
                self.output_unit_label.config(text="")
                self.shared_state.log(f"Could not parse units from: {selected_conversion_name}", level=logging.WARNING)
        else:
            self.input_unit_label.config(text="")
            self.output_unit_label.config(text="")


    def perform_conversion(self, *args):
        input_value_str = self.input_var.get()
        selected_category = self.category_var.get()
        selected_conversion_name = self.conversion_var.get()

        if not input_value_str:
            self.output_var.set("")
            return

        try:
            input_value = float(input_value_str)
        except ValueError:
            self.output_var.set("Invalid input")
            return

        if selected_category in self.conversion_types and \
            selected_conversion_name in self.conversion_types[selected_category]:
            conversion_func = self.conversion_types[selected_category][selected_conversion_name]
            try:
                output_value = conversion_func(input_value)
                # Format output to a reasonable number of decimal places
                if isinstance(output_value, float):
                     # Show more precision for smaller numbers, less for larger ones
                    if abs(output_value) < 0.0001 and output_value != 0:
                        self.output_var.set(f"{output_value:.6g}")
                    elif abs(output_value) < 1:
                        self.output_var.set(f"{output_value:.4f}")
                    elif abs(output_value) < 1000:
                         self.output_var.set(f"{output_value:.2f}")
                    else: # Larger numbers
                        self.output_var.set(f"{output_value:.1f}")

                else: # Should not happen if functions return float
                    self.output_var.set(str(output_value))

            except Exception as e:
                self.output_var.set("Error")
                self.shared_state.log(f"Conversion error for '{selected_conversion_name}': {e}", level=logging.ERROR)
        else:
            self.output_var.set("") # No valid conversion selected

    def on_destroy(self):
        # Clean up traces if any were added that might cause issues
        if self.input_var:
            try:
                self.input_var.trace_remove("write", self.input_var.trace_info()[0][1]) # Attempt to remove the specific callback
            except: # General catch if trace_info is empty or issues
                pass
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
