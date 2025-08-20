
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
        self.selected_file_path = tk.StringVar()

        self.create_ui()

    def create_ui(self):
        """Create the user interface, now with a scrollable area."""
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill="x", pady=5, padx=5)

        select_button = ttk.Button(control_frame, text="選擇EXE檔案", command=self.select_and_run_exe)
        select_button.pack(side="left", padx=(0, 10))

        path_label = ttk.Label(control_frame, textvariable=self.selected_file_path)
        path_label.pack(side="left", fill="x", expand=True)

        # Host frame for the canvas and scrollbars
        scroll_host_frame = ttk.Frame(self.frame, relief="sunken")
        scroll_host_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
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
            pre_existing_windows = self._get_all_visible_windows()
            self.process = subprocess.Popen([filepath])
            self.master.after(500, self.find_and_embed_window, pre_existing_windows)
        except Exception as e:
            self.selected_file_path.set(f"錯誤: {e}")
            self.process = None

    def find_and_embed_window(self, pre_existing_windows, retries=25):
        """Finds a new window that wasn't in the pre_existing_windows set."""
        if self.process and self.process.poll() is not None:
            self.selected_file_path.set(f"錯誤: 應用程式意外終止")
            self.on_destroy()
            return

        if retries <= 0:
            self.selected_file_path.set(f"錯誤: 找不到新的GUI視窗")
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
        
        self.selected_file_path.set("")
        
        # Reset scroll region when clearing
        self.embed_target_frame.config(width=1, height=1)
        self.canvas.config(scrollregion="0 0 1 1")

        if cleanup_resources:
            super().on_destroy()

