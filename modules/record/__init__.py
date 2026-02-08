import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from main import Module
import datetime
import os
import time
import ctypes
from ctypes import windll, byref, c_ubyte, c_int, c_void_p, POINTER, Structure
import threading
import numpy as np
import cv2
import subprocess
import struct
from PIL import ImageGrab, Image

# Try importing PyAudio
try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

__version__ = "1.2.0"

# --- Windows API Constants ---
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011
SRCCOPY = 0x00CC0020
CURSOR_SHOWING = 0x00000001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class POINT(Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class CURSORINFO(Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("flags", ctypes.c_uint),
                ("hCursor", ctypes.c_void_p),
                ("ptScreenPos", POINT)]

class BITMAPINFOHEADER(Structure):
    _fields_ = [('biSize', ctypes.c_uint),
                ('biWidth', ctypes.c_int),
                ('biHeight', ctypes.c_int),
                ('biPlanes', ctypes.c_ushort),
                ('biBitCount', ctypes.c_ushort),
                ('biCompression', ctypes.c_uint),
                ('biSizeImage', ctypes.c_uint),
                ('biXPelsPerMeter', ctypes.c_long),
                ('biYPelsPerMeter', ctypes.c_long),
                ('biClrUsed', ctypes.c_uint),
                ('biClrImportant', ctypes.c_uint)]

# --- GDI Screen Capture (64-bit compatible) ---
class GDIScreenCapture:
    def __init__(self):
        self.user32 = windll.user32
        self.gdi32 = windll.gdi32
        self.hwin_dc = None
        self.hmem_dc = None
        self.h_bitmap = None
        self.width = 0
        self.height = 0

        # Set API argtypes
        self.user32.DrawIcon.argtypes = [c_void_p, c_int, c_int, c_void_p]
        self.user32.DrawIcon.restype = c_int
        self.gdi32.BitBlt.argtypes = [c_void_p, c_int, c_int, c_int, c_int, c_void_p, c_int, c_int, ctypes.c_uint32]
        self.gdi32.BitBlt.restype = c_int
        self.gdi32.SelectObject.argtypes = [c_void_p, c_void_p]
        self.gdi32.SelectObject.restype = c_void_p
        self.gdi32.CreateCompatibleDC.argtypes = [c_void_p]
        self.gdi32.CreateCompatibleDC.restype = c_void_p
        self.gdi32.CreateCompatibleBitmap.argtypes = [c_void_p, c_int, c_int]
        self.gdi32.CreateCompatibleBitmap.restype = c_void_p
        self.gdi32.GetDIBits.argtypes = [c_void_p, c_void_p, c_int, c_int, c_void_p, POINTER(BITMAPINFOHEADER), c_int]
        self.gdi32.GetDIBits.restype = c_int
        self.gdi32.DeleteDC.argtypes = [c_void_p]
        self.gdi32.DeleteDC.restype = c_int
        self.gdi32.DeleteObject.argtypes = [c_void_p]
        self.gdi32.DeleteObject.restype = c_int
        self.user32.ReleaseDC.argtypes = [c_void_p, c_void_p]
        self.user32.ReleaseDC.restype = c_int
        self.user32.GetDC.argtypes = [c_void_p]
        self.user32.GetDC.restype = c_void_p
        self.user32.GetCursorInfo.argtypes = [POINTER(CURSORINFO)]
        self.user32.GetCursorInfo.restype = c_int

    def initialize(self, x, y, w, h):
        self.x, self.y, self.width, self.height = x, y, w, h
        self.hwin_dc = self.user32.GetDC(None)
        self.hmem_dc = self.gdi32.CreateCompatibleDC(self.hwin_dc)
        self.h_bitmap = self.gdi32.CreateCompatibleBitmap(self.hwin_dc, w, h)
        self.gdi32.SelectObject(self.hmem_dc, self.h_bitmap)

    def capture_frame(self):
        if not self.hmem_dc: return None
        self.gdi32.BitBlt(self.hmem_dc, 0, 0, self.width, self.height, 
                          self.hwin_dc, self.x, self.y, SRCCOPY)
        cursor_info = CURSORINFO()
        cursor_info.cbSize = ctypes.sizeof(CURSORINFO)
        if self.user32.GetCursorInfo(byref(cursor_info)):
            if cursor_info.flags & CURSOR_SHOWING:
                cx = cursor_info.ptScreenPos.x - self.x
                cy = cursor_info.ptScreenPos.y - self.y
                self.user32.DrawIcon(self.hmem_dc, cx, cy, cursor_info.hCursor)
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = self.width
        bmi.biHeight = -self.height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0
        buffer_len = self.width * self.height * 4
        buffer = (c_ubyte * buffer_len)()
        self.gdi32.GetDIBits(self.hmem_dc, self.h_bitmap, 0, self.height, 
                             byref(buffer), byref(bmi), 0)
        img_np = np.frombuffer(buffer, dtype=np.uint8).reshape((self.height, self.width, 4))
        return img_np[:, :, :3] 

    def release(self):
        if self.hmem_dc: self.gdi32.DeleteDC(self.hmem_dc)
        if self.h_bitmap: self.gdi32.DeleteObject(self.h_bitmap)
        if self.hwin_dc: self.user32.ReleaseDC(None, self.hwin_dc)
        self.hmem_dc = None

# --- Audio Recording & Monitoring ---
class AudioRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio() if AUDIO_AVAILABLE else None
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.is_monitoring = False
        self.record_thread = None
        self.monitor_thread = None
        self.monitor_callback = None
        
    def get_device_list(self):
        devices = []
        if not self.p: return []
        num_devices = self.p.get_device_count()
        for i in range(num_devices):
            dev_info = self.p.get_device_info_by_index(i)
            if dev_info.get('maxInputChannels') > 0:
                name = dev_info.get('name')
                try: name = name.encode('latin-1').decode('utf-8')
                except: pass
                host_api = self.p.get_host_api_info_by_index(dev_info.get('hostApi')).get('name')
                devices.append((i, f"[{host_api}] {name}"))
        return devices

    def start_monitoring(self, device_index, callback):
        if not self.p: return
        self.stop_monitoring()
        self.monitor_callback = callback
        self.is_monitoring = True
        try:
            self.stream = self.p.open(format=pyaudio.paInt16, channels=2, rate=44100, input=True,
                                      input_device_index=device_index, frames_per_buffer=1024)
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
        except Exception:
            self.is_monitoring = False
            if self.monitor_callback: self.monitor_callback(-1)

    def _monitor_loop(self):
        while self.is_monitoring and self.stream:
            try:
                data = self.stream.read(1024, exception_on_overflow=False)
                shorts = np.frombuffer(data, dtype=np.int16)
                if len(shorts) > 0:
                    peak = np.abs(shorts).max()
                    level = min(100, int(peak / 32767 * 100 * 4))
                    if self.monitor_callback: self.monitor_callback(level)
            except: break

    def stop_monitoring(self):
        self.is_monitoring = False
        if self.stream:
            try: self.stream.stop_stream(); self.stream.close()
            except: pass
            self.stream = None

    def start_recording(self, device_index, filename):
        self.stop_monitoring()
        if not self.p: return
        self.frames = []
        self.is_recording = True
        try:
            self.stream = self.p.open(format=pyaudio.paInt16, channels=2, rate=44100, input=True,
                                      input_device_index=device_index, frames_per_buffer=1024)
            self.record_thread = threading.Thread(target=self._record_loop)
            self.record_thread.daemon = True
            self.record_thread.start()
        except Exception as e:
            print(f"Record Start Error: {e}")
            self.is_recording = False

    def _record_loop(self):
        while self.is_recording and self.stream:
            try:
                data = self.stream.read(1024, exception_on_overflow=False)
                self.frames.append(data)
            except: break

    def stop_recording(self, save_path):
        self.is_recording = False
        if self.record_thread: self.record_thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        try:
            if self.frames and len(self.frames) > 0:
                raw_data = b''.join(self.frames)
                self.manual_wav_write(save_path, 2, 44100, 2, raw_data)
                return True
        except Exception as e:
            print(f"Audio Save Error: {e}")
            return False
        return False

    def manual_wav_write(self, filename, channels, rate, sampwidth, data):
        """Manual WAV write to ensure 4-byte alignment"""
        data_len = len(data)
        
        block_align = channels * sampwidth
        padding = data_len % block_align
        if padding != 0:
            pad_len = block_align - padding
            data += b'\x00' * pad_len
            data_len += pad_len
            
        file_size = 36 + data_len
        byte_rate = rate * block_align
        bits_per_sample = sampwidth * 8
        
        try:
            with open(filename, 'wb') as f:
                f.write(b'RIFF')
                f.write(struct.pack('<I', file_size))
                f.write(b'WAVE')
                f.write(b'fmt ')
                f.write(struct.pack('<I', 16)) 
                f.write(struct.pack('<H', 1)) 
                f.write(struct.pack('<H', channels))
                f.write(struct.pack('<I', rate))
                f.write(struct.pack('<I', byte_rate))
                f.write(struct.pack('<H', block_align))
                f.write(struct.pack('<H', bits_per_sample))
                f.write(b'data')
                f.write(struct.pack('<I', data_len))
                f.write(data)
        except Exception as e:
            print(f"Manual WAV Write Error: {e}")
            raise

    def cleanup(self):
        self.stop_monitoring()
        self.is_recording = False
        if self.p: self.p.terminate()

class RecordModule(Module):
    def __init__(self, master, shared_state, module_name="Record", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"RecordModule '{self.module_name}' initialized.")
        
        self.save_dir = os.getcwd()
        self.is_manual_save = tk.BooleanVar(value=False)
        self.is_exclude_window = tk.BooleanVar(value=True)
        
        self.record_audio = tk.BooleanVar(value=AUDIO_AVAILABLE)
        self.audio_recorder = AudioRecorder() if AUDIO_AVAILABLE else None
        self.selected_audio_idx = None
        
        self.is_fixed_size = tk.BooleanVar(value=False)
        self.anchor_pos = tk.StringVar(value="tl") 
        self.last_width = 0
        self.last_height = 0
        self.last_bbox = None
        self.start_x = None
        self.start_y = None
        self.current_mode = "screenshot"
        self.is_recording = False
        
        # Automation State
        self.is_use_last_region = tk.BooleanVar(value=False)
        self.auto_click_pos = None
        self.aux_points = []
        self.aux_click_timing = tk.StringVar(value="before") # before or after
        self.is_automating = False
        self.auto_count = tk.IntVar(value=10)
        self.auto_interval = tk.DoubleVar(value=2.0)
        
        self.gdi_capture = GDIScreenCapture()
        
        self.create_ui()
        self.update_language()

    def create_ui(self):
        """Create the user interface for the record module."""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Path Selection
        path_frame = tk.Frame(main_frame)
        path_frame.pack(pady=5, fill='x')
        self.path_label = tk.Label(path_frame, text=f"位置: {self.get_short_path(self.save_dir)}", fg="gray")
        self.path_label.pack(side="left")
        ttk.Button(path_frame, text="瀏覽...", command=self.choose_directory).pack(side="right")

        # General Options
        opt_frame = tk.LabelFrame(main_frame, text=" 一般設定 ", padx=10, pady=5)
        opt_frame.pack(pady=5, fill='x')
        tk.Checkbutton(opt_frame, text="截圖時詢問檔名", variable=self.is_manual_save).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(opt_frame, text="錄影時對鏡頭隱形 (視窗透明)", variable=self.is_exclude_window).grid(row=1, column=0, sticky="w")
        tk.Checkbutton(opt_frame, text="直接使用上次範圍 (不用重拉)", variable=self.is_use_last_region).grid(row=2, column=0, sticky="w")

        # Audio Settings
        audio_frame = tk.LabelFrame(main_frame, text=" 音訊設定 ", padx=10, pady=5)
        audio_frame.pack(pady=5, fill='x')

        if AUDIO_AVAILABLE:
            top_audio = tk.Frame(audio_frame)
            top_audio.pack(fill="x")
            tk.Checkbutton(top_audio, text="啟用錄音功能", variable=self.record_audio, command=self.toggle_audio_ui).pack(side="left")
            tk.Button(top_audio, text="音訊疑難排解", command=self.show_audio_help, fg="blue", font=("Arial", 9, "underline"), bd=0, cursor="hand2").pack(side="right")
            
            dev_frame = tk.Frame(audio_frame)
            dev_frame.pack(fill="x", pady=5)
            tk.Label(dev_frame, text="輸入裝置:").pack(side="left")
            self.device_combo = ttk.Combobox(dev_frame, state="readonly", width=25)
            self.device_combo.pack(side="left", padx=5, fill='x', expand=True)
            self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)
            
            vol_frame = tk.Frame(audio_frame)
            vol_frame.pack(fill="x", pady=5)
            tk.Label(vol_frame, text="音量測試:").pack(side="left")
            self.vol_bar = ttk.Progressbar(vol_frame, orient="horizontal", length=150, mode="determinate")
            self.vol_bar.pack(side="left", padx=5, fill='x', expand=True)
            
            self.audio_hint = tk.Label(audio_frame, text="請選擇 [MME] Stereo Mix 進行錄製", fg="gray", font=("Arial", 8))
            self.audio_hint.pack(anchor="w")
            
            self.refresh_audio_devices()
        else:
            tk.Label(audio_frame, text="未安裝 PyAudio，無法使用錄音功能", fg="red").pack()

        # Fixed Size Mode
        fixed_frame = tk.LabelFrame(main_frame, text=" 固定尺寸模式 ", padx=10, pady=5)
        fixed_frame.pack(fill="x", pady=5)
        top_box = tk.Frame(fixed_frame)
        top_box.pack(fill="x")
        tk.Checkbutton(top_box, text="啟用固定大小", variable=self.is_fixed_size, command=self.toggle_fixed_mode).pack(side="left")
        self.size_label = tk.Label(top_box, text="無紀錄", fg="red")
        self.size_label.pack(side="right")
        
        anchor_frame = tk.Frame(fixed_frame)
        anchor_frame.pack()
        for pos, txt in [("tl","左上"), ("tr","右上"), ("bl","左下"), ("br","右下")]:
            tk.Radiobutton(anchor_frame, text=txt, variable=self.anchor_pos, value=pos).pack(side="left")

        # Automation
        auto_frame = tk.LabelFrame(main_frame, text=" 自動翻頁截圖 (5秒後開始) ", padx=10, pady=5)
        auto_frame.pack(fill="x", pady=5)
        
        af_opts = tk.Frame(auto_frame)
        af_opts.pack(fill="x")
        tk.Label(af_opts, text="頁數:").pack(side="left")
        tk.Entry(af_opts, textvariable=self.auto_count, width=5).pack(side="left", padx=5)
        tk.Label(af_opts, text="間隔(秒):").pack(side="left")
        tk.Entry(af_opts, textvariable=self.auto_interval, width=5).pack(side="left", padx=5)
        
        af_acts = tk.Frame(auto_frame)
        af_acts.pack(fill="x", pady=5)
        self.btn_pick_pos = ttk.Button(af_acts, text="設定翻頁點", command=lambda: self.prepare_snip("pick_point"))
        self.btn_pick_pos.pack(side="left")
        self.lbl_click_pos = tk.Label(af_acts, text="未設定", fg="gray")
        self.lbl_click_pos.pack(side="left", padx=5)
        
        aux_frame = tk.Frame(auto_frame, pady=2)
        aux_frame.pack(fill="x")
        
        ttk.Button(aux_frame, text="設定額外點 (+)", command=lambda: self.prepare_snip("pick_aux_point")).pack(side="left")
        ttk.Button(aux_frame, text="清除", command=self.clear_aux_points).pack(side="left", padx=5)
        self.lbl_aux_count = tk.Label(aux_frame, text="0 點", fg="blue")
        self.lbl_aux_count.pack(side="left")
        
        timing_frame = tk.Frame(auto_frame)
        timing_frame.pack(fill="x")
        tk.Radiobutton(timing_frame, text="截圖前", variable=self.aux_click_timing, value="pre_capture", fg="red").pack(side="left")
        tk.Radiobutton(timing_frame, text="翻頁前", variable=self.aux_click_timing, value="before").pack(side="left")
        tk.Radiobutton(timing_frame, text="翻頁後", variable=self.aux_click_timing, value="after").pack(side="left")

        ttk.Button(af_acts, text="開始自動", command=self.start_automation).pack(side="right")

        # Action Buttons
        btn_area = tk.Frame(main_frame)
        btn_area.pack(pady=10, fill="x", padx=10)
        self.btn_capture = tk.Button(btn_area, text="截圖", command=lambda: self.prepare_snip("screenshot"), bg="#0078D7", fg="white", font=("微軟正黑體", 12, "bold"), height=2, width=10)
        self.btn_capture.pack(side="left", padx=5, expand=True, fill='x')
        self.btn_record = tk.Button(btn_area, text="開始錄影", command=lambda: self.toggle_record_action(), bg="#D70000", fg="white", font=("微軟正黑體", 12, "bold"), height=2, width=10)
        self.btn_record.pack(side="right", padx=5, expand=True, fill='x')

        self.status_label = tk.Label(main_frame, text="就緒", fg="gray")
        self.status_label.pack(side="bottom", pady=5)

    def update_language(self):
        super().update_language()
        # Here we could update UI texts if we had translation keys
        # For now, we keep defaults from create_ui

    def show_audio_help(self):
        messagebox.showinfo("音訊疑難排解", "請確保 ffmpeg.exe 與本程式在同一資料夾。\n若音量條沒動，請檢查 Windows 隱私權設定。")

    def toggle_audio_ui(self):
        if self.record_audio.get():
            self.device_combo.config(state="readonly")
            self.on_device_selected(None)
        else:
            self.device_combo.config(state="disabled")
            if self.audio_recorder: self.audio_recorder.stop_monitoring()
            self.vol_bar['value'] = 0

    def refresh_audio_devices(self):
        if not self.audio_recorder: return
        devices = self.audio_recorder.get_device_list()
        device_names = [f"{idx}: {name}" for idx, name in devices]
        if device_names:
            self.device_combo['values'] = device_names
            default_idx = 0
            for i, name in enumerate(device_names):
                if "Stereo Mix" in name or "立體聲混音" in name:
                    default_idx = i
                    break
            self.device_combo.current(default_idx)
            self.on_device_selected(None)
        else:
            self.device_combo['values'] = ["找不到輸入裝置"]
            self.device_combo.current(0)

    def on_device_selected(self, event):
        if not self.record_audio.get(): return
        idx = self.get_selected_device_index()
        if idx is not None:
            self.selected_audio_idx = idx
            self.audio_recorder.start_monitoring(idx, self.update_vol_bar)

    def update_vol_bar(self, level):
        try:
            if level == -1:
                self.audio_hint.config(text="錯誤：無法開啟裝置", fg="red")
                self.vol_bar['value'] = 0
            else:
                self.vol_bar['value'] = level
                if level > 0: self.audio_hint.config(text="偵測到訊號！", fg="green")
        except: pass

    def get_selected_device_index(self):
        try: return int(self.device_combo.get().split(":")[0])
        except: return None

    def set_window_affinity(self, exclude: bool):
        try:
            # We need the HWND of the top-level window (ModularGUI root)
            root_window = self.frame.winfo_toplevel()
            hwnd = ctypes.windll.user32.GetParent(root_window.winfo_id())
            if hwnd == 0: hwnd = root_window.winfo_id()
            flag = WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, flag)
        except Exception as e: print(f"Error setting window affinity: {e}")

    def toggle_fixed_mode(self):
        if self.is_fixed_size.get():
            if self.last_width == 0 or self.last_height == 0:
                messagebox.showwarning("提示", "尚無尺寸紀錄！\n請先手動拖曳一次。")
                self.is_fixed_size.set(False)

    def get_short_path(self, path):
        return path[:10] + "..." + path[-10:] if len(path) > 25 else path

    def choose_directory(self):
        d = filedialog.askdirectory()
        if d:
            self.save_dir = d
            self.path_label.config(text=f"位置: {self.get_short_path(self.save_dir)}")

    def toggle_record_action(self):
        if self.is_recording: self.stop_recording()
        else: self.prepare_snip("record")

    def prepare_snip(self, mode):
        self.current_mode = mode
        root = self.frame.winfo_toplevel()
        
        if self.is_use_last_region.get() and mode not in ["pick_point", "pick_aux_point"]:
            if self.last_bbox:
                if mode == "screenshot":
                    root.withdraw()
                    # Delay to ensure window is hidden
                    root.after(200, lambda: self._delayed_snap(self.last_bbox))
                    return
                elif mode == "record":
                    self.start_recording(self.last_bbox)
                    return
            else:
                self.is_use_last_region.set(False)
                messagebox.showwarning("提示", "尚無相關範圍紀錄！\n請先手動選取一次。")

        if self.is_fixed_size.get() and (self.last_width == 0) and mode not in ["pick_point", "pick_aux_point"]:
             messagebox.showwarning("提示", "請先手動拖曳一次以紀錄尺寸。")
             self.is_fixed_size.set(False)
             return
        
        root.withdraw()
        if self.audio_recorder: self.audio_recorder.stop_monitoring()
        time.sleep(0.2)
        
        self.snip_surface = tk.Toplevel(root)
        self.snip_surface.attributes("-fullscreen", True)
        self.snip_surface.attributes("-alpha", 0.3)
        self.snip_surface.attributes("-topmost", True)
        self.snip_surface.config(cursor="target" if self.is_fixed_size.get() else "cross")
        
        self.canvas = tk.Canvas(self.snip_surface, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        if not self.is_fixed_size.get():
            self.canvas.bind("<B1-Motion>", self.on_move_press)
            self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.snip_surface.bind("<Escape>", lambda e: self.cancel_snip())

    def on_button_press(self, event):
        if self.current_mode == "pick_point" or self.current_mode == "pick_aux_point":
            self.on_click_point_selected(event.x_root, event.y_root)
            return
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.is_fixed_size.get(): self.calculate_fixed_rect_and_capture()
        else: self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=3)

    def on_move_press(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        if (x2 - x1) < 5 or (y2 - y1) < 5:
            self.cancel_snip()
            return
        self.last_width, self.last_height = x2 - x1, y2 - y1
        self.size_label.config(text=f"{int(self.last_width)}x{int(self.last_height)}", fg="blue")
        self.finish_snip(x1, y1, x2, y2)

    def on_click_point_selected(self, x, y):
        if self.current_mode == "pick_point":
            self.auto_click_pos = (int(x), int(y))
            self.lbl_click_pos.config(text=f"位置: {self.auto_click_pos}", fg="blue")
        elif self.current_mode == "pick_aux_point":
            self.aux_points.append((int(x), int(y)))
            count = len(self.aux_points)
            self.lbl_aux_count.config(text=f"已設定: {count} 點")
            print(f"Added Aux Point: {x}, {y}")
            
        self.cancel_snip()
        self.frame.winfo_toplevel().deiconify()

    def clear_aux_points(self):
        self.aux_points = []
        self.lbl_aux_count.config(text="0 點")

    def calculate_fixed_rect_and_capture(self):
        x, y, w, h = self.start_x, self.start_y, self.last_width, self.last_height
        anchor = self.anchor_pos.get()
        x1, y1 = x, y
        if anchor == "tr": x1 = x - w
        elif anchor == "bl": y1 = y - h
        elif anchor == "br": x1, y1 = x - w, y - h
        self.rect = self.canvas.create_rectangle(x1, y1, x1+w, y1+h, outline='red', width=3)
        self.snip_surface.update()
        time.sleep(0.05)
        self.finish_snip(x1, y1, x1+w, y1+h)

    def finish_snip(self, x1, y1, x2, y2):
        self.snip_surface.destroy()
        bbox = (int(x1), int(y1), int(x2), int(y2))
        self.last_bbox = bbox
        if self.current_mode == "screenshot":
            self.frame.winfo_toplevel().deiconify()
            self.take_screenshot(bbox)
            if self.record_audio.get(): self.on_device_selected(None)
        elif self.current_mode == "record":
            self.start_recording(bbox)
            
    def _delayed_snap(self, bbox):
        self.take_screenshot(bbox)
        self.frame.winfo_toplevel().deiconify()
        if self.record_audio.get(): self.on_device_selected(None)

    def cancel_snip(self):
        self.snip_surface.destroy()
        self.frame.winfo_toplevel().deiconify()
        if self.record_audio.get(): self.on_device_selected(None)

    def take_screenshot(self, bbox):
        time.sleep(0.1)
        try:
            img = ImageGrab.grab(bbox=bbox)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = f"screenshot_{ts}.png"
            if self.is_manual_save.get():
                fp = filedialog.asksaveasfilename(defaultextension=".png", initialfile=fn, initialdir=self.save_dir)
                if fp: img.save(fp)
            else:
                img.save(os.path.join(self.save_dir, fn))
                self.status_label.config(text=f"已儲存: {fn}")
        except Exception as e: messagebox.showerror("錯誤", str(e))

    def start_recording(self, bbox):
        self.is_recording = True
        if self.is_exclude_window.get(): self.set_window_affinity(True)
        self.frame.winfo_toplevel().deiconify()
        self.btn_record.config(text="停止錄影", bg="black")
        self.btn_capture.config(state="disabled")
        self.device_combo.config(state="disabled")
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_filename = f"video_{ts}.mp4"
        self.audio_filename = f"audio_{ts}.wav"
        self.final_filename = f"record_{ts}.mp4"
        
        if self.record_audio.get() and self.selected_audio_idx is not None and self.audio_recorder:
            self.status_label.config(text="錄影中 (● REC Audio)...", fg="red")
            audio_path = os.path.join(self.save_dir, self.audio_filename)
            self.audio_recorder.start_recording(self.selected_audio_idx, audio_path)
        else:
            self.status_label.config(text="錄影中 (無聲音)...", fg="red")

        self.record_thread = threading.Thread(target=self.record_process, args=(bbox,))
        self.record_thread.daemon = True
        self.record_thread.start()

    def stop_recording(self):
        self.is_recording = False
        self.status_label.config(text="正在處理影片 (背景合併中)...", fg="blue")
        self.set_window_affinity(False)

    def record_process(self, bbox):
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        vid_path = os.path.join(self.save_dir, self.video_filename)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        fps = 15.0 
        out = cv2.VideoWriter(vid_path, fourcc, fps, (w, h))
        self.gdi_capture.initialize(x1, y1, w, h)
        frame_interval = 1.0 / fps 

        try:
            while self.is_recording:
                start_time = time.time()
                frame = self.gdi_capture.capture_frame()
                if frame is not None: out.write(frame)
                elapsed = time.time() - start_time
                if elapsed < frame_interval: time.sleep(frame_interval - elapsed)
        finally:
            out.release()
            self.gdi_capture.release()
            
            has_audio = False
            if self.audio_recorder and self.audio_recorder.is_recording:
                audio_path = os.path.join(self.save_dir, self.audio_filename)
                has_audio = self.audio_recorder.stop_recording(audio_path)

            self.process_media_merge(has_audio)

    def process_media_merge(self, has_audio):
        error_msg = None
        final_name = self.final_filename

        if not has_audio:
            final_name = self.video_filename
        else:
            video_path = os.path.join(self.save_dir, self.video_filename)
            audio_path = os.path.join(self.save_dir, self.audio_filename)
            output_path = os.path.join(self.save_dir, self.final_filename)

            ffmpeg_cmd = "ffmpeg"
            if os.path.exists(os.path.join(os.getcwd(), "ffmpeg.exe")):
                ffmpeg_cmd = os.path.join(os.getcwd(), "ffmpeg.exe")

            cmd = [ffmpeg_cmd, "-y", "-i", video_path, "-i", audio_path, 
                   "-c:v", "copy", "-c:a", "aac", "-shortest", output_path]
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            try:
                subprocess.run(cmd, check=True, startupinfo=startupinfo, timeout=120)
                try:
                    if os.path.exists(video_path): os.remove(video_path)
                    if os.path.exists(audio_path): os.remove(audio_path)
                except: pass
            except subprocess.TimeoutExpired:
                error_msg = "合併超時 (Timeout)"
                final_name = f"{self.video_filename} (未合併)"
            except FileNotFoundError:
                error_msg = "找不到 ffmpeg.exe，請確認已下載並放入資料夾。"
                final_name = f"{self.video_filename} + {self.audio_filename}"
            except Exception as e:
                error_msg = f"合併錯誤: {e}"
                final_name = f"{self.video_filename} (未合併)"

        # Use after to schedule UI update on main thread
        self.frame.after(0, lambda: self.finish_merge_ui(final_name, error_msg))

    def finish_merge_ui(self, filename, error_msg):
        self.btn_record.config(text="開始錄影", bg="#D70000")
        self.btn_capture.config(state="normal")
        self.device_combo.config(state="readonly")
        
        if error_msg:
            self.status_label.config(text=f"錄影完成 (但合併失敗): {filename}", fg="orange")
            messagebox.showwarning("合併問題", f"{error_msg}\n\n影像與聲音檔已分別保留。")
        else:
            self.status_label.config(text=f"錄影完成: {filename}", fg="green")
            messagebox.showinfo("完成", f"檔案已儲存至:\n{filename}")
            
        if self.record_audio.get(): self.on_device_selected(None)

    def start_automation(self):
        if not self.last_bbox:
            messagebox.showwarning("錯誤", "請先手動截圖一次以設定範圍 (或啟用固定範圍)。")
            return
        if not self.auto_click_pos:
            messagebox.showwarning("錯誤", "請先設定翻頁點位置。")
            return
        
        self.frame.winfo_toplevel().withdraw()
        self.is_automating = True
        
        # Stop Control Window
        self.stop_win = tk.Toplevel(self.frame)
        self.stop_win.title("控制")
        self.stop_win.geometry("200x80+10+10")
        self.stop_win.attributes("-topmost", True)
        self.stop_win.protocol("WM_DELETE_WINDOW", self.stop_automation_action)
        
        tk.Label(self.stop_win, text="自動截圖進行中...", fg="blue").pack(pady=5)
        self.lbl_auto_status = tk.Label(self.stop_win, text="準備中 (5s)...")
        self.lbl_auto_status.pack()
        tk.Button(self.stop_win, text="停止 (Stop)", bg="red", fg="white", command=self.stop_automation_action).pack(pady=5)
        
        threading.Thread(target=self.automation_process, daemon=True).start()

    def stop_automation_action(self):
        self.is_automating = False
        if self.stop_win:
            self.stop_win.destroy()
            self.stop_win = None
        self.frame.winfo_toplevel().deiconify()

    def automation_process(self):
        count = self.auto_count.get()
        interval = self.auto_interval.get()
        click_x, click_y = self.auto_click_pos
        
        # 5 second countdown
        for k in range(5, 0, -1):
            if not self.is_automating: return
            self.update_stop_win_label(f"倒數 {k} 秒開始...")
            time.sleep(1.0)
        
        timing = self.aux_click_timing.get()
        
        for i in range(count):
            if not self.is_automating: break
            
            self.update_stop_win_label(f"正在執行第 {i+1}/{count} 張...")
            
            if timing == "pre_capture":
                self.perform_aux_clicks()
                time.sleep(0.5)

            # Capture
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = f"auto_{i+1:03d}_{ts}.png"
            fp = os.path.join(self.save_dir, fn)
            try:
                img = ImageGrab.grab(bbox=self.last_bbox)
                img.save(fp)
                print(f"Captured {i+1}/{count}: {fn}")
            except Exception as e:
                print(f"Capture Error: {e}")

            if i < count - 1: 
                if timing == "before":
                    self.perform_aux_clicks()
                    self.perform_click(click_x, click_y)
                elif timing == "after":
                    self.perform_click(click_x, click_y)
                    self.perform_aux_clicks()
                else:
                    self.perform_click(click_x, click_y)

                time.sleep(interval)
        
        self.is_automating = False
        self.frame.after(0, self.finish_automation_ui)    

    def perform_aux_clicks(self):
        for idx, (ax, ay) in enumerate(self.aux_points):
            if not self.is_automating: break
            self.perform_click(ax, ay)
            time.sleep(0.5)
    
    def update_stop_win_label(self, text):
        if self.stop_win:
             try: self.lbl_auto_status.config(text=text)
             except: pass

    def perform_click(self, x, y):
        try:
            ctypes.windll.user32.SetCursorPos(x, y)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception as e:
            print(f"Click Error: {e}")

    def finish_automation_ui(self):
        if self.stop_win:
            self.stop_win.destroy()
            self.stop_win = None
        self.frame.winfo_toplevel().deiconify()
        messagebox.showinfo("完成", "自動截圖作業已完成。")

    def on_destroy(self):
        """Cleanup resources when the module is closed."""
        self.shared_state.log(f"RecordModule '{self.module_name}' is being destroyed.")
        if self.audio_recorder:
            self.audio_recorder.cleanup()
        self.is_recording = False
        self.is_automating = False
        super().on_destroy()
