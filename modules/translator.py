import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import pyperclip
from concurrent.futures import ThreadPoolExecutor
import keyboard
import requests
import win32gui
import win32api
import win32con

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
        
    def show_translation(self, original_text, translated_text, x, y):
        # 如果已有浮動視窗，先關閉
        if self.window:
            self.close()
            
        # 創建新的浮動視窗
        self.window = tk.Toplevel(self.parent.root)
        self.window.title("")
        
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
        title_label = tk.Label(title_bar, text="翻譯結果 (可拖曳)", 
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
            
        original_label = tk.Label(frame, text=f"原文: {display_original}", 
                                bg='#34495e', fg='#bdc3c7', 
                                font=('Microsoft YaHei', 9), 
                                wraplength=400, justify='left')
        original_label.pack(fill='x', padx=5, pady=(5, 2))
        self.bind_mouse_events(original_label)
        
        # 翻譯結果標籤（較大字體）
        translated_label = tk.Label(frame, text=translated_text, 
                                  bg='#2c3e50', fg='#ecf0f1', 
                                  font=('Microsoft YaHei', 11, 'bold'), 
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
        
        # 更新視窗邊界
        self.update_window_bounds()
        
        # 延遲啟動點擊監聽（給拖曳操作一些時間）
        self.window.after(100, self.start_click_monitoring)
    
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
            self.click_monitor_thread = threading.Thread(target=self.monitor_mouse_clicks, daemon=True)
            self.click_monitor_thread.start()

    def monitor_mouse_clicks(self):
        while self.is_monitoring_clicks:
            if win32api.GetKeyState(win32con.VK_LBUTTON) < 0: # Left button pressed
                if self.window and not self.dragging and not self.mouse_inside_window:
                    x, y = win32gui.GetCursorPos()
                    is_outside = (x < self.window_bounds['x1'] or x > self.window_bounds['x2'] or
                                  y < self.window_bounds['y1'] or y > self.window_bounds['y2'])
                    if is_outside:
                        self.parent.root.after(0, self.close)
                        break 
            time.sleep(0.1) # Polling interval

    def close(self):
        self.is_monitoring_clicks = False
        if self.click_monitor_thread and self.click_monitor_thread.is_alive():
            self.click_monitor_thread.join(timeout=0.2)
        
        if self.window:
            self.window.destroy()
            self.window = None

class RealtimeTranslator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("即時翻譯工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 設定翻譯器
        self.is_translating = False
        self.last_text = ""
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.keyboard_listener = None
        
        # 浮動視窗
        self.floating_window = FloatingWindow(self)
        
        # 建立介面
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 標題
        title_label = ttk.Label(main_frame, text="即時翻譯工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # 左右分割
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=1, column=0, sticky="ns", padx=(0, 10))
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=1, column=1, sticky="nsew")

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # --- 左側控制面板 ---
        controls_frame = ttk.LabelFrame(left_panel, text="控制項")
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.columnconfigure(0, weight=1)

        # 目標語言選擇
        ttk.Label(controls_frame, text="翻譯目標語言:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(controls_frame, textvariable=self.language_var)
        
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
        
        # 顯示模式選擇
        mode_frame = ttk.Frame(controls_frame)
        mode_frame.grid(row=2, column=0, pady=10, sticky="ew", padx=5)
        
        ttk.Label(mode_frame, text="顯示模式:").pack(side="left")
        
        self.display_mode = tk.StringVar(value="floating")
        ttk.Radiobutton(mode_frame, text="浮動", variable=self.display_mode, 
                       value="floating").pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="主視窗", variable=self.display_mode, 
                       value="main").pack(side="left")
        
        # 啟用/停用翻譯按鈕
        self.toggle_btn = ttk.Button(controls_frame, text="啟用翻譯", command=self.toggle_translation)
        self.toggle_btn.grid(row=3, column=0, pady=10)
        
        # 狀態標籤
        self.status_label = ttk.Label(controls_frame, text="翻譯未啟用", foreground="red", anchor="center")
        self.status_label.grid(row=4, column=0, pady=5, sticky="ew")
        
        # 手動輸入框
        manual_input_frame = ttk.LabelFrame(left_panel, text="手動翻譯")
        manual_input_frame.grid(row=1, column=0, sticky="ew")
        manual_input_frame.columnconfigure(0, weight=1)

        self.input_text = tk.Text(manual_input_frame, height=5, wrap=tk.WORD)
        self.input_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        manual_btn = ttk.Button(manual_input_frame, text="翻譯輸入的文字", command=self.manual_translate)
        manual_btn.grid(row=1, column=0, pady=(0, 5))

        # --- 右側面板 ---
        right_panel.rowconfigure(1, weight=1)
        right_panel.columnconfigure(0, weight=1)

        # 說明文字
        instruction_frame = ttk.LabelFrame(right_panel, text="使用說明")
        instruction_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        instruction_text = """1. 點擊「啟用翻譯」
2. 在任何地方反白文字後按 Ctrl+C
3. 翻譯結果會根據顯示模式呈現

顯示模式:
- 浮動: 結果在滑鼠旁彈出
- 主視窗: 結果顯示於此處"""
        
        instruction_label = ttk.Label(instruction_frame, text=instruction_text, justify=tk.LEFT)
        instruction_label.pack(anchor="w", padx=5, pady=5)

        # 翻譯結果顯示區域
        result_frame = ttk.LabelFrame(right_panel, text="翻譯紀錄")
        result_frame.grid(row=1, column=0, sticky="nsew")
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        self.result_text = tk.Text(result_frame, wrap=tk.WORD, font=("Arial", 10))
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)

        self.result_text.grid(row=0, column=0, sticky="nsew", padx=(5,0), pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0,5), pady=5)
        
    def toggle_translation(self):
        if not self.is_translating:
            self.start_translation()
        else:
            self.stop_translation()
    
    def start_translation(self):
        self.is_translating = True
        self.toggle_btn.config(text="停用翻譯")
        self.status_label.config(text="翻譯已啟用 - 反白文字後按Ctrl+C", foreground="green")
        
        # 啟動剪貼簿監控
        self.monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        self.monitor_thread.start()
        
        # 啟動鍵盤監控（監控Ctrl+C）
        try:
            self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
            self.keyboard_listener.start()
        except Exception as e:
            print(f"無法啟動鍵盤監控: {e}")
        
    def stop_translation(self):
        self.is_translating = False
        self.toggle_btn.config(text="啟用翻譯")
        self.status_label.config(text="翻譯未啟用", foreground="red")
        
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
                        print(f"文字過長 ({len(current_text)} 字元)，跳過翻譯")
                        self.last_text = current_text
                        continue
                    
                    # 更寬鬆的過濾條件
                    # 只排除明顯的檔案路徑和單純的URL
                    if (current_text.startswith(('http://', 'https://', 'file://', 'ftp://')) and 
                        len(current_text.split()) == 1):  # 單一URL
                        print("跳過URL內容")
                        self.last_text = current_text
                        continue
                    
                    # 排除Windows檔案路徑（含有:\\ 且沒有空格的）
                    if (':\\' in current_text and ' ' not in current_text and 
                        len(current_text.split('\n')) == 1):
                        print("跳過檔案路徑")
                        self.last_text = current_text
                        continue
                    
                    print(f"準備翻譯: {current_text[:50]}..." if len(current_text) > 50 else f"準備翻譯: {current_text}")
                    self.last_text = current_text
                    
                    # 在背景執行翻譯
                    self.executor.submit(self.translate_text, current_text)
                    
                time.sleep(0.3)  # 檢查間隔
                
            except Exception as e:
                print(f"監控剪貼簿時發生錯誤: {e}")
                time.sleep(1)
    
    def manual_translate(self):
        # 手動翻譯輸入框中的文字
        text = self.input_text.get("1.0", tk.END).strip()
        if text:
            self.executor.submit(self.translate_text, text)
            self.input_text.delete("1.0", tk.END)  # 清空輸入框
    
    def translate_text(self, text):
        try:
            print(f"開始翻譯文字 ({len(text)} 字元)")
            
            # 獲取目標語言代碼
            selected_lang = self.language_var.get()
            target_lang = self.lang_code_map.get(selected_lang, 'zh-tw')
            
            # 對於較長的文字，分段處理
            if len(text) > 2000:
                # 將長文字分段翻譯
                segments = self.split_text_into_segments(text, 2000)
                translated_segments = []
                
                for i, segment in enumerate(segments):
                    print(f"翻譯第 {i+1}/{len(segments)} 段")
                    translated_segment = self.translate_segment(segment, target_lang)
                    if translated_segment.startswith("翻譯失敗"):
                        # 如果某段翻譯失敗，直接返回錯誤
                        self.root.after(0, self.update_result, text, translated_segment, "error")
                        return
                    translated_segments.append(translated_segment)
                    time.sleep(0.5)  # 避免API請求過於頻繁
                
                translated_text = ' '.join(translated_segments)
            else:
                # 短文字直接翻譯
                translated_text = self.translate_segment(text, target_lang)
            
            print(f"翻譯完成: {translated_text[:50]}...")
            
            # 在主執行緒更新UI
            self.root.after(0, self.update_result, text, translated_text, target_lang)
            
        except Exception as e:
            error_msg = f"翻譯錯誤: {str(e)}"
            print(f"翻譯出錯: {text[:50]}... -> {error_msg}")
            self.root.after(0, self.update_result, text, error_msg, "error")
    
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
        # 根據顯示模式決定如何顯示結果
        if self.display_mode.get() == "floating" and target_lang != "error":
            # 浮動視窗模式
            x, y = win32gui.GetCursorPos()
            self.floating_window.show_translation(original_text, translated_text, x + 10, y + 10)
        
        # 同時也在主視窗顯示（作為備份記錄）
        timestamp = time.strftime("%H:%M:%S")
        result_info = f"[{timestamp}] 翻譯至 {self.language_var.get()}\n"
        result_info += f"原文: {original_text}\n"
        result_info += f"譯文: {translated_text}\n"
        result_info += "-" * 50 + "\n"
        
        self.result_text.insert(tk.END, result_info)
        self.result_text.see(tk.END)  # 捲動到最新內容
        
        # 將翻譯結果複製到剪貼簿
        if target_lang != "error":
            # 暫時停止監控以避免無窮迴圈
            temp_last = self.last_text
            pyperclip.copy(translated_text)
            time.sleep(0.1)
            self.last_text = translated_text  # 避免翻譯結果被再次翻譯
    
    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
    
    def on_closing(self):
        self.is_translating = False
        if hasattr(self, 'monitor_thread') and self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.floating_window.close()
        self.executor.shutdown(wait=False)
        self.root.destroy()

if __name__ == "__main__":
    # 檢查必要套件
    required_packages = {
        'pyperclip': 'pyperclip',
        'keyboard': 'keyboard',
        'requests': 'requests',
        'win32gui': 'pywin32'
    }
    
    missing_packages = []
    for package, install_name in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(install_name)
    
    if missing_packages:
        print("請安裝以下必要套件:")
        for package in missing_packages:
            print(f"pip install {package}")
        print("\n完整安裝指令:")
        print("pip install pyperclip keyboard requests pywin32")
        input("安裝完成後按 Enter 繼續...")
    
    try:
        app = RealtimeTranslator()
        app.run()
    except Exception as e:
        print(f"程式執行錯誤: {e}")
        input("按 Enter 結束...")