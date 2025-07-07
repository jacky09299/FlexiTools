import sys
import os
from ctypes import windll
# Check if the application is running in a bundled environment (PyInstaller)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Change the current working directory to the one containing the executable
    os.chdir(sys._MEIPASS)
import time
import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog, messagebox
import importlib.util
import random
from shared_state import SharedState
from style_manager import (
    configure_styles, apply_post_creation_styles,
    COLOR_PRIMARY_BG,
    COLOR_WINDOW_BORDER, COLOR_TITLE_BAR_BG, COLOR_MENU_BAR_BG,
    COLOR_MENU_BUTTON_FG, COLOR_MENU_BUTTON_ACTIVE_BG, COLOR_ACCENT_HOVER
)
import logging
import json
import threading # For running update checks in background
import tempfile # For temporary installer download
import subprocess # For running installer and helper script
import os # For PID and path manipulation (os.getpid, os.path.join etc.)
# sys is already imported

# Attempt to import update_manager and its components
try:
    import update_manager
except ImportError:
    # This fallback is for environments where update_manager.py might not be discoverable
    # during certain development phases or if the file structure is temporarily changed.
    # A more robust solution would ensure PYTHONPATH is correctly set or use relative imports if structured as a package.
    print("ERROR: update_manager.py not found. Update functionality will be disabled.")
    print(f"Current sys.path: {sys.path}")
    # Define dummy functions/constants if update_manager is critical for other parts of main.py to load
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

        self.frame = ttk.Frame(self.master, borderwidth=1, relief=tk.SOLID)

        self.title_bar_frame = ttk.Frame(self.frame, height=25, style="DragHandle.TFrame")
        self.title_bar_frame.pack(fill=tk.X, side=tk.TOP, pady=(0,2))

        self.drag_handle_label = ttk.Label(self.title_bar_frame, text="☰", cursor="fleur")
        self.drag_handle_label.pack(side=tk.LEFT, padx=5)

        self.title_label = ttk.Label(self.title_bar_frame, text=self.module_name)
        self.title_label.pack(side=tk.LEFT, padx=5)

        self.close_button = ttk.Button(self.title_bar_frame, text="X", width=3,
                                        command=self.close_module_action)
        self.close_button.pack(side=tk.RIGHT, padx=(0, 2))

        self.maximize_button = ttk.Button(
            self.title_bar_frame, text="⬜", width=3,
            command=self.toggle_maximize_action
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
            self.gui_manager.root_minsize_backup = self.gui_manager.root.minsize()  # <-- store minsize
            current_width = self.gui_manager.root.winfo_width()
            current_height = self.gui_manager.root.winfo_height()
            self.gui_manager.window_geometry_before_module_resize = f"{current_width}x{current_height}"
            self.gui_manager.root.maxsize(current_width, current_height)
            self.gui_manager.root.minsize(current_width, current_height)  # <-- lock minsize
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
        delta_y = event.y_root - self.resize_start_y  # <-- fix: use y_root for y

        new_width = self.resize_start_width + delta_x
        new_height = self.resize_start_height + delta_y

        min_width = 50
        min_height = 50
        new_width = max(min_width, new_width)
        new_height = max(min_height, new_height)

        # --- Cap width to canvas width if it exceeds ---
        if self.gui_manager and hasattr(self.gui_manager, "canvas"):
            canvas_width = self.gui_manager.canvas.winfo_width()
            if canvas_width > 1:
                new_width = min(new_width, canvas_width)
        # ----------------------------------------------

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
            # Restore maxsize
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
            # Restore minsize
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

            # Do NOT restore geometry here, just leave as is

            # 強制把視窗尺寸設回目前大小，避免自動調整
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

    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)  # 移除系統邊框
        root.iconbitmap("tools.ico")
        self.root.geometry("800x600") # 初始尺寸，之後會被載入的佈局覆蓋

        # 視窗狀態
        self.is_maximized = False
        self.normal_geometry = "800x600" # 儲存正常狀態下的尺寸和位置

        # 拖拽和縮放變數
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_mode = None

        # 主容器
        self.main_frame = tk.Frame(self.root, bg=COLOR_WINDOW_BORDER, bd=1, relief="solid") # 調整邊框顏色和樣式
        self.main_frame.pack(fill="both", expand=True)

        # 標題欄
        self.title_bar = tk.Frame(self.main_frame, bg=COLOR_TITLE_BAR_BG, height=35, relief="flat") # 調整標題欄背景
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)

        # 標題文字
        self.title_label = tk.Label(self.title_bar, text="FlexiTools",
                                   bg=COLOR_TITLE_BAR_BG, fg="white", font=("Arial", 10, "bold")) # 調整標題文字顏色
        self.title_label.pack(side="left", padx=10, pady=8)

        # 視窗控制按鈕容器
        self.controls_frame = tk.Frame(self.title_bar, bg=COLOR_TITLE_BAR_BG) # 調整按鈕容器背景
        self.controls_frame.pack(side="right", padx=5)

        # 最小化按鈕
        self.min_btn = tk.Button(self.controls_frame, text="🗕",
                                command=self.minimize_window,
                                bg=COLOR_TITLE_BAR_BG, fg="white", relief="flat", # 調整按鈕顏色
                                font=("Arial", 8), width=3, height=1,
                                activebackground=COLOR_ACCENT_HOVER, activeforeground="white")
        self.min_btn.pack(side="left", padx=2)

        # 最大化按鈕
        self.max_btn = tk.Button(self.controls_frame, text="🗖",
                                command=self.toggle_maximize,
                                bg=COLOR_TITLE_BAR_BG, fg="white", relief="flat", # 調整按鈕顏色
                                font=("Arial", 8), width=3, height=1,
                                activebackground=COLOR_ACCENT_HOVER, activeforeground="white")
        self.max_btn.pack(side="left", padx=2)

        # 關閉按鈕
        self.close_btn = tk.Button(self.controls_frame, text="🗙",
                                  command=self.close_window,
                                  bg=COLOR_TITLE_BAR_BG, fg="white", relief="flat", # 調整按鈕顏色
                                  font=("Arial", 8), width=3, height=1,
                                  activebackground="#e74c3c", activeforeground="white")
        self.close_btn.pack(side="right", padx=2)

        # 內容區域
        self.content_frame = tk.Frame(self.main_frame, bg=COLOR_PRIMARY_BG, bd=0, relief="flat") # 調整內容區域背景
        self.content_frame.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        # 狀態欄 (可選，如果main.py中沒有類似的，可以新增)
        self.status_bar = tk.Frame(self.main_frame, bg=COLOR_TITLE_BAR_BG, height=25) # 調整狀態欄背景
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(self.status_bar, text="就緒",
                                    bg=COLOR_TITLE_BAR_BG, fg="white", font=("Arial", 8)) # 調整狀態欄文字顏色
        self.status_label.pack(side="left", padx=10, pady=4)

        self.shared_state = SharedState()  # <-- Move this to the top

        self.shared_state = SharedState()  # <-- Move this to the top

        # Use user-writable directory for saves (layouts, profiles, update_info)
        # The get_user_writable_data_path in update_manager returns the 'saves' subdirectory directly.
        self.saves_dir = os.path.join("modules", "saves") 
        if self.saves_dir is None:
            # This is a critical failure. update_manager.py logs this.
            # main.py should probably show an error and potentially exit or run in a degraded mode.
            messagebox.showerror("Fatal Error",
                                 "Could not determine or create a writable directory for application data. "
                                 "Settings and session data will not be saved.")
            # Fallback to a local 'modules/saves' for dev or if all else fails,
            # but this won't work well for an installed application.
            self.shared_state.log("CRITICAL: Using fallback self.saves_dir due to earlier errors.", "ERROR")
            self.saves_dir = os.path.join("modules", "saves") # Original problematic path
            try:
                if not os.path.exists(self.saves_dir):
                    os.makedirs(self.saves_dir)
            except Exception as e_mkdir:
                 self.shared_state.log(f"Failed to create even fallback saves_dir: {e_mkdir}", "ERROR")
                 self.saves_dir = "." # Last ditch

        self.shared_state.log(f"Application saves directory set to: {self.saves_dir}", "INFO")

        # 自訂菜單欄容器
        self.menu_frame = tk.Frame(self.content_frame, bg=COLOR_MENU_BAR_BG) # 調整菜單欄背景
        self.menu_frame.pack(fill="x", side="top")

        # Modules 選單
        self.modules_menu = tk.Menu(self.root, tearoff=0)
        self.modules_menubutton = tk.Menubutton(self.menu_frame, text="Modules", menu=self.modules_menu, 
                                                bg=COLOR_MENU_BAR_BG, fg=COLOR_MENU_BUTTON_FG, activebackground=COLOR_MENU_BUTTON_ACTIVE_BG, activeforeground="white", # 調整菜單按鈕顏色
                                                relief="flat", padx=10, pady=5)
        self.modules_menubutton.pack(side="left")
        self.modules_menubutton.bind("<Button-1>", lambda e: self.modules_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height()))

        # 設定檔選單
        self.profile_menu = tk.Menu(self.root, tearoff=0)
        self.profile_menubutton = tk.Menubutton(self.menu_frame, text="設定檔", menu=self.profile_menu, 
                                                 bg=COLOR_MENU_BAR_BG, fg=COLOR_MENU_BUTTON_FG, activebackground=COLOR_MENU_BUTTON_ACTIVE_BG, activeforeground="white", # 調整菜單按鈕顏色
                                                 relief="flat", padx=10, pady=5)
        self.profile_menubutton.pack(side="left")
        self.profile_menubutton.bind("<Button-1>", lambda e: self.profile_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height()))
        self.profile_menu.add_command(label="儲存目前佈局為設定檔...", command=self.save_profile_dialog)
        self.profile_menu.add_command(label="載入設定檔...", command=self.load_profile_dialog)
        self.profile_menu.add_separator()
        self.profile_menu.add_command(label="管理設定檔...", command=self.manage_profiles_dialog)

        # Help 選單
        self.help_menu = tk.Menu(self.root, tearoff=0)
        self.help_menubutton = tk.Menubutton(self.menu_frame, text="Help", menu=self.help_menu, 
                                             bg=COLOR_MENU_BAR_BG, fg=COLOR_MENU_BUTTON_FG, activebackground=COLOR_MENU_BUTTON_ACTIVE_BG, activeforeground="white", # 調整菜單按鈕顏色
                                             relief="flat", padx=10, pady=5)
        self.help_menubutton.pack(side="left")
        self.help_menubutton.bind("<Button-1>", lambda e: self.help_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height()))
        self.help_menu.add_command(label="Check for Updates...", command=self.ui_check_for_updates_manual)
        # We can add an "About" item here later if desired

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

        self.canvas_container = ttk.Frame(self.content_frame, style='Main.TFrame') # Changed parent to content_frame
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_container, bg=COLOR_PRIMARY_BG, highlightthickness=0)

        self.setup_bindings() # Call setup_bindings here

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

        self.discover_modules()

        for module_name in sorted(self.available_module_classes.keys()):
            self.modules_menu.add_command(
                label=f"Add {module_name}",
                command=lambda mn=module_name: self.add_module_from_menu(mn)
            )

        self.setup_default_layout()

        # Initial update check on startup (non-blocking)
        self.root.after(1000, self.ui_check_for_updates_startup) # Delay slightly to let UI load

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _start_download_in_thread(self, version_to_download, download_url):
        """Starts the download process in a separate thread."""
        download_thread = threading.Thread(
            target=self._download_installer_and_launch_update,
            args=(version_to_download, download_url),
            daemon=True
        )
        download_thread.start()

    def _download_installer_and_launch_update(self, version_to_download, download_url):
        """Downloads the installer and then launches the update helper script."""
        try:
            import requests
            import tempfile
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
        """Creates and runs a helper batch script to perform the update."""
        self.shared_state.log("Preparing to launch update helper script.", "INFO")

        confirm_update = messagebox.askyesno("Ready to Update",
                                             "The update has been downloaded.\n\n"
                                             "FlexiTools will now close to install the update and then restart automatically.\n\n"
                                             "Do you want to proceed?", parent=self.root)
        if not confirm_update:
            self.shared_state.log("User cancelled update before applying.", "INFO")
            try: # Clean up downloaded installer
                if os.path.exists(installer_path):
                    os.remove(installer_path)
                    self.shared_state.log(f"Cleaned up downloaded installer: {installer_path}", "INFO")
            except Exception as e:
                self.shared_state.log(f"Error cleaning up installer {installer_path}: {e}", "WARNING")
            return

        current_pid = os.getpid()
        # sys.executable is the path to FlexiTools.exe when bundled
        # For development, it's python.exe, so we need to be careful.
        # The restart path should point to the installed FlexiTools.exe.
        # We assume the installer puts FlexiTools.exe in a known location relative to its install dir.
        # The NSI script uses $INSTDIR\\FlexiTools.exe
        # sys.executable should be this path when the bundled app is running.

        app_executable_path = sys.executable
        # 移除開發模式下跳過更新的判斷，讓 dev mode 也會執行 batch script

        # Create batch script content
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

            # Launch the batch script in a new process, detached if possible
            # CREATE_NEW_CONSOLE or DETACHED_PROCESS can be used.
            # DETACHED_PROCESS is better as it won't show a console window briefly.
            # However, DETACHED_PROCESS might not work with TASKKILL on itself if not careful.
            # For simplicity, allowing a brief console window for the updater is acceptable.
            subprocess.Popen([batch_file_path], creationflags=subprocess.CREATE_NEW_CONSOLE)

            self.shared_state.log("Update helper script launched. Closing application.", "INFO")
            self.root.destroy() # Close the current application

        except Exception as e:
            self.shared_state.log(f"Failed to create or launch update helper script: {e}", "ERROR")
            messagebox.showerror("Update Error", f"Failed to start the update process: {e}", parent=self.root)


    def _initiate_update_download_and_install(self, version, url):
        self.shared_state.log(f"User agreed to update to version {version} from {url}. Starting download process...", "INFO")
        # Start the download in a new thread
        self._start_download_in_thread(version, url)


    def _handle_update_check_result(self, status_code, manual_check=False):
        """Handles the result from check_for_updates and interacts with the user."""
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
            else: # Should not happen if status is UPDATE_AVAILABLE
                 if manual_check:
                    messagebox.showerror("Update Error", "Update information is inconsistent. Please try again.")
                 self.shared_state.log("Update status was AVAILABLE but no details found in update_info.json.", "ERROR")

        elif status_code == update_manager.NO_UPDATE_FOUND:
            if manual_check: # Only show "up to date" if user manually checked
                messagebox.showinfo("No Updates", f"{update_manager.APP_NAME} is up to date.")
            self.shared_state.log("No new update found.", "INFO")

        elif status_code == update_manager.ERROR_FETCHING:
            if manual_check:
                messagebox.showerror("Update Check Failed",
                                     "Could not connect to the update server. Please check your internet connection and try again.")
            self.shared_state.log("Error fetching update information.", "WARNING")

        elif status_code == update_manager.ERROR_CONFIG:
            if manual_check:
                 messagebox.showerror("Update Error",
                                     "There was an error with the update configuration. Please contact support or try reinstalling the application.")
            self.shared_state.log("Update configuration error.", "ERROR")

        elif status_code in [update_manager.CHECK_SKIPPED_RATE_LIMIT, update_manager.CHECK_SKIPPED_ALREADY_PENDING]:
            if manual_check: # Should not happen if force_check=True was used for manual check
                 self.shared_state.log(f"Manual check resulted in unexpected status: {status_code}", "WARNING")
            else: # Startup check
                 self.shared_state.log(f"Update check skipped: {status_code}", "INFO")

        # Re-enable menu item if it was disabled during check
        if manual_check and hasattr(self, 'help_menubutton'):
            try:
                self.help_menubutton.config(state=tk.NORMAL)
            except tk.TclError:
                pass # Menu might not exist or item removed

    def _perform_update_check_threaded(self, force_check=False, is_manual_check=False):
        """Worker function for threaded update check."""
        self.shared_state.log(f"Threaded update check started. Force: {force_check}, Manual: {is_manual_check}", "INFO")
        if is_manual_check and hasattr(self, 'help_menubutton'): # Disable menu item during check
            try:
                self.help_menubutton.config(state=tk.DISABLED)
            except tk.TclError:
                pass # Menu might not exist or item removed

        status = update_manager.check_for_updates(force_check=force_check)
        # Schedule GUI updates back on the main thread
        self.root.after(0, self._handle_update_check_result, status, is_manual_check)

    def setup_bindings(self):
        # 標題欄拖拽
        self.title_bar.bind("<Button-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<Button-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)
        
        # 視窗狀態監聽
        self.root.bind('<Map>', self.restore_window)
        
        # 整個視窗的滑鼠事件
        self.root.bind("<Motion>", self.on_mouse_motion)
        self.root.bind("<Button-1>", self.on_mouse_down)
        self.root.bind("<B1-Motion>", self.on_mouse_drag)
        self.root.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # 雙擊標題欄最大化
        self.title_bar.bind("<Double-Button-1>", self.toggle_maximize)
        self.title_label.bind("<Double-Button-1>", self.toggle_maximize)

    def ui_check_for_updates_startup(self):
        """Initiates the non-blocking update check on startup."""
        self.shared_state.log("Initiating startup update check.", "INFO")
        # Run in a separate thread to not block GUI
        thread = threading.Thread(target=self._perform_update_check_threaded, args=(False, False), daemon=True)
        thread.start()

    def ui_check_for_updates_manual(self):
        """Handles the 'Check for Updates...' menu command."""
        self.shared_state.log("Manual update check initiated by user.", "INFO")
        if hasattr(self, 'help_menu'): # Show some immediate feedback
            try:
                # Potentially show a "checking..." message or disable button temporarily
                # For now, just log. Disabling is handled in the thread.
                messagebox.showinfo("Checking for Updates", "Checking for updates in the background...", parent=self.root)
            except tk.TclError:
                pass # Menu might not exist or item removed

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
        if canvas_viewport_width <= 1:
            canvas_viewport_width = 800

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
        if canvas_viewport_width <= 1:
            canvas_viewport_width = self.root.winfo_width()
        if canvas_viewport_width <= 1:
            canvas_viewport_width = 800

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
        base_min_width = 200
        padding = 20
        effective_min_width = max(base_min_width, max_module_w + padding if max_module_w > 0 else base_min_width)

        current_min_height = 0
        try:
            current_min_height = self.root.minsize()[1]
        except tk.TclError:
            current_min_height = 0 
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

        frame_wrapper = ttk.Frame(parent_layout_manager, relief=tk.SUNKEN, borderwidth=1)

        try:
            module_instance = ModuleClass(frame_wrapper, self.shared_state, instance_id, self)
            module_instance.get_frame().pack(fill=tk.BOTH, expand=True)

            self.loaded_modules[instance_id] = {
                'class': ModuleClass,
                'instance': module_instance,
                'frame_wrapper': frame_wrapper,
                'module_name': module_name,
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
            if frame_wrapper.winfo_exists():
                frame_wrapper.destroy()
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
            print("[SAVE] No modules loaded, skip saving layout config.")
            empty_config = {
                "modules": [],
                "maximized_module_name": None,
                "module_order": []
            }
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(empty_config, f, indent=2)
                print(f"[SAVE] Layout config cleared.")
            except Exception as e:
                print(f"[SAVE][ERROR] Failed to clear layout config: {e}")
            return
        config = {
            "modules": [],
            "maximized_module_name": self.maximized_module_name,
            "module_order": []
        }
        current_instance_ids = set(self.loaded_modules.keys()) & set(self.main_layout_manager.modules.keys())
        config["module_order"] = [iid for iid in self.main_layout_manager.modules.keys() if iid in current_instance_ids]
        for iid in config["module_order"]:
            mod_data = self.loaded_modules.get(iid)
            info = self.main_layout_manager.get_module_info(iid)
            if mod_data:
                # 取得目前視窗寬度作為基準
                canvas_width = self.canvas.winfo_width()
                if canvas_width <= 1:
                    canvas_width = 800
                    
                # 計算相對寬度 (0~1 之間的值)
                relative_width = info["width"] / canvas_width if info else 0.25
                relative_height = info["height"] / canvas_width if info else 0.187
                
                config["modules"].append({
                    "module_name": mod_data["module_name"],
                    "instance_id": iid,
                    "relative_width": relative_width,
                    "relative_height": relative_height
                })
        print(f"[SAVE] Writing layout config to: {config_path}")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            print(f"[SAVE] Layout config written.")
        except Exception as e:
            print(f"[SAVE][ERROR] Failed to write layout config: {e}")

    def load_layout_config(self):
        config_path = os.path.join(self.saves_dir, self.CONFIG_FILE)
        print(f"[LOAD] Try loading layout config from: {config_path}")
        if not os.path.exists(config_path):
            print("[LOAD] No layout config file found, using default layout.")
            return False
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            for iid in list(self.loaded_modules.keys()):
                self.hide_module(iid)
            max_counters = {}
            for mod in config.get("modules", []):
                module_name = mod["module_name"]
                iid = mod["instance_id"]
                if "#" in iid:
                    base, num = iid.rsplit("#", 1)
                    try:
                        num = int(num)
                        if base not in max_counters or num > max_counters[base]:
                            max_counters[base] = num
                    except Exception:
                        pass
            for base, max_num in max_counters.items():
                self.module_instance_counters[base] = max_num + 1

            module_order = config.get("module_order")
            if module_order:
                iid_to_mod = {mod["instance_id"]: mod for mod in config.get("modules", [])}
                ordered_mods = [iid_to_mod[iid] for iid in module_order if iid in iid_to_mod]
            else:
                ordered_mods = config.get("modules", [])

            for mod in ordered_mods:
                module_name = mod["module_name"]
                iid = mod["instance_id"]
                
                # 從相對值計算實際尺寸
                canvas_width = self.canvas.winfo_width()
                if canvas_width <= 1:
                    canvas_width = 800
                    
                width = int(mod.get("relative_width", 0.25) * canvas_width)
                height = int(mod.get("relative_height", 0.187) * canvas_width)
                
                # 確保最小尺寸
                width = max(50, width)
                height = max(50, height)
                
                if module_name in self.available_module_classes:
                    old_counter = self.module_instance_counters.get(module_name, 1)
                    try:
                        if "#" in iid:
                            base, num = iid.rsplit("#", 1)
                            num = int(num)
                            self.module_instance_counters[module_name] = num
                    except Exception:
                        pass
                    frame_wrapper = self.instantiate_module(module_name, self.main_layout_manager)
                    self.module_instance_counters[module_name] = max(old_counter, max_counters.get(module_name, 0) + 1)
                    if frame_wrapper:
                        self.loaded_modules[iid] = self.loaded_modules.pop(list(self.loaded_modules.keys())[-1])
                        self.loaded_modules[iid]["instance_id"] = iid
                        self.main_layout_manager.resize_module(iid, width, height, defer_reflow=True)
            self.main_layout_manager.reflow_layout()
            self.update_min_window_size()
            self.update_layout_scrollregion()
            maximized = config.get("maximized_module_name")
            if maximized and maximized in self.loaded_modules:
                self.maximize_module(maximized)
            print("[LOAD] Layout config loaded and restored.")
            return True
        except Exception as e:
            print(f"[LOAD][ERROR] Failed to load layout config: {e}")
            return False

    # 儲存目前佈局為設定檔
    def save_profile_dialog(self):
        name = simpledialog.askstring("儲存設定檔", "請輸入設定檔名稱：")
        if not name:
            return
        filename = f"{self.PROFILE_PREFIX}{name}{self.PROFILE_SUFFIX}"
        path = os.path.join(self.saves_dir, filename)
        config = self._get_current_layout_config()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("儲存成功", f"設定檔已儲存為 {filename}")
        except Exception as e:
            messagebox.showerror("儲存失敗", f"無法儲存設定檔：{e}")

    # 載入設定檔
    def load_profile_dialog(self):
        profiles = self._list_profiles()
        if not profiles:
            messagebox.showinfo("無設定檔", "目前沒有可用的設定檔。")
            return
        # 彈出選單讓用戶選擇
        sel = self._choose_profile_dialog(profiles, "載入設定檔", "請選擇要載入的設定檔：")
        if not sel:
            return
        filename = f"{self.PROFILE_PREFIX}{sel}{self.PROFILE_SUFFIX}"
        path = os.path.join(self.saves_dir, filename)
        self._load_layout_config_from_file(path)

    # 管理設定檔（可刪除）
    def manage_profiles_dialog(self):
        profiles = self._list_profiles()
        if not profiles:
            messagebox.showinfo("無設定檔", "目前沒有可用的設定檔。")
            return
        sel = self._choose_profile_dialog(profiles, "刪除設定檔", "請選擇要刪除的設定檔：")
        if not sel:
            return
        filename = f"{self.PROFILE_PREFIX}{sel}{self.PROFILE_SUFFIX}"
        path = os.path.join(self.saves_dir, filename)
        try:
            os.remove(path)
            messagebox.showinfo("刪除成功", f"設定檔 {filename} 已刪除")
        except Exception as e:
            messagebox.showerror("刪除失敗", f"無法刪除設定檔：{e}")

    def _choose_profile_dialog(self, profiles, title, prompt):
        # 彈出一個簡單的選擇視窗
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.grab_set()
        tk.Label(dialog, text=prompt).pack(padx=10, pady=(10, 5))
        var = tk.StringVar(value=profiles[0])
        listbox = tk.Listbox(dialog, listvariable=tk.StringVar(value=profiles), height=min(10, len(profiles)))
        listbox.pack(padx=10, pady=5)
        listbox.selection_set(0)
        def on_ok():
            sel = listbox.get(listbox.curselection())
            var.set(sel)
            dialog.destroy()
        def on_cancel():
            var.set("")
            dialog.destroy()
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=(0,10))
        tk.Button(btn_frame, text="確定", width=8, command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", width=8, command=on_cancel).pack(side=tk.LEFT, padx=5)
        dialog.wait_window()
        return var.get()

    def _list_profiles(self):
        if not os.path.exists(self.saves_dir):
            return []
        files = os.listdir(self.saves_dir)
        profiles = []
        for f in files:
            if f.startswith(self.PROFILE_PREFIX) and f.endswith(self.PROFILE_SUFFIX):
                name = f[len(self.PROFILE_PREFIX):-len(self.PROFILE_SUFFIX)]
                profiles.append(name)
        return profiles

    def _get_current_layout_config(self):
        # 取得目前佈局設定（與 save_layout_config 類似，但回傳 dict）
        if not self.loaded_modules:
            return {
                "modules": [],
                "maximized_module_name": self.maximized_module_name,
                "module_order": []
            }
        config = {
            "modules": [],
            "maximized_module_name": self.maximized_module_name,
            "module_order": []
        }
        current_instance_ids = set(self.loaded_modules.keys()) & set(self.main_layout_manager.modules.keys())
        config["module_order"] = [iid for iid in self.main_layout_manager.modules.keys() if iid in current_instance_ids]
        for iid in config["module_order"]:
            mod_data = self.loaded_modules.get(iid)
            info = self.main_layout_manager.get_module_info(iid)
            if mod_data:
                # 取得目前視窗寬度作為基準
                canvas_width = self.canvas.winfo_width()
                if canvas_width <= 1:
                    canvas_width = 800
                    
                # 計算相對寬度 (0~1 之間的值)
                relative_width = info["width"] / canvas_width if info else 0.25
                relative_height = info["height"] / canvas_width if info else 0.187
                
                config["modules"].append({
                    "module_name": mod_data["module_name"],
                    "instance_id": iid,
                    "relative_width": relative_width,
                    "relative_height": relative_height
                })
        return config

    def _load_layout_config_from_file(self, path):
        print(f"[LOAD] Try loading layout config from: {path}")
        if not os.path.exists(path):
            print("[LOAD] No layout config file found, using default layout.")
            messagebox.showerror("載入失敗", "找不到設定檔。")
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            for iid in list(self.loaded_modules.keys()):
                self.hide_module(iid)
            max_counters = {}
            for mod in config.get("modules", []):
                module_name = mod["module_name"]
                iid = mod["instance_id"]
                if "#" in iid:
                    base, num = iid.rsplit("#", 1)
                    try:
                        num = int(num)
                        if base not in max_counters or num > max_counters[base]:
                            max_counters[base] = num
                    except Exception:
                        pass
            for base, max_num in max_counters.items():
                self.module_instance_counters[base] = max_num + 1

            module_order = config.get("module_order")
            if module_order:
                iid_to_mod = {mod["instance_id"]: mod for mod in config.get("modules", [])}
                ordered_mods = [iid_to_mod[iid] for iid in module_order if iid in iid_to_mod]
            else:
                ordered_mods = config.get("modules", [])

            for mod in ordered_mods:
                module_name = mod["module_name"]
                iid = mod["instance_id"]
                
                # 從相對值計算實際尺寸
                canvas_width = self.canvas.winfo_width()
                if canvas_width <= 1:
                    canvas_width = 800
                    
                width = int(mod.get("relative_width", 0.25) * canvas_width)
                height = int(mod.get("relative_height", 0.187) * canvas_width)
                
                # 確保最小尺寸
                width = max(50, width)
                height = max(50, height)
                
                if module_name in self.available_module_classes:
                    old_counter = self.module_instance_counters.get(module_name, 1)
                    try:
                        if "#" in iid:
                            base, num = iid.rsplit("#", 1)
                            num = int(num)
                            self.module_instance_counters[module_name] = num
                    except Exception:
                        pass
                    frame_wrapper = self.instantiate_module(module_name, self.main_layout_manager)
                    self.module_instance_counters[module_name] = max(old_counter, max_counters.get(module_name, 0) + 1)
                    if frame_wrapper:
                        self.loaded_modules[iid] = self.loaded_modules.pop(list(self.loaded_modules.keys())[-1])
                        self.loaded_modules[iid]["instance_id"] = iid
                        self.main_layout_manager.resize_module(iid, width, height, defer_reflow=True)
            self.main_layout_manager.reflow_layout()
            self.update_min_window_size()
            self.update_layout_scrollregion()
            maximized = config.get("maximized_module_name")
            if maximized and maximized in self.loaded_modules:
                self.maximize_module(maximized)
            print("[LOAD] Layout config loaded and restored.")
            messagebox.showinfo("載入成功", "設定檔已載入。")
            return True
        except Exception as e:
            print(f"[LOAD][ERROR] Failed to load layout config: {e}")
            messagebox.showerror("載入失敗", f"無法載入設定檔：{e}")
            return False

    def on_closing(self):
        self.shared_state.log("Application closing...")
        for module_name, module_data in list(self.loaded_modules.items()):
            if module_data and module_data.get('instance'):
                try:
                    module_data['instance'].on_destroy()
                except Exception as e:
                    self.shared_state.log(f"Error during on_destroy for module {module_name}: {e}", level=logging.ERROR)

        self.root.destroy()

    def show_context_menu(self, event):
        self.context_menu.delete(0, tk.END)

        self.context_menu.add_command(label="Toggle Module Visibility:", state=tk.DISABLED)
        self.context_menu.add_separator()

        for instance_id, mod_data in self.loaded_modules.items():
            module_name = mod_data.get('module_name', instance_id)
            is_visible = mod_data.get('frame_wrapper') and mod_data.get('frame_wrapper').winfo_exists()
            prefix = "[x]" if is_visible else "[ ]"
            self.context_menu.add_command(
                label=f"{prefix} {instance_id}",
                command=lambda iid=instance_id: self.toggle_module_visibility(iid)
            )

        self.context_menu.add_separator()
        for module_name in sorted(self.available_module_classes.keys()):
            self.context_menu.add_command(
                label=f"Add {module_name}",
                command=lambda mn=module_name: self.add_module_from_menu(mn)
            )

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def toggle_module_visibility(self, instance_id):
        self.shared_state.log(f"Toggle visibility for {instance_id}", level=logging.DEBUG)
        is_visible = False
        wrapper_to_check = None
        if instance_id in self.loaded_modules:
            mod_data = self.loaded_modules[instance_id]
            wrapper_to_check = mod_data.get('frame_wrapper')
            if wrapper_to_check and wrapper_to_check.winfo_exists():
                is_visible = True

        if is_visible:
            self.hide_module(instance_id)
        else:
            self.shared_state.log(f"Showing module: {instance_id}")

    def hide_module(self, instance_id: str):
        if self.maximized_module_name == instance_id:
            self.restore_modules()
            if self.maximized_module_name is None and instance_id in self.loaded_modules:
                self.hide_module(instance_id)
            return
        else:
            self.shared_state.log(f"Hiding module: {instance_id} via close button/hide action.")
            if instance_id in self.loaded_modules:
                module_data = self.loaded_modules[instance_id]
                frame_wrapper = module_data.get('frame_wrapper')
                instance = module_data.get('instance')

                if frame_wrapper and frame_wrapper.winfo_exists():
                    self.main_layout_manager.remove_module(instance_id)

                if instance:
                    try:
                        instance.on_destroy()
                    except Exception as e:
                        self.shared_state.log(f"Error during on_destroy for module {instance_id} when hiding: {e}", "ERROR")

                if frame_wrapper and frame_wrapper.winfo_exists():
                    frame_wrapper.destroy()

                del self.loaded_modules[instance_id]
                self.shared_state.log(f"Module '{instance_id}' hidden and instance destroyed.")

                self.update_min_window_size()
                self.update_layout_scrollregion()
                self.save_layout_config()
            else:
                self.shared_state.log(f"Module '{instance_id}' not found or not loaded, cannot hide.", "WARNING")

    def start_drag(self, event, instance_id):
        self.shared_state.log(f"Start dragging module: {instance_id}", level=logging.DEBUG)
        self.dragged_module_name = instance_id
        self.drag_start_widget = event.widget

        if self.dragged_module_name not in self.main_layout_manager.modules or \
           self.dragged_module_name not in self.loaded_modules:
            self.shared_state.log(f"Dragged module {self.dragged_module_name} not found in layout manager or loaded modules.", "ERROR")
            self.dragged_module_name = None
            return

        dragged_module_layout_info = self.main_layout_manager.modules[self.dragged_module_name]
        original_frame_wrapper = self.loaded_modules[self.dragged_module_name]['frame_wrapper']

        original_width = dragged_module_layout_info['width']
        original_height = dragged_module_layout_info['height']
        original_x = dragged_module_layout_info['x']
        original_y = dragged_module_layout_info['y']
        
        if original_frame_wrapper:
            self.original_dragged_module_relief = original_frame_wrapper.cget("relief")
        
        self.ghost_module_frame = ttk.Frame(self.canvas, width=original_width, height=original_height)
        self.ghost_module_frame.configure(relief=tk.RIDGE, borderwidth=2)
        ttk.Label(self.ghost_module_frame, text=f"Preview: {self.dragged_module_name}").pack(expand=True, fill=tk.BOTH)

        self.ghost_canvas_window_id = self.canvas.create_window(
            original_x, original_y, 
            window=self.ghost_module_frame, 
            anchor=tk.NW, 
            width=original_width, 
            height=original_height
        )
        self.shared_state.log(f"Ghost created at {original_x},{original_y} with ID {self.ghost_canvas_window_id}", "DEBUG")

        if original_frame_wrapper:
            original_frame_wrapper.place_forget()
            self.shared_state.log(f"Original module {self.dragged_module_name} hidden.", "DEBUG")

        self.last_preview_target_module_name = None 

        self.root.config(cursor="fleur")
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.end_drag)
        
    def on_drag(self, event):
        if not self.dragged_module_name or not self.ghost_canvas_window_id or \
           self.dragged_module_name not in self.main_layout_manager.modules:
            return

        try:
            mouse_x_on_canvas = event.x_root - self.canvas.winfo_rootx()
            mouse_y_on_canvas = event.y_root - self.canvas.winfo_rooty()
        except tk.TclError: 
            return

        other_modules_info = []
        for name, module_props in self.main_layout_manager.modules.items():
            if name == self.dragged_module_name:
                continue
            if module_props and module_props.get('frame') and module_props['frame'].winfo_exists() and \
               all(k in module_props for k in ['x', 'y', 'width', 'height']):
                other_modules_info.append({
                    'name': name,
                    'x': module_props['x'],
                    'y': module_props['y'],
                    'width': module_props['width'],
                    'height': module_props['height'],
                })
        
        self.last_preview_target_module_name = None

        if other_modules_info: 
            modules_sorted_y = sorted(other_modules_info, key=lambda m: (m['y'], m['x']))
            best_h_target = {'dist': float('inf'), 'target_name': None}

            if modules_sorted_y:
                mod_y_first = modules_sorted_y[0]
                if mouse_x_on_canvas >= mod_y_first['x'] and mouse_x_on_canvas <= mod_y_first['x'] + mod_y_first['width']:
                    dist = abs(mouse_y_on_canvas - mod_y_first['y'])
                    if dist < best_h_target['dist']:
                        best_h_target['dist'] = dist
                        best_h_target['target_name'] = mod_y_first['name']
            
            for i, mod_y in enumerate(modules_sorted_y):
                gap_line_y = mod_y['y'] + mod_y['height']
                if mouse_x_on_canvas >= mod_y['x'] and mouse_x_on_canvas <= mod_y['x'] + mod_y['width']:
                    dist = abs(mouse_y_on_canvas - gap_line_y)
                    if dist < best_h_target['dist']:
                        best_h_target['dist'] = dist
                        best_h_target['target_name'] = modules_sorted_y[i+1]['name'] if (i + 1) < len(modules_sorted_y) else None

            modules_sorted_x = sorted(other_modules_info, key=lambda m: (m['x'], m['y']))
            best_v_target = {'dist': float('inf'), 'target_name': None}

            if modules_sorted_x:
                mod_x_first = modules_sorted_x[0]
                if mouse_y_on_canvas >= mod_x_first['y'] and mouse_y_on_canvas <= mod_x_first['y'] + mod_x_first['height']:
                    dist = abs(mouse_x_on_canvas - mod_x_first['x'])
                    if dist < best_v_target['dist']:
                        best_v_target['dist'] = dist
                        best_v_target['target_name'] = mod_x_first['name']

            for i, mod_x in enumerate(modules_sorted_x):
                gap_line_x = mod_x['x'] + mod_x['width']
                if mouse_y_on_canvas >= mod_x['y'] and mouse_y_on_canvas <= mod_x['y'] + mod_x_first['height']:
                    dist = abs(mouse_x_on_canvas - gap_line_x)
                    if dist < best_v_target['dist']:
                        best_v_target['dist'] = dist
                        best_v_target['target_name'] = modules_sorted_x[i+1]['name'] if (i + 1) < len(modules_sorted_x) else None
            
            final_target_name = None
            h_target_is_valid = best_h_target['dist'] != float('inf')
            v_target_is_valid = best_v_target['dist'] != float('inf')

            if h_target_is_valid and v_target_is_valid:
                if best_h_target['dist'] <= best_v_target['dist']: 
                    final_target_name = best_h_target['target_name']
                else:
                    final_target_name = best_v_target['target_name']
            elif h_target_is_valid:
                final_target_name = best_h_target['target_name']
            elif v_target_is_valid:
                final_target_name = best_v_target['target_name']
            
            self.last_preview_target_module_name = final_target_name

        self.shared_state.log("Optimized on_drag: Updating ghost position without full layout simulation.", "DEBUG")
        new_x, new_y = mouse_x_on_canvas, mouse_y_on_canvas

        if self.last_preview_target_module_name and self.last_preview_target_module_name in self.main_layout_manager.modules:
            target_props = self.main_layout_manager.modules[self.last_preview_target_module_name]
            new_x = target_props.get('x', mouse_x_on_canvas)
            new_y = target_props.get('y', mouse_y_on_canvas)
            self.shared_state.log(f"Ghost target: {self.last_preview_target_module_name} at ({new_x},{new_y})", "DEBUG")
        else:
            self.shared_state.log(f"Ghost follows mouse to ({new_x},{new_y})", "DEBUG")

        if self.ghost_canvas_window_id:
            self.canvas.coords(self.ghost_canvas_window_id, new_x, new_y)

    def end_drag(self, event):
        if not self.dragged_module_name:
            self.root.config(cursor="")
            self.root.unbind("<B1-Motion>")
            self.root.unbind("<ButtonRelease-1>")
            return

        if self.ghost_canvas_window_id:
            self.canvas.delete(self.ghost_canvas_window_id)
            self.ghost_canvas_window_id = None
        if self.ghost_module_frame: 
            self.ghost_module_frame = None

        self.shared_state.log(f"End dragging module: {self.dragged_module_name}. Target before: {self.last_preview_target_module_name}", level=logging.DEBUG)
        
        dragged_module_data = self.loaded_modules.get(self.dragged_module_name)
        if dragged_module_data:
            original_frame_wrapper = dragged_module_data.get('frame_wrapper')
            if original_frame_wrapper and hasattr(self, 'original_dragged_module_relief') and self.original_dragged_module_relief:
                try:
                    original_frame_wrapper.config(relief=self.original_dragged_module_relief, borderwidth=1)
                except tk.TclError as e:
                    self.shared_state.log(f"Error resetting relief for {self.dragged_module_name}: {e}", "WARNING")
        
        if self.dragged_module_name:
            self.main_layout_manager.move_module_before(
                self.dragged_module_name, 
                self.last_preview_target_module_name
            )
            self.update_layout_scrollregion()
            self.update_min_window_size()
            self.save_layout_config()

    def maximize_module(self, instance_id):
        if self.maximized_module_name == instance_id:
            return

        self.shared_state.log(f"Maximizing module: {instance_id}", "INFO")
        self._pre_maximize_layout = self.main_layout_manager.get_layout_data()
        self.maximized_module_name = instance_id

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.main_layout_manager.config(width=canvas_width, height=canvas_height)
        self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width, height=canvas_height)

        for iid, mod_data in self.loaded_modules.items():
            frame_wrapper = mod_data.get('frame_wrapper')
            instance = mod_data.get('instance')
            if iid == instance_id:
                if frame_wrapper and frame_wrapper.winfo_exists():
                    frame_wrapper.lift()
                    frame_wrapper.place(x=0, y=0, width=canvas_width, height=canvas_height)
                if instance:
                    instance.is_maximized = True
            else:
                if frame_wrapper and frame_wrapper.winfo_exists():
                    frame_wrapper.place_forget()
                if instance:
                    instance.is_maximized = False

        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        self.save_layout_config()

    def restore_modules(self):
        if not self.maximized_module_name:
            return
        self.shared_state.log("Restoring modules from maximized state.", "INFO")
        for iid, mod_data in self.loaded_modules.items():
            instance = mod_data.get('instance')
            if instance:
                instance.is_maximized = False

        content_height = self.main_layout_manager.last_calculated_content_height
        content_width = self.main_layout_manager.last_calculated_content_width
        self.main_layout_manager.config(width=content_width, height=content_height)
        self.canvas.itemconfig(self.main_layout_manager_window_id, width=content_width, height=content_height)

        if self._pre_maximize_layout:
            for iid, props in self._pre_maximize_layout.items():
                if iid in self.loaded_modules:
                    self.main_layout_manager.resize_module(iid, props.get('width', 200), props.get('height', 150))
            self.main_layout_manager.reflow_layout()
        else:
            self.main_layout_manager.reflow_layout()

        self.canvas.config(scrollregion=(0, 0, content_width, content_height))
        self.update_layout_scrollregion()
        self.maximized_module_name = None
        self._pre_maximize_layout = None
        self.save_layout_config()

    def get_resize_cursor(self):
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        border_width = 8
        corner_size = 15

        # 取得滑鼠在 root 視窗內的絕對座標
        mouse_y = self.root.winfo_pointery() - self.root.winfo_rooty()
        mouse_x = self.root.winfo_pointerx() - self.root.winfo_rootx()

        # 角落判斷
        if mouse_x <= corner_size and mouse_y <= corner_size:
            return "top_left_corner", "top_left_corner"
        elif mouse_x <= corner_size and mouse_y >= height - corner_size:
            return "bottom_left_corner", "bottom_left_corner"
        elif mouse_x >= width - corner_size and mouse_y >= height - corner_size:
            return "bottom_right_corner", "bottom_right_corner"
        # 邊判斷
        elif mouse_y <= border_width:
            return "top", "top_side"
        elif mouse_y >= height - border_width:
            return "bottom", "bottom_side"
        elif mouse_x <= border_width:
            return "left", "left_side"
        elif mouse_x >= width - border_width:
            return "right", "right_side"
        else:
            return None, "arrow"

    def on_mouse_motion(self, event):
        """滑鼠移動時改變游標"""
        if self.is_maximized:
            return
        
        resize_mode, cursor = self.get_resize_cursor()
        try:
            self.root.configure(cursor=cursor)
        except:
            pass
    
    def on_mouse_down(self, event):
        """滑鼠按下"""
        if self.is_maximized:
            return
        
        self.resize_mode, _ = self.get_resize_cursor()
        if self.resize_mode:
            self.resize_start_x = event.x_root
            self.resize_start_y = event.y_root
            self.start_geometry = self.root.geometry()
    
    def on_mouse_drag(self, event):
        """滑鼠拖拽"""
        if self.is_maximized or not self.resize_mode:
            return
        
        dx = event.x_root - self.resize_start_x
        dy = event.y_root - self.resize_start_y
        
        # 解析當前幾何
        geo = self.start_geometry
        parts = geo.split('+')
        size_part = parts[0]
        width, height = map(int, size_part.split('x'))
        x = int(parts[1]) if len(parts) > 1 else 0
        y = int(parts[2]) if len(parts) > 2 else 0
        
        # 最小尺寸
        min_width, min_height = 300, 200
        
        # 根據縮放模式調整
        if self.resize_mode == "right":
            width = max(min_width, width + dx)
        elif self.resize_mode == "left":
            new_width = max(min_width, width - dx)
            x = x + (width - new_width)
            width = new_width
        elif self.resize_mode == "bottom":
            height = max(min_height, height + dy)
        elif self.resize_mode == "top":
            new_height = max(min_height, height - dy)
            y = y + (height - new_height)
            height = new_height
        elif self.resize_mode == "top_left_corner":
            # 左上角：左邊和上邊
            new_width = max(min_width, width - dx)
            new_height = max(min_height, height - dy)
            x = x + (width - new_width)
            y = y + (height - new_height)
            width = new_width
            height = new_height
        elif self.resize_mode == "bottom_left_corner":
            # 左下角：左邊和下邊
            new_width = max(min_width, width - dx)
            x = x + (width - new_width)
            width = new_width
            height = max(min_height, height + dy)
        elif self.resize_mode == "bottom_right_corner":
            # 右下角：右邊和下邊
            width = max(min_width, width + dx)
            height = max(min_height, height + dy)
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def on_mouse_up(self, event):
        """滑鼠釋放"""
        self.resize_mode = None
        self.root.configure(cursor="arrow")
    
    def start_move(self, event):
        """開始拖拽視窗"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def do_move(self, event):
        """執行拖拽視窗"""
        if self.is_maximized:
            return
        
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")
    
    def toggle_maximize(self, event=None):
        """切換最大化狀態"""
        if self.is_maximized:
            self.restore_window_custom() # 避免與 restore_modules 衝突
        else:
            self.maximize_window_custom() # 避免與 maximize_module 衝突
    
    def maximize_window_custom(self): # 避免與 maximize_module 衝突
        """最大化視窗"""
        self.normal_geometry = self.root.geometry()
        self.is_maximized = True
        self.max_btn.config(text="🗗")
        
        # 獲取螢幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 考慮工作列高度
        self.root.geometry(f"{screen_width}x{screen_height-40}+0+0")
        self.status_label.config(text="最大化")
    
    def restore_window_custom(self): # 避免與 restore_modules 衝突
        """還原視窗"""
        self.is_maximized = False
        self.max_btn.config(text="🗖")
        self.root.geometry(self.normal_geometry)
        self.status_label.config(text="就緒")
    
    def close_window(self):
        """關閉視窗"""
        self.on_closing() # 呼叫現有的關閉邏輯

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    def show_on_taskbar(self, root):
        hwnd = windll.user32.GetParent(root.winfo_id())
        style = windll.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        style = style & ~self.WS_EX_TOOLWINDOW | self.WS_EX_APPWINDOW
        windll.user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, style)
        root.wm_withdraw()
        root.after(10, lambda: root.wm_deiconify())

    def minimize_window(self, event=None):
        self.root.overrideredirect(False)
        self.root.update_idletasks()
        self.root.iconify()
        self.root.bind('<Map>', lambda e: self.restore_window())

    def restore_window(self, event=None):
        self.map_event_handled += 1
        if self.map_event_handled == 2:
            self.root.unbind('<Map>')
            self.root.withdraw()
            self.root.after(100, self._finish_restore)

    def _finish_restore(self):
        self.root.deiconify()
        self.root.overrideredirect(True)
        self.show_on_taskbar(self.root)
        self.map_event_handled = 0


if __name__ == "__main__":
    import sys
    if '__main__' in sys.modules:
        sys.modules['main'] = sys.modules['__main__']

    root = tk.Tk()
    #root.withdraw() # Hide main window during setup

    splash = None
    try:
        from PIL import Image, ImageTk

        splash = tk.Toplevel(root)
        splash.overrideredirect(True)

        splash_width = 450
        splash_height = 200

        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (splash_width / 2))
        y_cordinate = int((screen_height / 2) - (splash_height / 2))
        splash.geometry(f"{splash_width}x{splash_height}+{x_cordinate}+{y_cordinate}")

        # Use colors from style_manager if available, otherwise fallback
        BG_COLOR = "#2c3e50"
        BORDER_COLOR = "#3498db"
        try:
            # These are imported at the top level of main.py
            BG_COLOR = COLOR_PRIMARY_BG
            BORDER_COLOR = COLOR_ACCENT_HOVER
        except NameError:
            pass # Use fallback if not found

        splash.config(bg=BG_COLOR)

        # A frame to hold all content, allowing for a border effect
        container = tk.Frame(splash, bg=BG_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # --- Image on the left ---
        img = Image.open("assets/logo.png")
        img.thumbnail((128, 128), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(img)

        img_label = tk.Label(container, image=logo_img, bg=BG_COLOR)
        img_label.image = logo_img # Keep a reference!
        img_label.pack(side=tk.LEFT, padx=(20, 15), pady=20)

        # --- Text on the right ---
        text_frame = tk.Frame(container, bg=BG_COLOR)
        text_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, pady=10, padx=(0, 20))

        # Use a sub-frame to center the text labels vertically
        center_frame = tk.Frame(text_frame, bg=BG_COLOR)
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # FlexiTools Title
        app_name_label = tk.Label(center_frame, text="FlexiTools", font=("Segoe UI", 28, "bold"), bg=BG_COLOR, fg="white")
        app_name_label.pack(pady=(0, 5))

        # Status Message
        status_label = tk.Label(center_frame, text="正在初始化...", font=("Segoe UI", 10), bg=BG_COLOR, fg="#cccccc")
        status_label.pack(pady=(5, 0))

        splash.update()

    except Exception as e:
        print(f"Failed to create splash screen: {e}")
        # If splash fails, we don't want to hang, just continue.
        # The 'splash' variable will be None.

    # --- Main App Initialization ---
    configure_styles()
    apply_post_creation_styles(root)
    app = ModularGUI(root)

    # --- Cleanup ---
    if splash:
        splash.destroy()

    # The ModularGUI class handles making the main window visible.
    root.mainloop()
    if splash:
        splash.destroy()

    # The ModularGUI class handles making the main window visible.
    root.mainloop()

