import tkinter as tk
from tkinter import ttk, messagebox
from main import Module
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

__version__ = "1.1.0"

# --- 支援中文設定 ---
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'Droid Sans Fallback', 'AR PL UMing TW', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'Microsoft JhengHei', 'SimHei', 'PingFang HK', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

class LatexViewerModule(Module):
    def __init__(self, master, shared_state, module_name="LaTeX Viewer", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        
        self.input_font_size = 14
        self.output_font_size = 24
        self.render_timer = None
        
        self.create_ui()
        self.update_language()

    def has_chinese(self, text):
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def render_latex(self, event=None):
        latex_text = self.text_input.get("1.0", "end-1c")
        if not latex_text.strip():
            self.ax.clear()
            self.ax.axis("off")
            self.canvas.draw()
            return
        
        if not self.has_chinese(latex_text) and '$' not in latex_text and '\\begin' not in latex_text:
            display_text = f"${latex_text.strip()}$"
        else:
            display_text = latex_text

        self.ax.clear()
        self.ax.axis("off")
        try:
            self.ax.text(0.01, 0.99, display_text, size=self.output_font_size, ha="left", va="top", multialignment="left")
            self.canvas.draw()
        except Exception as e:
            self.ax.clear()
            self.ax.axis("off")
            error_msg = self.tr("latex_viewer_error", "語法錯誤\n(提示: Matplotlib 不支援在 $...$ 內寫中文，\n中文字請寫在 $ 符號外面)")
            self.ax.text(0.01, 0.99, error_msg, color="red", size=max(12, self.output_font_size - 6), ha="left", va="top")
            self.canvas.draw()

    def select_all(self, event):
        self.text_input.tag_add(tk.SEL, "1.0", tk.END)
        self.text_input.mark_set(tk.INSERT, "1.0")
        self.text_input.see(tk.INSERT)
        return 'break'

    def on_paste(self, event):
        try:
            if self.text_input.tag_ranges(tk.SEL):
                self.text_input.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass

    def clear_text(self):
        self.text_input.delete("1.0", tk.END)
        self.render_latex()

    def auto_fix(self):
        import re
        text = self.text_input.get("1.0", "end-1c")
        # 尋找包含 \ 或 ^ 或 _ 或 = 的 [ ... ] 並替換為 \[ ... \]
        text = re.sub(r'\[([^\]]*(\\|_|\^|=)[^\]]*)\]', r'\\[\1\\]', text)
        # 尋找包含 \ 的 ( ... ) 並替換為 \( ... \)
        text = re.sub(r'\(([^)]*\\[^)]*)\)', r'\\(\1\\)', text)
        
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", text)
        self.render_latex()

    def open_web_version(self):
        import webbrowser
        import urllib.parse
        import os
        
        current_text = self.text_input.get("1.0", "end-1c")
        encoded_text = urllib.parse.quote(current_text)
        html_path = os.path.join(os.path.dirname(__file__), "latex_viewer.html")
        url = f"file://{html_path}#{encoded_text}"
        webbrowser.open(url)

    def change_in_font(self, delta):
        self.input_font_size = max(8, self.input_font_size + delta)
        self.text_input.config(font=("Consolas", self.input_font_size))

    def change_out_font(self, delta):
        self.output_font_size = max(8, self.output_font_size + delta)
        self.render_latex()

    def on_key_release(self, event):
        if self.render_timer is not None:
            self.frame.after_cancel(self.render_timer)
        self.render_timer = self.frame.after(400, self.render_latex)

    def create_ui(self):
        paned_window = tk.PanedWindow(self.frame, orient=tk.VERTICAL, sashwidth=8, bg="#cccccc")
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ----------------- 輸出區塊 (上方) -----------------
        output_frame = ttk.Frame(paned_window)
        paned_window.add(output_frame, stretch="always")

        out_toolbar = ttk.Frame(output_frame)
        out_toolbar.pack(fill=tk.X, pady=(0, 2))
        self.lbl_output = ttk.Label(out_toolbar, font=("Arial", 12, "bold"))
        self.lbl_output.pack(side=tk.LEFT)
        
        self.btn_out_plus = tk.Button(out_toolbar, text="+", command=lambda: self.change_out_font(2), width=3, bg="#e6f2ff")
        self.btn_out_plus.pack(side=tk.RIGHT, padx=2)
        self.btn_out_minus = tk.Button(out_toolbar, text="-", command=lambda: self.change_out_font(-2), width=3, bg="#e6f2ff")
        self.btn_out_minus.pack(side=tk.RIGHT, padx=2)
        self.lbl_out_font = ttk.Label(out_toolbar, text="")
        self.lbl_out_font.pack(side=tk.RIGHT, padx=5)

        self.fig = plt.figure(figsize=(20, 10))
        self.fig.patch.set_facecolor('#ffffff') 
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.axis("off")

        output_canvas_widget = tk.Canvas(output_frame, bg="white")
        output_vbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=output_canvas_widget.yview)
        output_hbar = ttk.Scrollbar(output_frame, orient=tk.HORIZONTAL, command=output_canvas_widget.xview)
        output_canvas_widget.configure(yscrollcommand=output_vbar.set, xscrollcommand=output_hbar.set)

        output_vbar.pack(side=tk.RIGHT, fill=tk.Y)
        output_hbar.pack(side=tk.BOTTOM, fill=tk.X)
        output_canvas_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=output_canvas_widget)
        mpl_widget = self.canvas.get_tk_widget()
        output_canvas_widget.create_window((0, 0), window=mpl_widget, anchor="nw")
        output_canvas_widget.configure(scrollregion=(0, 0, 20 * self.fig.dpi, 10 * self.fig.dpi))

        # ----------------- 輸入區塊 (下方) -----------------
        input_frame = ttk.Frame(paned_window)
        paned_window.add(input_frame, stretch="always")

        toolbar_frame = ttk.Frame(input_frame)
        toolbar_frame.pack(fill=tk.X, pady=(5, 5))

        self.lbl_input = ttk.Label(toolbar_frame, font=("Arial", 12, "bold"))
        self.lbl_input.pack(side=tk.LEFT)
        
        self.btn_clear = tk.Button(toolbar_frame, command=self.clear_text, bg="#ffcccc", width=10)
        self.btn_clear.pack(side=tk.RIGHT, padx=2)
        
        self.btn_autofix = tk.Button(toolbar_frame, command=self.auto_fix, bg="#e6e6ff")
        self.btn_autofix.pack(side=tk.RIGHT, padx=5)
        
        self.btn_web = tk.Button(toolbar_frame, command=self.open_web_version, bg="#cceeff")
        self.btn_web.pack(side=tk.RIGHT, padx=5)
        
        self.btn_in_plus = tk.Button(toolbar_frame, text="+", command=lambda: self.change_in_font(2), width=3, bg="#e6ffe6")
        self.btn_in_plus.pack(side=tk.RIGHT, padx=2)
        self.btn_in_minus = tk.Button(toolbar_frame, text="-", command=lambda: self.change_in_font(-2), width=3, bg="#e6ffe6")
        self.btn_in_minus.pack(side=tk.RIGHT, padx=2)
        self.lbl_in_font = ttk.Label(toolbar_frame, text="")
        self.lbl_in_font.pack(side=tk.RIGHT, padx=5)

        text_frame = ttk.Frame(input_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        text_vbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        text_hbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)

        self.text_input = tk.Text(text_frame, font=("Consolas", self.input_font_size), wrap=tk.NONE,
                                  yscrollcommand=text_vbar.set, xscrollcommand=text_hbar.set)

        text_vbar.config(command=self.text_input.yview)
        text_hbar.config(command=self.text_input.xview)

        text_vbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_input.bind("<Control-a>", self.select_all)
        self.text_input.bind("<Control-A>", self.select_all)
        self.text_input.bind("<<Paste>>", self.on_paste)
        self.text_input.bind("<KeyRelease>", self.on_key_release)

        default_text = self.tr("latex_viewer_default", r"這是一個帶有中文的公式範例：$E = mc^2$")
        self.text_input.insert("1.0", default_text)
        self.render_latex()

        # 等待介面繪製後，再調整 sash 比例
        self.frame.after(100, lambda: self.set_sash(paned_window))

    def set_sash(self, paned_window):
        try:
            h = self.frame.winfo_height()
            if h > 100:
                paned_window.sash_place(0, 0, h // 2)
        except Exception:
            pass

    def update_language(self):
        super().update_language()
        if not getattr(self, 'lbl_output', None):
            return

        self.lbl_output.config(text=self.tr("latex_viewer_out_title", "輸出預覽"))
        self.lbl_out_font.config(text=self.tr("latex_viewer_out_font", "輸出字體"))
        self.lbl_input.config(text=self.tr("latex_viewer_in_title", "請輸入 LaTeX:"))
        self.lbl_in_font.config(text=self.tr("latex_viewer_in_font", "輸入字體"))
        self.btn_clear.config(text=self.tr("latex_viewer_clear", "清除 (Clear)"))
        self.btn_autofix.config(text=self.tr("latex_viewer_autofix", "修復 ChatGPT 公式 🔧"))
        self.btn_web.config(text=self.tr("latex_viewer_web", "在網頁版開啟 🌐"))

    def on_destroy(self):
        self.shared_state.log(f"LatexViewerModule '{self.module_name}' is being destroyed.")
        plt.close(self.fig) # 釋放 Matplotlib 資源
        super().on_destroy()
