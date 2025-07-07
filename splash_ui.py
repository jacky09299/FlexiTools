import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from style_manager import COLOR_PRIMARY_BG, COLOR_ACCENT_HOVER

def create_splash_screen(root):
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)

    splash_width = 450
    splash_height = 200

    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x_cordinate = int((screen_width / 2) - (splash_width / 2))
    y_cordinate = int((screen_height / 2) - (splash_height / 2))
    splash.geometry(f"{splash_width}x{splash_height}+{x_cordinate}+{y_cordinate}")

    BG_COLOR = COLOR_PRIMARY_BG
    BORDER_COLOR = COLOR_ACCENT_HOVER

    splash.config(bg=BG_COLOR)

    container = tk.Frame(splash, bg=BG_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
    container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    img = Image.open("assets/logo.png")
    img.thumbnail((128, 128), Image.Resampling.LANCZOS)
    logo_img = ImageTk.PhotoImage(img)

    img_label = tk.Label(container, image=logo_img, bg=BG_COLOR)
    img_label.image = logo_img
    img_label.pack(side=tk.LEFT, padx=(20, 15), pady=20)

    text_frame = tk.Frame(container, bg=BG_COLOR)
    text_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, pady=10, padx=(0, 20))

    center_frame = tk.Frame(text_frame, bg=BG_COLOR)
    center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    app_name_label = tk.Label(center_frame, text="FlexiTools", font=("Segoe UI", 28, "bold"), bg=BG_COLOR, fg="white")
    app_name_label.pack(pady=(0, 5))

    status_label = tk.Label(center_frame, text="正在初始化...", font=("Segoe UI", 10), bg=BG_COLOR, fg="#cccccc")
    status_label.pack(pady=(5, 0))

    splash.update()
    return splash
