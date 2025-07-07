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
    container.pack(expand=True, fill=tk.BOTH, pady=(5, 0))  # 往上移動，原本是 pady=20

    # --- Logo with circular border ---
    logo_base_size = 90
    border_thickness = 4

    try:
        # Load and resize the logo
        img = Image.open("assets/logo.png")
        img.thumbnail((logo_base_size, logo_base_size), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(img)

        # Calculate the diagonal of the logo to determine the circle's diameter
        logo_width, logo_height = img.size
        diagonal = (logo_width**2 + logo_height**2)**0.5
        
        # The canvas should be large enough for the circle and its border
        canvas_size = int(diagonal + border_thickness)-20

        logo_canvas = tk.Canvas(
            container,
            width=canvas_size,
            height=canvas_size,
            bg=BG_COLOR,
            highlightthickness=0,
            bd=0
        )
        logo_canvas.pack(pady=(50, 5))  # 再下移logo，原本是 pady=(30, 5)

        # Place the logo in the center of the canvas
        logo_canvas.create_image(canvas_size / 2, canvas_size / 2, image=logo_img)
        logo_canvas.image = logo_img # Keep a reference

        # Draw the circular border on top of the logo, centered and smaller than the logo
        # 讓圓的直徑比 logo 小 10 像素
        circle_diameter = diagonal-11
        circle_radius = circle_diameter / 2
        center_x = canvas_size / 2
        center_y = canvas_size / 2
        """
        logo_canvas.create_oval(
            center_x - circle_radius,
            center_y - circle_radius,
            center_x + circle_radius,
            center_y + circle_radius,
            outline=LOGO_BORDER_COLOR,
            width=border_thickness
        )
        """
    except FileNotFoundError:
        # Fallback if image is not found
        logo_size = 110
        logo_canvas = tk.Canvas(
            container,
            width=logo_size + border_thickness,
            height=logo_size + border_thickness,
            bg=BG_COLOR,
            highlightthickness=0,
            bd=0
        )
        logo_canvas.pack(pady=(50, 0))  # 再下移logo，原本是 pady=(40, 0)

        logo_canvas.create_oval(
            border_thickness / 2,
            border_thickness / 2,
            logo_size + border_thickness / 2,
            logo_size + border_thickness / 2,
            outline=LOGO_BORDER_COLOR,
            width=border_thickness
        )
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
    app_name_label.pack(pady=(0, 10))  # 往上靠近 logo，原本是 pady=(0, 20)

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
    progress_bar.pack(pady=5)  # 往上靠近標題，原本是 pady=10

    # --- Status Log ---
    # Choose a monospace font available on Windows
    log_font = "Consolas" if "Consolas" in tkfont.families() else "Courier New"
    status_label = tk.Label(
        container,
        text="啟動中...",
        font=(log_font, 10),
        bg=BG_COLOR,
        fg=LOG_TEXT_COLOR
    )
    status_label.pack(pady=(2, 5))  # 往上靠近進度條，原本是 pady=(5, 10)

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