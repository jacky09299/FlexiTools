import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog, messagebox
import os
import importlib.util
import logging
import json
import threading # For running update checks in background
import tempfile # For temporary installer download
import subprocess # For running installer and helper script
import sys # For sys.executable

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


# Attempt to import update_manager and its components
try:
    import update_manager
except ImportError:
    print("ERROR: update_manager.py not found in ui.py. Update functionality will be disabled.")
    print(f"Current sys.path in ui.py: {sys.path}")
    class update_manager: # type: ignore
        UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
        NO_UPDATE_FOUND = "NO_UPDATE_FOUND"
        ERROR_FETCHING = "ERROR_FETCHING"
        ERROR_CONFIG = "ERROR_CONFIG"
        CHECK_SKIPPED_RATE_LIMIT = "CHECK_SKIPPED_RATE_LIMIT"
        CHECK_SKIPPED_ALREADY_PENDING = "CHECK_SKIPPED_ALREADY_PENDING"

        @staticmethod
        def get_current_version(): return "N/A"
        @staticmethod
        def get_update_info(): return {}
        @staticmethod
        def check_for_updates(force_check=False): return update_manager.ERROR_CONFIG
        APP_NAME = "FlexiTools"


from shared_state import SharedState
from style_manager import (
    COLOR_PRIMARY_BG,
    COLOR_WINDOW_BORDER, COLOR_TITLE_BAR_BG, COLOR_MENU_BAR_BG,
    COLOR_MENU_BUTTON_FG, COLOR_MENU_BUTTON_ACTIVE_BG, COLOR_ACCENT_HOVER
)
# from ctypes import windll # Moved to be platform-specific

# Platform-specific imports
if sys.platform == "win32":
    from ctypes import windll
else:
    windll = None # Placeholder for non-Windows systems


class AnimatedCanvas(tk.Canvas):
    """一個具有動態漸變背景和閃爍星星的畫布。"""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs, highlightthickness=0)
        self.stars = []
        self.bind("<Configure>", self._on_resize)

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'

    def _on_resize(self, event=None):
        pass # No gradient or stars to draw

class Module:
    def __init__(self, master, shared_state, module_name="UnknownModule", gui_manager=None):
        self.master = master
        self.shared_state = shared_state
        self.module_name = module_name
        self.gui_manager = gui_manager

        self.frame = ttk.Frame(self.master)

        self.title_bar_frame = ttk.Frame(self.frame, height=25, style="DragHandle.TFrame")
        self.title_bar_frame.pack(fill=tk.X, side=tk.TOP, pady=(0,2))

        self.drag_handle_label = ttk.Label(self.title_bar_frame, text="☰", cursor="fleur", style='Module.TLabel')
        self.drag_handle_label.pack(side=tk.LEFT, padx=5)

        self.title_label = ttk.Label(self.title_bar_frame, text=self.module_name, style='Module.TLabel')
        self.title_label.pack(side=tk.LEFT, padx=5)

        self.close_button = ttk.Button(self.title_bar_frame, text="X", width=3,
                                        command=self.close_module_action, style='TitleBar.TButton')
        self.close_button.pack(side=tk.RIGHT, padx=(0, 2))

        self.maximize_button = ttk.Button(
            self.title_bar_frame, text="⬜", width=3,
            command=self.toggle_maximize_action, style='TitleBar.TButton'
        )
        self.maximize_button.pack(side=tk.RIGHT, padx=(0, 2))

        self.resize_handle = ttk.Sizegrip(self.frame)
        self.resize_handle.pack(side=tk.BOTTOM, anchor=tk.SE)
        self.resize_handle.bind("<ButtonPress-1>", self._on_resize_start)
        self.resize_handle.bind("<B1-Motion>", self._on_resize_motion)
        self.resize_handle.bind("<ButtonRelease-1>", self._on_resize_release)

        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0

        self.is_maximized = False

        self.shared_state.log(f"Module '{self.module_name}' initialized with title bar.")

    def close_module_action(self):
        if self.gui_manager:
            self.shared_state.log(f"Close button clicked for module '{self.module_name}'.")
            self.gui_manager.hide_module(self.module_name)
        else:
            self.shared_state.log(f"Cannot close module '{self.module_name}': gui_manager not available.", "ERROR")

    def toggle_maximize_action(self):
        if not self.gui_manager:
            self.shared_state.log(f"Cannot maximize module '{self.module_name}': gui_manager not available.", "ERROR")
            return
        if not self.is_maximized:
            self.gui_manager.maximize_module(self.module_name)
        else:
            self.gui_manager.restore_modules()

    def _on_resize_start(self, event):
        if self.gui_manager and hasattr(self.gui_manager, 'window_size_fixed_after_init') and self.gui_manager.window_size_fixed_after_init and hasattr(self.gui_manager, 'root') and hasattr(self.gui_manager.root, 'maxsize') and hasattr(self.gui_manager.root, 'winfo_width') and hasattr(self.gui_manager.root, 'winfo_height'):
            self.gui_manager.is_module_resizing = True
            self.gui_manager.root_maxsize_backup = self.gui_manager.root.maxsize()
            self.gui_manager.root_minsize_backup = self.gui_manager.root.minsize()
            current_width = self.gui_manager.root.winfo_width()
            current_height = self.gui_manager.root.winfo_height()
            self.gui_manager.window_geometry_before_module_resize = f"{current_width}x{current_height}"
            self.gui_manager.root.maxsize(current_width, current_height)
            self.gui_manager.root.minsize(current_width, current_height)
            if hasattr(self.gui_manager, 'shared_state'):
                self.gui_manager.shared_state.log(
                    f"Module resize started: Geometry '{self.gui_manager.window_geometry_before_module_resize}' stored. Maxsize/minsize temporarily set to {current_width}x{current_height}.", "DEBUG"
                )
        elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
             if not (hasattr(self.gui_manager, 'window_size_fixed_after_init') and self.gui_manager.window_size_fixed_after_init):
                 self.gui_manager.shared_state.log("Module resize started: window_size_fixed_after_init is False, not modifying window constraints.", "DEBUG")
             else:
                 self.gui_manager.shared_state.log("Module resize started: Could not set temporary window constraints (root or methods missing).", "WARNING")

        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root

        if self.gui_manager and self.gui_manager.main_layout_manager:
            module_props = self.gui_manager.main_layout_manager.get_module_info(self.module_name)
            if module_props:
                self.resize_start_width = module_props['width']
                self.resize_start_height = module_props['height']
            else:
                frame_wrapper = self.master
                self.resize_start_width = frame_wrapper.winfo_width()
                self.resize_start_height = frame_wrapper.winfo_height()
        else:
            frame_wrapper = self.master
            self.resize_start_width = frame_wrapper.winfo_width()
            self.resize_start_height = frame_wrapper.winfo_height()

    def _on_resize_motion(self, event):
        if not self.gui_manager or not self.gui_manager.main_layout_manager:
            return

        delta_x = event.x_root - self.resize_start_x
        delta_y = event.y_root - self.resize_start_y

        new_width = self.resize_start_width + delta_x
        new_height = self.resize_start_height + delta_y

        min_width = 50
        min_height = 50
        new_width = max(min_width, new_width)
        new_height = max(min_height, new_height)

        if self.gui_manager and hasattr(self.gui_manager, "canvas"):
            canvas_width = self.gui_manager.canvas.winfo_width()
            if canvas_width > 1:
                new_width = min(new_width, canvas_width)

        self.gui_manager.main_layout_manager.resize_module(self.module_name, new_width, new_height)

        if self.gui_manager and hasattr(self.gui_manager, 'update_layout_manager_canvas_item_config'):
            self.gui_manager.update_layout_manager_canvas_item_config()

    def _on_resize_release(self, event):
        if self.gui_manager:
            self.gui_manager.update_layout_scrollregion()
            if hasattr(self.gui_manager, "save_layout_config"):
                self.gui_manager.save_layout_config()
        if self.gui_manager:
            self.gui_manager.update_layout_scrollregion()

        if self.gui_manager and hasattr(self.gui_manager, 'is_module_resizing') and self.gui_manager.is_module_resizing:
            if hasattr(self.gui_manager, 'root_maxsize_backup') and self.gui_manager.root_maxsize_backup is not None and hasattr(self.gui_manager, 'root') and hasattr(self.gui_manager.root, 'maxsize'):
                self.gui_manager.root.maxsize(
                    self.gui_manager.root_maxsize_backup[0],
                    self.gui_manager.root_maxsize_backup[1]
                )
                if hasattr(self.gui_manager, 'shared_state'):
                    self.gui_manager.shared_state.log(
                        f"Module resize ended: Main window maxsize restored to {self.gui_manager.root_maxsize_backup}.", "DEBUG"
                    )
            elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
                self.gui_manager.shared_state.log(
                    "Module resize ended: No valid maxsize backup found to restore.", "WARNING"
                )
            if hasattr(self.gui_manager, 'root_minsize_backup') and self.gui_manager.root_minsize_backup is not None and hasattr(self.gui_manager, 'root') and hasattr(self.gui_manager.root, 'minsize'):
                self.gui_manager.root.minsize(
                    self.gui_manager.root_minsize_backup[0],
                    self.gui_manager.root_minsize_backup[1]
                )
                if hasattr(self.gui_manager, 'shared_state'):
                    self.gui_manager.shared_state.log(
                        f"Module resize ended: Main window minsize restored to {self.gui_manager.root_minsize_backup}.", "DEBUG"
                    )
            elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
                self.gui_manager.shared_state.log(
                    "Module resize ended: No valid minsize backup found to restore.", "WARNING"
                )

            if hasattr(self.gui_manager, 'root'):
                w = self.gui_manager.root.winfo_width()
                h = self.gui_manager.root.winfo_height()
                self.gui_manager.root.geometry(f"{w}x{h}")

            self.gui_manager.is_module_resizing = False
            if hasattr(self.gui_manager, 'root_maxsize_backup'):
                self.gui_manager.root_maxsize_backup = None
            if hasattr(self.gui_manager, 'root_minsize_backup'):
                self.gui_manager.root_minsize_backup = None
            if hasattr(self.gui_manager, 'window_geometry_before_module_resize'):
                self.gui_manager.window_geometry_before_module_resize = None

    def get_frame(self):
        return self.frame

    def create_ui(self):
        ttk.Label(self.frame, text=f"Default content for {self.module_name}").pack(padx=10, pady=10)
        self.shared_state.log(f"Module '{self.module_name}' UI created (default implementation).")

    def on_destroy(self):
        self.shared_state.log(f"Module '{self.module_name}' is being destroyed.")

class CustomLayoutManager(AnimatedCanvas):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.modules = {}
        self.canvas_parent = master
        self.current_canvas_width = self.canvas_parent.winfo_width() if self.canvas_parent.winfo_width() > 1 else 800
        self.last_calculated_content_width = 0
        self.last_calculated_content_height = 0

    def add_module(self, module_frame, module_name, width, height, defer_reflow=False):
        self.modules[module_name] = {
            'frame': module_frame,
            'name': module_name,
            'width': width,
            'height': height,
        }
        if not defer_reflow:
            self.reflow_layout()
        else:
            logging.debug(f"Add_module for {module_name} deferred reflow.")

    def remove_module(self, module_name):
        if module_name in self.modules:
            module_info = self.modules.pop(module_name)
            module_info['frame'].place_forget()
            self.reflow_layout()
        else:
            logging.getLogger().warning(f"CustomLayoutManager: Attempted to remove non-existent module '{module_name}'.")

    def resize_module(self, module_name, width, height, defer_reflow=False):
        if module_name in self.modules:
            self.modules[module_name]['width'] = max(10, width)
            self.modules[module_name]['height'] = max(10, height)
            if not defer_reflow:
                self.reflow_layout()
            else:
                logging.debug(f"Resize_module for {module_name} deferred reflow.")
        else:
            logging.warning(f"CustomLayoutManager: Attempted to resize non-existent module: {module_name}")

    def _is_overlapping(self, r1_x, r1_y, r1_w, r1_h, r2_x, r2_y, r2_w, r2_h) -> bool:
        return r1_x < r2_x + r2_w and \
               r1_x + r1_w > r2_x and \
               r1_y < r2_y + r2_h and \
               r1_y + r1_h > r2_y

    def reflow_layout(self, simulate=False, module_configs_override=None):
        logging.info("Reflowing layout with new optimized algorithm.")
        placed_modules_rects = []

        if module_configs_override is not None:
            module_iterator = module_configs_override
        else:
            module_iterator = list(self.modules.values())

        container_width = self.current_canvas_width
        if container_width <= 1:
             container_width = self.canvas_parent.winfo_width()
        if container_width <= 1:
             container_width = 800

        min_module_dim = 10
        module_margin_x = 5
        module_margin_y = 5

        current_x = 0
        current_y = 0
        row_height = 0
        max_x_coord = 0
        max_y_coord = 0

        for module_info in module_iterator:
            module_name = module_info['name']
            current_w = max(min_module_dim, module_info['width'])
            current_h = max(min_module_dim, module_info['height'])

            if current_x > 0 and (current_x + current_w) > container_width:
                current_y += row_height + module_margin_y
                current_x = 0
                row_height = 0

            final_x = current_x
            final_y = current_y

            module_info['x'] = final_x
            module_info['y'] = final_y

            if not simulate:
                if 'frame' in module_info and module_info['frame']:
                    module_info['frame'].place(x=final_x, y=final_y, width=current_w, height=current_h)
                elif not module_configs_override:
                    logging.warning(f"CustomLayoutManager: Frame not found for module {module_name} during actual placement.")

            placed_modules_rects.append({'name': module_name, 'x': final_x, 'y': final_y, 'w': current_w, 'h': current_h})

            current_x += current_w + module_margin_x
            row_height = max(row_height, current_h)

            max_x_coord = max(max_x_coord, final_x + current_w)
            max_y_coord = max(max_y_coord, final_y + current_h)

        self.last_calculated_content_width = max_x_coord
        self.last_calculated_content_height = max_y_coord

        layout_manager_own_width = self.current_canvas_width
        if layout_manager_own_width <= 1:
            layout_manager_own_width = self.canvas_parent.winfo_width()
            if layout_manager_own_width <= 1:
                layout_manager_own_width = 800

        effective_height = self.last_calculated_content_height if self.last_calculated_content_height > 0 else 10
        self.config(width=layout_manager_own_width, height=effective_height)
        logging.debug(f"Reflow complete. Content WxH: {self.last_calculated_content_width}x{self.last_calculated_content_height}. LM WxH: {layout_manager_own_width}x{effective_height}")

    def scale_modules(self, scale_ratio):
        for module_info in self.modules.values():
            module_info['width'] = int(module_info['width'] * scale_ratio)
            module_info['height'] = int(module_info['height'] * scale_ratio)
        self.reflow_layout()

    def get_max_module_width(self) -> int:
        if not self.modules:
            return 0

        max_w = 0
        for module_info in self.modules.values():
            if module_info.get('width', 0) > max_w:
                max_w = module_info['width']
        return max_w

    def move_module_before(self, module_to_move_name: str, target_module_name: str or None):
        if module_to_move_name not in self.modules:
            logging.error(f"CustomLayoutManager: Module to move '{module_to_move_name}' not found.")
            return

        moved_item_info = self.modules.pop(module_to_move_name)

        new_modules_dict = {}

        if target_module_name is None or target_module_name == module_to_move_name or target_module_name not in self.modules:
            for name, info in self.modules.items():
                new_modules_dict[name] = info
            new_modules_dict[module_to_move_name] = moved_item_info
        else:
            inserted = False
            for name, info in self.modules.items():
                if name == target_module_name:
                    new_modules_dict[module_to_move_name] = moved_item_info
                    inserted = True
                new_modules_dict[name] = info
            if not inserted:
                 new_modules_dict[module_to_move_name] = moved_item_info

        self.modules = new_modules_dict
        logging.info(f"New module order: {list(self.modules.keys())}")
        self.reflow_layout()

    def get_layout_data(self) -> dict:
        data = {}
        for name, info in self.modules.items():
            data[name] = {
                'width': info['width'],
                'height': info['height'],
                'x': info.get('x', 0),
                'y': info.get('y', 0)
            }
        return data

    def get_module_info(self, module_name):
        return self.modules.get(module_name)

class ModularGUI:
    CONFIG_FILE = "layout_config.json"
    PROFILE_PREFIX = "layout_profile_"
    PROFILE_SUFFIX = ".json"

    def __init__(self, root, shared_state: SharedState): # Added shared_state parameter
        self.root = root
        self.shared_state = shared_state # Use passed shared_state
        self.root.overrideredirect(True)
        try: # Try to set icon, ignore if fails (e.g. file not found)
            root.iconbitmap("tools.ico")
        except tk.TclError:
            self.shared_state.log("Could not load window icon 'tools.ico'.", "WARNING")

        self.root.geometry("800x600")

        self.is_maximized = False
        self.normal_geometry = "800x600"

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_mode = None

        self.main_frame = tk.Frame(self.root, bg=COLOR_WINDOW_BORDER, bd=1, relief="solid")
        self.main_frame.pack(fill="both", expand=True)

        self.title_bar = tk.Frame(self.main_frame, bg=COLOR_TITLE_BAR_BG, height=35, relief="flat")
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)

        if Image and ImageTk:
            try:
                logo_path = "assets/logo.png"
                logo_image = Image.open(logo_path)
                logo_image = logo_image.resize((24, 24), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image) # Keep reference
                logo_label = tk.Label(self.title_bar, image=self.logo_photo, bg=COLOR_TITLE_BAR_BG)
                logo_label.pack(side="left", padx=(10, 5), pady=5)
            except Exception as e:
                self.shared_state.log(f"Could not load logo: {e}", "WARNING")

        self.title_label = tk.Label(self.title_bar, text="FlexiTools",
                                   bg=COLOR_TITLE_BAR_BG, fg="white", font=("Arial", 10, "bold"))
        self.title_label.pack(side="left", padx=(0, 10), pady=8)

        self.controls_frame = tk.Frame(self.title_bar, bg=COLOR_TITLE_BAR_BG)
        self.controls_frame.pack(side="right", padx=5)

        self.min_btn = tk.Button(self.controls_frame, text="🗕",
                                command=self.minimize_window,
                                bg=COLOR_TITLE_BAR_BG, fg="white", relief="flat",
                                font=("Arial", 8), width=3, height=1,
                                activebackground=COLOR_ACCENT_HOVER, activeforeground="white")
        self.min_btn.pack(side="left", padx=2)

        self.max_btn = tk.Button(self.controls_frame, text="🗖",
                                command=self.toggle_maximize,
                                bg=COLOR_TITLE_BAR_BG, fg="white", relief="flat",
                                font=("Arial", 8), width=3, height=1,
                                activebackground=COLOR_ACCENT_HOVER, activeforeground="white")
        self.max_btn.pack(side="left", padx=2)

        self.close_btn = tk.Button(self.controls_frame, text="🗙",
                                  command=self.close_window,
                                  bg=COLOR_TITLE_BAR_BG, fg="white", relief="flat",
                                  font=("Arial", 8), width=3, height=1,
                                  activebackground="#e74c3c", activeforeground="white")
        self.close_btn.pack(side="right", padx=2)

        self.content_frame = tk.Frame(self.main_frame, bg=COLOR_PRIMARY_BG, bd=0, relief="flat")
        self.content_frame.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        self.status_bar = tk.Frame(self.main_frame, bg=COLOR_TITLE_BAR_BG, height=25)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(self.status_bar, text="就緒",
                                    bg=COLOR_TITLE_BAR_BG, fg="white", font=("Arial", 8))
        self.status_label.pack(side="left", padx=10, pady=4)

        # Register log callback with shared_state
        if self.shared_state:
            self.shared_state.set_log_callback(self.update_status_bar_log)

        self.saves_dir = os.path.join("modules", "saves")
        if not os.path.exists(self.saves_dir):
            try:
                os.makedirs(self.saves_dir)
                self.shared_state.log(f"Created saves directory: {self.saves_dir}", "INFO")
            except Exception as e_mkdir:
                 self.shared_state.log(f"Failed to create saves_dir '{self.saves_dir}': {e_mkdir}", "ERROR")
                 self.saves_dir = "."

        self.shared_state.log(f"Application saves directory set to: {self.saves_dir}", "INFO")

        self.menu_frame = tk.Frame(self.content_frame, bg=COLOR_MENU_BAR_BG)
        self.menu_frame.pack(fill="x", side="top")

        self.modules_menu = tk.Menu(self.root, tearoff=0)
        self.modules_menubutton = tk.Menubutton(self.menu_frame, text="Modules", menu=self.modules_menu,
                                                bg=COLOR_MENU_BAR_BG, fg=COLOR_MENU_BUTTON_FG, activebackground=COLOR_MENU_BUTTON_ACTIVE_BG, activeforeground="white",
                                                relief="flat", padx=10, pady=5)
        self.modules_menubutton.pack(side="left")
        self.modules_menubutton.bind("<Button-1>", lambda e: self.modules_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height()))

        self.profile_menu = tk.Menu(self.root, tearoff=0)
        self.profile_menubutton = tk.Menubutton(self.menu_frame, text="設定檔", menu=self.profile_menu,
                                                 bg=COLOR_MENU_BAR_BG, fg=COLOR_MENU_BUTTON_FG, activebackground=COLOR_MENU_BUTTON_ACTIVE_BG, activeforeground="white",
                                                 relief="flat", padx=10, pady=5)
        self.profile_menubutton.pack(side="left")
        self.profile_menubutton.bind("<Button-1>", lambda e: self.profile_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height()))
        self.profile_menu.add_command(label="儲存目前佈局為設定檔...", command=self.save_profile_dialog)
        self.profile_menu.add_command(label="載入設定檔...", command=self.load_profile_dialog)
        self.profile_menu.add_separator()
        self.profile_menu.add_command(label="管理設定檔...", command=self.manage_profiles_dialog)

        self.help_menu = tk.Menu(self.root, tearoff=0)
        self.help_menubutton = tk.Menubutton(self.menu_frame, text="Help", menu=self.help_menu,
                                             bg=COLOR_MENU_BAR_BG, fg=COLOR_MENU_BUTTON_FG, activebackground=COLOR_MENU_BUTTON_ACTIVE_BG, activeforeground="white",
                                             relief="flat", padx=10, pady=5)
        self.help_menubutton.pack(side="left")
        self.help_menubutton.bind("<Button-1>", lambda e: self.help_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height()))
        self.help_menu.add_command(label="Check for Updates...", command=self.ui_check_for_updates_manual)

        self.shared_state.log("ModularGUI initialized.")

        self.modules_dir = "modules"
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            self.shared_state.log(f"Created modules directory: {self.modules_dir}")

        self.loaded_modules = {}
        self.module_instance_counters = {}
        self.map_event_handled = 0
        self.root.after(10, lambda: self.show_on_taskbar(self.root))
        self.maximized_module_name = None
        self._pre_maximize_layout = None

        self.dragged_module_name = None
        self.drag_start_widget = None
        self.drop_target_module_frame_wrapper = None
        self.original_dragged_module_relief = None

        self.ghost_module_frame = None
        self.ghost_canvas_window_id = None
        self.last_preview_target_module_name = None

        self.is_module_resizing = False
        self.root_maxsize_backup = None
        self.window_geometry_before_module_resize = None

        self.resize_debounce_timer = None
        self.resize_debounce_delay = 250

        self.canvas_container = ttk.Frame(self.content_frame, style='Main.TFrame')
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_container, bg=COLOR_PRIMARY_BG, highlightthickness=0)

        self.setup_bindings()

        self.v_scrollbar = ttk.Scrollbar(self.canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_container.pack_propagate(False)

        self.main_layout_manager = CustomLayoutManager(self.canvas)

        self.main_layout_manager_window_id = self.canvas.create_window(
            (0, 0), window=self.main_layout_manager, anchor='nw'
        )

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.available_module_classes = {}
        self.window_size_fixed_after_init = False
        self.shared_state.log(f"ModularGUI.__init__: self.window_size_fixed_after_init initialized to {self.window_size_fixed_after_init}", "INFO")

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.main_layout_manager.bind("<Button-3>", self.show_context_menu)

        self.shared_state.log("Discovering modules...")
        self.discover_modules()
        self.shared_state.update_splash_progress(80) # Progress after discovering modules

        for module_name in sorted(self.available_module_classes.keys()):
            self.modules_menu.add_command(
                label=f"Add {module_name}",
                command=lambda mn=module_name: self.add_module_from_menu(mn)
            )

        self.shared_state.log("Setting up layout...")
        self.setup_default_layout()
        self.shared_state.update_splash_progress(90) # Progress after layout setup

        self.root.after(1000, self.ui_check_for_updates_startup)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_status_bar_log(self, message):
        try:
            status_bar_width = self.status_bar.winfo_width()
            # Estimate average character width; for more accuracy, could use font.measure
            # For simplicity, let's assume an average character width of 7 pixels for Arial 8.
            # This is a rough estimate and might need adjustment.
            avg_char_width = 7 
            max_chars = (status_bar_width // 2) // avg_char_width

            if len(message) > max_chars:
                display_message = message[:max_chars-3] + "..."
            else:
                display_message = message
            
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=display_message)
            else:
                # This case should ideally not happen if status_label is always present
                print(f"Status label not available for message: {display_message}")
        except tk.TclError as e:
            # This can happen if the window is being destroyed
            self.shared_state.log(f"Error updating status bar log (TclError): {e}", "WARNING")
        except Exception as e:
            # Catch any other unexpected errors
            if hasattr(self, 'shared_state') and self.shared_state: # Check if shared_state is available
                 self.shared_state.log(f"Unexpected error updating status bar log: {e}", "ERROR")
            else:
                print(f"Unexpected error updating status bar log (shared_state not available): {e}")


    def _start_download_in_thread(self, version_to_download, download_url):
        download_thread = threading.Thread(
            target=self._download_installer_and_launch_update,
            args=(version_to_download, download_url),
            daemon=True
        )
        download_thread.start()

    def _download_installer_and_launch_update(self, version_to_download, download_url):
        try:
            import requests # Keep import here as it's only for this functionality
            self.shared_state.log(f"Downloading installer from {download_url}...", "INFO")
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, f"FlexiToolsInstaller_{version_to_download}.exe")
            with open(installer_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            self.shared_state.log(f"Installer downloaded to {installer_path}", "INFO")
            messagebox.showinfo("下載完成", f"安裝檔已下載到：\n{installer_path}")
            self.root.after(0, self._launch_update_helper, installer_path)
        except requests.exceptions.RequestException as e:
            self.shared_state.log(f"Download failed: {e}", "ERROR")
            messagebox.showerror("Update Error", f"下載更新失敗：{e}")
        except Exception as e:
            self.shared_state.log(f"Unexpected error: {e}", "ERROR")
            messagebox.showerror("Update Error", f"下載更新時發生錯誤：{e}")

    def _launch_update_helper(self, installer_path):
        self.shared_state.log("Preparing to launch update helper script.", "INFO")

        confirm_update = messagebox.askyesno("Ready to Update",
                                             "The update has been downloaded.\n\n"
                                             "FlexiTools will now close to install the update and then restart automatically.\n\n"
                                             "Do you want to proceed?", parent=self.root)
        if not confirm_update:
            self.shared_state.log("User cancelled update before applying.", "INFO")
            try:
                if os.path.exists(installer_path):
                    os.remove(installer_path)
                    self.shared_state.log(f"Cleaned up downloaded installer: {installer_path}", "INFO")
            except Exception as e:
                self.shared_state.log(f"Error cleaning up installer {installer_path}: {e}", "WARNING")
            return

        current_pid = os.getpid()
        app_executable_path = sys.executable

        batch_script_content = f"""@echo off
        echo Closing FlexiTools (PID: {current_pid})...
        TASKKILL /F /PID {current_pid}
        echo Waiting for application to close...
        timeout /t 3 /nobreak > NUL

        echo Running installer in silent mode...
        start /wait "" "{installer_path}" /UPDATE /S

        echo Installer finished.
        timeout /t 2 /nobreak > NUL

        echo Restarting FlexiTools...
        start "" "{app_executable_path}"

        echo Cleaning up...
        del "{installer_path}"
        (goto) 2>nul & del "%~f0"
        """
        temp_dir = tempfile.gettempdir()
        batch_file_path = os.path.join(temp_dir, "flexitools_update_runner.bat")

        try:
            with open(batch_file_path, "w") as bf:
                bf.write(batch_script_content)
            self.shared_state.log(f"Update helper script created at: {batch_file_path}", "INFO")
            subprocess.Popen([batch_file_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.shared_state.log("Update helper script launched. Closing application.", "INFO")
            self.root.destroy()
        except Exception as e:
            self.shared_state.log(f"Failed to create or launch update helper script: {e}", "ERROR")
            messagebox.showerror("Update Error", f"Failed to start the update process: {e}", parent=self.root)

    def _initiate_update_download_and_install(self, version, url):
        self.shared_state.log(f"User agreed to update to version {version} from {url}. Starting download process...", "INFO")
        self._start_download_in_thread(version, url)

    def _handle_update_check_result(self, status_code, manual_check=False):
        if status_code == update_manager.UPDATE_AVAILABLE:
            update_details = update_manager.get_update_info().get("available_update")
            if update_details:
                version = update_details["version"]
                url = update_details["url"]
                current_version_str = update_manager.get_current_version()
                msg = (f"A new version ({version}) of {update_manager.APP_NAME} is available!\n"
                       f"You are currently running version {current_version_str}.\n\n"
                       "Would you like to download and install it now?")
                if messagebox.askyesno("Update Available", msg):
                    self._initiate_update_download_and_install(version, url)
                else:
                    self.shared_state.log("User declined automatic update.", "INFO")
            else:
                 if manual_check:
                    messagebox.showerror("Update Error", "Update information is inconsistent. Please try again.")
                 self.shared_state.log("Update status was AVAILABLE but no details found in update_info.json.", "ERROR")
        elif status_code == update_manager.NO_UPDATE_FOUND:
            if manual_check:
                messagebox.showinfo("No Updates", f"{update_manager.APP_NAME} is up to date.")
            self.shared_state.log("No new update found.", "INFO")
        elif status_code == update_manager.ERROR_FETCHING:
            if manual_check:
                messagebox.showerror("Update Check Failed", "Could not connect to the update server.")
            self.shared_state.log("Error fetching update information.", "WARNING")
        elif status_code == update_manager.ERROR_CONFIG:
            if manual_check:
                 messagebox.showerror("Update Error", "Update configuration error.")
            self.shared_state.log("Update configuration error.", "ERROR")
        elif status_code in [update_manager.CHECK_SKIPPED_RATE_LIMIT, update_manager.CHECK_SKIPPED_ALREADY_PENDING]:
            if manual_check:
                 self.shared_state.log(f"Manual check resulted in unexpected status: {status_code}", "WARNING")
            else:
                 self.shared_state.log(f"Update check skipped: {status_code}", "INFO")
        if manual_check and hasattr(self, 'help_menubutton'):
            try:
                self.help_menubutton.config(state=tk.NORMAL)
            except tk.TclError: pass

    def _perform_update_check_threaded(self, force_check=False, is_manual_check=False):
        self.shared_state.log(f"Threaded update check started. Force: {force_check}, Manual: {is_manual_check}", "INFO")
        if is_manual_check and hasattr(self, 'help_menubutton'):
            try:
                self.help_menubutton.config(state=tk.DISABLED)
            except tk.TclError: pass
        status = update_manager.check_for_updates(force_check=force_check)
        self.root.after(0, self._handle_update_check_result, status, is_manual_check)

    def setup_bindings(self):
        self.title_bar.bind("<Button-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<Button-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)
        self.root.bind('<Map>', self.restore_window)
        self.root.bind("<Motion>", self.on_mouse_motion)
        self.root.bind("<Button-1>", self.on_mouse_down)
        self.root.bind("<B1-Motion>", self.on_mouse_drag)
        self.root.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.title_bar.bind("<Double-Button-1>", self.toggle_maximize)
        self.title_label.bind("<Double-Button-1>", self.toggle_maximize)

    def ui_check_for_updates_startup(self):
        self.shared_state.log("Initiating startup update check.", "INFO")
        thread = threading.Thread(target=self._perform_update_check_threaded, args=(False, False), daemon=True)
        thread.start()

    def ui_check_for_updates_manual(self):
        self.shared_state.log("Manual update check initiated by user.", "INFO")
        if hasattr(self, 'help_menu'):
            try:
                messagebox.showinfo("Checking for Updates", "Checking for updates in the background...", parent=self.root)
            except tk.TclError: pass
        thread = threading.Thread(target=self._perform_update_check_threaded, args=(True, True), daemon=True)
        thread.start()

    def _finalize_initial_window_state(self):
        self.root.update_idletasks()
        self.window_size_fixed_after_init = True
        current_w = self.root.winfo_width()
        current_h = self.root.winfo_height()
        self.shared_state.log(
            f"Initial window state finalized. window_size_fixed_after_init=True. Window remains user-resizable. Min size fixed. Current size: {current_w}x{current_h}",
            "INFO"
        )

    def _on_mousewheel(self, event):
        if hasattr(event, 'num') and event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif hasattr(event, 'num') and event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, 'delta'):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_layout_scrollregion(self):
        self.main_layout_manager.update_idletasks()
        content_total_height = self.main_layout_manager.last_calculated_content_height
        content_total_width = self.main_layout_manager.last_calculated_content_width
        canvas_viewport_width = self.canvas.winfo_width()
        if canvas_viewport_width <= 1: canvas_viewport_width = 800
        item_width_for_canvas = canvas_viewport_width
        self.canvas.config(scrollregion=(0, 0, content_total_width, content_total_height))
        self.canvas.itemconfig(self.main_layout_manager_window_id,
                               width=item_width_for_canvas,
                               height=content_total_height)

    def update_layout_manager_canvas_item_config(self):
        if not hasattr(self, 'main_layout_manager') or self.main_layout_manager is None:
            self.shared_state.log("update_layout_manager_canvas_item_config: main_layout_manager not available.", "WARNING")
            return
        content_height = self.main_layout_manager.last_calculated_content_height
        content_width = self.main_layout_manager.last_calculated_content_width
        canvas_viewport_width = self.canvas.winfo_width()
        if canvas_viewport_width <= 1: canvas_viewport_width = self.root.winfo_width()
        if canvas_viewport_width <= 1: canvas_viewport_width = 800
        self.canvas.itemconfig(self.main_layout_manager_window_id,
                               width=canvas_viewport_width,
                               height=content_height)
        self.canvas.config(scrollregion=(0, 0, content_width, content_height))
        self.shared_state.log(f"update_layout_manager_canvas_item_config: Canvas item for LM set to width={canvas_viewport_width}, height={content_height}. Scrollregion set to (0,0,{content_width},{content_height})", "DEBUG")

    def on_canvas_configure(self, event):
        if self.resize_debounce_timer is not None:
            self.root.after_cancel(self.resize_debounce_timer)
        self.resize_debounce_timer = self.root.after(
            self.resize_debounce_delay,
            lambda e=event: self._handle_canvas_resize_debounced(e)
        )

    def _handle_canvas_resize_debounced(self, event):
        self.shared_state.log(f"Debounced canvas resize handling. New width: {event.width}", "DEBUG")
        canvas_width = event.width
        if self.maximized_module_name and self.maximized_module_name in self.loaded_modules:
            canvas_height = self.canvas.winfo_height()
            self.main_layout_manager.config(width=canvas_width, height=canvas_height)
            self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width, height=canvas_height)
            mod_data = self.loaded_modules[self.maximized_module_name]
            frame_wrapper = mod_data.get('frame_wrapper')
            if frame_wrapper and frame_wrapper.winfo_exists():
                frame_wrapper.place(x=0, y=0, width=canvas_width, height=canvas_height)
            self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        else:
            prev_width = 0
            if hasattr(self.main_layout_manager, 'current_canvas_width'):
                prev_width = self.main_layout_manager.current_canvas_width
                self.main_layout_manager.current_canvas_width = canvas_width
            self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width)
            if prev_width > 0 and canvas_width > 0 and prev_width != canvas_width:
                scale_ratio = canvas_width / prev_width
                self.shared_state.log(f"Debounced resize: Scaling modules. Prev width: {prev_width}, New width: {canvas_width}, Ratio: {scale_ratio}", "DEBUG")
                if hasattr(self.main_layout_manager, 'scale_modules'):
                    self.main_layout_manager.scale_modules(scale_ratio)
            elif hasattr(self.main_layout_manager, 'reflow_layout'):
                self.shared_state.log(f"Debounced resize: Reflowing layout. Prev width: {prev_width}, New width: {canvas_width}", "DEBUG")
                self.main_layout_manager.reflow_layout()
            self.update_layout_scrollregion()

    def update_min_window_size(self):
        flag_exists = hasattr(self, 'window_size_fixed_after_init')
        flag_value = self.window_size_fixed_after_init if flag_exists else "N/A"
        self.shared_state.log(f"update_min_window_size CALLED. Flag 'window_size_fixed_after_init' exists: {flag_exists}, Value: {flag_value}", "INFO")
        if flag_exists and self.window_size_fixed_after_init:
            self.shared_state.log("update_min_window_size: Returning early because window_size_fixed_after_init is True.", "INFO")
            return
        if not hasattr(self, 'main_layout_manager') or self.main_layout_manager is None:
            self.shared_state.log("update_min_window_size: Returning early because main_layout_manager is not available.", "INFO")
            return
        max_module_w = self.main_layout_manager.get_max_module_width()
        base_min_width = 200; padding = 20
        effective_min_width = max(base_min_width, max_module_w + padding if max_module_w > 0 else base_min_width)
        current_min_height = 0
        try: current_min_height = self.root.minsize()[1]
        except tk.TclError: current_min_height = 0
        if current_min_height == 1 and self.root.winfo_height() > 1 :
             current_min_height = self.root.winfo_height() if self.root.winfo_height() > 20 else 200
        current_min_height = max(200, current_min_height)
        self.shared_state.log(f"update_min_window_size: Proceeding to set minsize. Calculated effective_min_width: {effective_min_width}, current_min_height: {current_min_height}", "INFO")
        try:
            self.root.minsize(effective_min_width, current_min_height)
            self.shared_state.log(f"update_min_window_size: self.root.minsize({effective_min_width}, {current_min_height}) CALLED.", "INFO")
            self.shared_state.log(f"Minimum window width set to: {effective_min_width}, min_height: {current_min_height}", "DEBUG")
        except tk.TclError as e:
            self.shared_state.log(f"update_min_window_size: Error setting minsize: {e}", "WARNING")

    def _generate_instance_id(self, module_name):
        count = self.module_instance_counters.get(module_name, 1)
        instance_id = f"{module_name}#{count}"
        self.module_instance_counters[module_name] = count + 1
        return instance_id

    def add_module_from_menu(self, module_name: str):
        self.shared_state.log(f"Attempting to add module '{module_name}' from menu.")
        if module_name in self.available_module_classes:
            children = self.main_layout_manager.winfo_children()
            if len(children) == 1 and isinstance(children[0], ttk.Label):
                if "No modules available" in children[0].cget("text") or \
                   "No modules displayed" in children[0].cget("text"):
                    children[0].destroy()
                    self.shared_state.log("Removed default placeholder label.", "DEBUG")
            self.instantiate_module(module_name, self.main_layout_manager)
            self.main_layout_manager.reflow_layout()
            self.root.update_idletasks()
            self.update_min_window_size()
            self.update_layout_scrollregion()
            self.shared_state.log(f"Module '{module_name}' instantiated from menu and layout reflowed.")
            self.save_layout_config()
        else:
            self.shared_state.log(f"Module '{module_name}' cannot be added, not found in available modules.", "WARNING")

    def discover_modules(self):
        self.shared_state.log("Discovering available modules...")
        self.available_module_classes.clear()
        if not os.path.exists(self.modules_dir):
            self.shared_state.log(f"Modules directory '{self.modules_dir}' not found.", level=logging.WARNING)
            return
        for filename in os.listdir(self.modules_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                try:
                    filepath = os.path.join(self.modules_dir, filename)
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    module_lib = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module_lib)
                    module_class_name = None
                    for item_name in dir(module_lib):
                        item = getattr(module_lib, item_name)
                        if isinstance(item, type) and issubclass(item, Module) and item is not Module:
                            module_class_name = item_name
                            break
                    if module_class_name:
                        ModuleClass = getattr(module_lib, module_class_name)
                        self.available_module_classes[module_name] = ModuleClass
                        self.shared_state.log(f"Discovered module class {ModuleClass.__name__} in {filename}")
                    else:
                        self.shared_state.log(f"No suitable Module class found in {filename}", level=logging.WARNING)
                except Exception as e:
                    self.shared_state.log(f"Failed to discover module from {filename}: {e}", level=logging.ERROR)
        self.shared_state.log(f"Module discovery complete. Available: {list(self.available_module_classes.keys())}")

    def instantiate_module(self, module_name, parent_layout_manager):
        if module_name not in self.available_module_classes:
            self.shared_state.log(f"Module class for '{module_name}' not found.", level=logging.ERROR)
            return None
        ModuleClass = self.available_module_classes[module_name]
        instance_id = self._generate_instance_id(module_name)
        frame_wrapper = ttk.Frame(parent_layout_manager)
        try:
            module_instance = ModuleClass(frame_wrapper, self.shared_state, instance_id, self)
            module_instance.get_frame().pack(fill=tk.BOTH, expand=True)
            self.loaded_modules[instance_id] = {
                'class': ModuleClass, 'instance': module_instance,
                'frame_wrapper': frame_wrapper, 'module_name': module_name,
                'instance_id': instance_id
            }
            drag_handle_widget = module_instance.drag_handle_label
            drag_handle_widget.bind("<ButtonPress-1>", lambda event, iid=instance_id: self.start_drag(event, iid))
            initial_width, initial_height = 200, 150
            parent_layout_manager.add_module(frame_wrapper, instance_id, initial_width, initial_height, defer_reflow=True)
            self.shared_state.log(f"Instantiated module '{instance_id}', reflow deferred.")
            return frame_wrapper
        except Exception as e:
            self.shared_state.log(f"Error instantiating module {module_name}: {e}", level=logging.ERROR)
            if frame_wrapper.winfo_exists(): frame_wrapper.destroy()
            return None

    def setup_default_layout(self):
        self.shared_state.log("Setting up default layout...")
        self.update_min_window_size()
        self.update_layout_scrollregion()
        self._finalize_initial_window_state()
        self.load_layout_config()

    def save_layout_config(self):
        config_path = os.path.join(self.saves_dir, self.CONFIG_FILE)
        if not self.loaded_modules:
            self.shared_state.log("[SAVE] No modules loaded, skip saving layout config.", "DEBUG")
            empty_config = {"modules": [], "maximized_module_name": None, "module_order": []}
            try:
                with open(config_path, "w", encoding="utf-8") as f: json.dump(empty_config, f, indent=2)
                self.shared_state.log(f"[SAVE] Layout config cleared: {config_path}", "DEBUG")
            except Exception as e:
                self.shared_state.log(f"[SAVE][ERROR] Failed to clear layout config: {e}", "ERROR")
            return
        config = {"modules": [], "maximized_module_name": self.maximized_module_name, "module_order": []}
        current_instance_ids = set(self.loaded_modules.keys()) & set(self.main_layout_manager.modules.keys())
        config["module_order"] = [iid for iid in self.main_layout_manager.modules.keys() if iid in current_instance_ids]
        for iid in config["module_order"]:
            mod_data = self.loaded_modules.get(iid)
            info = self.main_layout_manager.get_module_info(iid)
            if mod_data:
                canvas_width = self.canvas.winfo_width();
                if canvas_width <= 1: canvas_width = 800
                relative_width = info["width"] / canvas_width if info else 0.25
                relative_height = info["height"] / canvas_width if info else 0.187
                config["modules"].append({
                    "module_name": mod_data["module_name"], "instance_id": iid,
                    "relative_width": relative_width, "relative_height": relative_height
                })
        self.shared_state.log(f"[SAVE] Writing layout config to: {config_path}", "DEBUG")
        try:
            with open(config_path, "w", encoding="utf-8") as f: json.dump(config, f, indent=2)
            self.shared_state.log(f"[SAVE] Layout config written to {config_path}.", "DEBUG")
        except Exception as e:
            self.shared_state.log(f"[SAVE][ERROR] Failed to write layout config: {e}", "ERROR")

    def load_layout_config(self):
        config_path = os.path.join(self.saves_dir, self.CONFIG_FILE)
        self.shared_state.log(f"[LOAD] Try loading layout config from: {config_path}", "DEBUG")
        if not os.path.exists(config_path):
            self.shared_state.log("[LOAD] No layout config file found, using default layout.", "DEBUG")
            return False
        try:
            with open(config_path, "r", encoding="utf-8") as f: config = json.load(f)
            for iid in list(self.loaded_modules.keys()): self.hide_module(iid) # Clear existing
            max_counters = {}
            for mod in config.get("modules", []):
                module_name = mod["module_name"]; iid = mod["instance_id"]
                if "#" in iid:
                    base, num = iid.rsplit("#", 1)
                    try:
                        num = int(num)
                        if base not in max_counters or num > max_counters[base]: max_counters[base] = num
                    except Exception: pass
            for base, max_num in max_counters.items(): self.module_instance_counters[base] = max_num + 1
            module_order = config.get("module_order")
            ordered_mods = [({mod_iid: mod for mod_iid, mod in [(m["instance_id"], m) for m in config.get("modules", [])]})[iid] for iid in module_order if iid in ({mod_iid: mod for mod_iid, mod in [(m["instance_id"], m) for m in config.get("modules", [])]})] if module_order else config.get("modules", [])
            for mod in ordered_mods:
                module_name = mod["module_name"]; iid = mod["instance_id"]
                canvas_width = self.canvas.winfo_width();
                if canvas_width <= 1: canvas_width = 800
                width = int(mod.get("relative_width", 0.25) * canvas_width)
                height = int(mod.get("relative_height", 0.187) * canvas_width)
                width = max(50, width); height = max(50, height)
                if module_name in self.available_module_classes:
                    old_counter = self.module_instance_counters.get(module_name, 1)
                    try:
                        if "#" in iid:
                            base, num = iid.rsplit("#", 1); num = int(num)
                            self.module_instance_counters[module_name] = num
                    except Exception: pass
                    frame_wrapper = self.instantiate_module(module_name, self.main_layout_manager)
                    self.module_instance_counters[module_name] = max(old_counter, max_counters.get(module_name, 0) + 1)
                    if frame_wrapper:
                        self.loaded_modules[iid] = self.loaded_modules.pop(list(self.loaded_modules.keys())[-1])
                        self.loaded_modules[iid]["instance_id"] = iid
                        self.main_layout_manager.resize_module(iid, width, height, defer_reflow=True)
            self.main_layout_manager.reflow_layout()
            self.update_min_window_size(); self.update_layout_scrollregion()
            maximized = config.get("maximized_module_name")
            if maximized and maximized in self.loaded_modules: self.maximize_module(maximized)
            self.shared_state.log("[LOAD] Layout config loaded and restored.", "DEBUG")
            return True
        except Exception as e:
            self.shared_state.log(f"[LOAD][ERROR] Failed to load layout config: {e}", "ERROR")
            return False

    def save_profile_dialog(self):
        name = simpledialog.askstring("儲存設定檔", "請輸入設定檔名稱：", parent=self.root)
        if not name: return
        filename = f"{self.PROFILE_PREFIX}{name}{self.PROFILE_SUFFIX}"
        path = os.path.join(self.saves_dir, filename)
        config = self._get_current_layout_config()
        try:
            with open(path, "w", encoding="utf-8") as f: json.dump(config, f, indent=2)
            messagebox.showinfo("儲存成功", f"設定檔已儲存為 {filename}", parent=self.root)
        except Exception as e: messagebox.showerror("儲存失敗", f"無法儲存設定檔：{e}", parent=self.root)

    def load_profile_dialog(self):
        profiles = self._list_profiles()
        if not profiles:
            messagebox.showinfo("無設定檔", "目前沒有可用的設定檔。", parent=self.root)
            return
        sel = self._choose_profile_dialog(profiles, "載入設定檔", "請選擇要載入的設定檔：")
        if not sel: return
        filename = f"{self.PROFILE_PREFIX}{sel}{self.PROFILE_SUFFIX}"
        path = os.path.join(self.saves_dir, filename)
        self._load_layout_config_from_file(path)

    def manage_profiles_dialog(self):
        profiles = self._list_profiles()
        if not profiles:
            messagebox.showinfo("無設定檔", "目前沒有可用的設定檔。", parent=self.root)
            return
        sel = self._choose_profile_dialog(profiles, "刪除設定檔", "請選擇要刪除的設定檔：")
        if not sel: return
        filename = f"{self.PROFILE_PREFIX}{sel}{self.PROFILE_SUFFIX}"
        path = os.path.join(self.saves_dir, filename)
        try:
            os.remove(path)
            messagebox.showinfo("刪除成功", f"設定檔 {filename} 已刪除", parent=self.root)
        except Exception as e: messagebox.showerror("刪除失敗", f"無法刪除設定檔：{e}", parent=self.root)

    def _choose_profile_dialog(self, profiles, title, prompt):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.grab_set()
        tk.Label(dialog, text=prompt).pack(padx=10, pady=(10, 5))
        var = tk.StringVar(value="")
        listbox = tk.Listbox(dialog, listvariable=tk.StringVar(value=profiles), height=min(10, len(profiles)))
        listbox.pack(padx=10, pady=5)
        if profiles:
            listbox.selection_set(0)
        result = {"value": ""}
        def on_ok():
            if listbox.curselection():
                result["value"] = listbox.get(listbox.curselection())
            else:
                result["value"] = ""
            dialog.destroy()
        def on_cancel():
            result["value"] = ""
            dialog.destroy()
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=(0,10))
        tk.Button(btn_frame, text="確定", width=8, command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", width=8, command=on_cancel).pack(side=tk.LEFT, padx=5)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)  # 關閉視窗也當作取消
        dialog.wait_window()
        return result["value"]

    def _list_profiles(self):
        if not os.path.exists(self.saves_dir): return []
        files = os.listdir(self.saves_dir)
        return [f[len(self.PROFILE_PREFIX):-len(self.PROFILE_SUFFIX)] for f in files if f.startswith(self.PROFILE_PREFIX) and f.endswith(self.PROFILE_SUFFIX)]

    def _get_current_layout_config(self):
        if not self.loaded_modules: return {"modules": [], "maximized_module_name": self.maximized_module_name, "module_order": []}
        config = {"modules": [], "maximized_module_name": self.maximized_module_name, "module_order": []}
        current_instance_ids = set(self.loaded_modules.keys()) & set(self.main_layout_manager.modules.keys())
        config["module_order"] = [iid for iid in self.main_layout_manager.modules.keys() if iid in current_instance_ids]
        for iid in config["module_order"]:
            mod_data = self.loaded_modules.get(iid); info = self.main_layout_manager.get_module_info(iid)
            if mod_data:
                canvas_width = self.canvas.winfo_width();
                if canvas_width <= 1: canvas_width = 800
                relative_width = info["width"] / canvas_width if info else 0.25
                relative_height = info["height"] / canvas_width if info else 0.187
                config["modules"].append({
                    "module_name": mod_data["module_name"], "instance_id": iid,
                    "relative_width": relative_width, "relative_height": relative_height
                })
        return config

    def _load_layout_config_from_file(self, path):
        self.shared_state.log(f"[LOAD] Try loading layout config from file: {path}", "DEBUG")
        if not os.path.exists(path):
            self.shared_state.log(f"[LOAD] File not found: {path}", "WARNING")
            messagebox.showerror("載入失敗", "找不到設定檔。", parent=self.root)
            return False
        try:
            with open(path, "r", encoding="utf-8") as f: config = json.load(f)
            for iid in list(self.loaded_modules.keys()): self.hide_module(iid) # Clear existing
            max_counters = {}
            for mod in config.get("modules", []):
                module_name = mod["module_name"]; iid = mod["instance_id"]
                if "#" in iid:
                    base, num = iid.rsplit("#", 1)
                    try:
                        num = int(num)
                        if base not in max_counters or num > max_counters[base]: max_counters[base] = num
                    except Exception: pass
            for base, max_num in max_counters.items(): self.module_instance_counters[base] = max_num + 1
            module_order = config.get("module_order")
            ordered_mods = [({mod_iid: mod for mod_iid, mod in [(m["instance_id"], m) for m in config.get("modules", [])]})[iid] for iid in module_order if iid in ({mod_iid: mod for mod_iid, mod in [(m["instance_id"], m) for m in config.get("modules", [])]})] if module_order else config.get("modules", [])
            for mod in ordered_mods:
                module_name = mod["module_name"]; iid = mod["instance_id"]
                canvas_width = self.canvas.winfo_width();
                if canvas_width <= 1: canvas_width = 800
                width = int(mod.get("relative_width", 0.25) * canvas_width)
                height = int(mod.get("relative_height", 0.187) * canvas_width)
                width = max(50, width); height = max(50, height)
                if module_name in self.available_module_classes:
                    old_counter = self.module_instance_counters.get(module_name, 1)
                    try:
                        if "#" in iid:
                            base, num = iid.rsplit("#", 1); num = int(num)
                            self.module_instance_counters[module_name] = num
                    except Exception: pass
                    frame_wrapper = self.instantiate_module(module_name, self.main_layout_manager)
                    self.module_instance_counters[module_name] = max(old_counter, max_counters.get(module_name, 0) + 1)
                    if frame_wrapper:
                        self.loaded_modules[iid] = self.loaded_modules.pop(list(self.loaded_modules.keys())[-1])
                        self.loaded_modules[iid]["instance_id"] = iid
                        self.main_layout_manager.resize_module(iid, width, height, defer_reflow=True)
            self.main_layout_manager.reflow_layout()
            self.update_min_window_size(); self.update_layout_scrollregion()
            maximized = config.get("maximized_module_name")
            if maximized and maximized in self.loaded_modules: self.maximize_module(maximized)
            self.shared_state.log("[LOAD] Layout config loaded and restored from file.", "DEBUG")
            messagebox.showinfo("載入成功", "設定檔已載入。", parent=self.root)
            return True
        except Exception as e:
            self.shared_state.log(f"[LOAD][ERROR] Failed to load layout config from file {path}: {e}", "ERROR")
            messagebox.showerror("載入失敗", f"無法載入設定檔：{e}", parent=self.root)
            return False

    def on_closing(self):
        self.shared_state.log("Application closing...")
        for module_name, module_data in list(self.loaded_modules.items()):
            if module_data and module_data.get('instance'):
                try: module_data['instance'].on_destroy()
                except Exception as e: self.shared_state.log(f"Error during on_destroy for module {module_name}: {e}", level=logging.ERROR)
        self.root.destroy()

    def show_context_menu(self, event):
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(label="Toggle Module Visibility:", state=tk.DISABLED)
        self.context_menu.add_separator()
        for instance_id, mod_data in self.loaded_modules.items():
            is_visible = mod_data.get('frame_wrapper') and mod_data.get('frame_wrapper').winfo_exists()
            prefix = "[x]" if is_visible else "[ ]"
            self.context_menu.add_command(label=f"{prefix} {instance_id}", command=lambda iid=instance_id: self.toggle_module_visibility(iid))
        self.context_menu.add_separator()
        for module_name in sorted(self.available_module_classes.keys()):
            self.context_menu.add_command(label=f"Add {module_name}", command=lambda mn=module_name: self.add_module_from_menu(mn))
        try: self.context_menu.tk_popup(event.x_root, event.y_root)
        finally: self.context_menu.grab_release()

    def toggle_module_visibility(self, instance_id):
        self.shared_state.log(f"Toggle visibility for {instance_id}", level=logging.DEBUG)
        is_visible = False
        if instance_id in self.loaded_modules:
            mod_data = self.loaded_modules[instance_id]
            wrapper_to_check = mod_data.get('frame_wrapper')
            if wrapper_to_check and wrapper_to_check.winfo_exists(): is_visible = True
        if is_visible: self.hide_module(instance_id)
        else: self.shared_state.log(f"Showing module: {instance_id} (functionality to re-show not fully implemented here, relies on add_module)", "DEBUG")

    def hide_module(self, instance_id: str):
        if self.maximized_module_name == instance_id:
            self.restore_modules()
            if self.maximized_module_name is None and instance_id in self.loaded_modules: self.hide_module(instance_id)
            return
        else:
            self.shared_state.log(f"Hiding module: {instance_id} via close button/hide action.")
            if instance_id in self.loaded_modules:
                module_data = self.loaded_modules[instance_id]
                frame_wrapper = module_data.get('frame_wrapper'); instance = module_data.get('instance')
                if frame_wrapper and frame_wrapper.winfo_exists(): self.main_layout_manager.remove_module(instance_id)
                if instance:
                    try: instance.on_destroy()
                    except Exception as e: self.shared_state.log(f"Error during on_destroy for module {instance_id} when hiding: {e}", "ERROR")
                if frame_wrapper and frame_wrapper.winfo_exists(): frame_wrapper.destroy()
                del self.loaded_modules[instance_id]
                self.shared_state.log(f"Module '{instance_id}' hidden and instance destroyed.")
                self.update_min_window_size(); self.update_layout_scrollregion(); self.save_layout_config()
            else: self.shared_state.log(f"Module '{instance_id}' not found or not loaded, cannot hide.", "WARNING")

    def start_drag(self, event, instance_id):
        self.shared_state.log(f"Start dragging module: {instance_id}", level=logging.DEBUG)
        self.dragged_module_name = instance_id; self.drag_start_widget = event.widget
        if self.dragged_module_name not in self.main_layout_manager.modules or \
           self.dragged_module_name not in self.loaded_modules:
            self.shared_state.log(f"Dragged module {self.dragged_module_name} not found in layout manager or loaded modules.", "ERROR")
            self.dragged_module_name = None; return
        dragged_module_layout_info = self.main_layout_manager.modules[self.dragged_module_name]
        original_frame_wrapper = self.loaded_modules[self.dragged_module_name]['frame_wrapper']
        original_width = dragged_module_layout_info['width']; original_height = dragged_module_layout_info['height']
        original_x = dragged_module_layout_info['x']; original_y = dragged_module_layout_info['y']
        if original_frame_wrapper: self.original_dragged_module_relief = original_frame_wrapper.cget("relief")
        self.ghost_module_frame = ttk.Frame(self.canvas, width=original_width, height=original_height)
        self.ghost_module_frame.configure(relief=tk.RIDGE, borderwidth=2)
        ttk.Label(self.ghost_module_frame, text=f"Preview: {self.dragged_module_name}").pack(expand=True, fill=tk.BOTH)
        self.ghost_canvas_window_id = self.canvas.create_window(original_x, original_y, window=self.ghost_module_frame, anchor=tk.NW, width=original_width, height=original_height)
        self.shared_state.log(f"Ghost created at {original_x},{original_y} with ID {self.ghost_canvas_window_id}", "DEBUG")
        if original_frame_wrapper: original_frame_wrapper.place_forget(); self.shared_state.log(f"Original module {self.dragged_module_name} hidden.", "DEBUG")
        self.last_preview_target_module_name = None
        self.root.config(cursor="fleur"); self.root.bind("<B1-Motion>", self.on_drag); self.root.bind("<ButtonRelease-1>", self.end_drag)

    def on_drag(self, event):
        if not self.dragged_module_name or not self.ghost_canvas_window_id or \
           self.dragged_module_name not in self.main_layout_manager.modules: return
        try:
            mouse_x_on_canvas = event.x_root - self.canvas.winfo_rootx()
            mouse_y_on_canvas = event.y_root - self.canvas.winfo_rooty()
        except tk.TclError: return
        other_modules_info = [{'name': name, 'x': mp['x'], 'y': mp['y'], 'width': mp['width'], 'height': mp['height']} for name, mp in self.main_layout_manager.modules.items() if name != self.dragged_module_name and mp and mp.get('frame') and mp['frame'].winfo_exists() and all(k in mp for k in ['x', 'y', 'width', 'height'])]
        self.last_preview_target_module_name = None
        if other_modules_info:
            modules_sorted_y = sorted(other_modules_info, key=lambda m: (m['y'], m['x']))
            best_h_target = {'dist': float('inf'), 'target_name': None}
            if modules_sorted_y:
                mod_y_first = modules_sorted_y[0]
                if mouse_x_on_canvas >= mod_y_first['x'] and mouse_x_on_canvas <= mod_y_first['x'] + mod_y_first['width']:
                    dist = abs(mouse_y_on_canvas - mod_y_first['y'])
                    if dist < best_h_target['dist']: best_h_target = {'dist': dist, 'target_name': mod_y_first['name']}
            for i, mod_y in enumerate(modules_sorted_y):
                gap_line_y = mod_y['y'] + mod_y['height']
                if mouse_x_on_canvas >= mod_y['x'] and mouse_x_on_canvas <= mod_y['x'] + mod_y['width']:
                    dist = abs(mouse_y_on_canvas - gap_line_y)
                    if dist < best_h_target['dist']: best_h_target = {'dist': dist, 'target_name': modules_sorted_y[i+1]['name'] if (i + 1) < len(modules_sorted_y) else None}
            modules_sorted_x = sorted(other_modules_info, key=lambda m: (m['x'], m['y']))
            best_v_target = {'dist': float('inf'), 'target_name': None}
            if modules_sorted_x:
                mod_x_first = modules_sorted_x[0]
                if mouse_y_on_canvas >= mod_x_first['y'] and mouse_y_on_canvas <= mod_x_first['y'] + mod_x_first['height']:
                    dist = abs(mouse_x_on_canvas - mod_x_first['x'])
                    if dist < best_v_target['dist']: best_v_target = {'dist': dist, 'target_name': mod_x_first['name']}
            for i, mod_x in enumerate(modules_sorted_x):
                gap_line_x = mod_x['x'] + mod_x['width']
                if mouse_y_on_canvas >= mod_x['y'] and mouse_y_on_canvas <= mod_x['y'] + mod_x_first['height']: # Typo, should be mod_x['height']
                    dist = abs(mouse_x_on_canvas - gap_line_x)
                    if dist < best_v_target['dist']: best_v_target = {'dist': dist, 'target_name': modules_sorted_x[i+1]['name'] if (i + 1) < len(modules_sorted_x) else None}
            final_target_name = None
            h_target_is_valid = best_h_target['dist'] != float('inf'); v_target_is_valid = best_v_target['dist'] != float('inf')
            if h_target_is_valid and v_target_is_valid: final_target_name = best_h_target['target_name'] if best_h_target['dist'] <= best_v_target['dist'] else best_v_target['target_name']
            elif h_target_is_valid: final_target_name = best_h_target['target_name']
            elif v_target_is_valid: final_target_name = best_v_target['target_name']
            self.last_preview_target_module_name = final_target_name
        self.shared_state.log("Optimized on_drag: Updating ghost position without full layout simulation.", "DEBUG")
        new_x, new_y = mouse_x_on_canvas, mouse_y_on_canvas
        if self.last_preview_target_module_name and self.last_preview_target_module_name in self.main_layout_manager.modules:
            target_props = self.main_layout_manager.modules[self.last_preview_target_module_name]
            new_x = target_props.get('x', mouse_x_on_canvas); new_y = target_props.get('y', mouse_y_on_canvas)
            self.shared_state.log(f"Ghost target: {self.last_preview_target_module_name} at ({new_x},{new_y})", "DEBUG")
        else: self.shared_state.log(f"Ghost follows mouse to ({new_x},{new_y})", "DEBUG")
        if self.ghost_canvas_window_id: self.canvas.coords(self.ghost_canvas_window_id, new_x, new_y)

    def end_drag(self, event):
        if not self.dragged_module_name:
            self.root.config(cursor=""); self.root.unbind("<B1-Motion>"); self.root.unbind("<ButtonRelease-1>"); return
        if self.ghost_canvas_window_id: self.canvas.delete(self.ghost_canvas_window_id); self.ghost_canvas_window_id = None
        if self.ghost_module_frame: self.ghost_module_frame = None
        self.shared_state.log(f"End dragging module: {self.dragged_module_name}. Target before: {self.last_preview_target_module_name}", level=logging.DEBUG)
        dragged_module_data = self.loaded_modules.get(self.dragged_module_name)
        if dragged_module_data:
            original_frame_wrapper = dragged_module_data.get('frame_wrapper')
            if original_frame_wrapper and hasattr(self, 'original_dragged_module_relief') and self.original_dragged_module_relief:
                try: original_frame_wrapper.config(relief=self.original_dragged_module_relief, borderwidth=1)
                except tk.TclError as e: self.shared_state.log(f"Error resetting relief for {self.dragged_module_name}: {e}", "WARNING")
        if self.dragged_module_name:
            self.main_layout_manager.move_module_before(self.dragged_module_name, self.last_preview_target_module_name)
            self.update_layout_scrollregion(); self.update_min_window_size(); self.save_layout_config()
        self.dragged_module_name = None; self.drag_start_widget = None; self.last_preview_target_module_name = None; self.original_dragged_module_relief = None
        self.root.config(cursor=""); self.root.unbind("<B1-Motion>"); self.root.unbind("<ButtonRelease-1>")
        # Re-bind general mouse events if they were unbound specifically for drag
        self.setup_bindings() # Call this to ensure general bindings are restored if they were affected

    def maximize_module(self, instance_id):
        if self.maximized_module_name == instance_id: return
        self.shared_state.log(f"Maximizing module: {instance_id}", "INFO")
        self._pre_maximize_layout = self.main_layout_manager.get_layout_data()
        self.maximized_module_name = instance_id
        canvas_width = self.canvas.winfo_width(); canvas_height = self.canvas.winfo_height()
        self.main_layout_manager.config(width=canvas_width, height=canvas_height)
        self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width, height=canvas_height)
        for iid, mod_data in self.loaded_modules.items():
            frame_wrapper = mod_data.get('frame_wrapper'); instance = mod_data.get('instance')
            if iid == instance_id:
                if frame_wrapper and frame_wrapper.winfo_exists():
                    frame_wrapper.lift(); frame_wrapper.place(x=0, y=0, width=canvas_width, height=canvas_height)
                if instance: instance.is_maximized = True
            else:
                if frame_wrapper and frame_wrapper.winfo_exists(): frame_wrapper.place_forget()
                if instance: instance.is_maximized = False
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height)); self.save_layout_config()

    def restore_modules(self):
        if not self.maximized_module_name: return
        self.shared_state.log("Restoring modules from maximized state.", "INFO")
        for iid, mod_data in self.loaded_modules.items():
            instance = mod_data.get('instance')
            if instance: instance.is_maximized = False
        content_height = self.main_layout_manager.last_calculated_content_height
        content_width = self.main_layout_manager.last_calculated_content_width
        self.main_layout_manager.config(width=content_width, height=content_height)
        self.canvas.itemconfig(self.main_layout_manager_window_id, width=content_width, height=content_height)
        if self._pre_maximize_layout:
            for iid, props in self._pre_maximize_layout.items():
                if iid in self.loaded_modules: self.main_layout_manager.resize_module(iid, props.get('width', 200), props.get('height', 150))
            self.main_layout_manager.reflow_layout()
        else: self.main_layout_manager.reflow_layout()
        self.canvas.config(scrollregion=(0, 0, content_width, content_height))
        self.update_layout_scrollregion(); self.maximized_module_name = None; self._pre_maximize_layout = None; self.save_layout_config()

    def get_resize_cursor(self):
        width = self.root.winfo_width(); height = self.root.winfo_height()
        border_width = 8; corner_size = 15
        mouse_y = self.root.winfo_pointery() - self.root.winfo_rooty()
        mouse_x = self.root.winfo_pointerx() - self.root.winfo_rootx()
        if mouse_x <= corner_size and mouse_y <= corner_size: return "top_left_corner", "top_left_corner"
        elif mouse_x <= corner_size and mouse_y >= height - corner_size: return "bottom_left_corner", "bottom_left_corner"
        elif mouse_x >= width - corner_size and mouse_y >= height - corner_size: return "bottom_right_corner", "bottom_right_corner"
        elif mouse_y <= border_width: return "top", "top_side"
        elif mouse_y >= height - border_width: return "bottom", "bottom_side"
        elif mouse_x <= border_width: return "left", "left_side"
        elif mouse_x >= width - border_width: return "right", "right_side"
        else: return None, "arrow"

    def on_mouse_motion(self, event):
        if self.is_maximized: return
        resize_mode, cursor = self.get_resize_cursor()
        try: self.root.configure(cursor=cursor)
        except: pass

    def on_mouse_down(self, event):
        if self.is_maximized: return
        self.resize_mode, _ = self.get_resize_cursor()
        if self.resize_mode:
            self.resize_start_x = event.x_root; self.resize_start_y = event.y_root
            self.start_geometry = self.root.geometry()

    def on_mouse_drag(self, event):
        if self.is_maximized or not self.resize_mode: return
        dx = event.x_root - self.resize_start_x; dy = event.y_root - self.resize_start_y
        geo = self.start_geometry; parts = geo.split('+'); size_part = parts[0]
        width, height = map(int, size_part.split('x'))
        x = int(parts[1]) if len(parts) > 1 else 0; y = int(parts[2]) if len(parts) > 2 else 0
        min_width, min_height = 300, 200
        if self.resize_mode == "right": width = max(min_width, width + dx)
        elif self.resize_mode == "left": new_width = max(min_width, width - dx); x = x + (width - new_width); width = new_width
        elif self.resize_mode == "bottom": height = max(min_height, height + dy)
        elif self.resize_mode == "top": new_height = max(min_height, height - dy); y = y + (height - new_height); height = new_height
        elif self.resize_mode == "top_left_corner":
            new_width = max(min_width, width - dx); new_height = max(min_height, height - dy)
            x = x + (width - new_width); y = y + (height - new_height); width = new_width; height = new_height
        elif self.resize_mode == "bottom_left_corner":
            new_width = max(min_width, width - dx); x = x + (width - new_width); width = new_width; height = max(min_height, height + dy)
        elif self.resize_mode == "bottom_right_corner": width = max(min_width, width + dx); height = max(min_height, height + dy)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def on_mouse_up(self, event):
        self.resize_mode = None; self.root.configure(cursor="arrow")

    def start_move(self, event): self.drag_start_x = event.x; self.drag_start_y = event.y

    def do_move(self, event):
        if self.is_maximized: return
        x = event.x_root - self.drag_start_x; y = event.y_root - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def toggle_maximize(self, event=None):
        if self.is_maximized: self.restore_window_custom()
        else: self.maximize_window_custom()

    def maximize_window_custom(self):
        self.normal_geometry = self.root.geometry(); self.is_maximized = True
        self.max_btn.config(text="🗗")
        screen_width = self.root.winfo_screenwidth(); screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height-40}+0+0") # Adjust for taskbar
        self.status_label.config(text="最大化")

    def restore_window_custom(self):
        self.is_maximized = False; self.max_btn.config(text="🗖")
        self.root.geometry(self.normal_geometry); self.status_label.config(text="就緒")

    def close_window(self): self.on_closing()

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    def show_on_taskbar(self, root_window):
        if sys.platform == "win32" and windll:
            try:
                hwnd = windll.user32.GetParent(root_window.winfo_id())
                style = windll.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
                style = style & ~self.WS_EX_TOOLWINDOW | self.WS_EX_APPWINDOW
                windll.user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, style)
                root_window.wm_withdraw()
                root_window.after(10, lambda: root_window.wm_deiconify())
            except Exception as e:
                self.shared_state.log(f"Failed to show on taskbar (Windows-specific): {e}", "WARNING")
        else:
            # For non-Windows, just deiconify if needed, or do nothing if already visible
            # This part might need more nuanced handling depending on desired behavior on other OS
            try:
                if root_window.state() == 'withdrawn':
                    root_window.deiconify()
                self.shared_state.log("show_on_taskbar: Non-Windows platform, standard deiconify behavior.", "DEBUG")
            except tk.TclError as e:
                 self.shared_state.log(f"show_on_taskbar: Error during non-Windows deiconify: {e}", "WARNING")
            # root_window.wm_withdraw()
            # root_window.after(10, lambda: root_window.wm_deiconify())


    def minimize_window(self, event=None):
        self.root.overrideredirect(False)
        self.root.update_idletasks()
        self.root.iconify()
        self.root.bind('<Map>', lambda e: self.restore_window())

    def restore_window(self, event=None):
        self.map_event_handled += 1
        if self.map_event_handled == 2: # This count might need adjustment based on OS/Tk version
            self.root.unbind('<Map>')
            self.root.withdraw() # Temporarily hide
            self.root.after(100, self._finish_restore) # Delay to ensure proper state change

    def _finish_restore(self):
        self.root.deiconify() # Bring back
        self.root.overrideredirect(True) # Re-apply borderless
        self.show_on_taskbar(self.root) # Ensure it's in taskbar
        self.map_event_handled = 0 # Reset for next time
