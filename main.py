import sys
import os
# from ctypes import windll # Moved platform-specific import
# Check if the application is running in a bundled environment (PyInstaller)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Change the current working directory to the one containing the executable
    os.chdir(sys._MEIPASS)
import time
import tkinter as tk
from tkinter import ttk
# import tkinter.simpledialog and tkinter.messagebox are now in ui.py
# import importlib.util # Moved to ui.py as it's used by discover_modules
# import random # Not used directly in main.py after refactor
from shared_state import SharedState
from style_manager import (
    configure_styles, apply_post_creation_styles,
    COLOR_PRIMARY_BG, # Used by splash
    # COLOR_WINDOW_BORDER, COLOR_TITLE_BAR_BG, COLOR_MENU_BAR_BG, # Moved to ui.py
    # COLOR_MENU_BUTTON_FG, COLOR_MENU_BUTTON_ACTIVE_BG, # Moved to ui.py
    COLOR_ACCENT_HOVER # Used by splash
)
# import logging # Moved to ui.py
# import json # Moved to ui.py
# import threading # Moved to ui.py
# import tempfile # Moved to ui.py
# import subprocess # Moved to ui.py
import os # For PID and path manipulation (os.getpid, os.path.join etc.) - Still needed for splash assets
# sys is already imported

# Attempt to import update_manager and its components - This can remain if main.py needs it directly
# or if the splash/init phase uses it. For now, ui.py also has its own import.
# Consider if only one place should "own" update_manager or if both modules can import it.
# For now, let's keep it here as well, assuming main.py might have reasons.
try:
    import update_manager
except ImportError:
    print("ERROR: update_manager.py not found in main.py. Update functionality may be affected.")
    print(f"Current sys.path in main.py: {sys.path}")
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

# Import the ModularGUI class from ui.py
from ui import ModularGUI, Module
# Module class is defined and used within ui.py, no need to import it directly in main.py

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
    shared_state_instance = SharedState() # Create SharedState instance
    configure_styles()
    apply_post_creation_styles(root)
    # Pass shared_state_instance to ModularGUI
    app = ModularGUI(root, shared_state_instance)

    # --- Cleanup ---
    if splash:
        splash.destroy()

    # The ModularGUI class handles making the main window visible.
    root.mainloop()
    if splash:
        splash.destroy()

    # The ModularGUI class handles making the main window visible.
    root.mainloop()

