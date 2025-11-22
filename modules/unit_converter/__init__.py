import tkinter as tk
from tkinter import ttk
import logging

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class UnitConverterModule(Module):
    def __init__(self, master, shared_state, module_name="UnitConverter", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.conversion_types = {
            "uc_cat_length": {
                "uc_conv_m_to_ft": lambda m: m * 3.28084,
                "uc_conv_ft_to_m": lambda ft: ft / 3.28084,
                "uc_conv_km_to_mi": lambda km: km * 0.621371,
                "uc_conv_mi_to_km": lambda mi: mi / 0.621371,
            },
            "uc_cat_temperature": {
                "uc_conv_c_to_f": lambda c: (c * 9/5) + 32,
                "uc_conv_f_to_c": lambda f: (f - 32) * 5/9,
            },
            "uc_cat_weight": {
                "uc_conv_kg_to_lb": lambda kg: kg * 2.20462,
                "uc_conv_lb_to_kg": lambda lb: lb / 2.20462,
                "uc_conv_g_to_oz": lambda g: g * 0.035274,
                "uc_conv_oz_to_g": lambda oz: oz / 0.035274,
            }
        }

        # Map displayed string back to internal key for lookup
        self.display_to_key_map = {}

        # UI Elements
        self.category_var = tk.StringVar()
        self.conversion_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()

        self.lbl_category = None
        self.lbl_conversion = None
        self.lbl_input = None
        self.lbl_output = None

        self.category_selector = None
        self.conversion_selector = None
        self.input_entry = None
        self.output_label = None # Changed from Entry to Label for output
        self.input_unit_label = None
        self.output_unit_label = None

        self.current_category_key = None
        self.current_conversion_key = None

        self.create_ui()
        self.update_language() # Initial language set

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        content_frame = ttk.Frame(self.frame, padding="10")
        content_frame.pack(expand=True, fill=tk.BOTH)
        content_frame.columnconfigure(1, weight=1) # Allow entry/label widgets to expand

        # Category Selector
        self.lbl_category = ttk.Label(content_frame, text="Category:")
        self.lbl_category.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.category_selector = ttk.Combobox(content_frame, textvariable=self.category_var, state="readonly", width=15)
        self.category_selector.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.category_selector.bind("<<ComboboxSelected>>", self.on_category_selected)

        # Conversion Type Selector
        self.lbl_conversion = ttk.Label(content_frame, text="Conversion:")
        self.lbl_conversion.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.conversion_selector = ttk.Combobox(content_frame, textvariable=self.conversion_var, state="readonly", width=25)
        self.conversion_selector.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.conversion_selector.bind("<<ComboboxSelected>>", self.on_conversion_selected)

        # Input Area
        self.lbl_input = ttk.Label(content_frame, text="Input:")
        self.lbl_input.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.input_entry = ttk.Entry(content_frame, textvariable=self.input_var, width=15)
        self.input_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.input_unit_label = ttk.Label(content_frame, text="", width=10) # Unit for input
        self.input_unit_label.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.input_var.trace_add("write", self.perform_conversion)

        # Output Area
        self.lbl_output = ttk.Label(content_frame, text="Output:")
        self.lbl_output.grid(row=3, column=0, padx=5, pady=5, sticky="w")

        self.output_label = ttk.Label(content_frame, textvariable=self.output_var, relief="sunken", padding=2, width=15, anchor="w") # Output as a label
        self.output_label.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.output_unit_label = ttk.Label(content_frame, text="", width=10) # Unit for output
        self.output_unit_label.grid(row=3, column=2, padx=5, pady=5, sticky="w")

        # Initial selection setup happens in update_language or explicitly
        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def update_language(self):
        super().update_language()

        # Guard against uninitialized UI elements
        if not getattr(self, 'lbl_category', None):
            return

        # Update labels
        self.lbl_category.config(text=self.tr("uc_category"))
        self.lbl_conversion.config(text=self.tr("uc_conversion"))
        self.lbl_input.config(text=self.tr("uc_input"))
        self.lbl_output.config(text=self.tr("uc_output"))

        # Refresh categories list
        self.display_to_key_map.clear()
        categories_display = []
        current_cat_display = ""

        for key in self.conversion_types.keys():
            display = self.tr(key)
            categories_display.append(display)
            self.display_to_key_map[display] = key
            if key == self.current_category_key:
                current_cat_display = display

        self.category_selector['values'] = categories_display

        if current_cat_display:
            self.category_selector.set(current_cat_display)
            # Refresh conversions list based on current category
            self.update_conversions_list()
        elif categories_display:
            self.category_selector.current(0)
            self.on_category_selected(None)

    def update_conversions_list(self):
        if not self.current_category_key:
            self.conversion_selector['values'] = []
            return

        conversions_map = self.conversion_types[self.current_category_key]
        conversions_display = []
        current_conv_display = ""

        for key in conversions_map.keys():
            display = self.tr(key)
            conversions_display.append(display)
            self.display_to_key_map[display] = key # Add to map
            if key == self.current_conversion_key:
                current_conv_display = display

        self.conversion_selector['values'] = conversions_display

        if current_conv_display:
            self.conversion_selector.set(current_conv_display)
        elif conversions_display:
            self.conversion_selector.current(0)
            self.on_conversion_selected(None)

        # Update units
        self._update_unit_labels()


    def on_category_selected(self, event=None):
        display_val = self.category_var.get()
        key = self.display_to_key_map.get(display_val)

        if key:
            self.current_category_key = key
            self.update_conversions_list()
        else:
            self.conversion_selector['values'] = []
            self.conversion_var.set("")
            self.current_conversion_key = None
            self.on_conversion_selected()

    def on_conversion_selected(self, event=None):
        display_val = self.conversion_var.get()
        key = self.display_to_key_map.get(display_val)

        self.current_conversion_key = key

        self.input_var.set("")
        self.output_var.set("")
        self._update_unit_labels()
        self.perform_conversion()

    def _update_unit_labels(self):
        # Logic to parse "UnitA to UnitB" from the translated string is fragile if translation doesn't follow pattern.
        # Better to rely on the keys if possible, or just parse the translated string assuming structure.
        # The translated string structure "A to B" (English) or "A 轉 B" (Chinese).
        # If I use keys, I can define unit names separately?
        # Or I can just display empty unit labels if I don't want to parse.
        # But parsing is useful for visual feedback.

        # Let's try to parse the DISPLAY string
        display_val = self.conversion_var.get()
        if not display_val:
            self.input_unit_label.config(text="")
            self.output_unit_label.config(text="")
            return

        # Heuristic parsing based on known separators
        separators = [" to ", " 轉 "]
        found_sep = None
        for sep in separators:
            if sep in display_val:
                found_sep = sep
                break

        if found_sep:
            parts = display_val.split(found_sep)
            if len(parts) == 2:
                self.input_unit_label.config(text=parts[0].strip())
                self.output_unit_label.config(text=parts[1].strip())
            else:
                self.input_unit_label.config(text="")
                self.output_unit_label.config(text="")
        else:
            self.input_unit_label.config(text="")
            self.output_unit_label.config(text="")


    def perform_conversion(self, *args):
        input_value_str = self.input_var.get()

        if not input_value_str:
            self.output_var.set("")
            return

        try:
            input_value = float(input_value_str)
        except ValueError:
            self.output_var.set("Invalid input")
            return

        cat_key = self.current_category_key
        conv_key = self.current_conversion_key

        if cat_key and conv_key and \
           cat_key in self.conversion_types and \
           conv_key in self.conversion_types[cat_key]:

            conversion_func = self.conversion_types[cat_key][conv_key]
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
                self.shared_state.log(f"Conversion error for '{conv_key}': {e}", level=logging.ERROR)
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
