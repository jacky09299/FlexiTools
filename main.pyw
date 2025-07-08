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
    shared_state_instance = SharedState() # Create SharedState instance EARLIER

    splash = None
    update_splash_progress = None
    try:
        from splash_ui import create_splash_screen
        # Pass shared_state_instance to create_splash_screen
        splash, update_splash_progress_func = create_splash_screen(root, shared_state_instance)
        if update_splash_progress_func:
            shared_state_instance.set_splash_progress_callback(update_splash_progress_func)
            shared_state_instance.update_splash_progress(10) # Initial progress
    except Exception as e:
        print(f"Failed to create splash screen: {e}")
        # If splash fails, we don't want to hang, just continue.
        # The 'splash' variable will be None.
        root.deiconify() # Show the main window if splash fails

    # --- Main App Initialization ---
    shared_state_instance.log("Configuring styles...")
    configure_styles()
    shared_state_instance.update_splash_progress(30)
    time.sleep(0.1) # Simulate work

    shared_state_instance.log("Applying post-creation styles...")
    apply_post_creation_styles(root)
    shared_state_instance.update_splash_progress(50)
    time.sleep(0.1) # Simulate work

    # Pass shared_state_instance to ModularGUI
    shared_state_instance.log("Initializing UI...")
    app = ModularGUI(root, shared_state_instance)
    # Progress will be further updated within ModularGUI's __init__
    shared_state_instance.update_splash_progress(70) # Progress after ModularGUI init starts

    # --- Cleanup ---
    if splash:
        shared_state_instance.update_splash_progress(100) # Final progress
        time.sleep(0.2) # Give a moment to see 100%
        splash.destroy()
        shared_state_instance.clear_splash_log_callback()
        shared_state_instance.clear_splash_progress_callback() # Clear progress callback

    # The ModularGUI class handles making the main window visible.
    root.mainloop()

