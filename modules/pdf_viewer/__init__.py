import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pypdfium2 as pdfium
from PIL import Image, ImageTk
import io
from ui import Module

class PDFViewerModule(Module):
    def __init__(self, master, shared_state, module_name="PDF Viewer", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        Image.MAX_IMAGE_PIXELS = None
        # PDF 相關變數
        self.pdf_document = None
        self.current_page = 0
        self.current_image = None
        self.current_pil_image = None
        self.zoom_level = 1.0
        
        # 當前檢視狀態
        # current_crop_rect 存儲為 (left, top, right, bottom) 在頁面原始座標系(Top-Left origin)中的位置
        # 雖然PDF通常是Bottom-Left，但為了方便與Canvas交互，我們在邏輯層統一使用Top-Left，
        # 只在傳給 pypdfium2 render 時轉換為 Bottom-Left。
        self.current_crop_rect = None 
        
        # 歷史記錄用於回上一步
        self.view_history = []
        self.max_history = 100  # 最多保存100個歷史記錄
        
        # 框選相關變數
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        self.is_selecting = False
        
        self.initial_fit_done = False  # 標記是否已做初始縮放
        
        self.setup_ui()

    def setup_ui(self):
        # The main frame for the module's content, child of self.frame
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 工具列
        toolbar = ttk.Frame(content_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # 按鈕
        self.btn_open = ttk.Button(toolbar, text="選擇 PDF", command=self.open_pdf)
        self.btn_open.pack(side=tk.LEFT, padx=(0, 5))
        self.btn_prev = ttk.Button(toolbar, text="上一頁", command=self.prev_page)
        self.btn_prev.pack(side=tk.LEFT, padx=(0, 5))
        self.btn_next = ttk.Button(toolbar, text="下一頁", command=self.next_page)
        self.btn_next.pack(side=tk.LEFT, padx=(0, 5))
        
        # 歷史檢視按鈕組
        history_frame = ttk.Frame(toolbar)
        history_frame.pack(side=tk.LEFT, padx=(10, 5))
        
        self.btn_back1 = ttk.Button(history_frame, text="回上1個", command=lambda: self.go_back_steps(1))
        self.btn_back1.pack(side=tk.LEFT, padx=(0, 2))
        self.btn_back2 = ttk.Button(history_frame, text="回上2個", command=lambda: self.go_back_steps(2))
        self.btn_back2.pack(side=tk.LEFT, padx=(0, 2))
        self.btn_back3 = ttk.Button(history_frame, text="回上3個", command=lambda: self.go_back_steps(3))
        self.btn_back3.pack(side=tk.LEFT, padx=(0, 2))
        self.btn_back4 = ttk.Button(history_frame, text="回上4個", command=lambda: self.go_back_steps(4))
        self.btn_back4.pack(side=tk.LEFT, padx=(0, 2))
        
        self.btn_reset = ttk.Button(toolbar, text="重置檢視", command=self.reset_view)
        self.btn_reset.pack(side=tk.LEFT, padx=(0, 5))
        
        # 頁碼顯示
        self.page_label = ttk.Label(toolbar, text="頁碼: 0/0")
        self.page_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 縮放顯示
        self.zoom_label = ttk.Label(toolbar, text="縮放: 100%")
        self.zoom_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 歷史記錄顯示
        self.history_label = ttk.Label(toolbar, text="歷史: 0")
        self.history_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 畫布框架（帶滾動條）
        canvas_frame = ttk.Frame(content_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 創建畫布和滾動條
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 放置滾動條和畫布
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 綁定滑鼠事件
        self.canvas.bind("<Button-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        
        # 狀態列
        self.status_bar = ttk.Label(content_frame, text="請選擇 PDF 檔案", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

        self.update_language()

    def update_language(self):
        super().update_language()
        if not getattr(self, 'btn_open', None): return

        self.btn_open.config(text=self.tr("module_pdfviewer_btn_open", "Open PDF"))
        self.btn_prev.config(text=self.tr("module_pdfviewer_btn_prev", "Prev Page"))
        self.btn_next.config(text=self.tr("module_pdfviewer_btn_next", "Next Page"))

        self.btn_back1.config(text=self.tr("module_pdfviewer_btn_back1", "Back 1"))
        self.btn_back2.config(text=self.tr("module_pdfviewer_btn_back2", "Back 2"))
        self.btn_back3.config(text=self.tr("module_pdfviewer_btn_back3", "Back 3"))
        self.btn_back4.config(text=self.tr("module_pdfviewer_btn_back4", "Back 4"))
        self.btn_reset.config(text=self.tr("module_pdfviewer_btn_reset", "Reset View"))

        if "請選擇 PDF 檔案" in self.status_bar.cget("text") or "Please select" in self.status_bar.cget("text"):
             self.status_bar.config(text=self.tr("module_pdfviewer_status_select_pdf", "Please select a PDF file"))

    def fit_page_to_canvas(self):
        """計算讓整個PDF頁面剛好顯示於畫布的縮放比例"""
        if not self.pdf_document:
            return 1.0
        page = self.pdf_document[self.current_page]
        page_width, page_height = page.get_size()
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        # 若canvas尚未顯示，預設1200x800
        if canvas_width < 10 or canvas_height < 10:
            canvas_width = 1200
            canvas_height = 800
        zoom_x = canvas_width / page_width
        zoom_y = canvas_height / page_height
        return min(zoom_x, zoom_y) * 0.95

    def open_pdf(self):
        """開啟 PDF 檔案"""
        title = self.tr("module_pdfviewer_dialog_select", "Select PDF File")
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.pdf_document = pdfium.PdfDocument(file_path)
                self.current_page = 0
                self.current_crop_rect = None
                self.view_history = []
                self.initial_fit_done = False
                # 先顯示頁面，等canvas顯示後再fit
                self.display_page()
                self.frame.after(100, self.initial_fit_page)
                self.update_history_label()
                self.status_bar.config(text=f"已開啟: {file_path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法開啟 PDF 檔案: {str(e)}")
    
    def initial_fit_page(self):
        """初次載入PDF時自動縮放整個頁面"""
        if not self.pdf_document or self.initial_fit_done:
            return
        self.zoom_level = self.fit_page_to_canvas()
        self.initial_fit_done = True
        self.display_page()

    def display_page(self, crop_rect=None):
        """顯示頁面"""
        if not self.pdf_document:
            return
        
        try:
            page = self.pdf_document[self.current_page]
            page_width, page_height = page.get_size()
            
            # 更新當前裁切區域
            if crop_rect is not None:
                self.current_crop_rect = crop_rect
            
            # 準備渲染參數
            render_kwargs = {
                'scale': self.zoom_level,
            }
            
            # 如果有裁切區域，設定 crop 參數
            # pypdfium2 crop 格式: (left_margin, bottom_margin, right_margin, top_margin)
            # self.current_crop_rect 格式: (left, top, right, bottom) (Top-Left origin)
            if self.current_crop_rect:
                l, t, r, b = self.current_crop_rect
                
                # 確保數值在有效範圍內 (Clamp to page dimensions)
                epsilon = 0.1
                l = max(0, min(l, page_width - epsilon))
                r = max(0, min(r, page_width))
                t = max(0, min(t, page_height - epsilon))
                b = max(0, min(b, page_height))
                
                # 確保寬高為正
                if r <= l: r = l + 1
                if b <= t: b = t + 1
                
                # 計算 Margins
                margin_left = l
                margin_bottom = page_height - b
                margin_right = page_width - r
                margin_top = t
                
                # 確保 margins 不為負
                margin_left = max(0, margin_left)
                margin_bottom = max(0, margin_bottom)
                margin_right = max(0, margin_right)
                margin_top = max(0, margin_top)
                
                render_kwargs['crop'] = (margin_left, margin_bottom, margin_right, margin_top)
            
            # 渲染頁面
            try:
                bitmap = page.render(**render_kwargs)
            except Exception as e:
                if "Crop exceeds page dimensions" in str(e):
                    print(f"Crop failed: {render_kwargs.get('crop')}, Page: {page_width}x{page_height}")
                    # 嘗試移除 crop 參數並重新渲染 (Fallback to full page)
                    if 'crop' in render_kwargs:
                        del render_kwargs['crop']
                    bitmap = page.render(**render_kwargs)
                else:
                    raise e

            self.current_pil_image = bitmap.to_pil()
            self.current_image = ImageTk.PhotoImage(self.current_pil_image)
            
            # 清除畫布並顯示圖片
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)
            
            # 更新畫布捲動區域
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # 重置滾動位置到左上角
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)
            
            # 更新標籤
            total_pages = len(self.pdf_document)
            self.page_label.config(text=f"頁碼: {self.current_page + 1}/{total_pages}")
            self.zoom_label.config(text=f"縮放: {int(self.zoom_level * 100)}%")
            self.update_history_label()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("錯誤", f"無法顯示頁面: {str(e)}")
    
    def prev_page(self):
        """上一頁"""
        if self.pdf_document and self.current_page > 0:
            self.current_page -= 1
            self.zoom_level = 1.0
            self.current_crop_rect = None
            self.display_page()
    
    def next_page(self):
        """下一頁"""
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.zoom_level = 1.0
            self.current_crop_rect = None
            self.display_page()

    def start_selection(self, event):
        """開始框選"""
        if not self.current_image:
            return
            
        # 記錄起始位置
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.is_selecting = True
        
        # 刪除之前的選擇框
        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def update_selection(self, event):
        """更新框選"""
        if not self.is_selecting:
            return
            
        # 獲取當前位置
        current_x = self.canvas.canvasx(event.x)
        current_y = self.canvas.canvasy(event.y)
        
        # 刪除之前的選擇框
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        # 繪製新的選擇框
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, current_x, current_y,
            outline='red', width=2
        )
    
    def end_selection(self, event):
        """結束框選並放大選中區域"""
        if not self.is_selecting:
            return
            
        self.is_selecting = False
        
        # 獲取結束位置
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        
        # 計算選擇區域 (Canvas 座標)
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        # 檢查選擇區域是否足夠大
        if x2 - x1 < 10 or y2 - y1 < 10:
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            return
        
        # 保存當前檢視狀態到歷史記錄
        self.view_history.append({
            'page': self.current_page,
            'zoom': self.zoom_level,
            'crop': self.current_crop_rect
        })
        
        # 獲取頁面資訊
        page = self.pdf_document[self.current_page]
        page_width, page_height = page.get_size()
        
        # 計算當前顯示區域的寬高 (PDF 單位)
        if self.current_crop_rect:
            # current_crop_rect 是 (l, t, r, b)
            display_width = self.current_crop_rect[2] - self.current_crop_rect[0]
            display_height = self.current_crop_rect[3] - self.current_crop_rect[1]
            display_offset_x = self.current_crop_rect[0]
            display_offset_y = self.current_crop_rect[1]
        else:
            display_width = page_width
            display_height = page_height
            display_offset_x = 0
            display_offset_y = 0
        
        # 計算畫布座標在當前顯示區域中的比例
        # self.current_pil_image.width 是當前渲染出來的圖片寬度
        canvas_to_display_scale_x = display_width / self.current_pil_image.width
        canvas_to_display_scale_y = display_height / self.current_pil_image.height
        
        # 將畫布座標轉換為相對於當前顯示區域的位移
        rel_x1 = x1 * canvas_to_display_scale_x
        rel_y1 = y1 * canvas_to_display_scale_y
        rel_x2 = x2 * canvas_to_display_scale_x
        rel_y2 = y2 * canvas_to_display_scale_y
        
        # 計算新的絕對座標 (PDF 單位, Top-Left origin)
        new_x1 = display_offset_x + rel_x1
        new_y1 = display_offset_y + rel_y1
        new_x2 = display_offset_x + rel_x2
        new_y2 = display_offset_y + rel_y2
        
        # 創建新的裁切矩形 (l, t, r, b)
        new_crop_rect = (new_x1, new_y1, new_x2, new_y2)
        
        # 計算裁剪區域的實際尺寸
        crop_width = new_x2 - new_x1
        crop_height = new_y2 - new_y1
        
        # 調整縮放等級以讓裁剪區域佔滿視窗
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        zoom_x = canvas_width / crop_width
        zoom_y = canvas_height / crop_height
        
        # 選擇較小的縮放比例以確保完整顯示，並留一點邊距
        self.zoom_level = min(zoom_x, zoom_y) * 0.95
        
        # 顯示放大的區域
        self.display_page(new_crop_rect)
        
        # 刪除選擇框
        if self.rect_id:
            self.canvas.delete(self.rect_id)
    
    def add_to_history(self):
        """將當前狀態添加到歷史記錄"""
        current_state = {
            'page': self.current_page,
            'zoom': self.zoom_level,
            'crop': self.current_crop_rect
        }
        
        self.view_history.append(current_state)
        
        # 限制歷史記錄數量
        if len(self.view_history) > self.max_history:
            self.view_history.pop(0)  # 移除最舊的記錄
        
        self.update_history_label()
    
    def update_history_label(self):
        """更新歷史記錄顯示"""
        history_count = len(self.view_history)
        self.history_label.config(text=f"歷史: {history_count}")
    
    def go_back_steps(self, steps):
        """回到前N個檢視"""
        history_len = len(self.view_history)
        if history_len < steps:
            messagebox.showinfo("提示", f"歷史記錄不足，只有 {history_len} 個記錄")
            return

        # pop N-1 次，然後用最後一個狀態恢復
        for _ in range(steps - 1):
            if self.view_history:
                self.view_history.pop()

        # 恢復到最新的狀態
        if self.view_history:
            last_view = self.view_history.pop()
            self.current_page = last_view['page']
            self.zoom_level = last_view['zoom']
            self.current_crop_rect = last_view['crop']
        else:
            # 如果沒有歷史記錄了，重置到初始狀態
            self.zoom_level = 1.0
            self.current_crop_rect = None

        self.display_page()
    
    def go_back(self):
        """回到上一個檢視（保持向後兼容）"""
        self.go_back_steps(1)
    
    def reset_view(self):
        """重置檢視"""
        if self.pdf_document:
            # 保存當前狀態到歷史記錄（如果有變化的話）
            if self.zoom_level != 1.0 or self.current_crop_rect is not None:
                self.view_history.append({
                    'page': self.current_page,
                    'zoom': self.zoom_level,
                    'crop': self.current_crop_rect
                })
            
            self.zoom_level = 1.0
            self.current_crop_rect = None
            self.display_page()
    
    def key_pressed(self, event):
        """鍵盤事件處理"""
        if event.keysym == "Left":
            self.prev_page()
        elif event.keysym == "Right":
            self.next_page()
        elif event.keysym == "BackSpace":
            self.go_back()
        elif event.keysym == "Escape":
            self.reset_view()