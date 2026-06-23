import tkinter as tk
from tkinter import ttk, colorchooser
from main import Module

class DesktopCrosshairModule(Module):
    def __init__(self, master, shared_state, module_name="Desktop Crosshair", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        
        self.crosshair_active = False
        self.crosshair_color = "red"
        self.crosshair_thickness = 2
        self.crosshair_mode = tk.StringVar(value="drag")
        
        self.win_h = None
        self.win_v = None
        self.win_c = None
        
        self.create_ui()

    def create_ui(self):
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.btn_toggle = ttk.Button(main_frame, text="Show Crosshair", command=self.toggle_crosshair)
        self.btn_toggle.pack(pady=10)
        
        self.btn_color = ttk.Button(main_frame, text="Change Color", command=self.change_color)
        self.btn_color.pack(pady=10)

        thickness_frame = ttk.Frame(main_frame)
        thickness_frame.pack(pady=10, fill=tk.X)
        self.lbl_thickness = ttk.Label(thickness_frame, text=f"Thickness: {self.crosshair_thickness}")
        self.lbl_thickness.pack(side=tk.LEFT, padx=(0, 10))
        self.scale_thickness = ttk.Scale(thickness_frame, from_=1, to=10, orient=tk.HORIZONTAL, command=self.on_thickness_change)
        self.scale_thickness.set(self.crosshair_thickness)
        self.scale_thickness.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(pady=10)
        self.rb_drag = ttk.Radiobutton(mode_frame, text="Drag Mode", variable=self.crosshair_mode, value="drag", command=self.on_mode_change)
        self.rb_drag.pack(side=tk.LEFT, padx=10)
        self.rb_follow = ttk.Radiobutton(mode_frame, text="Follow Cursor", variable=self.crosshair_mode, value="follow", command=self.on_mode_change)
        self.rb_follow.pack(side=tk.LEFT, padx=10)
        
        self.lbl_instructions = ttk.Label(main_frame, text="Drag the yellow icon (\u2725) to move the crosshair.\nRight-click the icon to hide.", justify=tk.CENTER)
        self.lbl_instructions.pack(pady=20)

        self.update_language()

    def on_thickness_change(self, event=None):
        self.crosshair_thickness = int(self.scale_thickness.get())
        
        # Format the translation string with current thickness
        label_text = self.tr("module_crosshair_lbl_thickness", "Thickness: {thickness}").format(thickness=self.crosshair_thickness)
        self.lbl_thickness.config(text=label_text)
        
        if self.crosshair_active:
            self.update_crosshair_position()

    def update_language(self):
        super().update_language()
        if not getattr(self, 'btn_toggle', None): return
        
        if self.crosshair_active:
            self.btn_toggle.config(text=self.tr("module_crosshair_btn_hide", "Hide Crosshair"))
        else:
            self.btn_toggle.config(text=self.tr("module_crosshair_btn_show", "Show Crosshair"))
            
        self.btn_color.config(text=self.tr("module_crosshair_btn_color", "Change Color"))
        
        self.rb_drag.config(text=self.tr("module_crosshair_mode_drag", "Drag Mode"))
        self.rb_follow.config(text=self.tr("module_crosshair_mode_follow", "Follow Cursor"))
        
        label_text = self.tr("module_crosshair_lbl_thickness", "Thickness: {thickness}").format(thickness=self.crosshair_thickness)
        self.lbl_thickness.config(text=label_text)
        
        self.lbl_instructions.config(text=self.tr("module_crosshair_instructions", "Drag the yellow icon (\u2725) to move the crosshair.\nRight-click the icon to hide."))

    def change_color(self):
        color = colorchooser.askcolor(initialcolor=self.crosshair_color, parent=self.frame)
        if color[1]:
            self.crosshair_color = color[1]
            if self.crosshair_active:
                self.win_h.configure(bg=self.crosshair_color)
                self.win_v.configure(bg=self.crosshair_color)

    def on_mode_change(self):
        if self.crosshair_active:
            if self.crosshair_mode.get() == "follow":
                if self.win_c:
                    self.win_c.withdraw()
                self.follow_cursor_loop()
            else:
                if self.win_c:
                    self.win_c.deiconify()

    def follow_cursor_loop(self):
        if self.crosshair_active and self.crosshair_mode.get() == "follow":
            x = self.frame.winfo_pointerx()
            y = self.frame.winfo_pointery()
            if x != self.cx or y != self.cy:
                self.cx = x
                self.cy = y
                self.update_crosshair_position()
            self.frame.after(16, self.follow_cursor_loop)

    def toggle_crosshair(self):
        if self.crosshair_active:
            self.destroy_crosshair()
            self.btn_toggle.config(text=self.tr("module_crosshair_btn_show", "Show Crosshair"))
        else:
            self.create_crosshair()
            self.btn_toggle.config(text=self.tr("module_crosshair_btn_hide", "Hide Crosshair"))

    def create_crosshair(self):
        self.crosshair_active = True
        screen_width = self.frame.winfo_screenwidth()
        screen_height = self.frame.winfo_screenheight()
        
        self.cx = screen_width // 2
        self.cy = screen_height // 2
        
        self.win_h = tk.Toplevel(self.frame)
        self.win_h.overrideredirect(True)
        self.win_h.attributes('-topmost', True)
        self.win_h.configure(bg=self.crosshair_color)
        
        self.win_v = tk.Toplevel(self.frame)
        self.win_v.overrideredirect(True)
        self.win_v.attributes('-topmost', True)
        self.win_v.configure(bg=self.crosshair_color)
        
        self.win_c = tk.Toplevel(self.frame)
        self.win_c.overrideredirect(True)
        self.win_c.attributes('-topmost', True)
        
        # ✥ icon inside a yellow square
        self.lbl_drag = tk.Label(self.win_c, text="\u2725", bg="yellow", fg="black", cursor="fleur", font=("Arial", 12))
        self.lbl_drag.pack(fill=tk.BOTH, expand=True)
        
        self.lbl_drag.bind("<ButtonPress-1>", self.start_move)
        self.lbl_drag.bind("<B1-Motion>", self.do_move)
        self.lbl_drag.bind("<ButtonPress-3>", lambda e: self.toggle_crosshair())
        
        # Also bind the lines just in case
        for win in (self.win_h, self.win_v):
            win.bind("<ButtonPress-1>", self.start_move)
            win.bind("<B1-Motion>", self.do_move)
            win.bind("<ButtonPress-3>", lambda e: self.toggle_crosshair())

        self.update_crosshair_position()
        
        if self.crosshair_mode.get() == "follow":
            self.win_c.withdraw()
            self.follow_cursor_loop()

    def update_crosshair_position(self):
        if not self.crosshair_active: return
        t = self.crosshair_thickness
        
        screen_width = self.frame.winfo_screenwidth()
        screen_height = self.frame.winfo_screenheight()
        
        w = screen_width * 3
        h = screen_height * 3
        
        self.win_h.geometry(f"{w}x{t}+{-screen_width}+{self.cy - t//2}")
        self.win_v.geometry(f"{t}x{h}+{self.cx - t//2}+{-screen_height}")
        self.win_c.geometry(f"24x24+{self.cx + 5}+{self.cy + 5}")

    def start_move(self, event):
        self.offset_x = self.cx - event.x_root
        self.offset_y = self.cy - event.y_root

    def do_move(self, event):
        self.cx = event.x_root + self.offset_x
        self.cy = event.y_root + self.offset_y
        self.update_crosshair_position()

    def destroy_crosshair(self):
        self.crosshair_active = False
        if self.win_h: self.win_h.destroy()
        if self.win_v: self.win_v.destroy()
        if self.win_c: self.win_c.destroy()
        self.win_h = self.win_v = self.win_c = None

    def on_destroy(self):
        self.destroy_crosshair()
        super().on_destroy()
