import tkinter as tk
from tkinter import ttk, colorchooser
import logging

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class DrawingPadModule(Module):
    def __init__(self, master, shared_state, module_name="DrawingPad", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.canvas = None
        self.pen_color = "black"
        self.pen_width = tk.IntVar(value=2)
        self.last_x, self.last_y = None, None

        self.create_ui()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Main content frame
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)
        content_frame.rowconfigure(1, weight=1)    # Canvas row
        content_frame.columnconfigure(0, weight=1) # Canvas column

        # Controls Bar
        controls_bar = ttk.Frame(content_frame)
        controls_bar.grid(row=0, column=0, sticky="ew", pady=(0,5))

        clear_button = ttk.Button(controls_bar, text="Clear Canvas", command=self.clear_canvas)
        clear_button.pack(side=tk.LEFT, padx=(0,5))

        color_button = ttk.Button(controls_bar, text="Pen Color", command=self.choose_color)
        color_button.pack(side=tk.LEFT, padx=(0,10))

        ttk.Label(controls_bar, text="Pen Width:").pack(side=tk.LEFT, padx=(0,2))
        pen_width_slider = ttk.Scale(controls_bar, from_=1, to=20, variable=self.pen_width, orient=tk.HORIZONTAL)
        pen_width_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Display current pen width
        # width_val_label = ttk.Label(controls_bar, textvariable=self.pen_width, width=3) # Can bind directly
        # width_val_label.pack(side=tk.LEFT, padx=(2,0))


        # Canvas for drawing
        self.canvas = tk.Canvas(content_frame, bg="white", relief="sunken", borderwidth=1)
        self.canvas.grid(row=1, column=0, sticky="nsew")

        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def draw(self, event):
        if self.last_x is not None and self.last_y is not None:
            current_x, current_y = event.x, event.y
            self.canvas.create_line(self.last_x, self.last_y, current_x, current_y,
                                    fill=self.pen_color, width=self.pen_width.get(),
                                    capstyle=tk.ROUND, smooth=tk.TRUE, splinesteps=36)
            self.last_x, self.last_y = current_x, current_y

    def stop_draw(self, event):
        self.last_x, self.last_y = None, None

    def clear_canvas(self):
        self.canvas.delete("all")
        self.shared_state.log("Drawing canvas cleared.", level=logging.DEBUG)

    def choose_color(self):
        color_code = colorchooser.askcolor(title="Choose pen color", initialcolor=self.pen_color, parent=self.frame)
        if color_code and color_code[1]:
            self.pen_color = color_code[1]
            self.shared_state.log(f"Pen color changed to: {self.pen_color}", level=logging.DEBUG)

    def on_destroy(self):
        # No specific resources like timers to clean up
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
