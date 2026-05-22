import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import sys
import pyperclip
from concurrent.futures import ThreadPoolExecutor
import requests
from ui import Module

# Platform-specific imports
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import win32gui
        import win32api
        import win32con
    except ImportError:
        win32gui = None
        win32api = None
        win32con = None
else:
    win32gui = None
    win32api = None
    win32con = None

try:
    import keyboard as keyboard_lib
except ImportError:
    keyboard_lib = None


def get_cursor_position(tk_widget=None):
    """Cross-platform cursor position helper."""
    if IS_WINDOWS and win32gui:
        return win32gui.GetCursorPos()
    elif tk_widget:
        return tk_widget.winfo_pointerxy()
    return (0, 0)

class FloatingWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.click_monitor_thread = None
        self.is_monitoring_clicks = False
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.click_timer = None
        self.mouse_inside_window = False
        
    def show_translation(self, original_text, translated_text, x, y, font_size):
        # 如果已有浮動視窗，先關閉
        if self.window:
            self.close()
            
        # 創建新的浮動視窗
        self.window = tk.Toplevel(self.parent.frame)
        self.window.withdraw()  # 先隱藏視窗，防止閃爍
        self.window.title(self.parent.tr("module_translator_win_title", "Translation Result (Draggable)"))
        
        # 設定視窗屬性：無邊框、置頂
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.95)
        
        # 創建內容框架
        frame = tk.Frame(self.window, bg='#2c3e50', bd=2, relief='solid')
        frame.pack(fill='both', expand=True, padx=2, pady=2)
        
        # 創建標題列（用於拖曳）
        title_bar = tk.Frame(frame, bg='#34495e', height=25)
        title_bar.pack(fill='x', padx=0, pady=0)
        title_bar.pack_propagate(False)
        
        # 標題文字
        title_label = tk.Label(title_bar, text=self.parent.tr("module_translator_win_title", "Translation Result (Draggable)"),
                             bg='#34495e', fg='#ecf0f1', 
                             font=('Microsoft YaHei', 9))
        title_label.pack(side='left', padx=5, pady=2)
        
        # 關閉按鈕
        close_btn = tk.Button(title_bar, text="×", command=self.close,
                            bg='#e74c3c', fg='white', font=('Arial', 10, 'bold'),
                            bd=0, width=3, height=1)
        close_btn.pack(side='right', padx=2, pady=2)
        
        # 綁定拖曳事件到標題列和標題文字
        title_bar.bind('<Button-1>', self.start_drag)
        title_bar.bind('<B1-Motion>', self.on_drag)
        title_bar.bind('<ButtonRelease-1>', self.stop_drag)
        title_label.bind('<Button-1>', self.start_drag)
        title_label.bind('<B1-Motion>', self.on_drag)
        title_label.bind('<ButtonRelease-1>', self.stop_drag)
        
        # 綁定滑鼠進入/離開事件到整個視窗
        self.bind_mouse_events(frame)
        self.bind_mouse_events(title_bar)
        self.bind_mouse_events(title_label)
        
        # 原文標籤（較小字體）
        if len(original_text) > 50:
            display_original = original_text[:50] + "..."
        else:
            display_original = original_text
            
        original_label = tk.Label(frame, text=f"Original: {display_original}",
                                bg='#34495e', fg='#bdc3c7', 
                                font=('Microsoft YaHei', 9), 
                                wraplength=400, justify='left')
        original_label.pack(fill='x', padx=5, pady=(5, 2))
        self.bind_mouse_events(original_label)
        
        # 翻譯結果標籤（較大字體）
        translated_label = tk.Label(frame, text=translated_text, 
                                  bg='#2c3e50', fg='#ecf0f1', 
                                  font=('Microsoft YaHei', font_size, 'bold'), 
                                  wraplength=400, justify='left')
        translated_label.pack(fill='x', padx=5, pady=(2, 5))
        self.bind_mouse_events(translated_label)
        
        # 更新視窗以獲取實際大小
        self.window.update_idletasks()
        
        # 計算視窗位置，確保不超出螢幕邊界
        window_width = self.window.winfo_reqwidth()
        window_height = self.window.winfo_reqheight()
        
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # 調整位置以避免超出螢幕
        if x + window_width > screen_width:
            x = screen_width - window_width - 10
        if y + window_height > screen_height:
            y = y - window_height - 20
            
        if x < 0:
            x = 10
        if y < 0:
            y = 10
            
        # 設定視窗位置
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 顯示視窗
        self.window.deiconify()
        
        # 更新視窗邊界
        self.update_window_bounds()
        
        # 延遲啟動點擊監聽（給拖曳操作一些時間）
        self.window.after(100, self.start_click_monitoring)
        
        # Linux: 需強制焦點才能收到 FocusOut 事件
        if not IS_WINDOWS:
            self.window.focus_force()
    
    def bind_mouse_events(self, widget):
        """為控件綁定滑鼠進入/離開事件"""
        widget.bind('<Enter>', self.on_mouse_enter)
        widget.bind('<Leave>', self.on_mouse_leave)
    
    def on_mouse_enter(self, event):
        """滑鼠進入視窗"""
        self.mouse_inside_window = True
    
    def on_mouse_leave(self, event):
        """滑鼠離開視窗"""
        if not self.dragging:
            self.mouse_inside_window = False
    
    def start_drag(self, event):
        """開始拖曳"""
        self.dragging = True
        self.mouse_inside_window = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        
    def on_drag(self, event):
        """拖曳過程中"""
        if self.dragging and self.window:
            current_x = self.window.winfo_x()
            current_y = self.window.winfo_y()
            new_x = current_x + (event.x_root - self.drag_start_x)
            new_y = current_y + (event.y_root - self.drag_start_y)
            
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            window_width = self.window.winfo_width()
            window_height = self.window.winfo_height()
            
            new_x = max(0, min(new_x, screen_width - window_width))
            new_y = max(0, min(new_y, screen_height - window_height))
            
            self.window.geometry(f"+{new_x}+{new_y}")
            self.update_window_bounds()
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
    
    def stop_drag(self, event):
        """停止拖曳"""
        self.dragging = False
        self.window.after(100, lambda: setattr(self, 'mouse_inside_window', False))

    def update_window_bounds(self):
        """更新視窗邊界用於點擊檢測"""
        if self.window:
            x = self.window.winfo_x()
            y = self.window.winfo_y()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            self.window_bounds = {'x1': x, 'y1': y, 'x2': x + width, 'y2': y + height}

    def start_click_monitoring(self):
        if not self.is_monitoring_clicks:
            self.is_monitoring_clicks = True
            if IS_WINDOWS and win32api and win32con:
                # Windows: use win32api polling
                self.click_monitor_thread = threading.Thread(target=self.monitor_mouse_clicks_win32, daemon=True)
                self.click_monitor_thread.start()
            else:
                # Linux/macOS: bind a global click handler via tkinter
                self._setup_linux_click_monitoring()

    def _setup_linux_click_monitoring(self):
        """Use tkinter's focus/event mechanisms for click-outside detection on Linux."""
        if self.window:
            # When the floating window loses focus, close it
            self.window.bind('<FocusOut>', self._on_focus_out_linux)
            # Also set up a periodic check
            self._linux_click_poll()

    def _on_focus_out_linux(self, event):
        """Close floating window when it loses focus (Linux)."""
        # FocusOut could be triggered by children widgets, so check if the focus really left the window
        # We also delay the check to bridge short focus transitions (e.g. during dragging start)
        if self.window and not self.dragging:
            self.parent.frame.after(100, self._check_and_close_linux)

    def _check_and_close_linux(self):
        """Delayed check to avoid closing during drag operations."""
        if self.window and not self.dragging and not self.mouse_inside_window:
            self.close()

    def _linux_click_poll(self):
        """Periodic polling for focus loss on Linux as a backup for FocusOut."""
        if not self.is_monitoring_clicks or not self.window:
            return
        
        try:
            # Check if focus is outside our window and its children
            current_focus = self.window.focus_get()
            
            # If current_focus is None, focus is on another application
            # If current_focus is not None and not a child of self.window, focus moved to main window
            is_focus_lost = (current_focus is None)
            
            if is_focus_lost and not self.dragging and not self.mouse_inside_window:
                # Add a small counter/delay to ignore transient focus loss
                if not hasattr(self, '_focus_lost_count'):
                    self._focus_lost_count = 0
                self._focus_lost_count += 1
                if self._focus_lost_count > 2: # ~600ms of focus loss
                    self.close()
                    return
            else:
                self._focus_lost_count = 0
                
        except Exception:
            pass
            
        if self.window:
            self.window.after(300, self._linux_click_poll)

    def monitor_mouse_clicks_win32(self):
        """Windows-specific mouse click monitoring using win32api."""
        while self.is_monitoring_clicks:
            if win32api.GetKeyState(win32con.VK_LBUTTON) < 0:  # Left button pressed
                if self.window and not self.dragging and not self.mouse_inside_window:
                    x, y = win32gui.GetCursorPos()
                    is_outside = (x < self.window_bounds['x1'] or x > self.window_bounds['x2'] or
                                  y < self.window_bounds['y1'] or y > self.window_bounds['y2'])
                    if is_outside:
                        self.parent.frame.after(0, self.close)
                        break
            time.sleep(0.1)  # Polling interval

    def close(self):
        self.is_monitoring_clicks = False
        if self.click_monitor_thread and self.click_monitor_thread.is_alive():
            self.click_monitor_thread.join(timeout=0.2)
        
        if self.window:
            self.window.destroy()
            self.window = None

class TranslatorModule(Module):
    def __init__(self, master, shared_state, module_name="Translator", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        
        # 設定翻譯器
        self.is_translating = False
        self.last_text = ""
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.keyboard_listener = None
        
        # Initialize widget references
        self.controls_frame = None
        self.lbl_target = None
        self.remove_newline_check = None
        self.mode_frame = None
        self.lbl_mode = None
        self.rb_float = None
        self.rb_main = None
        self.font_size_label = None
        self.lbl_font_size = None
        self.toggle_btn = None
        self.status_label = None
        self.manual_input_frame = None
        self.manual_btn = None
        self.instruction_frame = None
        self.instruction_label = None
        self.result_frame = None

        # 浮動視窗
        self.floating_window = FloatingWindow(self)
        self.font_size = tk.IntVar(value=11)
        
        # 建立介面
        self.create_ui()
        self.update_language()
        
    def create_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # 左右分割
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        # --- 左側控制面板 ---
        self.controls_frame = ttk.LabelFrame(left_panel, text="Controls")
        self.controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.controls_frame.columnconfigure(0, weight=1)

        # 目標語言選擇
        self.lbl_target = ttk.Label(self.controls_frame, text="Target Language:")
        self.lbl_target.grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(self.controls_frame, textvariable=self.language_var)
        
        # 常用語言清單
        common_languages = {
            'zh-tw': '繁體中文',
            'zh-cn': '簡體中文', 
            'en': 'English',
            'ja': '日本語',
            'ko': '한국어',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch',
            'it': 'Italiano',
            'pt': 'Português',
            'ru': 'Русский',
            'ar': 'العربية',
            'th': 'ไทย',
            'vi': 'Tiếng Việt'
        }
        
        self.language_combo['values'] = list(common_languages.values())
        self.language_combo.current(0)  # 預設選擇繁體中文
        self.language_combo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # 語言代碼對應
        self.lang_code_map = {v: k for k, v in common_languages.items()}
        
        # 移除換行勾選框
        self.remove_newline_var = tk.BooleanVar(value=True)
        self.remove_newline_check = ttk.Checkbutton(self.controls_frame,
                                                    text="Remove newlines",
                                                    variable=self.remove_newline_var)
        self.remove_newline_check.grid(row=2, column=0, sticky=tk.W, padx=5, pady=(5,0))
        
        # 顯示模式選擇
        self.mode_frame = ttk.Frame(self.controls_frame)
        self.mode_frame.grid(row=3, column=0, pady=10, sticky="ew", padx=5)
        
        self.lbl_mode = ttk.Label(self.mode_frame, text="Display Mode:")
        self.lbl_mode.pack(side="left")
        
        self.display_mode = tk.StringVar(value="floating")
        self.rb_float = ttk.Radiobutton(self.mode_frame, text="Float", variable=self.display_mode,
                       value="floating")
        self.rb_float.pack(side="left", padx=5)
        self.rb_main = ttk.Radiobutton(self.mode_frame, text="Main Window", variable=self.display_mode,
                       value="main")
        self.rb_main.pack(side="left")

        # 浮動視窗字體大小
        font_size_frame = ttk.Frame(self.controls_frame)
        font_size_frame.grid(row=4, column=0, pady=5, sticky="ew", padx=5)
        self.lbl_font_size = ttk.Label(font_size_frame, text="Floating Font:")
        self.lbl_font_size.pack(side="left")
        self.font_size_scale = ttk.Scale(font_size_frame, from_=8, to=50, orient=tk.HORIZONTAL, variable=self.font_size, command=self.update_font_label)
        self.font_size_scale.pack(side="left", expand=True, fill="x", padx=5)
        self.font_size_label = ttk.Label(font_size_frame, text=f"{self.font_size.get()}pt")
        self.font_size_label.pack(side="left")
        
        # 啟用/停用翻譯按鈕
        self.toggle_btn = ttk.Button(self.controls_frame, text="Enable Translate", command=self.toggle_translation)
        self.toggle_btn.grid(row=5, column=0, pady=10)
        
        # 狀態標籤
        self.status_label = ttk.Label(self.controls_frame, text="Disabled", foreground="red", anchor="center")
        self.status_label.grid(row=6, column=0, pady=5, sticky="ew")
        
        # 手動輸入框
        self.manual_input_frame = ttk.LabelFrame(left_panel, text="Manual Translate")
        self.manual_input_frame.grid(row=1, column=0, sticky="ew")
        self.manual_input_frame.columnconfigure(0, weight=1)

        self.input_text = tk.Text(self.manual_input_frame, height=5, wrap=tk.WORD)
        self.input_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.manual_btn = ttk.Button(self.manual_input_frame, text="Translate Input", command=self.manual_translate)
        self.manual_btn.grid(row=1, column=0, pady=(0, 5))

        # --- 右側面板 ---
        right_panel.rowconfigure(1, weight=1)
        right_panel.columnconfigure(0, weight=1)

        # 說明文字
        self.instruction_frame = ttk.LabelFrame(right_panel, text="Instructions")
        self.instruction_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        instruction_text = "..." # Placeholder, updated in update_language
        
        self.instruction_label = ttk.Label(self.instruction_frame, text=instruction_text, justify=tk.LEFT)
        self.instruction_label.pack(anchor="w", padx=5, pady=5)

        # 翻譯結果顯示區域
        self.result_frame = ttk.LabelFrame(right_panel, text="History")
        self.result_frame.grid(row=1, column=0, sticky="nsew")
        self.result_frame.rowconfigure(0, weight=1)
        self.result_frame.columnconfigure(0, weight=1)

        self.result_text = tk.Text(self.result_frame, wrap=tk.WORD, font=("Arial", 10))
        
        scrollbar = ttk.Scrollbar(self.result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)

        self.result_text.grid(row=0, column=0, sticky="nsew", padx=(5,0), pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0,5), pady=5)
        
    def update_language(self):
        super().update_language()
        if not getattr(self, 'controls_frame', None): return

        self.controls_frame.config(text=self.tr("module_translator_grp_controls", "Controls"))
        self.lbl_target.config(text=self.tr("module_translator_lbl_target", "Target Language:"))
        self.remove_newline_check.config(text=self.tr("module_translator_chk_remove_newline", "Remove newlines (pre-translate)"))
        self.lbl_mode.config(text=self.tr("module_translator_lbl_mode", "Display Mode:"))
        self.rb_float.config(text=self.tr("module_translator_rb_float", "Float"))
        self.rb_main.config(text=self.tr("module_translator_rb_main", "Main Window"))
        self.lbl_font_size.config(text=self.tr("module_translator_lbl_font_size", "Floating Font:"))

        if self.is_translating:
            self.toggle_btn.config(text=self.tr("module_translator_btn_toggle_off", "Disable Translate"))
            self.status_label.config(text=self.tr("module_translator_status_on", "Enabled - Highlight & Ctrl+C"))
        else:
            self.toggle_btn.config(text=self.tr("module_translator_btn_toggle_on", "Enable Translate"))
            self.status_label.config(text=self.tr("module_translator_status_off", "Disabled"))

        self.manual_input_frame.config(text=self.tr("module_translator_grp_manual", "Manual Translate"))
        self.manual_btn.config(text=self.tr("module_translator_btn_translate_manual", "Translate Input"))
        self.instruction_frame.config(text=self.tr("module_translator_grp_help", "Instructions"))
        self.instruction_label.config(text=self.tr("module_translator_help_text", "1. Click 'Enable Translate'\n2. Highlight text..."))
        self.result_frame.config(text=self.tr("module_translator_grp_history", "History"))

    def toggle_translation(self):
        if not self.is_translating:
            self.start_translation()
        else:
            self.stop_translation()
    
    def start_translation(self):
        self.is_translating = True
        self.toggle_btn.config(text=self.tr("module_translator_btn_toggle_off", "Disable Translate"))
        self.status_label.config(text=self.tr("module_translator_status_on", "Enabled - Highlight & Ctrl+C"), foreground="green")
        
        # 啟動剪貼簿監控
        self.monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        self.monitor_thread.start()
        
        # 啟動鍵盤監控（監控Ctrl+C）- optional, not critical for functionality
        if keyboard_lib:
            try:
                self.keyboard_listener = keyboard_lib.Listener(on_press=self.on_key_press)
                self.keyboard_listener.start()
            except Exception as e:
                self.shared_state.log(f"無法啟動鍵盤監控: {e}", "WARNING")
                self.keyboard_listener = None
        else:
            self.shared_state.log("Keyboard library not available, skipping keyboard monitoring.", "DEBUG")
        
    def stop_translation(self):
        self.is_translating = False
        self.toggle_btn.config(text=self.tr("module_translator_btn_toggle_on", "Enable Translate"))
        self.status_label.config(text=self.tr("module_translator_status_off", "Disabled"), foreground="red")
        
        # 停止監聽器
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            
        # 關閉浮動視窗
        self.floating_window.close()
    
    def on_key_press(self, key):
        try:
            # 檢測 Ctrl+C
            if hasattr(key, 'char') and key.char == 'c':
                pass
        except AttributeError:
            pass
    
    def monitor_clipboard(self):
        while self.is_translating:
            try:
                # 獲取剪貼簿內容
                current_text = pyperclip.paste()
                
                # 檢查是否有新的文字且不為空
                if current_text and current_text != self.last_text and len(current_text.strip()) > 0:
                    # 放寬文字長度限制，增加到5000字元
                    if len(current_text) > 5000:
                        self.shared_state.log(f"文字過長 ({len(current_text)} 字元)，跳過翻譯", "DEBUG")
                        self.last_text = current_text
                        continue
                    
                    # 更寬鬆的過濾條件
                    # 只排除明顯的檔案路徑和單純的URL
                    if (current_text.startswith(('http://', 'https://', 'file://', 'ftp://')) and 
                        len(current_text.split()) == 1):  # 單一URL
                        self.shared_state.log("跳過URL內容", "DEBUG")
                        self.last_text = current_text
                        continue
                    
                    # 排除Windows檔案路徑（含有:\\ 且沒有空格的）
                    if (':\\' in current_text and ' ' not in current_text and 
                        len(current_text.split('\n')) == 1):
                        self.shared_state.log("跳過檔案路徑", "DEBUG")
                        self.last_text = current_text
                        continue
                    
                    self.shared_state.log(f"準備翻譯: {current_text[:50]}..." if len(current_text) > 50 else f"準備翻譯: {current_text}", "DEBUG")
                    self.last_text = current_text
                    
                    # 在背景執行翻譯
                    self.executor.submit(self.translate_text, current_text)
                    
                time.sleep(0.3)  # 檢查間隔
                
            except pyperclip.PyperclipException as e:
                self.shared_state.log(f"剪貼簿機制錯誤 (Linux 建議安裝 xclip/xsel): {e}", "ERROR")
                if not hasattr(self, "_pyperclip_error_shown"):
                    self._pyperclip_error_shown = True
                    self.frame.after(0, lambda: messagebox.showerror("剪貼簿錯誤", "無法存取剪貼簿，請確保已安裝 xclip 或 xsel (例如: sudo apt install xclip)", parent=self.frame))
                self.is_translating = False # 停止監控避免無窮報錯
                self.frame.after(0, self.stop_translation)
            except Exception as e:
                self.shared_state.log(f"監控剪貼簿時發生錯誤: {e}", "ERROR")
                time.sleep(1)
    
    def manual_translate(self):
        # 手動翻譯輸入框中的文字
        text = self.input_text.get("1.0", tk.END).strip()
        if text:
            self.executor.submit(self.translate_text, text)
            self.input_text.delete("1.0", tk.END)  # 清空輸入框
    
    def translate_text(self, text):
        try:
            self.shared_state.log(f"開始翻譯文字 ({len(text)} 字元)", "DEBUG")
            
            # 檢查是否需要移除換行
            if self.remove_newline_var.get():
                text = " ".join(text.split())
            
            # 獲取目標語言代碼
            selected_lang = self.language_var.get()
            target_lang = self.lang_code_map.get(selected_lang, 'zh-tw')
            
            # 對於較長的文字，分段處理
            if len(text) > 2000:
                # 將長文字分段翻譯
                segments = self.split_text_into_segments(text, 2000)
                translated_segments = []
                
                for i, segment in enumerate(segments):
                    self.shared_state.log(f"翻譯第 {i+1}/{len(segments)} 段", "DEBUG")
                    translated_segment = self.translate_segment(segment, target_lang)
                    if translated_segment.startswith("翻譯失敗"):
                        # 如果某段翻譯失敗，直接返回錯誤
                        self.frame.after(0, self.update_result, text, translated_segment, "error")
                        return
                    translated_segments.append(translated_segment)
                    time.sleep(0.5)  # 避免API請求過於頻繁
                
                translated_text = ' '.join(translated_segments)
            else:
                # 短文字直接翻譯
                translated_text = self.translate_segment(text, target_lang)
            
            self.shared_state.log(f"翻譯完成: {translated_text[:50]}...", "DEBUG")
            
            # 在主執行緒更新UI
            self.frame.after(0, self.update_result, text, translated_text, target_lang)
            
        except Exception as e:
            error_msg = f"翻譯錯誤: {str(e)}"
            self.shared_state.log(f"翻譯出錯: {text[:50]}... -> {error_msg}", "ERROR")
            self.frame.after(0, self.update_result, text, error_msg, "error")
    
    def split_text_into_segments(self, text, max_length):
        """將長文字分割成較短的段落"""
        segments = []
        sentences = text.replace('\n', ' ').split('.')
        current_segment = ""
        
        for sentence in sentences:
            if len(current_segment + sentence + '.') <= max_length:
                current_segment += sentence + '.'
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence + '.'
        
        if current_segment:
            segments.append(current_segment.strip())
        
        return segments if segments else [text]
    
    def translate_segment(self, text, target_lang):
        """翻譯單一文字段落"""
        try:
            # 建構翻譯請求
            base_url = "https://translate.googleapis.com/translate_a/single"
            params = {
                'client': 'gtx',
                'sl': 'auto',
                'tl': target_lang,
                'dt': 't',
                'q': text
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(base_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0 and len(result[0]) > 0:
                    translated_text = ''.join([item[0] for item in result[0] if item[0]])
                    return translated_text
                else:
                    return "翻譯失敗：無法解析回應"
            else:
                return f"翻譯失敗：HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "翻譯失敗：請求超時"
        except requests.exceptions.RequestException as e:
            return f"翻譯失敗：網路錯誤 {str(e)}"
        except Exception as e:
            return f"翻譯失敗：{str(e)}"
    
    def update_result(self, original_text, translated_text, target_lang):
        # 如果勾選了移除換行，則先處理最終結果
        if self.remove_newline_var.get() and target_lang != "error":
            processed_translated_text = " ".join(translated_text.split())
        else:
            processed_translated_text = translated_text

        # 根據顯示模式決定如何顯示結果
        if self.display_mode.get() == "floating" and target_lang != "error":
            # 浮動視窗模式
            x, y = get_cursor_position(self.frame)
            font_size = self.font_size.get()
            self.floating_window.show_translation(original_text, processed_translated_text, x + 10, y + 10, font_size)
        
        # 同時也在主視窗顯示（作為備份記錄）
        timestamp = time.strftime("%H:%M:%S")
        result_info = f"[{timestamp}] -> {self.language_var.get()}\n"
        result_info += f"Src: {original_text}\n"
        result_info += f"Dst: {processed_translated_text}\n"
        result_info += "-" * 50 + "\n"
        
        self.result_text.insert(tk.END, result_info)
        self.result_text.see(tk.END)  # 捲動到最新內容
        """
        # 將翻譯結果複製到剪貼簿
        if target_lang != "error":
            # 暫時停止監控以避免無窮迴圈
            temp_last = self.last_text
            pyperclip.copy(processed_translated_text)
            time.sleep(0.1)
            self.last_text = processed_translated_text  # 避免翻譯結果被再次翻譯
        """

    def update_font_label(self, value):
        self.font_size_label.config(text=f"{float(value):.0f}pt")
        self.font_size.set(int(float(value)))
    
    def on_destroy(self):
        self.is_translating = False
        if hasattr(self, 'monitor_thread') and self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.floating_window.close()
        self.executor.shutdown(wait=False)
        super().on_destroy()