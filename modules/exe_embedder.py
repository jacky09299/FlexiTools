
import tkinter as tk
from tkinter import ttk, filedialog
import subprocess
import ctypes
from ctypes import wintypes
import time
import os
from main import Module

# Ctypes definitions for WinAPI
user32 = ctypes.windll.user32
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

class ExeEmbedderModule(Module):
    """
    A module to select and embed an external EXE's GUI into a tkinter frame.
    Uses a more robust window-finding mechanism that doesn't rely on PID.
    """
    def __init__(self, master, shared_state, module_name="ExeEmbedder", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"ExeEmbedderModule '{self.module_name}' initialized.")
        
        self.process = None
        self.embedded_hwnd = None
        self.selected_file_path = tk.StringVar()

        self.create_ui()

    def create_ui(self):
        """Create the user interface for the EXE embedder module."""
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill="x", pady=5, padx=5)

        select_button = ttk.Button(control_frame, text="選擇EXE檔案", command=self.select_and_run_exe)
        select_button.pack(side="left", padx=(0, 10))

        path_label = ttk.Label(control_frame, textvariable=self.selected_file_path)
        path_label.pack(side="left", fill="x", expand=True)

        self.embed_container = tk.Frame(self.frame, bg="black", relief="sunken", borderwidth=1)
        self.embed_container.pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def _get_all_visible_windows(self):
        """Returns a set of handles for all visible, top-level windows."""
        hwnds = set()
        def callback(hwnd, lParam):
            if user32.IsWindowVisible(hwnd) and not user32.GetParent(hwnd):
                hwnds.add(hwnd)
            return True
        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return hwnds

    def select_and_run_exe(self):
        """Opens a file dialog, gets current windows, and then runs the EXE."""
        filepath = filedialog.askopenfilename(
            title="選擇一個可執行的檔案",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
            parent=self.frame
        )
        if not filepath:
            return

        self.selected_file_path.set(f"執行中: {os.path.basename(filepath)}")
        self.on_destroy(cleanup_resources=False)

        try:
            # Get all window handles *before* starting the new process
            pre_existing_windows = self._get_all_visible_windows()
            
            self.process = subprocess.Popen([filepath])
            
            # Start searching for the *new* window that will appear
            self.master.after(500, self.find_and_embed_window, pre_existing_windows)

        except Exception as e:
            self.selected_file_path.set(f"錯誤: {e}")
            self.process = None

    def find_and_embed_window(self, pre_existing_windows, retries=25):
        """
        Finds a new window that wasn't in the pre_existing_windows set.
        """
        if self.process and self.process.poll() is not None: # Process has terminated
            self.selected_file_path.set(f"錯誤: 應用程式意外終止")
            self.on_destroy()
            return

        if retries <= 0:
            self.selected_file_path.set(f"錯誤: 找不到新的GUI視窗")
            self.on_destroy()
            return

        current_windows = self._get_all_visible_windows()
        new_windows = current_windows - pre_existing_windows

        if new_windows:
            # Found one or more new windows, assume the first one is our target
            self.embedded_hwnd = new_windows.pop()
            self._embed_window(self.embedded_hwnd)
            self.shared_state.log(f"Found and embedded new window: {self.embedded_hwnd}")
        else:
            # If not found, try again after a short delay
            self.master.after(200, self.find_and_embed_window, pre_existing_windows, retries - 1)

    def _embed_window(self, hwnd):
        """The core embedding logic: SetParent and resize."""
        container_id = self.embed_container.winfo_id()
        user32.SetParent(hwnd, container_id)
        
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        
        self.embed_container.bind("<Configure>", self.on_resize)
        self.embed_container.event_generate("<Configure>")

    def on_resize(self, event):
        """Resizes the embedded window to match the container frame."""
        if not self.embedded_hwnd:
            return
        user32.MoveWindow(self.embedded_hwnd, 0, 0, event.width, event.height, True)

    def on_destroy(self, cleanup_resources=True):
        """Cleanup function to be called when the module is closed."""
        self.shared_state.log(f"ExeEmbedderModule '{self.module_name}' is being destroyed.")
        if self.embedded_hwnd:
            user32.SetParent(self.embedded_hwnd, 0)
        self.embedded_hwnd = None

        if self.process:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=0.5)
                    if self.process.poll() is None:
                        self.process.kill()
            except Exception as e:
                self.shared_state.log(f"Error terminating process: {e}")
            self.process = None
        
        self.selected_file_path.set("")
        
        if cleanup_resources:
            super().on_destroy()

