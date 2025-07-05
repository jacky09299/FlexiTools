
import tkinter as tk
from tkinter import ttk

# --- 定義顏色方案 ---
COLOR_PRIMARY_BG = "#1a1a2e"       # 主視窗背景 (深藍紫)
COLOR_MODULE_BG = "#2c3e50"        # 模組背景 (深藍灰)
COLOR_MODULE_FG = "#e0e0e0"        # 模組前景/文字 (淺灰)
COLOR_ACCENT = "#0f4c75"           # 強調色 (深藍)
COLOR_ACCENT_HOVER = "#3282b8"     # 強調色 (亮藍)
COLOR_ENTRY_BG = "#34495e"         # 輸入框背景 (較淺的藍灰)
COLOR_BORDER = "#333333"           # 邊框顏色 (深灰)

# --- 專業藝術感漸變背景 ---
COLOR_GRADIENT_START = "#1a1a2e"   # 漸變起始色 (深藍紫)
COLOR_GRADIENT_END = "#16213e"     # 漸變結束色 (更深的藍紫)

# New colors for custom window elements
COLOR_WINDOW_BORDER = "#0f0f0f"    # 最外層視窗邊框
COLOR_TITLE_BAR_BG = "#0f0f0f"     # 標題欄背景
COLOR_MENU_BAR_BG = "#222222"      # 選單欄背景
COLOR_MENU_BUTTON_FG = "#e0e0e0"   # 選單按鈕文字顏色
COLOR_MENU_BUTTON_ACTIVE_BG = "#0f4c75" # 選單按鈕懸停背景

# Scrollbar colors
COLOR_SCROLLBAR_TROUGH = "#2a2a2a" # 滾動條軌道
COLOR_SCROLLBAR_THUMB = "#555555"  # 滾動條滑塊
COLOR_SCROLLBAR_ACTIVE_THUMB = "#777777" # 滾動條滑塊懸停

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
    # 這比 'default' 或 'winnative' 提供了更多的樣式控制權
    style.theme_use('clam')

    # --- 1. 主視窗樣式 ---
    # 創建一個名為 'Main.TFrame' 的新樣式，只用於主視窗背景
    style.configure('Main.TFrame', background=COLOR_PRIMARY_BG)

    # --- 2. 模組樣式 (與主視窗分離) ---
    # 為模組內的各種小工具定義一套獨立的樣式
    style.configure('Module.TFrame',
                    background=COLOR_MODULE_BG,
                    borderwidth=1,
                    relief='solid')

    style.configure('Module.TLabel',
                    background=COLOR_MODULE_BG,
                    foreground=COLOR_MODULE_FG,
                    font=FONT_NORMAL)

    style.configure('Module.Header.TLabel',
                    background=COLOR_MODULE_BG,
                    foreground=COLOR_ACCENT,
                    font=FONT_HEADER)

    # --- 按鈕樣式 ---
    style.configure('Module.TButton',
                    background=COLOR_ACCENT,
                    foreground="#000000",
                    font=FONT_BOLD,
                    borderwidth=0,
                    relief='flat',
                    padding=(10, 5))

    # 使用 map 來定義不同狀態下的外觀 (例如滑鼠懸停)
    style.map('Module.TButton',
              background=[('!active', COLOR_ACCENT),
                          ('pressed', COLOR_ACCENT),
                          ('active', COLOR_ACCENT_HOVER)],
              relief=[('pressed', 'sunken')])

    # --- 輸入框樣式 ---
    style.configure('Module.TEntry',
                    fieldbackground=COLOR_ENTRY_BG,
                    foreground=COLOR_MODULE_FG,
                    insertcolor=COLOR_MODULE_FG, # 游標顏色
                    borderwidth=1,
                    relief='flat')

    # --- 下拉選單樣式 ---
    style.configure('Module.TCombobox',
                    background=COLOR_ENTRY_BG,
                    fieldbackground=COLOR_ENTRY_BG,
                    foreground=COLOR_MODULE_FG,
                    arrowcolor=COLOR_ACCENT,
                    selectbackground=COLOR_ENTRY_BG,
                    selectforeground=COLOR_MODULE_FG,
                    borderwidth=0,
                    relief='flat')

    # --- 滾動條樣式 ---
    style.configure('TScrollbar',
                    troughcolor=COLOR_SCROLLBAR_TROUGH,
                    background=COLOR_SCROLLBAR_THUMB,
                    bordercolor=COLOR_SCROLLBAR_TROUGH,
                    arrowcolor=COLOR_MODULE_FG)
    style.map('TScrollbar',
              background=[('active', COLOR_SCROLLBAR_ACTIVE_THUMB)])

def apply_post_creation_styles(root):
    """套用需要在 root 視窗建立後才能設定的樣式。"""
    style = ttk.Style()
    
    # 設定 Combobox 下拉選單的樣式
    # 這段代碼比較特殊，需要這樣設定才能影響到彈出的列表
    root.option_add('*TCombobox*Listbox.background', COLOR_ENTRY_BG)
    root.option_add('*TCombobox*Listbox.foreground', COLOR_MODULE_FG)
    root.option_add('*TCombobox*Listbox.selectBackground', COLOR_ACCENT)
    root.option_add('*TCombobox*Listbox.selectForeground', '#000000')
