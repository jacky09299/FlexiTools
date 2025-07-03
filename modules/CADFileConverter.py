import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import time
import win32con
import win32gui
import win32process
import ctypes
import os
import tempfile
import shutil
from main import Module

# 新增匯入
import gdstk
import ezdxf

class GDSModule(Module):
    def __init__(self, master, shared_state, module_name="CADFileConverter", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.proc = None
        self.child_hwnd = None
        self.container = None
        self._bind_id = None

        # 狀態變數
        self.input_path = tk.StringVar()
        self.input_is_folder = tk.BooleanVar(value=False)
        self.unit = tk.StringVar(value="micron")
        self.output_format = tk.StringVar(value="DXF")
        self.output_folder = tk.StringVar()
        self.output_name = tk.StringVar()
        self.dxf_version = tk.StringVar(value="R2018")

        # 支援的單位轉換
        self.unit_multipliers = {
            "micron": 1e-6,
            "mm": 1e-3,
            "cm": 1e-2,
            "inch": 0.0254
        }

        self.create_ui()

    def create_ui(self):
        # 主容器
        self.container = tk.Frame(self.frame, width=800, height=600, bg="#222")
        self.container.pack(fill="both", expand=True)
        self.frame.update_idletasks()

        # 控制面板
        control_frame = tk.LabelFrame(self.container, text="CAD 檔案轉換器", bg="#222", fg="#fff", font=("Arial", 10, "bold"))
        control_frame.pack(fill="x", padx=10, pady=10)

        # 檔案/資料夾選擇區
        file_frame = tk.Frame(control_frame, bg="#222")
        file_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(file_frame, text="來源：", bg="#222", fg="#fff", width=12, anchor="e").grid(row=0, column=0, sticky="e", padx=5)
        tk.Entry(file_frame, textvariable=self.input_path, width=60, bg="#333", fg="#fff").grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(file_frame, text="選檔", command=self.select_input_file, bg="#444", fg="#fff").grid(row=0, column=2, padx=2)
        tk.Button(file_frame, text="選資料夾", command=self.select_input_folder, bg="#444", fg="#fff").grid(row=0, column=3, padx=2)
        file_frame.columnconfigure(1, weight=1)

        # 輸出資料夾與檔名
        output_frame = tk.Frame(control_frame, bg="#222")
        output_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(output_frame, text="輸出資料夾：", bg="#222", fg="#fff", width=12, anchor="e").grid(row=0, column=0, sticky="e", padx=5)
        tk.Entry(output_frame, textvariable=self.output_folder, width=40, bg="#333", fg="#fff").grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(output_frame, text="選擇", command=self.select_output_folder, bg="#444", fg="#fff").grid(row=0, column=2, padx=2)
        tk.Label(output_frame, text="輸出檔名：", bg="#222", fg="#fff", width=10, anchor="e").grid(row=0, column=3, sticky="e", padx=5)
        tk.Entry(output_frame, textvariable=self.output_name, width=20, bg="#333", fg="#fff").grid(row=0, column=4, padx=5, sticky="ew")
        output_frame.columnconfigure(1, weight=1)
        output_frame.columnconfigure(4, weight=1)

        # 設定區
        settings_frame = tk.Frame(control_frame, bg="#222")
        settings_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(settings_frame, text="單位：", bg="#222", fg="#fff", width=12, anchor="e").grid(row=0, column=0, sticky="e", padx=5)
        unit_combo = ttk.Combobox(settings_frame, textvariable=self.unit, values=list(self.unit_multipliers.keys()), width=10, state="readonly")
        unit_combo.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(settings_frame, text="輸出格式：", bg="#222", fg="#fff", width=12, anchor="e").grid(row=0, column=2, sticky="e", padx=5)
        format_combo = ttk.Combobox(settings_frame, textvariable=self.output_format, values=["GDS", "DXF", "DWG"], width=10, state="readonly")
        format_combo.grid(row=0, column=3, sticky="w", padx=5)
        format_combo.bind("<<ComboboxSelected>>", self.on_format_change)

        tk.Label(settings_frame, text="DXF版本：", bg="#222", fg="#fff", width=12, anchor="e").grid(row=1, column=0, sticky="e", padx=5)
        version_combo = ttk.Combobox(settings_frame, textvariable=self.dxf_version, 
                                   values=["R12", "R2000", "R2004", "R2007", "R2010", "R2013", "R2018"], 
                                   width=10, state="readonly")
        version_combo.grid(row=1, column=1, sticky="w", padx=5)

        # 操作按鈕區
        button_frame = tk.Frame(control_frame, bg="#222")
        button_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(button_frame, text="執行轉換", command=self.convert, 
                 bg="#0066cc", fg="#fff", font=("Arial", 10, "bold"), 
                 width=15, height=2).pack(side="left", padx=10)

        tk.Button(button_frame, text="預覽", command=self.preview, 
                 bg="#006600", fg="#fff", font=("Arial", 10, "bold"), 
                 width=15, height=2).pack(side="left", padx=10)

        # 狀態顯示區
        status_frame = tk.LabelFrame(control_frame, text="轉換狀態", bg="#222", fg="#fff")
        status_frame.pack(fill="x", padx=10, pady=5)

        self.status_text = tk.Text(status_frame, height=4, bg="#111", fg="#0f0", font=("Consolas", 9))
        scrollbar = tk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        self.status_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)

    def log_status(self, message):
        """在狀態區域記錄訊息"""
        if hasattr(self, 'status_text'):
            self.status_text.insert(tk.END, f"{message}\n")
            self.status_text.see(tk.END)
            self.status_text.update()
        # 同時記錄到shared_state
        if hasattr(self, 'shared_state'):
            self.shared_state.log(f"GDSModule: {message}", level=20)

    # --- 新增/調整的UI事件 ---
    def select_input_file(self):
        path = filedialog.askopenfilename(
            title="選擇檔案",
            filetypes=[("CAD files", "*.gds *.dxf *.dwg"), ("All files", "*.*")]
        )
        if path:
            self.input_path.set(path)
            self.input_is_folder.set(False)
            self.output_folder.set(os.path.dirname(path))
            base = os.path.splitext(os.path.basename(path))[0]
            self.output_name.set(base)
            self.log_status(f"已選擇檔案: {os.path.basename(path)}")

    def select_input_folder(self):
        path = filedialog.askdirectory(title="選擇資料夾")
        if path:
            self.input_path.set(path)
            self.input_is_folder.set(True)
            self.output_folder.set(path)
            self.output_name.set("")  # 批次不設定單一檔名
            self.log_status(f"已選擇資料夾: {os.path.basename(path)}")

    def select_output_folder(self):
        path = filedialog.askdirectory(title="選擇輸出資料夾")
        if path:
            self.output_folder.set(path)
            self.log_status(f"輸出資料夾設定為: {os.path.basename(path)}")

    def on_format_change(self, event=None):
        # 若單檔，更新副檔名
        if not self.input_is_folder.get() and self.input_path.get():
            base = os.path.splitext(os.path.basename(self.input_path.get()))[0]
            ext = self.output_format.get().lower()
            self.output_name.set(base)

    def preview(self):
        # 單檔預覽
        if self.input_is_folder.get():
            messagebox.showinfo("預覽", "批次模式不支援預覽")
            return
        path = self.input_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("錯誤", "請先選擇有效的檔案")
            return
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".gds":
                lib = gdstk.read_gds(path)
                info = f"GDS 檔案資訊:\n"
                info += f"檔案: {os.path.basename(path)}\n"
                info += f"單位: {lib.unit} 米\n"
                info += f"精度: {lib.precision}\n"
                info += f"包含 {len(lib.cells)} 個 Cell\n\n"
                for i, cell in enumerate(lib.cells[:5]):
                    info += f"Cell {i+1}: {cell.name}\n"
                    info += f"  多邊形: {len(cell.polygons)} 個\n"
                    info += f"  路徑: {len(cell.paths)} 個\n"
                    info += f"  參考: {len(cell.references)} 個\n"
                if len(lib.cells) > 5:
                    info += f"... 還有 {len(lib.cells) - 5} 個 Cell\n"
                messagebox.showinfo("GDS 檔案預覽", info)
            elif ext == ".dxf":
                doc = ezdxf.readfile(path)
                info = f"DXF 檔案資訊:\n"
                info += f"檔案: {os.path.basename(path)}\n"
                info += f"版本: {doc.dxfversion}\n"
                info += f"圖層數: {len(doc.layers)}\n"
                info += f"物件數: {sum(1 for _ in doc.modelspace())}\n"
                messagebox.showinfo("DXF 檔案預覽", info)
            elif ext == ".dwg":
                messagebox.showinfo("DWG 檔案預覽", "DWG 預覽暫不支援")
            self.log_status("檔案預覽完成")
        except Exception as e:
            messagebox.showerror("預覽失敗", f"讀取檔案時發生錯誤:\n{str(e)}")
            self.log_status(f"預覽失敗: {str(e)}")

    def convert(self):
        input_path = self.input_path.get()
        output_folder = self.output_folder.get()
        output_format = self.output_format.get()
        output_name = self.output_name.get().strip()
        is_folder = self.input_is_folder.get()

        if not input_path or not output_folder:
            messagebox.showerror("錯誤", "請選擇來源與輸出資料夾")
            return

        if is_folder:
            # 批次模式
            files = []
            for fname in os.listdir(input_path):
                ext = os.path.splitext(fname)[1].lower()
                if ext in [".gds", ".dxf", ".dwg"]:
                    files.append(os.path.join(input_path, fname))
            if not files:
                messagebox.showerror("錯誤", "資料夾內沒有可轉換的檔案")
                return
            self.log_status(f"開始批次轉換，共 {len(files)} 個檔案")
            for f in files:
                base = os.path.splitext(os.path.basename(f))[0]
                out_name = f"{base}.{output_format.lower()}"
                out_path = os.path.join(output_folder, out_name)
                try:
                    self.convert_one(f, out_path, output_format)
                    self.log_status(f"轉換完成: {os.path.basename(f)} -> {out_name}")
                except Exception as e:
                    self.log_status(f"轉換失敗: {os.path.basename(f)} - {str(e)}")
            messagebox.showinfo("批次轉換完成", "所有檔案已處理完畢")
        else:
            # 單檔模式
            if not output_name:
                messagebox.showerror("錯誤", "請輸入輸出檔名")
                return
            ext = os.path.splitext(input_path)[1].lower()
            out_path = os.path.join(output_folder, f"{output_name}.{output_format.lower()}")
            try:
                self.convert_one(input_path, out_path, output_format)
                messagebox.showinfo("轉換完成", f"已成功轉換為 {output_format}:\n{out_path}")
                self.log_status("轉換完成!")
            except Exception as e:
                error_msg = f"轉換失敗: {str(e)}"
                messagebox.showerror("轉換失敗", error_msg)
                self.log_status(error_msg)

    def convert_one(self, src_path, out_path, output_format):
        ext = os.path.splitext(src_path)[1].lower()
        if output_format == "GDS":
            if ext == ".gds":
                shutil.copy2(src_path, out_path)
            elif ext == ".dxf":
                self.dxf_to_gds(src_path, out_path)
            elif ext == ".dwg":
                tmp_dir = tempfile.mkdtemp()
                try:
                    tmp_dxf = os.path.join(tmp_dir, "temp.dxf")
                    self.dwg_to_dxf(src_path, tmp_dxf)
                    self.dxf_to_gds(tmp_dxf, out_path)
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            else:
                raise RuntimeError("不支援的來源格式")
        elif output_format == "DXF":
            if ext == ".gds":
                self.gds_to_dxf(src_path, out_path)
            elif ext == ".dxf":
                shutil.copy2(src_path, out_path)
            elif ext == ".dwg":
                self.dwg_to_dxf(src_path, out_path)
            else:
                raise RuntimeError("不支援的來源格式")
        elif output_format == "DWG":
            if ext == ".gds":
                tmp_dir = tempfile.mkdtemp()
                try:
                    tmp_dxf = os.path.join(tmp_dir, "temp.dxf")
                    self.gds_to_dxf(src_path, tmp_dxf)
                    self.dxf_to_dwg_simple(tmp_dxf, out_path)
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            elif ext == ".dxf":
                self.dxf_to_dwg_simple(src_path, out_path)
            elif ext == ".dwg":
                shutil.copy2(src_path, out_path)
            else:
                raise RuntimeError("不支援的來源格式")
        else:
            raise RuntimeError("不支援的輸出格式")

    # --- DXF <-> GDS 轉換 ---
    def dxf_to_gds(self, dxf_path, gds_path):
        # DXF 轉 GDS (簡單範例)
        doc = ezdxf.readfile(dxf_path)
        lib = gdstk.Library()
        cell = gdstk.Cell("DXF")
        for e in doc.modelspace():
            if e.dxftype() == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points()]
                cell.add(gdstk.Polygon(pts))
        lib.add(cell)
        lib.write_gds(gds_path)
        self.log_status(f"DXF 轉 GDS 完成: {os.path.basename(gds_path)}")

    def dwg_to_dxf(self, dwg_path, dxf_path):
        # 使用 ODAFileConverter 轉 DWG->DXF
        exe_path = os.path.join(os.path.dirname(__file__), "ODAFileConverter 26.4.0", "ODAFileConverter.exe")
        if not os.path.exists(exe_path):
            raise RuntimeError("找不到 ODAFileConverter.exe，無法轉換")
        temp_output_dir = tempfile.mkdtemp()
        input_dir = os.path.dirname(dwg_path)
        try:
            cmd = [
                exe_path,
                input_dir,
                temp_output_dir,
                "ACAD2018",
                "DXF",
                "1",
                "1",
                "*.dwg"
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            # 找到對應DXF
            base = os.path.splitext(os.path.basename(dwg_path))[0]
            for root, dirs, files in os.walk(temp_output_dir):
                for file in files:
                    if file.lower().endswith('.dxf') and base in file:
                        shutil.copy2(os.path.join(root, file), dxf_path)
                        return
            raise RuntimeError("DWG 轉 DXF 失敗")
        finally:
            shutil.rmtree(temp_output_dir, ignore_errors=True)

    def gds_to_dxf(self, gds_path, dxf_path):
        """將GDS轉換為DXF"""
        self.log_status(f"讀取 GDS 檔案: {os.path.basename(gds_path)}")
        
        # 讀取GDS檔案
        lib = gdstk.read_gds(gds_path)
        
        # 獲取單位轉換係數
        unit_name = self.unit.get()
        target_unit = self.unit_multipliers[unit_name]
        scale_factor = lib.unit / target_unit
        self.log_status(f"建立 DXF 檔案 (版本: {self.dxf_version.get()})")
        
        # 建立DXF文檔
        doc = ezdxf.new(self.dxf_version.get())
        msp = doc.modelspace()
        
        # 設定圖層
        layers_created = set()
        
        total_polygons = sum(len(cell.polygons) for cell in lib.cells)
        total_paths = sum(len(cell.paths) for cell in lib.cells)
        processed = 0
        
        self.log_status(f"處理 {len(lib.cells)} 個 Cell, {total_polygons} 個多邊形, {total_paths} 個路徑")
        
        # 處理每個cell
        for cell in lib.cells:
            # 處理多邊形
            for poly in cell.polygons:
                # 創建圖層
                layer_name = f"Layer_{poly.layer}" if poly.layer is not None else "Layer_0"
                if layer_name not in layers_created:
                    doc.layers.new(name=layer_name)
                    layers_created.add(layer_name)
                
                # 轉換座標
                points = [(x * scale_factor, y * scale_factor) for x, y in poly.points]
                
                if len(points) >= 3:
                    try:
                        # 使用LWPOLYLINE繪製多邊形
                        msp.add_lwpolyline(points, close=True, dxfattribs={'layer': layer_name})
                        processed += 1
                    except Exception as e:
                        self.log_status(f"警告: 跳過無效多邊形 - {str(e)}")
            
            # 處理路徑
            for path in cell.paths:
                # 創建圖層
                layer_name = f"Layer_{path.layer}" if path.layer is not None else "Layer_0"
                if layer_name not in layers_created:
                    doc.layers.new(name=layer_name)
                    layers_created.add(layer_name)
                
                try:
                    # 將路徑轉換為多邊形
                    polygons = path.to_polygons()
                    for poly_points in polygons:
                        points = [(x * scale_factor, y * scale_factor) for x, y in poly_points]
                        if len(points) >= 3:
                            msp.add_lwpolyline(points, close=True, dxfattribs={'layer': layer_name})
                            processed += 1
                except Exception as e:
                    self.log_status(f"警告: 跳過無效路徑 - {str(e)}")
        
        # 保存DXF檔案
        self.log_status(f"儲存 DXF 檔案: {os.path.basename(dxf_path)}")
        doc.saveas(dxf_path)
        
        self.log_status(f"DXF 轉換完成: 處理了 {processed} 個圖形元素")

    def dxf_to_dwg_simple(self, dxf_path, dwg_path):
        """使用 ODAFileConverter.exe 轉換 DXF 為 DWG，命令格式參考範例"""
        exe_path = os.path.join(os.path.dirname(__file__), "ODAFileConverter 26.4.0", "ODAFileConverter.exe")
        
        if not os.path.exists(exe_path):
            raise RuntimeError("找不到 ODAFileConverter.exe，無法轉換為 DWG 格式")
        
        self.log_status("使用 ODAFileConverter 轉換為 DWG...")

        # 創建臨時輸出目錄
        temp_output_dir = tempfile.mkdtemp()
        input_dir = os.path.dirname(dxf_path)

        try:
            # 命令格式參考範例，不加引號，recurse 設為 1
            cmd = [
                exe_path,
                input_dir,                # 輸入資料夾
                temp_output_dir,          # 輸出資料夾
                "ACAD2018",               # 輸出版本
                "DWG",                    # 輸出檔案類型
                "1",                      # 遞迴處理子資料夾
                "1",                      # 啟用檔案檢查
                "*.dxf"                   # 輸入檔案篩選器
            ]

            self.log_status(f"執行命令: {' '.join(cmd)}")

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            self.log_status(f"ODAFileConverter 返回碼: {result.returncode}")
            if result.stdout:
                self.log_status(f"標準輸出: {result.stdout}")
            if result.stderr:
                self.log_status(f"錯誤輸出: {result.stderr}")

            # 尋找生成的DWG檔案
            dwg_files = []
            for root, dirs, files in os.walk(temp_output_dir):
                for file in files:
                    if file.lower().endswith('.dwg'):
                        dwg_files.append(os.path.join(root, file))

            self.log_status(f"找到 {len(dwg_files)} 個 DWG 檔案")

            if not dwg_files:
                all_files = []
                for root, dirs, files in os.walk(temp_output_dir):
                    for file in files:
                        all_files.append(os.path.join(root, file))
                self.log_status(f"輸出目錄中的檔案: {all_files}")
                raise RuntimeError("ODAFileConverter 沒有生成 DWG 檔案")

            # 使用第一個找到的DWG檔案
            source_dwg = dwg_files[0]
            shutil.copy2(source_dwg, dwg_path)
            self.log_status(f"DWG 轉換完成: {os.path.basename(dwg_path)}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("ODAFileConverter 執行逾時")
        except Exception as e:
            self.log_status(f"轉換過程中發生錯誤: {str(e)}")
            raise RuntimeError(f"DWG 轉換失敗: {str(e)}")
        finally:
            try:
                shutil.rmtree(temp_output_dir, ignore_errors=True)
            except Exception as e:
                self.log_status(f"清理臨時目錄失敗: {str(e)}")

    def dxf_to_dwg_alternative(self, dxf_path, dwg_path):
        """替代方案：使用批次檔案方式轉換"""
        exe_path = os.path.join(os.path.dirname(__file__), "ODAFileConverter 26.4.0", "ODAFileConverter.exe")
        
        if not os.path.exists(exe_path):
            raise RuntimeError("找不到 ODAFileConverter.exe，無法轉換為 DWG 格式")
        
        self.log_status("使用替代方案轉換為 DWG...")
        
        # 創建臨時批次檔
        temp_dir = tempfile.mkdtemp()
        batch_file = os.path.join(temp_dir, "convert.txt")
        input_dir = os.path.dirname(dxf_path)
        output_dir = os.path.dirname(dwg_path)
        
        try:
            # 創建批次轉換檔案
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(f'"{input_dir}"\n')
                f.write(f'"{output_dir}"\n')
                f.write('ACAD2018\n')
                f.write('DWG\n')
                f.write('0\n')
                f.write('1\n')
                f.write('*.DXF\n')
            
            # 使用批次檔案執行轉換
            cmd = [exe_path, f'@{batch_file}']
            
            self.log_status(f"執行批次轉換: {' '.join(cmd)}")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            self.log_status(f"批次轉換返回碼: {result.returncode}")
            
            if result.stdout:
                self.log_status(f"標準輸出: {result.stdout}")
            if result.stderr:
                self.log_status(f"錯誤輸出: {result.stderr}")
            
            # 檢查是否生成了DWG檔案
            expected_dwg = os.path.join(output_dir, os.path.splitext(os.path.basename(dxf_path))[0] + '.dwg')
            
            if os.path.exists(expected_dwg):
                if expected_dwg != dwg_path:
                    shutil.move(expected_dwg, dwg_path)
                self.log_status(f"DWG 轉換完成: {os.path.basename(dwg_path)}")
            else:
                # 列出輸出目錄中的所有檔案
                files_in_output = os.listdir(output_dir) if os.path.exists(output_dir) else []
                self.log_status(f"輸出目錄中的檔案: {files_in_output}")
                raise RuntimeError("批次轉換沒有生成 DWG 檔案")
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("批次轉換執行逾時")
        except Exception as e:
            self.log_status(f"批次轉換過程中發生錯誤: {str(e)}")
            raise RuntimeError(f"批次轉換失敗: {str(e)}")
        finally:
            # 清理臨時檔案
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                self.log_status(f"清理臨時檔案失敗: {str(e)}")

    def on_destroy(self):
        self.log_status("正在關閉模組...")
        self.log_status("GDSModule 已關閉")
        super().on_destroy()