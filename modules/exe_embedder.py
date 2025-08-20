
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import ctypes
from ctypes import wintypes
import time
import os
import shutil
from main import Module

# Ctypes definitions for WinAPI
user32 = ctypes.windll.user32
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
WM_CLOSE = 0x0010

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

class ExeEmbedderModule(Module):
    """
    A module to select and embed an external EXE's GUI into a scrollable tkinter frame.
    """
    def __init__(self, master, shared_state, module_name="ExeEmbedder", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"ExeEmbedderModule '{self.module_name}' initialized.")
        
        self.process = None
        self.embedded_hwnd = None
        self.is_external_script = False
        self.target_file = None # Will hold the path to the exe to be run
        self.scripts_dir = os.path.join("modules", "saves", "exe_embedders")
        os.makedirs(self.scripts_dir, exist_ok=True)

        self.create_ui()

        # Add event bindings for the hover menu
        self.hide_menu_timer = None
        # We assume the Module base class creates a title_label widget.
        # If not, this feature will not activate, and the menu will be shown by default.
        if hasattr(self, 'title_label'):
            self.title_label.bind("<Enter>", self.show_menu)
            self.title_label.bind("<Leave>", self.schedule_hide_menu)
            self.menu_frame.bind("<Enter>", self.cancel_hide_menu)
            self.menu_frame.bind("<Leave>", self.schedule_hide_menu)
        else:
            self.shared_state.log("Warning: ExeEmbedderModule could not find 'title_label' to bind hover menu.")
            # As a fallback, show the menu permanently if the title_label is not found.
            self.show_menu()

    def create_ui(self):
        """Create the user interface, with a hover-activated menu to save space."""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Row 1 (scroll area) will expand

        # --- Start of Hover Menu ---
        self.menu_frame = ttk.Frame(main_frame)
        # This frame will be gridded in/out by show_menu/hide_menu
        self.menu_frame.columnconfigure(1, weight=1)

        # Script management (now inside menu_frame)
        script_frame = ttk.Frame(self.menu_frame)
        script_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        script_frame.columnconfigure(1, weight=1)

        self.add_button = ttk.Button(script_frame, text="加入程式組", command=self.add_script_to_pool, state=tk.DISABLED)
        self.add_button.grid(row=0, column=0, padx=(0, 5))

        self.script_var = tk.StringVar()
        self.script_combo = ttk.Combobox(script_frame, textvariable=self.script_var, state="readonly")
        self.script_combo.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.script_combo.bind("<<ComboboxSelected>>", self.on_script_select)

        delete_button = ttk.Button(script_frame, text="刪除選定", command=self.delete_selected_script)
        delete_button.grid(row=0, column=2, padx=(0, 5))

        self.populate_scripts_dropdown()

        # File selection (now inside menu_frame)
        top_frame = ttk.Frame(self.menu_frame)
        top_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)

        select_button = ttk.Button(top_frame, text="選擇外部 .exe 檔案", command=self.select_external_exe)
        select_button.pack(side="left", padx=(0, 10))

        self.file_label = ttk.Label(top_frame, text="尚未選擇檔案", anchor="w")
        self.file_label.pack(side="left", fill="x", expand=True)
        # --- End of Hover Menu ---

        # Host frame for the canvas and scrollbars
        scroll_host_frame = ttk.Frame(main_frame, relief="sunken")
        scroll_host_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 5))
        scroll_host_frame.grid_rowconfigure(0, weight=1)
        scroll_host_frame.grid_columnconfigure(0, weight=1)

        # Create canvas and scrollbars
        self.canvas = tk.Canvas(scroll_host_frame, bg="black")
        v_scroll = ttk.Scrollbar(scroll_host_frame, orient="vertical", command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(scroll_host_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # This is the frame that will contain the embedded window
        self.embed_target_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.embed_target_frame, anchor="nw")

        # Bottom frame for execution button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        bottom_frame.columnconfigure(0, weight=1)

        self.run_button = ttk.Button(bottom_frame, text="執行", command=self.run_exe, state=tk.DISABLED)
        self.run_button.grid(row=0, column=0)

    def show_menu(self, event=None):
        """Shows the control menu."""
        self.cancel_hide_menu()
        self.menu_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

    def hide_menu(self, event=None):
        """Hides the control menu."""
        self.menu_frame.grid_remove()

    def schedule_hide_menu(self, event=None):
        """Schedules the menu to be hidden after a short delay."""
        self.cancel_hide_menu()
        self.hide_menu_timer = self.master.after(100, self.hide_menu)

    def cancel_hide_menu(self, event=None):
        """Cancels a scheduled menu hide action."""
        if self.hide_menu_timer:
            self.master.after_cancel(self.hide_menu_timer)
            self.hide_menu_timer = None

    def add_script_to_pool(self):
        """Adds the currently loaded external script to the scripts directory."""
        if not self.target_file or not self.is_external_script:
            messagebox.showwarning("沒有外部腳本", "請先選擇一個外部EXE檔案。", parent=self.frame)
            return

        filename = os.path.basename(self.target_file)
        dest_path = os.path.join(self.scripts_dir, filename)

        if os.path.exists(dest_path):
            if not messagebox.askyesno("檔案已存在", f"檔案 '{filename}' 已存在於程式組中。要覆蓋它嗎？", parent=self.frame):
                return

        try:
            shutil.copy(self.target_file, dest_path)
            messagebox.showinfo("成功", f"腳本 '{filename}' 已成功加入。", parent=self.frame)

            self.target_file = dest_path
            self.is_external_script = False
            self.add_button.config(state=tk.DISABLED)

            self.populate_scripts_dropdown()
            self.script_var.set(filename)

        except Exception as e:
            messagebox.showerror("複製失敗", f"無法將檔案複製到程式組資料夾：\n{e}", parent=self.frame)

    def populate_scripts_dropdown(self):
        """Scans the scripts directory and populates the dropdown."""
        try:
            scripts = [f for f in os.listdir(self.scripts_dir) if f.endswith(".exe")]
            self.script_combo['values'] = sorted(scripts)
            if not scripts:
                self.script_var.set("程式組中沒有腳本")
            else:
                if self.script_var.get() not in scripts:
                    self.script_var.set("")
        except Exception as e:
            self.shared_state.log(f"Error populating scripts dropdown: {e}")
            self.script_combo['values'] = []
            self.script_var.set("讀取腳本失敗")

    def on_script_select(self, event=None):
        """Handles the selection of a script from the dropdown."""
        selected_script = self.script_var.get()
        if not selected_script or selected_script == "程式組中沒有腳本":
            self.run_button.config(state=tk.DISABLED)
            return

        self.is_external_script = False
        self.add_button.config(state=tk.DISABLED)
        filepath = os.path.join(self.scripts_dir, selected_script)
        self.target_file = filepath
        self.file_label.config(text=os.path.basename(filepath))
        self.run_button.config(state=tk.NORMAL)

    def delete_selected_script(self):
        """Deletes the currently selected script from the pool."""
        selected_script = self.script_var.get()
        if not selected_script or selected_script == "程式組中沒有腳本":
            messagebox.showwarning("沒有選擇", "請先從下拉清單中選擇一個腳本。", parent=self.frame)
            return

        if not messagebox.askyesno("確認刪除", f"您確定要刪除腳本 '{selected_script}' 嗎？此操作無法復原。", parent=self.frame):
            return

        filepath_to_delete = os.path.join(self.scripts_dir, selected_script)

        # If the file to be deleted is the one currently running, stop it first.
        if self.target_file == filepath_to_delete:
            self.on_destroy(cleanup_resources=False)
            self.target_file = None
            self.run_button.config(state=tk.DISABLED)

        try:
            os.remove(filepath_to_delete)
            messagebox.showinfo("成功", f"腳本 '{selected_script}' 已被刪除。", parent=self.frame)
            self.populate_scripts_dropdown()

            # Reset UI elements
            self.file_label.config(text="尚未選擇檔案")
            self.add_button.config(state=tk.DISABLED)
            self.is_external_script = False
            self.run_button.config(state=tk.DISABLED)
            self.script_var.set("")

        except Exception as e:
            messagebox.showerror("刪除失敗", f"無法刪除檔案：\n{e}", parent=self.frame)

    def select_external_exe(self):
        """Open a file dialog to select an external .exe file."""
        filepath = filedialog.askopenfilename(
            title="選擇一個 .exe 檔案",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
            parent=self.frame
        )
        if not filepath:
            return

        self.target_file = filepath
        self.file_label.config(text=os.path.basename(filepath))
        self.script_var.set("") # Clear selection in combobox
        self.is_external_script = True
        self.add_button.config(state=tk.NORMAL)
        self.run_button.config(state=tk.NORMAL)

    def run_exe(self):
        # This will replace the direct action of select_and_run_exe
        self.run_and_embed_exe(self.target_file)

    def run_and_embed_exe(self, filepath):
        """Runs and embeds the specified EXE file."""
        if not filepath or not os.path.exists(filepath):
            messagebox.showerror("錯誤", "檔案不存在或未選擇。", parent=self.frame)
            return

        self.file_label.config(text=f"執行中: {os.path.basename(filepath)}")
        self.on_destroy(cleanup_resources=False) # Clean up previous instance

        try:
            pre_existing_windows = self._get_all_visible_windows()
            self.process = subprocess.Popen([filepath])
            self.master.after(500, self.find_and_embed_window, pre_existing_windows)
        except Exception as e:
            messagebox.showerror("執行錯誤", f"無法執行檔案: {e}", parent=self.frame)
            self.file_label.config(text=f"錯誤: {e}")
            self.process = None
            self.run_button.config(state=tk.NORMAL if self.target_file else tk.DISABLED)

    def _get_all_visible_windows(self):
        """Returns a set of handles for all visible, top-level windows."""
        hwnds = set()
        def callback(hwnd, lParam):
            if user32.IsWindowVisible(hwnd) and not user32.GetParent(hwnd):
                hwnds.add(hwnd)
            return True
        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return hwnds

    def find_and_embed_window(self, pre_existing_windows, retries=25):
        """Finds a new window that wasn't in the pre_existing_windows set."""
        if self.process and self.process.poll() is not None:
            self.file_label.config(text=f"錯誤: 應用程式意外終止")
            self.on_destroy()
            return

        if retries <= 0:
            self.file_label.config(text=f"錯誤: 找不到新的GUI視窗")
            self.on_destroy()
            return

        new_windows = self._get_all_visible_windows() - pre_existing_windows
        if new_windows:
            self.embedded_hwnd = new_windows.pop()
            self._embed_window(self.embedded_hwnd)
            self.shared_state.log(f"Found and embedded new window: {self.embedded_hwnd}")
        else:
            self.master.after(200, self.find_and_embed_window, pre_existing_windows, retries - 1)

    def _embed_window(self, hwnd):
        """Embed window, get its size, and configure the scrollable area."""
        container_id = self.embed_target_frame.winfo_id()
        user32.SetParent(hwnd, container_id)
        
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        
        # Get the embedded window's original size
        rect = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            width = rect.right - rect.left
            height = rect.bottom - rect.top

            # Set the container frame to this size
            self.embed_target_frame.config(width=width, height=height)
            
            # Update the canvas scrollregion
            self.canvas.config(scrollregion=self.canvas.bbox("all"))

            # Move the window to the top-left of the container
            user32.MoveWindow(self.embedded_hwnd, 0, 0, width, height, True)

    def on_destroy(self, cleanup_resources=True):
        """Cleanup function to be called when the module is closed."""
        self.shared_state.log(f"ExeEmbedderModule '{self.module_name}' is being destroyed.")
        if self.embedded_hwnd:
            # Attempt to gracefully close the embedded window by sending WM_CLOSE
            user32.PostMessageW(self.embedded_hwnd, WM_CLOSE, 0, 0)
            self.embedded_hwnd = None

        if self.process:
            try:
                # Wait a moment for the process to terminate gracefully
                self.process.wait(timeout=0.5)
            except (subprocess.TimeoutExpired, Exception):
                # If it's still running, force terminate
                if self.process.poll() is None:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=0.5)
                        if self.process.poll() is None:
                            self.process.kill()
                    except Exception as e:
                        self.shared_state.log(f"Error forcefully terminating process: {e}")
            self.process = None
        
        if hasattr(self, 'file_label'):
            self.file_label.config(text="尚未選擇檔案")
        
        # Reset scroll region when clearing
        self.embed_target_frame.config(width=1, height=1)
        self.canvas.config(scrollregion="0 0 1 1")

        if cleanup_resources:
            super().on_destroy()

