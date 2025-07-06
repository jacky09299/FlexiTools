import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
from PIL import Image, ImageTk
import pygame
from moviepy.editor import VideoFileClip
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import queue
import json
import random
import shutil
import tempfile
import numpy as np
import scipy.signal
import wave
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image as PILImage
import logging

# PyAcoustics for audio effects
try:
    import pyroomacoustics as pra
    PYROOM_AVAILABLE = True
except ImportError:
    PYROOM_AVAILABLE = False

# Import Module base class
from main import Module

# Helper classes (JumpToWindow, PlaylistEditor)
class JumpToWindow(tk.Toplevel):
    def __init__(self, video_player_module, playlist, current_index):
        super().__init__(video_player_module.frame.winfo_toplevel())
        self.master_player = video_player_module
        self.title("跳至影片")
        self.geometry("400x500")
        self.transient(video_player_module.frame.winfo_toplevel())
        self.grab_set()
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.listbox = tk.Listbox(frame, selectmode=tk.SINGLE, exportselection=False)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for video_path in playlist:
            self.listbox.insert(tk.END, os.path.basename(video_path))
        if current_index is not None and 0 <= current_index < self.listbox.size():
            self.listbox.selection_set(current_index)
            self.listbox.activate(current_index)
            self.listbox.see(current_index)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        tk.Button(button_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        tk.Button(button_frame, text="確定", command=self.confirm_selection).pack(side=tk.RIGHT)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.listbox.bind("<Double-Button-1>", lambda e: self.confirm_selection())
    def confirm_selection(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("未選擇", "請選擇一個影片。", parent=self)
            return
        selected_index = selection[0]
        self.master_player.jump_to_selected_video(selected_index)
        self.destroy()

class PlaylistEditor(tk.Toplevel):
    def __init__(self, video_player_module, playlist, folder_path, current_mode):
        super().__init__(video_player_module.frame.winfo_toplevel())
        self.master_player = video_player_module
        self.initial_playlist = list(playlist)
        self.folder_path = folder_path
        self.current_mode = current_mode
        self.pending_insert_index = None
        self.title("調整播放順序")
        self.geometry("550x500")
        self.transient(video_player_module.frame.winfo_toplevel())
        self.grab_set()
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        list_frame = tk.Frame(main_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, exportselection=False)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        for video_path in self.initial_playlist:
            self.listbox.insert(tk.END, os.path.basename(video_path))
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        move_frame = tk.LabelFrame(button_frame, text="位置調整")
        move_frame.pack(fill=tk.X, pady=5)
        tk.Button(move_frame, text="上移 ↑", command=self.move_up).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(move_frame, text="下移 ↓", command=self.move_down).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(move_frame, text="移到頂部", command=self.move_to_top).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(move_frame, text="移到底部", command=self.move_to_bottom).pack(fill=tk.X, padx=5, pady=2)
        insert_frame = tk.LabelFrame(button_frame, text="插入操作")
        insert_frame.pack(fill=tk.X, pady=5)
        tk.Button(insert_frame, text="設為待插入", command=self.set_pending_insert).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(insert_frame, text="插入其上", command=self.insert_above).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(insert_frame, text="插入其下", command=self.insert_below).pack(fill=tk.X, padx=5, pady=2)
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(bottom_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        tk.Button(bottom_frame, text="確定", command=self.confirm_changes).pack(side=tk.RIGHT, padx=5)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
    def get_selected_pos(self):
        selection = self.listbox.curselection()
        return selection[0] if selection else None
    def move_item(self, from_pos, to_pos):
        if from_pos is None or to_pos is None: return
        item_text = self.listbox.get(from_pos)
        self.listbox.delete(from_pos)
        self.listbox.insert(to_pos, item_text)
        self.listbox.selection_set(to_pos)
        self.listbox.activate(to_pos)
    def move_up(self):
        pos = self.get_selected_pos()
        if pos is not None and pos > 0: self.move_item(pos, pos - 1)
    def move_down(self):
        pos = self.get_selected_pos()
        if pos is not None and pos < self.listbox.size() - 1: self.move_item(pos, pos + 1)
    def move_to_top(self):
        pos = self.get_selected_pos()
        if pos is not None and pos > 0: self.move_item(pos, 0)
    def move_to_bottom(self):
        pos = self.get_selected_pos()
        if pos is not None and pos < self.listbox.size() - 1: self.move_item(pos, self.listbox.size() - 1)
    def update_pending_highlight(self, old_index=None, new_index=None):
        if old_index is not None: self.listbox.itemconfig(old_index, {'bg': 'white', 'fg': 'black'})
        if new_index is not None: self.listbox.itemconfig(new_index, {'bg': 'lightblue', 'fg': 'black'})
    def set_pending_insert(self):
        pos = self.get_selected_pos()
        if pos is not None:
            self.update_pending_highlight(self.pending_insert_index)
            self.pending_insert_index = pos
            self.update_pending_highlight(new_index=self.pending_insert_index)
    def insert_above(self): self.execute_insert(offset=0)
    def insert_below(self): self.execute_insert(offset=1)
    def execute_insert(self, offset):
        if self.pending_insert_index is None:
            messagebox.showwarning("操作無效", "請先使用「設為待插入」選擇一個來源影片。", parent=self)
            return
        target_pos = self.get_selected_pos()
        if target_pos is None:
            messagebox.showwarning("操作無效", "請選擇一個要插入的目標位置。", parent=self)
            return
        if self.pending_insert_index == target_pos: return
        item_text = self.listbox.get(self.pending_insert_index)
        self.listbox.delete(self.pending_insert_index)
        if self.pending_insert_index < target_pos: insert_pos = target_pos - 1 + offset
        else: insert_pos = target_pos + offset
        self.listbox.insert(insert_pos, item_text)
        self.update_pending_highlight(self.pending_insert_index)
        self.pending_insert_index = None
        self.listbox.selection_set(insert_pos)
        self.listbox.activate(insert_pos)
    def confirm_changes(self):
        new_order_basenames = list(self.listbox.get(0, tk.END))
        if self.current_mode == 'json':
            json_path = os.path.join(self.folder_path, "playlist.json")
            try:
                with open(json_path, 'w', encoding='utf-8') as f: json.dump(new_order_basenames, f, ensure_ascii=False, indent=4)
            except Exception as e:
                messagebox.showerror("儲存失敗", f"無法寫入 playlist.json:\n{e}", parent=self)
                return
        self.master_player.update_playlist_from_editor(new_order_basenames)
        self.destroy()

# --- EQ settings ---
EQ_BANDS = [
    (20, 32), (32, 63), (63, 125), (125, 250), (250, 500),
    (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)
]
EQ_PRESETS = {
    "無": [0]*10, "家庭式立體聲": [6, 6, 4.1, 4, 1.7, 2, 1.7, 4, 4.1, 6], "可攜式喇叭": [8, 8, 5.4, 5, 2.7, 3, 2.3, 4, 3.6, 5],
    "汽車": [8, 8, 4.8, 3, 0.1, 0, 0.7, 4, 4.8, 7], "電視": [3, 3, 4.5, 8, 2.8, 0, 1.3, 6, 6.1, 8],
    "音質": [2, 3, 2, -1, 0, 0, 1, 2, 1, 2], "低音增強": [6, 6, 6, 3, 0, 0, 0, 0, 0, 0],
    "低音減弱": [-6, -6, -3, 0, 0, 0, 0, 0, 0, 0], "高音增強": [-6, -6, -3, 0, 0, 0, 3, 6, 6, 6],
    "高音減弱": [3, 3, 0, 0, 0, 0, 0, -3, -6, -6], "響度": [6, 6, 3, 0, 0, 0, 0, 3, 6, 6],
    "沙發音樂": [-3, -3, -3, 0, 3, 3, 3, 3, 0, 0], "小喇叭": [3, 3, 3, 0, 0, 0, 0, 3, 6, 6],
    "口語清晰": [-6, -6, -3, 0, 3, 3, 3, 3, 0, 0], "聲音增強": [0, 0, 0, 0, 3, 6, 6, 3, 0, 0],
    "古典": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2], "舞曲": [6, 6, 3, 0, 0, 0, 0, 0, -6, -6],
    "深沉": [6, 6, 3, 0, 0, 0, 0, -3, -6, -6], "電子": [6, 6, 3, 0, 0, 0, 0, 3, 6, 6],
    "饒舌": [6, 6, 3, 0, 3, 3, 3, 0, 0, 0], "爵士": [3, 3, 0, 0, 0, 3, 3, 0, 3, 3],
    "拉丁": [0, 0, 0, 0, 3, 3, 3, 3, 6, 6], "鋼琴": [0, 0, 0, 0, 3, 3, 3, 3, 0, 0],
    "流行": [-3, -3, -3, -3, 3, 3, 3, 3, -3, -3], "R&B": [6, 6, 3, 0, 0, 0, 3, 3, 0, 0],
    "搖滾": [3, 3, 3, 0, 0, 0, 0, 3, 3, 3],
}

def get_equalizer_gains(mode):
    return EQ_PRESETS.get(mode, [0]*10)

def db_to_gain(db):
    return 10 ** (db / 20)

def apply_equalizer(wav_path, out_path, gains):
    with wave.open(wav_path, 'rb') as wf:
        params = wf.getparams()
        n_channels, sampwidth, framerate, n_frames = params[:4]
        audio_data = wf.readframes(n_frames)
        dtype = np.int16 if sampwidth == 2 else np.uint8
        data = np.frombuffer(audio_data, dtype=dtype)
        if n_channels == 2:
            data = data.reshape(-1, 2)
        else:
            data = data.reshape(-1, 1)

        # Use float64 for processing to avoid casting errors and precision loss.
        signal = data.astype(np.float64)
        eq_signal = np.zeros_like(signal, dtype=np.float64)

        # If all gains are 0 dB (gain is approx 1), the signal is unchanged.
        if all(abs(g) < 0.1 for g in gains):
            eq_signal = signal
        else:
            # Implement a basic graphic EQ by summing filtered bands
            for i, (low, high) in enumerate(EQ_BANDS):
                gain = db_to_gain(gains[i])
                if abs(gain - 1.0) < 1e-4: # Gain is 1 (0 dB), so this band is unchanged
                    # This is a simplification. A true graphic EQ would use parallel filters.
                    # For this implementation, we just add the gained components.
                    # A gain of 1 means we should add the component filtered for this band.
                    pass # Let's just add all gained components.

                nyquist = framerate / 2.0
                if low >= nyquist: continue
                high = min(high, nyquist - 1)
                if low >= high: continue
                
                b, a = scipy.signal.butter(2, [low/nyquist, high/nyquist], btype='band')
                
                for ch in range(n_channels):
                    filtered_ch = scipy.signal.lfilter(b, a, signal[:, ch])
                    eq_signal[:, ch] += filtered_ch * gain
        
        # If the result is all zeros (e.g., all gains were -inf), use the original signal
        if np.max(np.abs(eq_signal)) < 1e-6:
             eq_signal = signal

        # Normalize to prevent clipping
        max_val = np.max(np.abs(eq_signal))
        if max_val > 0:
            scale = 32767.0 / max_val
            eq_signal = eq_signal * scale
        
        # Clip and convert back to int16
        final_signal = np.clip(eq_signal, -32768, 32767).astype(np.int16)
        
        with wave.open(out_path, 'wb') as wf_out:
            wf_out.setparams(params)
            wf_out.writeframes(final_signal.tobytes())

# --- [NEW] Effects Settings Window ---
class EffectsSettingsWindow(tk.Toplevel):
    def __init__(self, parent_player):
        super().__init__(parent_player.frame.winfo_toplevel())
        self.transient(parent_player.frame.winfo_toplevel())
        self.grab_set()
        self.title("音訊效果設定")
        self.parent_player = parent_player
        self.result = None

        # Load current settings from parent
        self.settings = self.parent_player.audio_effects_settings.copy()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        mic_env_tab = ttk.Frame(notebook, padding="10")
        processing_tab = ttk.Frame(notebook, padding="10")
        eq_tab = ttk.Frame(notebook, padding="10")

        notebook.add(mic_env_tab, text="麥克風與環境")
        notebook.add(processing_tab, text="音訊處理")
        notebook.add(eq_tab, text="等化器")

        # --- Mic & Environment Tab ---
        mic_frame = ttk.LabelFrame(mic_env_tab, text="模擬收音裝置", padding="5")
        mic_frame.pack(fill=tk.X, pady=5)
        self.mic_var = tk.StringVar(value=self.settings.get("mic_sim", "無"))
        mic_options = ["無", "手機", "筆電", "錄音筆", "會議麥克風"]
        ttk.Combobox(mic_frame, textvariable=self.mic_var, values=mic_options, state="readonly").pack(fill=tk.X, expand=True)

        env_frame = ttk.LabelFrame(mic_env_tab, text="播放器環境", padding="5")
        env_frame.pack(fill=tk.X, pady=5)
        self.env_var = tk.StringVar(value=self.settings.get("environment", "無"))
        env_options = ["無", "小房間", "浴室", "教室", "音樂廳", "廢棄廠房", "錄音室", "會議室", "地下道", "劇場前排", "戶外", "車內", "購物中心中庭"]
        ttk.Combobox(env_frame, textvariable=self.env_var, values=env_options, state="readonly").pack(fill=tk.X, expand=True)

        pos_frame = ttk.LabelFrame(mic_env_tab, text="播放器位置", padding="5")
        pos_frame.pack(fill=tk.X, pady=5)
        self.pos_var = tk.StringVar(value=self.settings.get("position", "無"))
        pos_options = ["無", "前方", "後方", "上方", "下方", "左方", "右方", "360度環繞"]
        ttk.Combobox(pos_frame, textvariable=self.pos_var, values=pos_options, state="readonly").pack(fill=tk.X, expand=True)

        # --- Processing Tab ---
        proc_frame = ttk.LabelFrame(processing_tab, text="處理選項", padding="5")
        proc_frame.pack(fill=tk.X, pady=5)
        self.denoise_var = tk.BooleanVar(value=self.settings.get("denoise", False))
        self.aec_var = tk.BooleanVar(value=self.settings.get("aec", False))
        ttk.Checkbutton(proc_frame, text="降噪", variable=self.denoise_var).pack(anchor=tk.W)
        ttk.Checkbutton(proc_frame, text="回音消除 (AEC)", variable=self.aec_var).pack(anchor=tk.W)

        # --- Equalizer Tab ---
        eq_options_frame = ttk.LabelFrame(eq_tab, text="等化器預設", padding="5")
        eq_options_frame.pack(fill=tk.X, pady=5)
        self.eq_mode_var = tk.StringVar(value=self.settings.get("eq_mode", "無"))
        eq_options = list(EQ_PRESETS.keys())
        self.eq_menu = ttk.Combobox(eq_options_frame, values=eq_options, textvariable=self.eq_mode_var, state="readonly")
        self.eq_menu.pack(fill=tk.X, expand=True)
        self.eq_menu.bind("<<ComboboxSelected>>", self.draw_equalizer_visualization)

        self.eq_canvas = tk.Label(eq_tab)
        self.eq_canvas.pack(pady=10)
        self.eq_image = None
        self.draw_equalizer_visualization()

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="確定", command=self.ok).pack(side=tk.RIGHT)

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.wait_window(self)

    def draw_equalizer_visualization(self, event=None):
        gains = get_equalizer_gains(self.eq_mode_var.get())
        band_centers = [int((low * high) ** 0.5) for (low, high) in EQ_BANDS]
        def fmt_freq(f): return f"{f//1000}kHz" if f >= 1000 else f"{f}Hz"
        xtick_labels = [fmt_freq(f) for f in band_centers]

        fig, ax = plt.subplots(figsize=(5, 2.5), dpi=100)
        ax.bar(range(len(band_centers)), gains, width=0.7, color="#4A90E2")
        ax.set_xticks(range(len(band_centers)))
        ax.set_xticklabels(xtick_labels, rotation=45, ha='right', fontsize=8)
        ax.set_ylim(-12, 12)
        ax.set_ylabel("dB")
        ax.grid(True, axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout(pad=0.5)

        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        img = PILImage.open(buf)
        self.eq_image = ImageTk.PhotoImage(img)

        if self.eq_canvas and self.eq_canvas.winfo_exists():
            self.eq_canvas.config(image=self.eq_image)
        buf.close()

    def ok(self):
        self.settings["mic_sim"] = self.mic_var.get()
        self.settings["environment"] = self.env_var.get()
        self.settings["position"] = self.pos_var.get()
        self.settings["denoise"] = self.denoise_var.get()
        self.settings["aec"] = self.aec_var.get()
        self.settings["eq_mode"] = self.eq_mode_var.get()
        self.result = self.settings
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()

class VideoPlayerModule(Module):
    def __init__(self, master, shared_state, module_name="VideoPlayer", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"Initializing VideoPlayerModule: {self.module_name}", level=logging.INFO)

        self.window_width = 960
        self.window_height = 700
        self.play_mode_var = tk.StringVar(value="ctime")
        self.current_folder_path = None
        self.temp_cache_dir = None
        self.temp_audio_path = None
        self.canvas_size_lock = threading.Lock()
        initial_canvas_w = self.frame.winfo_width() if self.frame.winfo_exists() and self.frame.winfo_width() > 1 else self.window_width
        initial_canvas_h = self.frame.winfo_height() - 200 if self.frame.winfo_exists() and self.frame.winfo_height() > 200 else self.window_height - 200
        self.last_known_canvas_size = (max(1, initial_canvas_w), max(1, initial_canvas_h))

        self.video_path = ""
        self.audio_path = ""
        self.is_playing = False
        self.is_paused = False
        self.after_id = None
        self.playlist = []
        self.current_playlist_index = -1
        self.unplayed_indices = []
        self.history_indices = []

        self.max_workers = multiprocessing.cpu_count()
        self.buffer_size = 120
        self.frame_buffer = {}
        self.processing_queue = queue.Queue()
        self.processing_thread = None
        self.frame_reader_thread = None
        self.stop_processing = threading.Event()

        self.total_frames = 0
        self.fps = 25
        self.current_frame_idx = -1
        self.frames_processed_count = 0
        self.video_duration = 0
        self.video_width = 0
        self.video_height = 0

        self.seeking = False
        self.seek_request_frame = -1
        self.seek_lock = threading.Lock()

        self.start_time = None
        self.pause_time = None

        # --- [NEW] Audio Effects Settings ---
        self.audio_effects_settings = {
            "mic_sim": "無",
            "environment": "無",
            "position": "無",
            "denoise": False,
            "aec": False,
            "eq_mode": "無",
        }

        try:
            pygame.mixer.init()
            self.shared_state.log("Pygame mixer initialized.", level=logging.INFO)
        except pygame.error as e:
            self.shared_state.log(f"Failed to initialize pygame.mixer: {e}", level=logging.ERROR)

        self.volume_var = tk.DoubleVar(value=100)
        self.create_ui()
        if pygame.mixer.get_init():
             self.set_volume(self.volume_var.get())
        else:
            if hasattr(self, 'volume_scale') and self.volume_scale:
                self.volume_scale.config(state=tk.DISABLED)

    def create_ui(self):
        self.canvas = tk.Canvas(self.frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.on_resize)

        selection_area = tk.Frame(self.frame)
        selection_area.pack(fill=tk.X, padx=10, pady=5)

        file_selection_frame = tk.LabelFrame(selection_area, text="檔案選擇")
        file_selection_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.btn_select_file = tk.Button(file_selection_frame, text="選擇檔案", command=self.select_file)
        self.btn_select_file.pack(pady=5, padx=10)
        self.btn_select_folder = tk.Button(file_selection_frame, text="選擇資料夾", command=self.select_folder)
        self.btn_select_folder.pack(pady=5, padx=10)

        mode_selection_frame = tk.LabelFrame(selection_area, text="播放模式")
        mode_selection_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Radiobutton(mode_selection_frame, text="按建立時間", variable=self.play_mode_var, value="ctime", command=self.on_play_mode_change).pack(anchor=tk.W, padx=10)
        ttk.Radiobutton(mode_selection_frame, text="按JSON順序", variable=self.play_mode_var, value="json", command=self.on_play_mode_change).pack(anchor=tk.W, padx=10)
        ttk.Radiobutton(mode_selection_frame, text="隨機播放", variable=self.play_mode_var, value="random", command=self.on_play_mode_change).pack(anchor=tk.W, padx=10)
        self.btn_adjust_order = tk.Button(mode_selection_frame, text="調整播放順序", state=tk.DISABLED, command=self.open_playlist_editor)
        self.btn_adjust_order.pack(pady=5, padx=10, side=tk.LEFT)
        self.btn_jump_to = tk.Button(mode_selection_frame, text="跳至影片...", state=tk.DISABLED, command=self.open_jump_to_window)
        self.btn_jump_to.pack(pady=5, padx=10, side=tk.LEFT)

        # --- [NEW] Audio Effects Button ---
        effects_frame = tk.LabelFrame(selection_area, text="音訊")
        effects_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.btn_effects = tk.Button(effects_frame, text="音訊效果...", command=self.open_effects_window)
        self.btn_effects.pack(pady=5, padx=10)
        if not PYROOM_AVAILABLE:
            self.btn_effects.config(state=tk.DISABLED)

        timeline_frame = tk.Frame(self.frame)
        timeline_frame.pack(fill=tk.X, padx=10, pady=5)
        time_info_frame = tk.Frame(timeline_frame)
        time_info_frame.pack(fill=tk.X)
        self.time_current_label = tk.Label(time_info_frame, text="00:00", font=("Arial", 10))
        self.time_current_label.pack(side=tk.LEFT)
        self.time_total_label = tk.Label(time_info_frame, text="00:00", font=("Arial", 10))
        self.time_total_label.pack(side=tk.RIGHT)
        self.timeline_var = tk.DoubleVar()
        self.timeline_scale = ttk.Scale(timeline_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.timeline_var, command=self.on_timeline_change)
        self.timeline_scale.pack(fill=tk.X, pady=5)
        self.timeline_scale.bind("<Button-1>", self.on_timeline_press)
        self.timeline_scale.bind("<ButtonRelease-1>", self.on_timeline_release)

        control_frame = tk.Frame(self.frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        left_controls = tk.Frame(control_frame)
        left_controls.pack(side=tk.LEFT)
        self.btn_prev = tk.Button(left_controls, text="上一個", command=self.play_previous_video, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=5)
        self.btn_play_pause = tk.Button(left_controls, text="播放", command=self.toggle_play_pause, state=tk.DISABLED)
        self.btn_play_pause.pack(side=tk.LEFT, padx=5)
        self.btn_next = tk.Button(left_controls, text="下一個", command=self.play_next_video, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        right_controls = tk.Frame(control_frame)
        right_controls.pack(side=tk.RIGHT)
        self.volume_scale = ttk.Scale(right_controls, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.volume_var, command=self.set_volume, length=120)
        self.volume_scale.pack(side=tk.RIGHT)
        tk.Label(right_controls, text="音量:").pack(side=tk.RIGHT)
        self.progress_label = tk.Label(control_frame, text="請選擇檔案或資料夾", fg="blue")
        self.progress_label.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)

        self.shared_state.log("VideoPlayerModule UI created.", level=logging.INFO)

    def open_effects_window(self):
        if not PYROOM_AVAILABLE:
            messagebox.showerror("錯誤", "缺少 'pyroomacoustics' 套件，無法使用音訊效果功能。", parent=self.frame.winfo_toplevel())
            return
        
        window = EffectsSettingsWindow(self)
        if window.result is not None:
            # Check if settings actually changed
            if window.result != self.audio_effects_settings:
                self.audio_effects_settings = window.result
                self.shared_state.log(f"音訊效果已更新: {self.audio_effects_settings}", level=logging.INFO)
                # If a video is playing, restart it to apply new effects
                if self.is_playing or self.is_paused:
                    messagebox.showinfo("套用效果", "音訊效果已變更，將重新載入目前的影片以套用。", parent=self.frame.winfo_toplevel())
                    self.stop_video()
                    self.play_current_video_in_playlist()
            else:
                self.shared_state.log("音訊效果未變更。", level=logging.DEBUG)

    def apply_audio_effects(self, input_wav, output_wav):
        """
        Applies the chain of audio effects based on self.audio_effects_settings.
        New Order: mic_sim -> aec -> denoise -> eq -> environment -> position
        """
        if not PYROOM_AVAILABLE:
            shutil.copy(input_wav, output_wav)
            return output_wav

        self.shared_state.log(f"開始套用音訊效果: {self.audio_effects_settings}", level=logging.INFO)
        
        # Read the input file
        wf = wave.open(input_wav, 'rb')
        params = wf.getparams()
        n_channels, sampwidth, framerate, n_frames = params[:4]
        audio_data = wf.readframes(n_frames)
        wf.close()
        
        if sampwidth == 2:
            signal = np.frombuffer(audio_data, dtype=np.int16).astype(np.float64)
        else:
            signal = np.frombuffer(audio_data, dtype=np.uint8).astype(np.float64)

        if n_channels == 2:
            signal = signal.reshape(-1, 2)
        else:
            signal = signal.reshape(-1, 1)
        
        current_signal = signal
        
        # 1. Microphone Simulation (Placeholder)
        mic_sim = self.audio_effects_settings.get("mic_sim", "無")
        if mic_sim != "無":
            self.shared_state.log(f"模擬麥克風: {mic_sim}", level=logging.DEBUG)
            pass

        # 2. AEC (Echo Cancellation) - Placeholder
        if self.audio_effects_settings.get("aec", False):
            self.shared_state.log("AEC (回音消除) - 功能待實現", level=logging.WARNING)
            pass

        # 3. Denoise
        if self.audio_effects_settings.get("denoise", False):
            self.shared_state.log("套用降噪...", level=logging.DEBUG)
            try:
                if current_signal.ndim > 1:
                    processed_channels = []
                    for ch in range(current_signal.shape[1]):
                        denoiser = pra.denoise.SpectralSub(n_fft=512, db_reduc=10, look_back=5, beta=10, alpha=2)
                        processed_channels.append(denoiser.process(current_signal[:, ch]))
                    current_signal = np.stack(processed_channels, axis=1)
                else:
                    denoiser = pra.denoise.SpectralSub(n_fft=512, db_reduc=10, look_back=5, beta=10, alpha=2)
                    current_signal = denoiser.process(current_signal.flatten()).reshape(-1, 1)
            except Exception as e:
                self.shared_state.log(f"降噪失敗: {e}", level=logging.ERROR)

        # 4. Equalizer
        eq_mode = self.audio_effects_settings.get("eq_mode", "無")
        if eq_mode and eq_mode != "無":
            self.shared_state.log(f"套用等化器: {eq_mode}", level=logging.INFO)
            gains = get_equalizer_gains(eq_mode)
            eq_signal = np.zeros_like(current_signal, dtype=np.float64)

            if all(abs(g) < 0.1 for g in gains):
                eq_signal = current_signal
            else:
                for i, (low, high) in enumerate(EQ_BANDS):
                    gain = db_to_gain(gains[i])
                    if abs(gain - 1.0) < 1e-4:
                        continue
                    nyquist = framerate / 2.0
                    if low >= nyquist: continue
                    high = min(high, nyquist - 1)
                    if low >= high: continue
                    
                    b, a = scipy.signal.butter(2, [low/nyquist, high/nyquist], btype='band')
                    
                    # Apply filter to each channel
                    if current_signal.ndim > 1:
                        for ch in range(current_signal.shape[1]):
                            filtered_ch = scipy.signal.lfilter(b, a, current_signal[:, ch])
                            eq_signal[:, ch] += filtered_ch * gain
                    else:
                        filtered_ch = scipy.signal.lfilter(b, a, current_signal.flatten())
                        eq_signal = eq_signal.flatten()
                        eq_signal += filtered_ch * gain
                        eq_signal = eq_signal.reshape(-1, 1)

            if np.max(np.abs(eq_signal)) < 1e-6:
                 eq_signal = current_signal
            current_signal = eq_signal

        # 5. Environment & 6. Position
        environment = self.audio_effects_settings.get("environment", "無")
        position = self.audio_effects_settings.get("position", "無")

        if environment != "無" or position != "無":
            self.shared_state.log(f"模擬環境: {environment}, 位置: {position}", level=logging.DEBUG)
            try:
                env_presets = {
                    "小房間": ([4, 5, 3], 0.2), "浴室": ([2, 3, 2.5], 0.05),
                    "教室": ([10, 15, 4], 0.3), "音樂廳": ([50, 80, 20], 0.4),
                    "廢棄廠房": ([40, 60, 15], 0.1), "錄音室": ([5, 6, 3], 0.8),
                    "會議室": ([8, 12, 3.5], 0.5), "地下道": ([3, 50, 4], 0.02),
                    "劇場前排": ([30, 40, 15], 0.6), "戶外": (None, None),
                    "車內": ([2, 3, 1.5], 0.4), "購物中心中庭": ([50, 50, 30], 0.2)
                }
                room_dim, absorption = env_presets.get(environment, (None, None))

                if environment == "戶外":
                    # For outdoor, we can't simulate reverb, but we can still do positioning
                    # We'll create a stereo signal by delaying one channel slightly for non-center positions
                    if position not in ["無", "前方", "360度環繞"]:
                        self.shared_state.log("戶外模式簡化位置模擬...", level=logging.DEBUG)
                        mono_signal = np.mean(current_signal, axis=1) if current_signal.ndim > 1 else current_signal.flatten()
                        delay_samples = 0
                        if position == "左方": delay_samples = int(0.0005 * framerate) # 0.5ms delay for right channel
                        elif position == "右方": delay_samples = -int(0.0005 * framerate) # 0.5ms delay for left channel
                        
                        if delay_samples > 0: # Delay right channel
                            left = mono_signal
                            right = np.roll(mono_signal, delay_samples)
                            right[:delay_samples] = 0
                        elif delay_samples < 0: # Delay left channel
                            right = mono_signal
                            left = np.roll(mono_signal, -delay_samples)
                            left[:-delay_samples] = 0
                        else:
                            left = right = mono_signal
                        current_signal = np.column_stack([left, right])

                elif room_dim:
                    signal_for_room = current_signal
                    if current_signal.ndim > 1:
                        self.shared_state.log("環境模擬前將音訊轉為單聲道。", level=logging.DEBUG)
                        signal_for_room = np.mean(signal_for_room, axis=1)

                    room = pra.ShoeBox(room_dim, fs=framerate, materials=pra.Material(absorption), max_order=3)
                    
                    # Create a stereo microphone array
                    mic_center = np.array(room_dim) / 2.0
                    mic_locs = np.c_[
                        mic_center + np.array([-0.1, 0, 0]),  # Left mic
                        mic_center + np.array([0.1, 0, 0]),   # Right mic
                    ]
                    room.add_microphone_array(mic_locs)

                    pos_presets = {
                        "前方": mic_center + np.array([0, -2, 0]), "後方": mic_center + np.array([0, 2, 0]),
                        "上方": mic_center + np.array([0, 0, 1.5]), "下方": mic_center + np.array([0, 0, -1.5]),
                        "左方": mic_center + np.array([-1.5, 0, 0]), "右方": mic_center + np.array([1.5, 0, 0]),
                        "360度環繞": "surround"
                    }
                    source_pos = pos_presets.get(position, mic_center + np.array([0, -2, 0]))

                    if position == "360度環繞":
                        self.shared_state.log("360度環繞 - 簡化模擬", level=logging.WARNING)
                        t = np.arange(len(signal_for_room)) / framerate
                        radius = 2.0
                        x = mic_center[0] + radius * np.cos(2 * np.pi * 0.2 * t)
                        y = mic_center[1] + radius * np.sin(2 * np.pi * 0.2 * t)
                        z = np.full_like(x, mic_center[2])
                        source_path = np.c_[x, y, z]
                        room.add_source(source_path, signal=signal_for_room)
                    else:
                        source_pos = np.clip(source_pos, 0.1, np.array(room_dim) - 0.1)
                        room.add_source(source_pos, signal=signal_for_room)

                    room.simulate()
                    
                    # Get the two channels from the stereo microphone array
                    sim_len = len(signal_for_room)
                    left_channel = room.mic_array.signals[0, :sim_len]
                    right_channel = room.mic_array.signals[1, :sim_len]
                    current_signal = np.column_stack([left_channel, right_channel])

            except Exception as e:
                self.shared_state.log(f"環境模擬失敗: {e}", level=logging.ERROR)

        # Final normalization and conversion
        # Ensure output is stereo if we processed it as such
        final_params = list(params)
        if current_signal.ndim > 1 and current_signal.shape[1] == 2:
            final_params[0] = 2 # Set n_channels to 2
        
        current_signal_float = np.array(current_signal, dtype=np.float64)
        max_abs_val = np.max(np.abs(current_signal_float))
        
        if max_abs_val > 0:
            scaling_factor = 32767.0 / max_abs_val
            current_signal_float = current_signal_float * scaling_factor
        
        processed_signal_int = np.clip(current_signal_float, -32768, 32767).astype(np.int16)
        
        with wave.open(output_wav, 'wb') as wf_out:
            wf_out.setparams(tuple(final_params))
            wf_out.writeframes(processed_signal_int.tobytes())
            
        self.shared_state.log("音訊效果套用完畢。", level=logging.INFO)
        return output_wav

    def on_destroy(self):
        self.shared_state.log(f"VideoPlayerModule {self.module_name} on_destroy called.", level=logging.INFO)
        self.stop_video()
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            self.shared_state.log("Pygame mixer quit by VideoPlayerModule.", level=logging.INFO)
        self.cleanup_temp_cache()
        self.playlist = []
        self.current_playlist_index = -1
        if self.after_id:
            if self.frame and self.frame.winfo_exists():
                try:
                    self.frame.after_cancel(self.after_id)
                except tk.TclError:
                    pass
            self.after_id = None
        super().on_destroy()
        self.shared_state.log(f"VideoPlayerModule {self.module_name} destroyed.", level=logging.INFO)

    def cleanup_temp_cache(self):
        if self.temp_cache_dir and os.path.exists(self.temp_cache_dir):
            try:
                shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
            except Exception as e:
                self.shared_state.log(f"Error cleaning up temp cache: {e}", level=logging.ERROR)
        self.temp_cache_dir = None
        self.temp_audio_path = None
        self.temp_video_path = None

    def start_playlist(self, files_list):
        self.stop_video()
        self.playlist = files_list
        self.current_playlist_index = -1
        if self.play_mode_var.get() == 'random':
            self.reset_random_playlist()
            if self.unplayed_indices:
                self.current_playlist_index = self.unplayed_indices.pop(0)
                if self.current_playlist_index != -1:
                    self.history_indices.append(self.current_playlist_index)
        else:
            self.current_playlist_index = 0 if self.playlist else -1
        self.play_current_video_in_playlist()

    def extract_audio(self, video_path_to_extract):
        self.cleanup_temp_cache()
        try:
            video_dir = os.path.dirname(video_path_to_extract)
            self.temp_cache_dir = tempfile.mkdtemp(prefix='.vidplayer_cache_', dir=video_dir)
            
            temp_wav_path = os.path.join(self.temp_cache_dir, "temp.wav")
            with VideoFileClip(video_path_to_extract) as video:
                if video.audio is None:
                    raise Exception("影片不包含音軌。")
                video.audio.write_audiofile(temp_wav_path, codec='pcm_s16le', logger=None)

            # Apply audio effects chain if any are active
            effects_active = any(self.audio_effects_settings.get(k, "無" if isinstance(self.audio_effects_settings.get(k), str) else False) not in [False, "無"] for k in self.audio_effects_settings)
            
            path_for_ffmpeg = temp_wav_path
            if effects_active:
                self.shared_state.log("偵測到有效音訊效果，開始處理...", level=logging.INFO)
                effects_out_path = os.path.join(self.temp_cache_dir, "temp_effects.wav")
                self.apply_audio_effects(temp_wav_path, effects_out_path)
                path_for_ffmpeg = effects_out_path
            else:
                self.shared_state.log("無有效音訊效果，跳過處理。", level=logging.DEBUG)
            
            # --- Convert final WAV to MP3 for playback ---
            self.temp_audio_path = os.path.join(self.temp_cache_dir, "audio.mp3")
            cmd = f'ffmpeg -y -loglevel error -i "{path_for_ffmpeg}" -vn -ar 44100 -ac 2 -b:a 192k "{self.temp_audio_path}"'
            
            os.system(cmd)

            if not os.path.exists(self.temp_audio_path) or os.path.getsize(self.temp_audio_path) == 0:
                raise Exception(f"FFmpeg 無法建立或建立了空的音訊檔: {self.temp_audio_path}")

            self.shared_state.log(f"音訊已提取: {self.temp_audio_path}", level=logging.INFO)
            return self.temp_audio_path
        except Exception as e:
            self.shared_state.log(f"提取音訊時發生錯誤: {e}", level=logging.ERROR)
            self.cleanup_temp_cache()
            raise

    def open_jump_to_window(self):
        if not self.playlist: return
        JumpToWindow(self, self.playlist, self.current_playlist_index)

    def jump_to_selected_video(self, new_index):
        if self.current_playlist_index == new_index: return
        mode = self.play_mode_var.get()
        if mode == 'random':
            self.current_playlist_index = new_index
            all_indices = list(range(len(self.playlist)))
            self.unplayed_indices = [i for i in all_indices if i not in self.history_indices and i != self.current_playlist_index]
            random.shuffle(self.unplayed_indices)
        else:
            self.current_playlist_index = new_index
        self.stop_video()
        self.play_current_video_in_playlist()

    def on_play_mode_change(self):
        mode = self.play_mode_var.get()
        if mode == "json" and self.current_folder_path:
            if hasattr(self, 'btn_adjust_order'): self.btn_adjust_order.config(state=tk.NORMAL)
        else:
            if hasattr(self, 'btn_adjust_order'): self.btn_adjust_order.config(state=tk.DISABLED)
        if self.playlist:
            if mode == "random":
                self.reset_random_playlist()
            self.rebuild_playlist()
            if mode == 'random' and not self.is_playing and self.unplayed_indices:
                 self.play_next_video()

    def reset_random_playlist(self):
        if not self.playlist:
            self.unplayed_indices, self.history_indices = [], []
            return
        all_indices = list(range(len(self.playlist)))
        current_video_playing_idx = self.current_playlist_index
        self.history_indices = []
        potential_unplayed = [i for i in all_indices if i != current_video_playing_idx]
        random.shuffle(potential_unplayed)
        self.unplayed_indices = potential_unplayed

    def rebuild_playlist(self):
        if not self.playlist: return
        current_video_path = None
        if self.current_playlist_index != -1 and self.current_playlist_index < len(self.playlist):
            current_video_path = self.playlist[self.current_playlist_index]
        mode = self.play_mode_var.get()
        if mode == "ctime":
            self.playlist.sort(key=lambda p: os.path.getctime(p))
        elif mode == "json" and self.current_folder_path:
            self.playlist = self.sort_by_json(self.playlist, self.current_folder_path)
        if current_video_path and mode != "random":
            try: self.current_playlist_index = self.playlist.index(current_video_path)
            except ValueError: self.current_playlist_index = 0 if self.playlist else -1
        elif mode != "random":
             self.current_playlist_index = 0 if self.playlist else -1
        self.update_nav_buttons_state()
        self.update_module_title()

    def sort_by_json(self, file_paths, folder_path):
        json_path = os.path.join(folder_path, "playlist.json")
        disk_basenames = {os.path.basename(p) for p in file_paths}
        json_basenames = []
        json_exists = os.path.exists(json_path)
        if json_exists:
            try: 
                with open(json_path, 'r', encoding='utf-8') as f: json_basenames = json.load(f)
            except (json.JSONDecodeError, IOError): json_exists = False
        if not json_exists:
            sorted_by_ctime_paths = sorted(file_paths, key=lambda p: os.path.getctime(p))
            json_basenames = [os.path.basename(p) for p in sorted_by_ctime_paths]
            try:
                with open(json_path, 'w', encoding='utf-8') as f: json.dump(json_basenames, f, ensure_ascii=False, indent=4)
            except IOError: pass
            return [os.path.join(folder_path, name) for name in json_basenames if name in disk_basenames]
        json_basenames_set = set(json_basenames)
        deleted_files = json_basenames_set - disk_basenames
        new_files = disk_basenames - json_basenames_set
        final_json_list = [name for name in json_basenames if name not in deleted_files]
        final_json_list.extend(sorted(list(new_files)))
        if deleted_files or new_files:
            try:
                with open(json_path, 'w', encoding='utf-8') as f: json.dump(final_json_list, f, ensure_ascii=False, indent=4)
            except IOError: pass
        return [os.path.join(folder_path, basename) for basename in final_json_list if basename in disk_basenames]

    def open_playlist_editor(self):
        if not self.playlist or not self.current_folder_path: return
        PlaylistEditor(self, self.playlist, self.current_folder_path, self.play_mode_var.get())

    def update_playlist_from_editor(self, new_order_basenames):
        current_video_path = None
        if self.current_playlist_index != -1 and self.current_playlist_index < len(self.playlist):
             current_video_path = self.playlist[self.current_playlist_index]
        self.playlist = [os.path.join(self.current_folder_path, basename) for basename in new_order_basenames]
        if current_video_path:
            try: self.current_playlist_index = self.playlist.index(current_video_path)
            except ValueError: self.current_playlist_index = 0 if self.playlist else -1
        else: self.current_playlist_index = 0 if self.playlist else -1
        self.update_nav_buttons_state()
        self.update_module_title()

    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Video Folder", parent=self.frame.winfo_toplevel())
        if not folder_path: return
        self.current_folder_path = folder_path
        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv')
        try:
            video_files = [os.path.join(folder_path, item) for item in os.listdir(folder_path) if item.lower().endswith(valid_extensions) and os.path.isfile(os.path.join(folder_path, item))]
        except OSError: return
        if not video_files:
            self.current_folder_path = None
            self.playlist = []
            self.current_playlist_index = -1
            self.update_nav_buttons_state()
            self.update_module_title()
            return
        self.on_play_mode_change()
        self.start_playlist(video_files)

    def select_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv"), ("All files", "*.*")], parent=self.frame.winfo_toplevel())
        if not filepath: return
        self.current_folder_path = None
        if hasattr(self, 'btn_adjust_order'): self.btn_adjust_order.config(state=tk.DISABLED)
        if hasattr(self, 'btn_jump_to'): self.btn_jump_to.config(state=tk.DISABLED)
        self.start_playlist([filepath])

    def update_module_title(self):
        base_title = self.module_name
        if self.is_maximized: base_title = f"[Maximized] {base_title}"
        new_title = base_title
        if self.playlist and self.current_playlist_index != -1:
            filepath = self.playlist[self.current_playlist_index]
            playlist_info = f"({self.current_playlist_index + 1}/{len(self.playlist)})"
            new_title = f"{base_title}: {os.path.basename(filepath)} {playlist_info}"
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.config(text=new_title)

    def play_current_video_in_playlist(self):
        if not self.playlist or not (0 <= self.current_playlist_index < len(self.playlist)):
            self.stop_video()
            self.playlist = []
            self.current_playlist_index = -1
            self.update_module_title()
            if hasattr(self, 'progress_label'): self.progress_label.config(text="Ready")
            self.enable_button_states()
            return
        filepath = self.playlist[self.current_playlist_index]
        self.video_path = filepath
        self.update_module_title()
        if hasattr(self, 'btn_select_file'): self.btn_select_file.config(state=tk.DISABLED)
        if hasattr(self, 'btn_select_folder'): self.btn_select_folder.config(state=tk.DISABLED)
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(state=tk.DISABLED)
        self.update_nav_buttons_state()
        if hasattr(self, 'progress_label'): self.progress_label.config(text="Extracting audio...")
        if self.frame and self.frame.winfo_exists():
            threading.Thread(target=self.prepare_video, args=(filepath,), daemon=True).start()

    def play_next_video(self):
        if not self.playlist: return
        mode = self.play_mode_var.get()
        if mode == 'random':
            if self.current_playlist_index != -1: self.history_indices.append(self.current_playlist_index)
            if not self.unplayed_indices:
                self.reset_random_playlist()
            if self.unplayed_indices:
                self.current_playlist_index = self.unplayed_indices.pop(0)
            else:
                self.stop_video()
                return
        else:
            self.current_playlist_index = (self.current_playlist_index + 1) % len(self.playlist)
        self.stop_video()
        self.play_current_video_in_playlist()

    def play_previous_video(self):
        if not self.playlist: return
        mode = self.play_mode_var.get()
        if mode == 'random':
            if self.history_indices:
                if self.current_playlist_index != -1: self.unplayed_indices.insert(0, self.current_playlist_index)
                self.current_playlist_index = self.history_indices.pop()
            else: return
        else:
            self.current_playlist_index = (self.current_playlist_index - 1 + len(self.playlist)) % len(self.playlist)
        self.stop_video()
        self.play_current_video_in_playlist()

    def update_nav_buttons_state(self):
        mode = self.play_mode_var.get()
        can_go_next, can_go_prev = False, False
        if self.playlist:
            if mode == 'random':
                can_go_next = bool(self.unplayed_indices) or len(self.playlist) > 1
                can_go_prev = bool(self.history_indices)
            else:
                can_go_next = can_go_prev = len(self.playlist) > 1
        if hasattr(self, 'btn_prev'): self.btn_prev.config(state=tk.NORMAL if can_go_prev else tk.DISABLED)
        if hasattr(self, 'btn_next'): self.btn_next.config(state=tk.NORMAL if can_go_next else tk.DISABLED)
        if hasattr(self, 'btn_jump_to'): self.btn_jump_to.config(state=tk.NORMAL if self.playlist else tk.DISABLED)

    def update_frame(self):
        if not self.is_playing or self.is_paused:
            if self.after_id:
                if self.frame and self.frame.winfo_exists(): self.frame.after_cancel(self.after_id)
                self.after_id = None
            return
        now = time.time()
        elapsed = now - self.start_time if self.start_time else 0
        target_frame_idx = int(elapsed * self.fps)
        if self.total_frames > 0 and target_frame_idx >= self.total_frames:
            if self.playlist and (len(self.playlist) > 1 or (self.play_mode_var.get() == 'random' and self.unplayed_indices)):
                self.play_next_video()
            else:
                self.stop_video()
            return
        if target_frame_idx != self.current_frame_idx:
            if target_frame_idx in self.frame_buffer:
                self.display_frame(target_frame_idx)
                cleanup_threshold = target_frame_idx - int(self.buffer_size * 0.75)
                frames_to_remove = [idx for idx in self.frame_buffer.keys() if idx < cleanup_threshold]
                for idx in frames_to_remove:
                    del self.frame_buffer[idx]
                self.current_frame_idx = target_frame_idx
                self.update_timeline()
        if self.frame and self.frame.winfo_exists():
             self.after_id = self.frame.after(1, self.update_frame)

    def set_volume(self, value):
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(float(value) / 100)

    def calculate_proportional_size(self, canvas_w, canvas_h, video_w, video_h):
        if video_w == 0 or video_h == 0: return (max(1, canvas_w), max(1, canvas_h))
        canvas_ratio, video_ratio = canvas_w / canvas_h, video_w / video_h
        if canvas_ratio > video_ratio: new_h, new_w = canvas_h, int(canvas_h * video_ratio)
        else: new_w, new_h = canvas_w, int(canvas_w / video_ratio)
        return (max(1, new_w), max(1, new_h))

    def process_frame_batch(self, raw_frames_batch):
        results = []
        with self.canvas_size_lock:
            target_width, target_height = self.last_known_canvas_size
        new_size = self.calculate_proportional_size(target_width, target_height, self.video_width, self.video_height)
        for frame_index, frame_bgr in raw_frames_batch:
            if new_size[0] > 1 and new_size[1] > 1:
                pil_image = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
                results.append((frame_index, pil_image))
        return results

    def display_frame(self, frame_idx):
        if frame_idx in self.frame_buffer:
            if not (self.canvas and self.canvas.winfo_exists()): return
            current_canvas_width, current_canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
            if current_canvas_width <= 1 or current_canvas_height <= 1 : return
            try:
                self.photo = ImageTk.PhotoImage(image=self.frame_buffer[frame_idx])
                self.canvas.delete("all")
                self.canvas.create_image(current_canvas_width / 2, current_canvas_height / 2, anchor=tk.CENTER, image=self.photo)
            except Exception: pass

    def prepare_video(self, filepath):
        try:
            self.stop_processing.clear()
            self.frame_buffer.clear()
            self.frames_processed_count = 0
            self.current_frame_idx = -1
            self.audio_path = self.extract_audio(filepath)
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened(): raise Exception(f"Cannot open video file: {filepath}")
            orig_fps = cap.get(cv2.CAP_PROP_FPS) or 25
            self.fps = orig_fps
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_duration = self.total_frames / self.fps if self.fps > 0 else 0
            self.video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            self.temp_video_path = None
            video_path_for_play = filepath
            if orig_fps > 25:
                if not self.temp_cache_dir:
                    self.temp_cache_dir = tempfile.mkdtemp(prefix='.vidplayer_cache_', dir=os.path.dirname(filepath))
                self.temp_video_path = os.path.join(self.temp_cache_dir, "temp_fps25.mp4")
                cmd = f'ffmpeg -y -loglevel error -i "{filepath}" -r 25 -vsync 2 -c:v libx264 -preset ultrafast -crf 18 -c:a copy "{self.temp_video_path}"'
                os.system(cmd)
                if not os.path.exists(self.temp_video_path) or os.path.getsize(self.temp_video_path) == 0:
                    raise Exception("FFmpeg failed to create FPS=25 temp video.")
                video_path_for_play = self.temp_video_path
                cap2 = cv2.VideoCapture(video_path_for_play)
                self.fps, self.total_frames = cap2.get(cv2.CAP_PROP_FPS) or 25, int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
                self.video_duration = self.total_frames / self.fps if self.fps > 0 else 0
                self.video_width, self.video_height = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap2.release()
            self.video_path = video_path_for_play
            if self.video_width == 0 or self.video_height == 0: raise Exception("Failed to read video dimensions.")
            if self.frame and self.frame.winfo_exists():
                self.frame.after(0, lambda: self.time_total_label.config(text=self.format_time(self.video_duration)))
                self.frame.after(0, lambda: self.timeline_scale.config(to=100))
                self.processing_thread = threading.Thread(target=self.background_processor, daemon=True)
                self.frame_reader_thread = threading.Thread(target=self.read_frames_to_queue, daemon=True)
                self.processing_thread.start()
                self.frame_reader_thread.start()
                self.frame.after(0, lambda: self.progress_label.config(text="Buffering..."))
                def check_buffer_and_play():
                    if self.stop_processing.is_set(): return
                    if 0 in self.frame_buffer:
                        if pygame.mixer.get_init() and self.audio_path:
                            try:
                                pygame.mixer.music.load(self.audio_path)
                                self.frame.after(0, self.start_playback)
                            except pygame.error as e:
                                messagebox.showerror("Audio Error", f"Could not load audio: {e}", parent=self.frame.winfo_toplevel())
                        else:
                             self.frame.after(0, self.start_playback)
                        self.frame.after(0, self.enable_button_states)
                    elif self.frame and self.frame.winfo_exists():
                        self.frame.after(100, check_buffer_and_play)
                if self.frame and self.frame.winfo_exists(): self.frame.after(100, check_buffer_and_play)
        except Exception as e:
            if self.frame and self.frame.winfo_exists(): self.frame.after(0, self.enable_button_states)
            self.stop_video()
            if self.playlist and self.frame and self.frame.winfo_exists(): self.frame.after(100, self.play_next_video)

    def enable_button_states(self):
        if hasattr(self, 'btn_select_file'): self.btn_select_file.config(state=tk.NORMAL)
        if hasattr(self, 'btn_select_folder'): self.btn_select_folder.config(state=tk.NORMAL)
        play_pause_state = tk.NORMAL if self.video_path else tk.DISABLED
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(state=play_pause_state)
        self.update_nav_buttons_state()
        if hasattr(self, 'btn_adjust_order'):
            adj_order_state = tk.NORMAL if (self.play_mode_var.get() == 'json' and self.current_folder_path) else tk.DISABLED
            self.btn_adjust_order.config(state=adj_order_state)
        if hasattr(self, 'progress_label'):
            if self.is_playing and not self.is_paused: self.progress_label.config(text="Playing...")
            elif self.is_paused: self.progress_label.config(text="Paused")
            else:
                if self.playlist and self.current_playlist_index != -1:
                    self.progress_label.config(text=f"Ready ({self.current_playlist_index + 1}/{len(self.playlist)})")
                else: self.progress_label.config(text="Ready. Select file/folder.")

    def stop_video(self):
        self.is_playing = self.is_paused = False
        self.stop_processing.set()
        if self.after_id:
            if self.frame and self.frame.winfo_exists(): self.frame.after_cancel(self.after_id)
            self.after_id = None
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            if self.temp_audio_path and os.path.exists(self.temp_audio_path):
                try: pygame.mixer.music.unload()
                except pygame.error: pass
        if self.frame_reader_thread and self.frame_reader_thread.is_alive(): self.frame_reader_thread.join(timeout=0.5)
        if self.processing_thread and self.processing_thread.is_alive(): self.processing_thread.join(timeout=0.5)
        if self.canvas and self.canvas.winfo_exists(): self.canvas.delete("all")
        self.frame_buffer.clear()
        if hasattr(self, 'timeline_var'): self.timeline_var.set(0)
        if hasattr(self, 'time_current_label'): self.time_current_label.config(text="00:00")
        while not self.processing_queue.empty():
            try: self.processing_queue.get_nowait()
            except queue.Empty: break
        self.frame_reader_thread = self.processing_thread = None

    def on_resize(self, event):
        if event.width > 1 and event.height > 1:
            new_size = (event.width, event.height)
            with self.canvas_size_lock:
                if new_size != self.last_known_canvas_size:
                    self.last_known_canvas_size = new_size
                    self.frame_buffer.clear()
            if self.is_playing and self.current_frame_idx != -1:
                 self.display_frame(self.current_frame_idx)

    def on_timeline_press(self, event):
        if self.total_frames > 0 and self.video_path:
            self.seeking = True
            if self.is_playing and not self.is_paused and pygame.mixer.get_init(): pygame.mixer.music.pause()

    def on_timeline_release(self, event):
        if self.seeking and self.total_frames > 0 and self.video_path:
            self.seeking = False
            target_frame = int((self.timeline_var.get() / 100.0) * self.total_frames)
            target_frame = max(0, min(target_frame, self.total_frames - 1 if self.total_frames > 0 else 0))
            threading.Thread(target=self.seek_to_frame, args=(target_frame,), daemon=True).start()

    def on_timeline_change(self, value_str):
        if self.total_frames <= 0 or not self.video_path: return
        target_frame = int((float(value_str) / 100.0) * self.total_frames)
        if hasattr(self, 'time_current_label'):
            self.time_current_label.config(text=self.format_time(target_frame / self.fps if self.fps > 0 else 0))

    def format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def update_timeline(self):
        if not self.seeking and self.total_frames > 0 and self.current_frame_idx >= 0:
            progress_percent = (self.current_frame_idx / float(self.total_frames)) * 100.0
            if hasattr(self, 'timeline_var'): self.timeline_var.set(progress_percent)
            if hasattr(self, 'time_current_label'):
                self.time_current_label.config(text=self.format_time(self.current_frame_idx / self.fps if self.fps > 0 else 0))

    def background_processor(self):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            while not self.stop_processing.is_set():
                try:
                    if self.processing_queue.empty() and not futures:
                        time.sleep(0.01)
                        continue
                    while not self.processing_queue.empty() and len(futures) < self.max_workers * 2 :
                        futures.append(executor.submit(self.process_frame_batch, [self.processing_queue.get_nowait()]))
                        self.processing_queue.task_done()
                    done_futures = [f for f in futures if f.done()]
                    for future in done_futures:
                        futures.remove(future)
                        try:
                            for frame_index, pil_image in future.result():
                                if self.stop_processing.is_set(): break
                                self.frame_buffer[frame_index] = pil_image
                                self.frames_processed_count += 1
                        except Exception: pass
                    if self.stop_processing.is_set(): break
                    time.sleep(0.005)
                except queue.Empty: time.sleep(0.01)
                except Exception:
                    if not self.stop_processing.is_set(): time.sleep(0.1)

    def seek_to_frame(self, target_frame):
        if not self.video_path: return
        target_frame = max(0, min(target_frame, self.total_frames - 1 if self.total_frames > 0 else 0))
        was_playing_before_seek = self.is_playing and not self.is_paused
        self.is_paused = True
        if self.frame and self.frame.winfo_exists() and hasattr(self, 'progress_label'):
            self.frame.after(0, lambda: self.progress_label.config(text=f"Seeking..."))
        with self.seek_lock:
            self.seek_request_frame = target_frame
            self.frame_buffer.clear()
            while not self.processing_queue.empty():
                try: self.processing_queue.get_nowait()
                except queue.Empty: break
        start_wait_time = time.time()
        frame_to_display_after_seek = -1
        while time.time() - start_wait_time < 10:
            if self.stop_processing.is_set():
                if was_playing_before_seek: self.resume_playback()
                else: self.is_paused = False
                return
            for i in range(target_frame, min(target_frame + int(self.fps/2), self.total_frames)):
                if i in self.frame_buffer:
                    frame_to_display_after_seek = i
                    break
            if frame_to_display_after_seek != -1: break
            time.sleep(0.02)
        if frame_to_display_after_seek == -1:
            if was_playing_before_seek: self.resume_playback()
            else: self.is_paused = False
            return
        self.current_frame_idx = frame_to_display_after_seek
        seek_time_sec = frame_to_display_after_seek / self.fps if self.fps > 0 else 0
        if self.frame and self.frame.winfo_exists():
            self.frame.after(0, self.display_frame, frame_to_display_after_seek)
            self.frame.after(0, self.update_timeline)
        self.start_time = time.time() - seek_time_sec
        if pygame.mixer.get_init() and self.audio_path:
            try:
                pygame.mixer.music.play(start=seek_time_sec)
                if not was_playing_before_seek: pygame.mixer.music.pause()
            except pygame.error: pass
        if was_playing_before_seek:
            self.is_paused = False
            if self.frame and self.frame.winfo_exists():
                 if hasattr(self, 'progress_label'): self.frame.after(0, lambda: self.progress_label.config(text="Playing..."))
                 self.frame.after(0, self.update_frame)
        else:
            self.is_paused = False
            self.pause_playback()
            if hasattr(self, 'progress_label') and self.frame.winfo_exists():
                self.frame.after(0, lambda: self.progress_label.config(text="Paused"))

    def toggle_play_pause(self):
        if not self.video_path: return
        if self.is_playing:
            if self.is_paused: self.resume_playback()
            else: self.pause_playback()
        else: self.start_playback()

    def pause_playback(self):
        if not self.is_playing or self.is_paused: return
        self.is_paused = True
        self.pause_time = time.time()
        if pygame.mixer.get_init(): pygame.mixer.music.pause()
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(text="Play")
        if hasattr(self, 'progress_label'): self.progress_label.config(text="Paused")

    def resume_playback(self):
        if not self.is_playing or not self.is_paused: return
        if self.pause_time and self.start_time: self.start_time += (time.time() - self.pause_time)
        self.is_paused = False
        self.pause_time = None
        if pygame.mixer.get_init(): pygame.mixer.music.unpause()
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(text="Pause")
        if hasattr(self, 'progress_label'): self.progress_label.config(text="Playing...")
        if self.frame and self.frame.winfo_exists(): self.update_frame()

    def start_playback(self):
        if not self.video_path or self.is_playing: return
        self.is_playing = True
        self.is_paused = False
        self.current_frame_idx = max(0, self.current_frame_idx)
        start_sec = self.current_frame_idx / self.fps if self.fps > 0 else 0
        self.start_time = time.time() - start_sec
        if pygame.mixer.get_init() and self.audio_path:
            try:
                pygame.mixer.music.play(start=start_sec)
            except pygame.error: pass
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(text="Pause")
        if hasattr(self, 'progress_label'): self.progress_label.config(text="Playing...")
        if self.frame and self.frame.winfo_exists(): self.update_frame()

    def read_frames_to_queue(self):
        if not self.video_path: return
        try:
            video_capture = cv2.VideoCapture(self.video_path)
            if not video_capture.isOpened(): return
        except Exception: return
        current_read_frame_idx = 0
        while not self.stop_processing.is_set():
            with self.seek_lock:
                if self.seek_request_frame != -1:
                    target_seek_frame = self.seek_request_frame
                    video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_seek_frame)
                    current_read_frame_idx = target_seek_frame
                    self.seek_request_frame = -1
            if self.processing_queue.qsize() < self.buffer_size * 2:
                ret, frame = video_capture.read()
                if not ret: break
                try:
                    self.processing_queue.put((current_read_frame_idx, frame.copy()), timeout=0.1)
                    current_read_frame_idx += 1
                except queue.Full:
                    if self.stop_processing.is_set(): break
                    time.sleep(0.01)
            else:
                if self.stop_processing.is_set(): break
                time.sleep(0.01)
        video_capture.release()

if __name__ == '__main__':
    class MockSharedState:
        def log(self, message, level=logging.INFO): print(f"LOG: {message}")
        def get(self, key, default=None): return default
        def set(self, key, value): pass
    try: from main import Module as MainModuleBase
    except ImportError:
        class MainModuleBase:
            def __init__(self, master, shared_state, module_name="Test", gui_manager=None):
                self.master = master
                self.shared_state = shared_state
                self.module_name = module_name
                self.frame = ttk.Frame(master)
                self.title_label = ttk.Label(self.frame, text=module_name)
                self.is_maximized = False
            def get_frame(self): return self.frame
            def on_destroy(self): pass
    root = tk.Tk()
    root.title("Video Player Standalone Test")
    root.geometry("960x700")
    mock_shared_state = MockSharedState()
    player_module = VideoPlayerModule(root, mock_shared_state)
    player_module.get_frame().pack(fill=tk.BOTH, expand=True)
    root.protocol("WM_DELETE_WINDOW", lambda: (player_module.on_destroy(), root.destroy()))
    root.mainloop()