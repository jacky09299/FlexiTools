import tkinter as tk
from tkinter import ttk, colorchooser
import random
import logging

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class ColorPaletteModule(Module):
    def __init__(self, master, shared_state, module_name="ColorPalette", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.num_palettes = 6
        self.palette_frames = []
        self.palette_colors_hex = ["#FFFFFF"] * self.num_palettes
        self.selected_palette_index = tk.IntVar(value=0)

        # RGB sliders and HEX display
        self.scale_r = None
        self.scale_g = None
        self.scale_b = None
        self.hex_entry_var = tk.StringVar()
        self.hex_entry = None

        self._prevent_slider_recursion = False # Flag to prevent slider update loops

        self.create_ui()
        self.generate_initial_palettes()

    def _rgb_to_hex(self, r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Main content frame
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        # Palettes display frame
        palettes_master_frame = ttk.Frame(content_frame)
        palettes_master_frame.pack(pady=(0,10), fill=tk.X, expand=True)

        # Arrange palettes in a responsive grid-like manner
        # Max 3 palettes per row
        max_palettes_per_row = 3
        current_row_frame = None

        for i in range(self.num_palettes):
            if i % max_palettes_per_row == 0:
                current_row_frame = ttk.Frame(palettes_master_frame)
                current_row_frame.pack(fill=tk.X, expand=True, pady=2)

            palette_container = ttk.Frame(current_row_frame, width=60, height=60) # Container for border/selection
            palette_container.pack(side=tk.LEFT, padx=5, expand=True)
            # palette_container.pack_propagate(False) # To maintain size

            # Actual color frame
            p_frame = tk.Frame(palette_container, width=50, height=50, relief=tk.SUNKEN, borderwidth=1)
            p_frame.pack(padx=5,pady=5) # Center it

            p_frame.bind("<Button-1>", lambda event, idx=i: self.on_palette_click(idx))
            self.palette_frames.append(p_frame)

        # Separator
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Controls frame (sliders and HEX)
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill=tk.X, expand=True)

        # HEX display/entry
        hex_frame = ttk.Frame(controls_frame)
        hex_frame.pack(fill=tk.X, pady=5)
        ttk.Label(hex_frame, text="HEX:").pack(side=tk.LEFT, padx=(0,5))
        self.hex_entry_var = tk.StringVar()
        self.hex_entry = ttk.Entry(hex_frame, textvariable=self.hex_entry_var, width=10)
        self.hex_entry.pack(side=tk.LEFT, padx=(0,5))
        self.hex_entry.bind("<Return>", self.update_color_from_hex_entry)

        copy_hex_button = ttk.Button(hex_frame, text="Copy", command=self.copy_hex_to_clipboard)
        copy_hex_button.pack(side=tk.LEFT, padx=(0,5))

        # RGB Sliders
        slider_frame = ttk.Frame(controls_frame)
        slider_frame.pack(fill=tk.X, expand=True)

        self.scale_r = self._create_slider(slider_frame, "R", "#FF0000")
        self.scale_g = self._create_slider(slider_frame, "G", "#00FF00")
        self.scale_b = self._create_slider(slider_frame, "B", "#0000FF")

        # Action buttons
        action_frame = ttk.Frame(controls_frame)
        action_frame.pack(fill=tk.X, pady=(10,0))

        regenerate_button = ttk.Button(action_frame, text="Regenerate All Palettes", command=self.generate_initial_palettes)
        regenerate_button.pack(side=tk.LEFT, padx=(0,5))

        # choose_color_button = ttk.Button(action_frame, text="Choose Color...", command=self.open_color_chooser)
        # choose_color_button.pack(side=tk.LEFT)


        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)
        self.update_selection_highlight() # Initial highlight

    def _create_slider(self, parent, label_text, color):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True)
        # Dynamic styling for label based on color (simple foreground)
        style_name = f"{label_text}Value.TLabel"
        s = ttk.Style()
        s.configure(style_name, foreground=color)

        lbl = ttk.Label(frame, text=f"{label_text}:", width=2, style=style_name)
        lbl.pack(side=tk.LEFT, padx=(0,5))

        val_lbl = ttk.Label(frame, text="0", width=3) # To display current slider value
        val_lbl.pack(side=tk.LEFT, padx=(0,5))

        scale = ttk.Scale(frame, from_=0, to=255, orient=tk.HORIZONTAL, command=lambda v, l=val_lbl: self.on_slider_change(v, l))
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return scale

    def generate_initial_palettes(self):
        for i in range(self.num_palettes):
            r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
            self.palette_colors_hex[i] = self._rgb_to_hex(r,g,b)
            if self.palette_frames[i].winfo_exists():
                self.palette_frames[i].config(bg=self.palette_colors_hex[i])

        # Update controls if a palette is selected
        current_idx = self.selected_palette_index.get()
        self.on_palette_click(current_idx) # This will refresh sliders and HEX for the current selection
        self.shared_state.log("Generated initial random palettes.", level=logging.DEBUG)

    def on_palette_click(self, index):
        self.selected_palette_index.set(index)
        hex_color = self.palette_colors_hex[index]
        self.hex_entry_var.set(hex_color)

        self._prevent_slider_recursion = True # Prevent on_slider_change from re-triggering updates
        try:
            r, g, b = self._hex_to_rgb(hex_color)
            if self.scale_r: self.scale_r.set(r)
            if self.scale_g: self.scale_g.set(g)
            if self.scale_b: self.scale_b.set(b)
            # Update slider value labels directly
            self._update_slider_value_label(self.scale_r, r)
            self._update_slider_value_label(self.scale_g, g)
            self._update_slider_value_label(self.scale_b, b)

        except ValueError:
            self.shared_state.log(f"Invalid HEX color encountered: {hex_color}", level=logging.WARNING)
        finally:
            self._prevent_slider_recursion = False

        self.update_selection_highlight()
        self.copy_hex_to_clipboard() # Also copy on click
        self.shared_state.log(f"Palette {index} clicked. Color: {hex_color}", level=logging.DEBUG)

    def _update_slider_value_label(self, slider_widget, value):
        if slider_widget and slider_widget.master.winfo_exists():
            # Assuming the value label is the second child of the slider's master frame
            # Master frame structure: [Label(R/G/B), Label(Value), Scale]
            value_label_widget = slider_widget.master.winfo_children()[1]
            if isinstance(value_label_widget, ttk.Label):
                value_label_widget.config(text=str(int(float(value))))


    def on_slider_change(self, value, value_label_widget):
        if self._prevent_slider_recursion:
            return

        if value_label_widget and value_label_widget.winfo_exists():
             value_label_widget.config(text=str(int(float(value))))

        idx = self.selected_palette_index.get()
        if not (0 <= idx < self.num_palettes):
            return

        self._prevent_slider_recursion = True
        try:
            r = int(self.scale_r.get())
            g = int(self.scale_g.get())
            b = int(self.scale_b.get())

            new_hex_color = self._rgb_to_hex(r, g, b)
            self.palette_colors_hex[idx] = new_hex_color
            self.hex_entry_var.set(new_hex_color)
            if self.palette_frames[idx].winfo_exists():
                self.palette_frames[idx].config(bg=new_hex_color)
        finally:
            self._prevent_slider_recursion = False

    def update_color_from_hex_entry(self, event=None):
        hex_color = self.hex_entry_var.get().strip()
        if not hex_color.startswith("#"):
            hex_color = "#" + hex_color

        if len(hex_color) == 7 : # Basic validation for #RRGGBB
            try:
                r, g, b = self._hex_to_rgb(hex_color) # Validates format

                idx = self.selected_palette_index.get()
                if not (0 <= idx < self.num_palettes):
                    return

                self.palette_colors_hex[idx] = hex_color
                if self.palette_frames[idx].winfo_exists():
                    self.palette_frames[idx].config(bg=hex_color)

                # Update sliders
                self._prevent_slider_recursion = True
                if self.scale_r: self.scale_r.set(r)
                if self.scale_g: self.scale_g.set(g)
                if self.scale_b: self.scale_b.set(b)
                self._update_slider_value_label(self.scale_r, r)
                self._update_slider_value_label(self.scale_g, g)
                self._update_slider_value_label(self.scale_b, b)
                self._prevent_slider_recursion = False

                self.shared_state.log(f"Color updated from HEX entry to {hex_color}", level=logging.DEBUG)
            except ValueError:
                self.shared_state.log(f"Invalid HEX input: {hex_color}", level=logging.WARNING)
                # Optionally revert to last valid color or show error
                # For now, just log. If user types more, it might become valid.
        else:
            # Not a full hex code yet, or invalid length
            pass


    def copy_hex_to_clipboard(self):
        idx = self.selected_palette_index.get()
        if not (0 <= idx < self.num_palettes):
            return
        hex_to_copy = self.palette_colors_hex[idx]
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(hex_to_copy)
            self.shared_state.log(f"Copied {hex_to_copy} to clipboard.", level=logging.INFO)
            # Simple visual feedback (optional)
            original_text = self.hex_entry.cget("textvariable") # This gets the var name, not value
            current_hex_val = self.hex_entry_var.get()
            self.hex_entry_var.set(f"{current_hex_val} (Copied!)")
            self.hex_entry.after(1000, lambda: self.hex_entry_var.set(current_hex_val) if self.hex_entry_var.get().endswith("(Copied!)") else None)

        except tk.TclError:
            self.shared_state.log("Clipboard access failed.", level=logging.ERROR)

    def update_selection_highlight(self):
        # Simple highlight: change border of the container of the color frame
        for i, p_container_frame in enumerate(self.palette_frames):
            container_widget = p_container_frame.master # This is the palette_container frame
            if container_widget.winfo_exists():
                if i == self.selected_palette_index.get():
                    container_widget.config(relief=tk.SOLID, borderwidth=2) # Highlight
                else:
                    container_widget.config(relief=tk.FLAT, borderwidth=0) # No highlight

    def open_color_chooser(self):
        # This is an alternative way to select a color
        idx = self.selected_palette_index.get()
        if not (0 <= idx < self.num_palettes):
            return

        initial_color = self.palette_colors_hex[idx]
        color_code = colorchooser.askcolor(color=initial_color, title="Choose a color", parent=self.frame)

        if color_code and color_code[1]:  # color_code is ((r,g,b), hex_string) or (None, None)
            new_hex_color = color_code[1]
            self.palette_colors_hex[idx] = new_hex_color
            if self.palette_frames[idx].winfo_exists():
                self.palette_frames[idx].config(bg=new_hex_color)

            self.hex_entry_var.set(new_hex_color)
            r, g, b = self._hex_to_rgb(new_hex_color)

            self._prevent_slider_recursion = True
            if self.scale_r: self.scale_r.set(r); self._update_slider_value_label(self.scale_r, r)
            if self.scale_g: self.scale_g.set(g); self._update_slider_value_label(self.scale_g, g)
            if self.scale_b: self.scale_b.set(b); self._update_slider_value_label(self.scale_b, b)
            self._prevent_slider_recursion = False
            self.shared_state.log(f"Color chosen via dialog: {new_hex_color}", level=logging.DEBUG)


    def on_destroy(self):
        # No specific timers or resources to clean up for this module
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
