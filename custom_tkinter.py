import tkinter as tk
from tkinter import ttk
import os

class CustomWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # 移除系統邊框
        self.root.geometry("600x400")
        
        # 視窗狀態
        self.is_maximized = False
        self.normal_geometry = "600x400"
        
        # 拖拽和縮放變數
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_mode = None
        
        self.setup_ui()
        self.setup_bindings()
        
    def setup_ui(self):
        # 主容器
        self.main_frame = tk.Frame(self.root, bg="#2c3e50", bd=0)
        self.main_frame.pack(fill="both", expand=True)
        
        # 標題欄
        self.title_bar = tk.Frame(self.main_frame, bg="#34495e", height=35, relief="flat")
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)
        
        # 標題文字
        self.title_label = tk.Label(self.title_bar, text="自訂視窗", 
                                   bg="#34495e", fg="white", font=("Arial", 10, "bold"))
        self.title_label.pack(side="left", padx=10, pady=8)
        
        # 視窗控制按鈕容器
        self.controls_frame = tk.Frame(self.title_bar, bg="#34495e")
        self.controls_frame.pack(side="right", padx=5)
        
        # 最小化按鈕
        self.min_btn = tk.Button(self.controls_frame, text="🗕", 
                                command=self.minimize_window,
                                bg="#34495e", fg="white", relief="flat", 
                                font=("Arial", 8), width=3, height=1,
                                activebackground="#3498db", activeforeground="white")
        self.min_btn.pack(side="left", padx=2)
        
        # 最大化按鈕
        self.max_btn = tk.Button(self.controls_frame, text="🗖", 
                                command=self.toggle_maximize,
                                bg="#34495e", fg="white", relief="flat", 
                                font=("Arial", 8), width=3, height=1,
                                activebackground="#3498db", activeforeground="white")
        self.max_btn.pack(side="left", padx=2)
        
        # 關閉按鈕
        self.close_btn = tk.Button(self.controls_frame, text="🗙", 
                                  command=self.close_window,
                                  bg="#34495e", fg="white", relief="flat", 
                                  font=("Arial", 8), width=3, height=1,
                                  activebackground="#e74c3c", activeforeground="white")
        self.close_btn.pack(side="right", padx=2)
        
        # 內容區域
        self.content_frame = tk.Frame(self.main_frame, bg="#ecf0f1", bd=1, relief="flat")
        self.content_frame.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        
        # 示範內容
        self.content_label = tk.Label(self.content_frame, 
                                     text="這是自訂視窗\n\n支援功能：\n• 拖拽移動\n• 邊框縮放\n• 最小化/最大化\n• 自訂圖示",
                                     bg="#ecf0f1", fg="#2c3e50", 
                                     font=("Arial", 12), justify="center")
        self.content_label.pack(expand=True)
        
        # 狀態欄
        self.status_bar = tk.Frame(self.main_frame, bg="#34495e", height=25)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, text="就緒", 
                                    bg="#34495e", fg="white", font=("Arial", 8))
        self.status_label.pack(side="left", padx=10, pady=4)
        
    def setup_bindings(self):
        # 標題欄拖拽
        self.title_bar.bind("<Button-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<Button-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)
        
        # 視窗狀態監聽
        self.root.bind('<Map>', self.on_window_state_change)
        
        # 整個視窗的滑鼠事件
        self.root.bind("<Motion>", self.on_mouse_motion)
        self.root.bind("<Button-1>", self.on_mouse_down)
        self.root.bind("<B1-Motion>", self.on_mouse_drag)
        self.root.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # 雙擊標題欄最大化
        self.title_bar.bind("<Double-Button-1>", self.toggle_maximize)
        self.title_label.bind("<Double-Button-1>", self.toggle_maximize)
        
    def get_resize_cursor(self):
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        border_width = 8
        corner_size = 15

        # 取得滑鼠在 root 視窗內的絕對座標
        mouse_y = self.root.winfo_pointery() - self.root.winfo_rooty()
        mouse_x = self.root.winfo_pointerx() - self.root.winfo_rootx()

        # 角落判斷
        if mouse_x <= corner_size and mouse_y <= corner_size:
            return "top_left_corner", "top_left_corner"
        elif mouse_x <= corner_size and mouse_y >= height - corner_size:
            return "bottom_left_corner", "bottom_left_corner"
        elif mouse_x >= width - corner_size and mouse_y >= height - corner_size:
            return "bottom_right_corner", "bottom_right_corner"
        # 邊判斷
        elif mouse_y <= border_width:
            return "top", "top_side"
        elif mouse_y >= height - border_width:
            return "bottom", "bottom_side"
        elif mouse_x <= border_width:
            return "left", "left_side"
        elif mouse_x >= width - border_width:
            return "right", "right_side"
        else:
            return None, "arrow"

    def on_mouse_motion(self, event):
        """滑鼠移動時改變游標"""
        if self.is_maximized:
            return
        
        resize_mode, cursor = self.get_resize_cursor()
        try:
            self.root.configure(cursor=cursor)
        except:
            pass
    
    def on_mouse_down(self, event):
        """滑鼠按下"""
        if self.is_maximized:
            return
        
        self.resize_mode, _ = self.get_resize_cursor()
        if self.resize_mode:
            self.resize_start_x = event.x_root
            self.resize_start_y = event.y_root
            self.start_geometry = self.root.geometry()
    
    def on_mouse_drag(self, event):
        """滑鼠拖拽"""
        if self.is_maximized or not self.resize_mode:
            return
        
        dx = event.x_root - self.resize_start_x
        dy = event.y_root - self.resize_start_y
        
        # 解析當前幾何
        geo = self.start_geometry
        parts = geo.split('+')
        size_part = parts[0]
        width, height = map(int, size_part.split('x'))
        x = int(parts[1]) if len(parts) > 1 else 0
        y = int(parts[2]) if len(parts) > 2 else 0
        
        # 最小尺寸
        min_width, min_height = 300, 200
        
        # 根據縮放模式調整
        if self.resize_mode == "right":
            width = max(min_width, width + dx)
        elif self.resize_mode == "left":
            new_width = max(min_width, width - dx)
            x = x + (width - new_width)
            width = new_width
        elif self.resize_mode == "bottom":
            height = max(min_height, height + dy)
        elif self.resize_mode == "top":
            new_height = max(min_height, height - dy)
            y = y + (height - new_height)
            height = new_height
        elif self.resize_mode == "top_left_corner":
            # 左上角：左邊和上邊
            new_width = max(min_width, width - dx)
            new_height = max(min_height, height - dy)
            x = x + (width - new_width)
            y = y + (height - new_height)
            width = new_width
            height = new_height
        elif self.resize_mode == "bottom_left_corner":
            # 左下角：左邊和下邊
            new_width = max(min_width, width - dx)
            x = x + (width - new_width)
            width = new_width
            height = max(min_height, height + dy)
        elif self.resize_mode == "bottom_right_corner":
            # 右下角：右邊和下邊
            width = max(min_width, width + dx)
            height = max(min_height, height + dy)
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def on_mouse_up(self, event):
        """滑鼠釋放"""
        self.resize_mode = None
        self.root.configure(cursor="arrow")
    
    def start_move(self, event):
        """開始拖拽視窗"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def do_move(self, event):
        """執行拖拽視窗"""
        if self.is_maximized:
            return
        
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")
    
    def minimize_window(self):
        """最小化視窗"""
        self.root.update_idletasks()
        self.root.overrideredirect(False)
        self.root.iconify()
    
    def toggle_maximize(self, event=None):
        """切換最大化狀態"""
        if self.is_maximized:
            self.restore_window()
        else:
            self.maximize_window()
    
    def maximize_window(self):
        """最大化視窗"""
        self.normal_geometry = self.root.geometry()
        self.is_maximized = True
        self.max_btn.config(text="🗗")
        
        # 獲取螢幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 考慮工作列高度
        self.root.geometry(f"{screen_width}x{screen_height-40}+0+0")
        self.status_label.config(text="最大化")
    
    def restore_window(self):
        """還原視窗"""
        self.is_maximized = False
        self.max_btn.config(text="🗖")
        self.root.geometry(self.normal_geometry)
        self.status_label.config(text="就緒")
    
    def close_window(self):
        """關閉視窗"""
        self.root.destroy()
    
    def on_window_state_change(self, event):
        """視窗狀態改變時的處理"""
        if self.root.state() == 'normal':
            self.root.overrideredirect(True)
    
    def run(self):
        """運行視窗"""
        self.root.mainloop()

# 使用範例
if __name__ == "__main__":
    app = CustomWindow()
    app.run()