
import tkinter as tk
from tkinter import ttk

# --- 定義顏色方案 (專業現代化風格) ---
COLOR_PRIMARY_BG = "#1E1E1E"       # 主視窗背景 (非常深的灰，接近黑)
COLOR_MODULE_BG = "#2D2D2D"        # 模組背景 (深灰)
COLOR_MODULE_FG = "#E0E0E0"        # 模組前景/文字 (淺灰)
COLOR_ACCENT = "#007ACC"           # 強調色 (專業深藍)
COLOR_ACCENT_HOVER = "#005F99"     # 強調色 (懸停時更深)
COLOR_ENTRY_BG = "#3A3A3A"         # 輸入框背景 (中等深灰)
COLOR_BORDER = "#444444"           # 邊框顏色 (中等深灰)

# 自訂視窗元素顏色
COLOR_WINDOW_BORDER = "#000000"    # 最外層視窗邊框 (純黑，提供清晰邊界)
COLOR_TITLE_BAR_BG = "#1E1E1E"     # 標題欄背景 (與主背景一致)
COLOR_MENU_BAR_BG = "#252526"      # 選單欄背景 (比主背景稍亮，增加層次感)
COLOR_MENU_BUTTON_FG = "#E0E0E0"   # 選單按鈕文字顏色
COLOR_MENU_BUTTON_ACTIVE_BG = "#007ACC" # 選單按鈕懸停背景 (強調色)

# 滾動條顏色
COLOR_SCROLLBAR_TROUGH = "#2D2D2D" # 滾動條軌道 (與模組背景一致)
COLOR_SCROLLBAR_THUMB = "#555555"  # 滾動條滑塊 (中灰)
COLOR_SCROLLBAR_ACTIVE_THUMB = "#777777" # 滾動條滑塊懸停 (淺灰)

# --- 字體定義 ---
FONT_FAMILY = "Segoe UI"
FONT_NORMAL = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_HEADER = (FONT_FAMILY, 12, "bold")

def configure_styles():
    """
    配置 ttk 小工具的自定義樣式，具有科技感。
    """
    style = ttk.Style()

    # --- 使用一個可高度自訂的主題，如 'clam' 或 'alt' ---
    style.theme_use('clam')

    # --- 1. 主視窗樣式 ---
    style.configure('Main.TFrame', background=COLOR_PRIMARY_BG)

    # --- 2. 模組樣式 (與主視窗分離) ---
    style.configure('Module.TFrame',
                    background=COLOR_MODULE_BG,
                    borderwidth=1,
                    relief='solid',
                    bordercolor=COLOR_BORDER) # 新增 bordercolor

    style.configure('Module.TLabel',
                    background=COLOR_MODULE_BG,
                    foreground=COLOR_MODULE_FG,
                    font=FONT_NORMAL)

    style.configure('Module.Header.TLabel',
                    background=COLOR_MODULE_BG,
                    foreground=COLOR_ACCENT,
                    font=FONT_HEADER)

    style.configure('DragHandle.TFrame', background=COLOR_MODULE_BG)

    # --- 按鈕樣式 ---
    # Style for title bar buttons
    style.configure('TitleBar.TButton',
                    background=COLOR_MODULE_BG,
                    foreground=COLOR_MODULE_FG,
                    font=FONT_NORMAL,
                    borderwidth=0,
                    relief='flat',
                    padding=(2, 2))

    style.map('TitleBar.TButton',
              background=[('!active', COLOR_MODULE_BG),
                          ('pressed', COLOR_ACCENT_HOVER),
                          ('active', COLOR_ACCENT_HOVER)],
              foreground=[('active', '#FFFFFF')])

    style.configure('Module.TButton',
                    background=COLOR_ACCENT,
                    foreground="#FFFFFF", # 按鈕文字改為白色
                    font=FONT_BOLD,
                    borderwidth=0,
                    relief='flat',
                    padding=(10, 5))

    style.map('Module.TButton',
              background=[('!active', COLOR_ACCENT),
                          ('pressed', COLOR_ACCENT_HOVER),
                          ('active', COLOR_ACCENT_HOVER)],
              relief=[('pressed', 'sunken')])

    # --- 輸入框樣式 ---
    style.configure('Module.TEntry',
                    fieldbackground=COLOR_ENTRY_BG,
                    foreground=COLOR_MODULE_FG,
                    insertcolor=COLOR_MODULE_FG, # 游標顏色
                    borderwidth=1,
                    relief='flat',
                    bordercolor=COLOR_BORDER) # 新增 bordercolor

    # --- 下拉選單樣式 ---
    style.configure('Module.TCombobox',
                    background=COLOR_ENTRY_BG,
                    fieldbackground=COLOR_ENTRY_BG,
                    foreground=COLOR_MODULE_FG,
                    arrowcolor=COLOR_ACCENT,
                    selectbackground=COLOR_ENTRY_BG,
                    selectforeground=COLOR_MODULE_FG,
                    borderwidth=0,
                    relief='flat',
                    bordercolor=COLOR_BORDER) # 新增 bordercolor

    # --- 滾動條樣式 ---
    style.configure('TScrollbar',
                    troughcolor=COLOR_SCROLLBAR_TROUGH,
                    background=COLOR_SCROLLBAR_THUMB,
                    bordercolor=COLOR_SCROLLBAR_TROUGH,
                    arrowcolor=COLOR_MODULE_FG,
                    relief='flat') # 滾動條樣式更簡潔
    style.map('TScrollbar',
              background=[('active', COLOR_SCROLLBAR_ACTIVE_THUMB)])

    # --- Sizegrip 樣式 ---
    style.configure('TSizegrip',
                    background=COLOR_MODULE_BG)

def apply_post_creation_styles(root):
    """套用需要在 root 視窗建立後才能設定的樣式。"""
    style = ttk.Style()
    
    # 設定 Combobox 下拉選單的樣式
    root.option_add('*TCombobox*Listbox.background', COLOR_ENTRY_BG)
    root.option_add('*TCombobox*Listbox.foreground', COLOR_MODULE_FG)
    root.option_add('*TCombobox*Listbox.selectBackground', COLOR_ACCENT)
    root.option_add('*TCombobox*Listbox.selectForeground', "#FFFFFF") # 選中項文字改為白色
