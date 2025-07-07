import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import sys
import tkinter.font as tkfont  # <-- Add this import

def create_splash_screen(root, shared_state):
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)

    # --- Style Configuration based on HTML ---
    SPLASH_WIDTH = 450
    SPLASH_HEIGHT = 350
    BG_COLOR = "#EFF2F6"  # Gradient average: between #F5F7FA and #E1E5EA
    LOGO_BORDER_COLOR = "#0078D4"
    TITLE_COLOR = "#005090"
    PROGRESS_BAR_COLOR = "#0078D4"
    PROGRESS_BG_COLOR = "#E0E0E0" # Light grey for the trough
    LOG_TEXT_COLOR = "#2E3338"

    # --- Center the window ---
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x_cordinate = int((screen_width / 2) - (SPLASH_WIDTH / 2))
    y_cordinate = int((screen_height / 2) - (SPLASH_HEIGHT / 2))
    splash.geometry(f"{SPLASH_WIDTH}x{SPLASH_HEIGHT}+{x_cordinate}+{y_cordinate}")
    splash.config(bg=BG_COLOR)

    # --- Main container ---
    container = tk.Frame(splash, bg=BG_COLOR)
    container.pack(expand=True, fill=tk.BOTH, pady=20)

    # --- Logo with circular border ---
    logo_size = 90
    border_thickness = 4
    
    # Use a Canvas for a circular border
    logo_canvas = tk.Canvas(
        container,
        width=logo_size + border_thickness,
        height=logo_size + border_thickness,
        bg=BG_COLOR,
        highlightthickness=0,
        bd=0
    )
    logo_canvas.pack(pady=(10, 15))

    # Draw the circular border
    logo_canvas.create_oval(
        border_thickness / 2,
        border_thickness / 2,
        logo_size + border_thickness / 2,
        logo_size + border_thickness / 2,
        outline=LOGO_BORDER_COLOR,
        width=border_thickness
    )

    try:
        # Load and place the logo image inside the circle
        img = Image.open("assets/logo.png")
        img.thumbnail((logo_size - 10, logo_size - 10), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(img)

        img_label = tk.Label(logo_canvas, image=logo_img, bg=BG_COLOR, bd=0)
        img_label.image = logo_img
        img_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    except FileNotFoundError:
        # Fallback if image is not found
        logo_canvas.create_text(
            (logo_size + border_thickness) / 2,
            (logo_size + border_thickness) / 2,
            text="Logo",
            font=("Segoe UI", 16),
            fill=LOGO_BORDER_COLOR
        )


    # --- Title ---
    app_name_label = tk.Label(
        container,
        text="FlexiTools",
        font=("Segoe UI", 32, "bold"),
        bg=BG_COLOR,
        fg=TITLE_COLOR
    )
    app_name_label.pack(pady=(0, 20))

    # --- Progress Bar ---
    style = ttk.Style(splash)
    style.theme_use('clam')
    style.configure(
        "Splash.Horizontal.TProgressbar",
        troughcolor=PROGRESS_BG_COLOR,
        background=PROGRESS_BAR_COLOR,
        thickness=16,
        borderwidth=0,
    )
    
    progress_bar = ttk.Progressbar(
        container,
        orient="horizontal",
        length=300,
        mode="determinate",
        style="Splash.Horizontal.TProgressbar"
    )
    progress_bar.pack(pady=10)

    # --- Status Log ---
    # Choose a monospace font available on Windows
    log_font = "Consolas" if "Consolas" in tkfont.families() else "Courier New"
    status_label = tk.Label(
        container,
        text="啟動中...",
        font=(log_font, 12),
        bg=BG_COLOR,
        fg=LOG_TEXT_COLOR
    )
    status_label.pack(pady=(5, 10))

    # --- Update Functions ---
    def update_splash_status(message: str):
        if not status_label.winfo_exists():
            return
        max_chars = 50
        display_message = (message[:max_chars-3] + "...") if len(message) > max_chars else message
        status_label.config(text=display_message)
        splash.update_idletasks()

    def update_splash_progress(value: int):
        if not progress_bar.winfo_exists():
            return
        progress_bar['value'] = value
        splash.update_idletasks()

    shared_state.set_splash_log_callback(update_splash_status)
    
    splash.update()
    return splash, update_splash_progress