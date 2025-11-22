import tkinter as tk
from tkinter import ttk
import psutil
import logging
# Assuming main.py (and thus the Module class definition) is in the parent directory
# This import works when loaded by main.py
from main import Module

class SystemInfoModule(Module):
    def __init__(self, master, shared_state, module_name="SystemInfo", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.cpu_label = None
        self.mem_label = None
        self.lbl_cpu_title = None
        self.lbl_mem_title = None
        self.after_id = None
        # Try to install psutil if not already present.
        try:
            import psutil
        except ImportError:
            self.shared_state.log("psutil not found. Attempting to install.", level=logging.WARNING)
            try:
                import subprocess
                import sys
                # Ensure pip is available and use it to install psutil
                subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
                self.shared_state.log("psutil installed successfully.", level=logging.INFO)
            except Exception as e:
                self.shared_state.log(f"Failed to install psutil: {e}", level=logging.ERROR)
                # UI will show error or no data if psutil isn't available.

        self.create_ui()
        self.update_language()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        cpu_frame = ttk.Frame(content_frame)
        cpu_frame.pack(fill=tk.X)
        self.lbl_cpu_title = ttk.Label(cpu_frame, text="CPU Usage:")
        self.lbl_cpu_title.pack(side=tk.LEFT, padx=(0, 5))
        self.cpu_label = ttk.Label(cpu_frame, text="N/A", font=("Helvetica", 10))
        self.cpu_label.pack(side=tk.LEFT)

        mem_frame = ttk.Frame(content_frame)
        mem_frame.pack(fill=tk.X, pady=(5,0))
        self.lbl_mem_title = ttk.Label(mem_frame, text="Memory Usage:")
        self.lbl_mem_title.pack(side=tk.LEFT, padx=(0, 5))
        self.mem_label = ttk.Label(mem_frame, text="N/A", font=("Helvetica", 10))
        self.mem_label.pack(side=tk.LEFT)

        try:
            import psutil # Check again if it became available
            self.update_info()
            self.shared_state.log(f"UI for {self.module_name} created and initial info displayed.", level=logging.INFO)
        except ImportError:
            err_msg = self.tr("module_systeminfo_err_psutil", "Error: psutil not loaded")
            self.cpu_label.config(text=err_msg)
            self.mem_label.config(text=err_msg)
            self.shared_state.log("psutil still not available after attempted install. SystemInfo module may not function.", level=logging.ERROR)

    def update_language(self):
        super().update_language()
        if not getattr(self, 'lbl_cpu_title', None): return

        self.lbl_cpu_title.config(text=self.tr("module_systeminfo_lbl_cpu", "CPU Usage:"))
        self.lbl_mem_title.config(text=self.tr("module_systeminfo_lbl_mem", "Memory Usage:"))

        # If error state, translate error message
        if self.cpu_label.cget("text").startswith("Error"):
             err_msg = self.tr("module_systeminfo_err_psutil", "Error: psutil not loaded")
             self.cpu_label.config(text=err_msg)
             self.mem_label.config(text=err_msg)

    def update_info(self):
        try:
            import psutil # Ensure it's available for updates
            cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
            mem_percent = psutil.virtual_memory().percent

            if self.cpu_label and self.cpu_label.winfo_exists():
                self.cpu_label.config(text=f"{cpu_percent:.1f}%")

            if self.mem_label and self.mem_label.winfo_exists():
                self.mem_label.config(text=f"{mem_percent:.1f}%")

            # Schedule next update
            self.after_id = self.frame.after(2500, self.update_info) # Update every 2.5 seconds
        except ImportError:
            if self.cpu_label and self.cpu_label.winfo_exists():
                self.cpu_label.config(text="Error")
            if self.mem_label and self.mem_label.winfo_exists():
                self.mem_label.config(text="Error")
            self.shared_state.log("psutil not found during update_info. Stopping updates.", level=logging.ERROR)
            if self.after_id:
                self.frame.after_cancel(self.after_id)
                self.after_id = None
        except Exception as e:
            self.shared_state.log(f"Error updating system info: {e}", level=logging.ERROR)
            if self.cpu_label and self.cpu_label.winfo_exists():
                self.cpu_label.config(text="Error")
            if self.mem_label and self.mem_label.winfo_exists():
                self.mem_label.config(text="Error")
            # Stop updates on other errors too to prevent spamming logs
            if self.after_id:
                self.frame.after_cancel(self.after_id)
                self.after_id = None


    def on_destroy(self):
        if self.after_id:
            self.frame.after_cancel(self.after_id)
            self.after_id = None
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance and timer destroyed.")