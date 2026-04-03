import sys
import tkinter as tk

try:
    from ctypes import windll
except ImportError:
    windll = None

# Windows API Constants
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

def setup_custom_window_style(root, log_callback=None):
    """
    Applies custom borderless window styles on Windows to allow resizing
    and taskbar presence while removing the default caption bar.
    Falls back to overrideredirect(True) on non-Windows platforms.
    """
    if sys.platform == "win32" and windll:
        root.overrideredirect(False) # Ensure standard window first
        root.update_idletasks() # Ensure HWND is valid

        try:
            hwnd = windll.user32.GetParent(root.winfo_id())

            # Get current style
            style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

            # Remove caption and thick frame (borders)
            style = style & ~WS_CAPTION
            style = style & ~WS_THICKFRAME

            # Ensure minimize/maximize/sysmenu are present (for taskbar interaction)
            style = style | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU

            windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

            # Extended style for taskbar icon
            ex_style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style = ex_style | WS_EX_APPWINDOW
            ex_style = ex_style & ~WS_EX_TOOLWINDOW
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

            if log_callback:
                log_callback("Custom window style applied successfully.", "DEBUG")
        except Exception as e:
            if log_callback:
                log_callback(f"Failed to setup custom window: {e}", "ERROR")
            root.overrideredirect(True) # Fallback
    else:
        # On Linux/macOS, overrideredirect(True) causes button clicks to be unresponsive
        # because the window manager is bypassed. We skip it here and rely on the
        # custom title bar drawn in ui.py for the borderless look.
        # The window will still have a system border, but will remain interactive.
        pass


def start_drag_native(root, event, log_callback=None):
    """
    Initiates native window dragging on Windows using SendMessageW.
    Returns True if native drag was triggered, False otherwise (so caller can fallback).
    """
    if sys.platform == "win32" and windll:
        try:
            windll.user32.ReleaseCapture()
            windll.user32.SendMessageW(windll.user32.GetParent(root.winfo_id()), 0xA1, 0x2, 0) # WM_NCLBUTTONDOWN, HTCAPTION
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"Native drag failed: {e}", "WARNING")
            return False
    return False
