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
import logging # Added for logging constants

# Import Module base class
from main import Module

# Helper classes (JumpToWindow, PlaylistEditor)
# Their parent will be the top-level window of the module's frame
class JumpToWindow(tk.Toplevel):
    def __init__(self, video_player_module, playlist, current_index):
        # The master for Toplevel should be the main application window or the module's frame's toplevel
        super().__init__(video_player_module.frame.winfo_toplevel())
        self.master_player = video_player_module
        self.title("跳至影片")
        self.geometry("400x500")
        self.transient(video_player_module.frame.winfo_toplevel()) # Set transient to the module's actual window
        self.grab_set()

        frame = tk.Frame(self) # Content frame for this Toplevel
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

        main_frame = tk.Frame(self) # Content frame for this Toplevel
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
            print(f"'{self.listbox.get(pos)}' 已設為待插入。")
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
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(new_order_basenames, f, ensure_ascii=False, indent=4)
                print(f"播放列表已儲存至 {json_path}")
            except Exception as e:
                messagebox.showerror("儲存失敗", f"無法寫入 playlist.json:\n{e}", parent=self)
                return
        self.master_player.update_playlist_from_editor(new_order_basenames)
        self.destroy()

# --- [新增] 10 段等化器頻段與預設 ---
EQ_BANDS = [
    (20, 32), (32, 63), (63, 125), (125, 250), (250, 500),
    (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)
]
EQ_PRESETS = {
    "無": [0]*10,
    "家庭式立體聲": [6, 6, 4.1, 4, 1.7, 2, 1.7, 4, 4.1, 6],
    "可攜式喇叭": [8, 8, 5.4, 5, 2.7, 3, 2.3, 4, 3.6, 5],
    "汽車": [8, 8, 4.8, 3, 0.1, 0, 0.7, 4, 4.8, 7],
    "電視": [3, 3, 4.5, 8, 2.8, 0, 1.3, 6, 6.1, 8],
    "音質": [2, 3, 2, -1, 0, 0, 1, 2, 1, 2],
    "低音增強": [6, 6, 6, 3, 0, 0, 0, 0, 0, 0],
    "低音減弱": [-6, -6, -3, 0, 0, 0, 0, 0, 0, 0],
    "高音增強": [-6, -6, -3, 0, 0, 0, 3, 6, 6, 6],
    "高音減弱": [3, 3, 0, 0, 0, 0, 0, -3, -6, -6],
    "響度": [6, 6, 3, 0, 0, 0, 0, 3, 6, 6],
    "沙發音樂": [-3, -3, -3, 0, 3, 3, 3, 3, 0, 0],
    "小喇叭": [3, 3, 3, 0, 0, 0, 0, 3, 6, 6],
    "口語清晰": [-6, -6, -3, 0, 3, 3, 3, 3, 0, 0],
    "聲音增強": [0, 0, 0, 0, 3, 6, 6, 3, 0, 0],
    "古典": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    "舞曲": [6, 6, 3, 0, 0, 0, 0, 0, -6, -6],
    "深沉": [6, 6, 3, 0, 0, 0, 0, -3, -6, -6],
    "電子": [6, 6, 3, 0, 0, 0, 0, 3, 6, 6],
    "饒舌": [6, 6, 3, 0, 3, 3, 3, 0, 0, 0],
    "爵士": [3, 3, 0, 0, 0, 3, 3, 0, 3, 3],
    "拉丁": [0, 0, 0, 0, 3, 3, 3, 3, 6, 6],
    "鋼琴": [0, 0, 0, 0, 3, 3, 3, 3, 0, 0],
    "流行": [-3, -3, -3, -3, 3, 3, 3, 3, -3, -3],
    "R&B": [6, 6, 3, 0, 0, 0, 3, 3, 0, 0],
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
        audio = wf.readframes(n_frames)
        dtype = np.int16 if sampwidth == 2 else np.uint8
        data = np.frombuffer(audio, dtype=dtype)
        if n_channels == 2:
            data = data.reshape(-1, 2)
        else:
            data = data.reshape(-1, 1)
        data = data.astype(np.float32)
        eq_data = np.zeros_like(data)
        for i, (low, high) in enumerate(EQ_BANDS):
            gain = db_to_gain(gains[i])
            # 設定 bandpass 濾波器
            b, a = scipy.signal.butter(2, [low/(framerate/2), high/(framerate/2)], btype='band')
            for ch in range(n_channels):
                filtered = scipy.signal.lfilter(b, a, data[:, ch])
                eq_data[:, ch] += filtered * gain
        # 正規化
        max_val = np.max(np.abs(eq_data))
        if max_val > 0:
            eq_data = eq_data * (32767.0 / max_val)
        eq_data = np.clip(eq_data, -32768, 32767).astype(np.int16)
        eq_data_bytes = eq_data.tobytes()
        with wave.open(out_path, 'wb') as wf_out:
            wf_out.setparams(params)
            wf_out.writeframes(eq_data_bytes)

class VideoPlayerModule(Module):
    def __init__(self, master, shared_state, module_name="VideoPlayer", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"Initializing VideoPlayerModule: {self.module_name}", level=logging.INFO)

        # Default window size if run standalone, actual size managed by ModularGUI
        self.window_width = 960  # Expected width for layout calculations
        self.window_height = 700 # Expected height for layout calculations

        self.play_mode_var = tk.StringVar(value="ctime")
        self.current_folder_path = None
        self.temp_cache_dir = None
        self.temp_audio_path = None

        self.canvas_size_lock = threading.Lock()
        # Initialize last_known_canvas_size based on typical module proportions, not fixed window height
        # This will be updated by on_resize if the canvas exists and has a size.
        # Fallback to a reasonable default if frame/canvas isn't ready yet.
        initial_canvas_w = self.frame.winfo_width() if self.frame.winfo_exists() and self.frame.winfo_width() > 1 else self.window_width
        initial_canvas_h = self.frame.winfo_height() - 200 if self.frame.winfo_exists() and self.frame.winfo_height() > 200 else self.window_height - 200
        self.last_known_canvas_size = (max(1, initial_canvas_w), max(1, initial_canvas_h))


        self.video_path = ""
        self.audio_path = ""
        self.is_playing = False
        self.is_paused = False
        self.after_id = None # Store ID for self.frame.after
        self.playlist = []
        self.current_playlist_index = -1
        self.unplayed_indices = []
        self.history_indices = []

        self.max_workers = multiprocessing.cpu_count()
        self.buffer_size = 120  # Number of frames to buffer (approx)
        self.frame_buffer = {}  # Stores processed PIL.Image objects
        self.processing_queue = queue.Queue() # Queue for raw frames from video
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

        self.start_time = None # For playback timing
        self.pause_time = None # For playback timing

        try:
            pygame.mixer.init()
            self.shared_state.log("Pygame mixer initialized by VideoPlayerModule.", level=logging.INFO)
        except pygame.error as e:
            self.shared_state.log(f"Failed to initialize pygame.mixer: {e}. Audio playback will not work.", level=logging.ERROR)
            # Optionally, disable audio-dependent UI elements or show a warning
            # For now, we'll let it proceed, and audio functions will likely fail.

        self.volume_var = tk.DoubleVar(value=100)
        # self.set_volume(self.volume_var.get()) # Call this after UI is created if mixer is available

        self.create_ui() # Call to build the UI within self.frame
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing) # Replaced by on_destroy

        # Set initial volume if mixer is available
        if pygame.mixer.get_init():
             self.set_volume(self.volume_var.get())
        else:
            if hasattr(self, 'volume_scale') and self.volume_scale: # Check if volume_scale exists
                self.volume_scale.config(state=tk.DISABLED)


    def create_ui(self):
        # All widgets will be children of self.frame
        # self.frame is the main container for this module's UI, provided by the Module base class.

        # Video display canvas
        self.canvas = tk.Canvas(self.frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.on_resize)

        # Area for file/folder selection and play mode
        selection_area = tk.Frame(self.frame) # Parent is self.frame
        selection_area.pack(fill=tk.X, padx=10, pady=5)

        file_selection_frame = tk.LabelFrame(selection_area, text="檔案選擇")
        file_selection_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.btn_select_file = tk.Button(file_selection_frame, text="選擇檔案", command=self.select_file)
        self.btn_select_file.pack(pady=5, padx=10)
        self.btn_select_folder = tk.Button(file_selection_frame, text="選擇資料夾", command=self.select_folder)
        self.btn_select_folder.pack(pady=5, padx=10)

        mode_selection_frame = tk.LabelFrame(selection_area, text="播放模式")
        mode_selection_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        radio_ctime = ttk.Radiobutton(mode_selection_frame, text="按建立時間", variable=self.play_mode_var, value="ctime", command=self.on_play_mode_change)
        radio_ctime.pack(anchor=tk.W, padx=10)
        radio_json = ttk.Radiobutton(mode_selection_frame, text="按JSON順序", variable=self.play_mode_var, value="json", command=self.on_play_mode_change)
        radio_json.pack(anchor=tk.W, padx=10)
        radio_random = ttk.Radiobutton(mode_selection_frame, text="隨機播放", variable=self.play_mode_var, value="random", command=self.on_play_mode_change)
        radio_random.pack(anchor=tk.W, padx=10)
        self.btn_adjust_order = tk.Button(mode_selection_frame, text="調整播放順序", state=tk.DISABLED, command=self.open_playlist_editor)
        self.btn_adjust_order.pack(pady=5, padx=10, side=tk.LEFT)
        self.btn_jump_to = tk.Button(mode_selection_frame, text="跳至影片...", state=tk.DISABLED, command=self.open_jump_to_window)
        self.btn_jump_to.pack(pady=5, padx=10, side=tk.LEFT)

        # Timeline
        timeline_frame = tk.Frame(self.frame) # Parent is self.frame
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

        # Controls (play, pause, next, prev, volume) -- moved below timeline
        control_frame = tk.Frame(self.frame) # Parent is self.frame
        control_frame.pack(fill=tk.X, padx=10, pady=5) # Now just below timeline_frame

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

        # Equalizer controls with vertical scrollbar
        eq_frame_outer = tk.LabelFrame(self.frame, text="等化器") # Parent is self.frame
        eq_frame_outer.pack(fill=tk.X, padx=10, pady=5)

        # Create a canvas and a vertical scrollbar for the eq_frame
        eq_canvas_container = tk.Canvas(eq_frame_outer, height=90)  # Adjust height as needed
        eq_scrollbar = ttk.Scrollbar(eq_frame_outer, orient="vertical", command=eq_canvas_container.yview)
        eq_canvas_container.configure(yscrollcommand=eq_scrollbar.set)
        eq_canvas_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        eq_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame inside the canvas to hold the actual EQ widgets
        eq_frame = tk.Frame(eq_canvas_container)
        eq_canvas_container.create_window((0, 0), window=eq_frame, anchor="nw")

        # Bind to configure scrollregion
        def _on_eq_frame_configure(event):
            eq_canvas_container.configure(scrollregion=eq_canvas_container.bbox("all"))
        eq_frame.bind("<Configure>", _on_eq_frame_configure)

        # Mouse wheel scroll support
        def _on_mousewheel(event):
            eq_canvas_container.yview_scroll(int(-1*(event.delta/120)), "units")
        eq_frame.bind("<Enter>", lambda e: eq_canvas_container.bind_all("<MouseWheel>", _on_mousewheel))
        eq_frame.bind("<Leave>", lambda e: eq_canvas_container.unbind_all("<MouseWheel>"))

        eq_options = list(EQ_PRESETS.keys())
        self.eq_mode_var = tk.StringVar(value="無")
        self.eq_menu = ttk.Combobox(eq_frame, values=eq_options, textvariable=self.eq_mode_var, state="readonly", width=15)
        self.eq_menu.pack(side=tk.LEFT, padx=10)
        self.eq_menu.bind("<<ComboboxSelected>>", self.on_eq_mode_change)
        self.eq_canvas = tk.Label(eq_frame)
        self.eq_canvas.pack(side=tk.LEFT, padx=10)
        self.eq_gains = get_equalizer_gains("無") # Initial gains
        self.eq_image = None # To hold PhotoImage reference
        self.draw_equalizer_visualization()

        self.shared_state.log("VideoPlayerModule UI created.", level=logging.INFO)

    def on_destroy(self):
        self.shared_state.log(f"VideoPlayerModule {self.module_name} on_destroy called.", level=logging.INFO)
        self.stop_video() # Stop video playback and threads

        if pygame.mixer.get_init(): # Check if mixer was initialized
            pygame.mixer.quit()
            self.shared_state.log("Pygame mixer quit by VideoPlayerModule.", level=logging.INFO)

        self.cleanup_temp_cache() # Clean up any temporary audio files/folders

        self.playlist = []
        self.current_playlist_index = -1

        # Cancel any pending .after() calls
        if self.after_id:
            if self.frame and self.frame.winfo_exists():
                try:
                    self.frame.after_cancel(self.after_id)
                except tk.TclError: # Catch error if frame is already destroyed
                    pass
            self.after_id = None

        super().on_destroy() # Call base class on_destroy
        self.shared_state.log(f"VideoPlayerModule {self.module_name} destroyed.", level=logging.INFO)


    def on_eq_mode_change(self, event=None):
        self.eq_gains = get_equalizer_gains(self.eq_mode_var.get())
        self.draw_equalizer_visualization()
        if self.playlist and self.current_playlist_index != -1:
            self.shared_state.log(f"EQ mode changed to {self.eq_mode_var.get()}, restarting current video.", level=logging.DEBUG)
            self.stop_video()
            self.play_current_video_in_playlist()

    def draw_equalizer_visualization(self):
        gains = get_equalizer_gains(self.eq_mode_var.get())
        band_centers = [int((low * high) ** 0.5) for (low, high) in EQ_BANDS]

        # 格式化頻率標籤：1000 以上用 kHz
        def fmt_freq(f):
            return f"{f//1000}kHz" if f >= 1000 else f"{f}Hz"
        xtick_labels = [fmt_freq(f) for f in band_centers]

        fig, ax = plt.subplots(figsize=(5, 3), dpi=80)
        ax.bar(range(len(band_centers)), gains, width=0.7, color="#4A90E2")
        ax.set_xticks(range(len(band_centers)))
        ax.set_xticklabels(xtick_labels, rotation=0, ha='center', fontsize=8)
        ax.set_ylim(-8, 8)
        ax.set_ylabel("dB")
        ax.set_xlabel("Frequency Bands")
        ax.grid(True, axis='y', linestyle='--', alpha=0.5)
        ax.set_title("Equalizer")
        plt.tight_layout(pad=0.1)

        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        img = PILImage.open(buf)
        self.eq_image = ImageTk.PhotoImage(img)

        if self.eq_canvas and self.eq_canvas.winfo_exists():
            self.eq_canvas.config(image=self.eq_image)
        buf.close()

    def cleanup_temp_cache(self):
        if self.temp_cache_dir and os.path.exists(self.temp_cache_dir):
            try:
                self.shared_state.log(f"Cleaning up temp cache directory: {self.temp_cache_dir}", level=logging.DEBUG)
                shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
            except Exception as e:
                self.shared_state.log(f"Error cleaning up temp cache directory: {e}", level=logging.ERROR)
        self.temp_cache_dir = None
        self.temp_audio_path = None
        self.temp_video_path = None # 新增: 清理暫存影片路徑
    
    def start_playlist(self, files_list):
        self.stop_video()
        self.playlist = files_list
        self.current_playlist_index = -1 # Reset index

        if self.play_mode_var.get() == 'random':
            self.reset_random_playlist()
            if self.unplayed_indices:
                self.current_playlist_index = self.unplayed_indices.pop(0)
                if self.current_playlist_index != -1: # Ensure valid index
                    self.history_indices.append(self.current_playlist_index)
        else:
            self.current_playlist_index = 0 if self.playlist else -1 # Ensure valid index or -1 if empty

        self.play_current_video_in_playlist()

    def extract_audio(self, video_path_to_extract): # Renamed parameter to avoid conflict
        self.cleanup_temp_cache()
        try:
            video_dir = os.path.dirname(video_path_to_extract)
            self.temp_cache_dir = tempfile.mkdtemp(prefix='.vidplayer_cache_', dir=video_dir)
            self.shared_state.log(f"Created temp cache directory: {self.temp_cache_dir}", level=logging.DEBUG)

            temp_wav_path = os.path.join(self.temp_cache_dir, "temp.wav")
            with VideoFileClip(video_path_to_extract) as video: # Use renamed parameter
                if video.audio is None:
                    raise Exception("Video does not contain an audio track.")
                video.audio.write_audiofile(temp_wav_path, codec='pcm_s16le', logger=None)

            eq_mode = self.eq_mode_var.get()
            processed_wav_path = temp_wav_path
            if eq_mode and eq_mode != "無":
                eq_path = os.path.join(self.temp_cache_dir, "temp_eq.wav")
                apply_equalizer(temp_wav_path, eq_path, get_equalizer_gains(eq_mode))
                processed_wav_path = eq_path
            
            self.temp_audio_path = os.path.join(self.temp_cache_dir, "audio.mp3")
            cmd = f'ffmpeg -y -loglevel error -i "{processed_wav_path}" -vn -ar 44100 -ac 2 -b:a 192k "{self.temp_audio_path}"'

            # Check if ffmpeg exists before running
            ffmpeg_exists = (os.system('ffmpeg -version > nul 2>&1') == 0 or
                             os.system('ffmpeg -version > /dev/null 2>&1') == 0)
            if not ffmpeg_exists:
                self.shared_state.log("FFmpeg not found. Cannot extract audio to MP3.", level=logging.ERROR)
                messagebox.showerror("FFmpeg Error", "FFmpeg is not installed or not in PATH. Audio extraction to MP3 will fail.", parent=self.frame.winfo_toplevel())
                # Fallback: try to use the processed WAV directly if possible, or handle error
                # For simplicity now, we'll let it fail if ffmpeg is needed for MP3.
                # Alternatively, could try playing the WAV if pygame supports it well enough.
                # However, the original code implies MP3 is preferred.
                raise Exception("FFmpeg not found, cannot convert to MP3.")

            os.system(cmd) # This might still fail if ffmpeg has issues, but we've checked for existence

            if not os.path.exists(self.temp_audio_path) or os.path.getsize(self.temp_audio_path) == 0:
                raise Exception(f"FFmpeg failed to create or created an empty audio file: {self.temp_audio_path}")

            self.shared_state.log(f"Audio extracted: {self.temp_audio_path}", level=logging.INFO)
            return self.temp_audio_path
        except Exception as e:
            self.shared_state.log(f"Error extracting audio: {e}", level=logging.ERROR)
            self.cleanup_temp_cache() # Ensure cleanup on error
            raise # Re-raise the exception to be caught by the caller (prepare_video)

    # on_closing is removed, replaced by on_destroy

    def open_jump_to_window(self):
        if not self.playlist: return
        # Pass self (the module instance) to JumpToWindow
        JumpToWindow(self, self.playlist, self.current_playlist_index)

    def jump_to_selected_video(self, new_index):
        if self.current_playlist_index == new_index: return # No change
        mode = self.play_mode_var.get()
        if mode == 'random':
            print(f"跳轉至影片: {os.path.basename(self.playlist[self.current_playlist_index])}")
            self.shared_state.log(f"Jumping to video index {new_index}: {os.path.basename(self.playlist[new_index])}", level=logging.DEBUG)
            self.current_playlist_index = new_index
            all_indices = list(range(len(self.playlist)))
            # Update unplayed_indices: remove current, ensure no duplicates with history
            self.unplayed_indices = [i for i in all_indices if i not in self.history_indices and i != self.current_playlist_index]
            random.shuffle(self.unplayed_indices) # Re-shuffle remaining unplayed
        else: # Sequential modes
            self.current_playlist_index = new_index

        self.shared_state.log(f"Jumped to video: {os.path.basename(self.playlist[self.current_playlist_index])}", level=logging.INFO)
        self.stop_video()
        self.play_current_video_in_playlist()

    def on_play_mode_change(self):
        mode = self.play_mode_var.get()
        self.shared_state.log(f"Play mode changed to: {mode}", level=logging.INFO)
        if mode == "json" and self.current_folder_path:
            if hasattr(self, 'btn_adjust_order'): self.btn_adjust_order.config(state=tk.NORMAL)
        else:
            if hasattr(self, 'btn_adjust_order'): self.btn_adjust_order.config(state=tk.DISABLED)

        if self.playlist: # Only rebuild if there's a playlist
            if mode == "random":
                self.reset_random_playlist() # This also handles current_playlist_index for random start
            self.rebuild_playlist() # Sorts and potentially updates current_playlist_index
            # If mode changed to random, play_next_video might be needed if rebuild_playlist doesn't start one
            if mode == 'random' and not self.is_playing and self.unplayed_indices:
                 self.play_next_video() # Start playing if random mode selected and not already playing

    def reset_random_playlist(self):
        if not self.playlist:
            self.unplayed_indices = []
            self.history_indices = []
            return

        all_indices = list(range(len(self.playlist)))

        # If a video is currently selected, keep it out of the initial shuffle if it's not already played
        current_video_playing_idx = self.current_playlist_index

        self.history_indices = [] # Fresh history for a new random cycle

        # Potential unplayed: all except current (if any and valid)
        potential_unplayed = [i for i in all_indices if i != current_video_playing_idx]
        random.shuffle(potential_unplayed)

        self.unplayed_indices = potential_unplayed

        # If a video was selected (e.g. by user click) make it the first to play in this new random sequence
        # and add it to history. Otherwise, the list is already shuffled.
        if current_video_playing_idx != -1 and current_video_playing_idx in all_indices:
            if current_video_playing_idx in self.unplayed_indices: # If it wasn't "played" yet in this cycle
                self.unplayed_indices.remove(current_video_playing_idx) # Remove if present
            # self.unplayed_indices.insert(0, current_video_playing_idx) # Make it next only if it's a fresh start
            # No, don't insert. If user selected, it will play. reset_random_playlist is for mode switch or end of list.

        self.shared_state.log(f"Random playlist reset. Unplayed: {len(self.unplayed_indices)}", level=logging.DEBUG)


    def rebuild_playlist(self):
        if not self.playlist: return

        # Try to preserve the currently playing video's position if possible
        current_video_path = None
        if self.current_playlist_index != -1 and self.current_playlist_index < len(self.playlist):
            current_video_path = self.playlist[self.current_playlist_index]

        mode = self.play_mode_var.get()
        if mode == "ctime":
            self.playlist.sort(key=lambda p: os.path.getctime(p))
        elif mode == "json" and self.current_folder_path:
            self.playlist = self.sort_by_json(self.playlist, self.current_folder_path)
        # Random mode doesn't re-sort the main playlist here; reset_random_playlist handles unplayed_indices

        if current_video_path and mode != "random": # For non-random, try to find the video again
            try:
                self.current_playlist_index = self.playlist.index(current_video_path)
            except ValueError: # Video not found (e.g. deleted from json), reset to start
                self.current_playlist_index = 0 if self.playlist else -1
        elif mode == "random":
            # For random, current_playlist_index is managed by play_next/prev and reset_random_playlist
            pass # Do not change current_playlist_index here for random
        else: # No current video or playlist became empty
             self.current_playlist_index = 0 if self.playlist else -1

        self.shared_state.log("Playlist rebuilt based on new mode.", level=logging.DEBUG)
        self.update_nav_buttons_state()
        self.update_module_title() # Update module title (part of base Module)

    def sort_by_json(self, file_paths, folder_path):
        json_path = os.path.join(folder_path, "playlist.json")
        disk_basenames = {os.path.basename(p) for p in file_paths} # Basenames of files currently on disk
        json_basenames = []
        json_exists = os.path.exists(json_path)

        if json_exists:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_basenames = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.shared_state.log(f"Error reading playlist.json: {e}. Will create a new one.", level=logging.WARNING)
                json_exists = False

        if not json_exists: # Create new JSON if not found or unreadable
            self.shared_state.log("playlist.json not found or invalid, creating new based on ctime.", level=logging.INFO)
            sorted_by_ctime_paths = sorted(file_paths, key=lambda p: os.path.getctime(p))
            json_basenames = [os.path.basename(p) for p in sorted_by_ctime_paths]
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_basenames, f, ensure_ascii=False, indent=4)
                self.shared_state.log("New playlist.json created.", level=logging.INFO)
            except IOError as e:
                self.shared_state.log(f"Failed to create new playlist.json: {e}", level=logging.ERROR)
            # Return full paths based on the newly created (or intended) json_basenames
            return [os.path.join(folder_path, name) for name in json_basenames if name in disk_basenames]

        # Synchronize JSON with disk files
        json_basenames_set = set(json_basenames)
        deleted_files = json_basenames_set - disk_basenames # Files in JSON but not on disk
        new_files = disk_basenames - json_basenames_set     # Files on disk but not in JSON

        final_json_list = [name for name in json_basenames if name not in deleted_files] # Remove deleted
        final_json_list.extend(sorted(list(new_files))) # Add new files, sorted for consistency

        if deleted_files or new_files: # If changes were made, rewrite the JSON
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(final_json_list, f, ensure_ascii=False, indent=4)
                self.shared_state.log("playlist.json synchronized with disk files.", level=logging.INFO)
            except IOError as e:
                self.shared_state.log(f"Error rewriting playlist.json for sync: {e}", level=logging.ERROR)

        # Return full paths based on the final synchronized list, ensuring files exist
        return [os.path.join(folder_path, basename) for basename in final_json_list if basename in disk_basenames]

    def open_playlist_editor(self):
        if not self.playlist or not self.current_folder_path:
            messagebox.showwarning("Operation Invalid", "Please load a folder first.", parent=self.frame.winfo_toplevel())
            return
        current_mode = self.play_mode_var.get()
        # Pass self (the module instance) to PlaylistEditor
        PlaylistEditor(self, self.playlist, self.current_folder_path, current_mode)

    def update_playlist_from_editor(self, new_order_basenames):
        # Assume current_playlist_index points to a video in the OLD playlist
        current_video_path = None
        if self.current_playlist_index != -1 and self.current_playlist_index < len(self.playlist):
             current_video_path = self.playlist[self.current_playlist_index]

        self.playlist = [os.path.join(self.current_folder_path, basename) for basename in new_order_basenames]

        if current_video_path:
            try: # Try to find the previously current video in the new order
                self.current_playlist_index = self.playlist.index(current_video_path)
            except ValueError: # If not found, reset to the beginning
                self.current_playlist_index = 0 if self.playlist else -1
        else: # No video was current, or playlist was empty
            self.current_playlist_index = 0 if self.playlist else -1

        self.update_nav_buttons_state()
        self.update_module_title()
        messagebox.showinfo("Success", "Playlist order updated.", parent=self.frame.winfo_toplevel())

    def select_folder(self):
        # parent for filedialog should be the module's window
        folder_path = filedialog.askdirectory(title="Select Video Folder", parent=self.frame.winfo_toplevel())
        if not folder_path: return

        self.current_folder_path = folder_path
        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv') # Added more common types
        try:
            video_files = [os.path.join(folder_path, item) for item in os.listdir(folder_path)
                           if item.lower().endswith(valid_extensions) and os.path.isfile(os.path.join(folder_path, item))]
        except OSError as e:
            messagebox.showerror("Error", f"Cannot read folder: {e}", parent=self.frame.winfo_toplevel())
            return

        if not video_files:
            messagebox.showinfo("Info", "No supported video files found in this folder.", parent=self.frame.winfo_toplevel())
            self.current_folder_path = None # Reset if no valid files
            self.playlist = [] # Clear playlist
            self.current_playlist_index = -1
            self.update_nav_buttons_state()
            self.update_module_title()
            if hasattr(self, 'progress_label'): self.progress_label.config(text="No videos found.")
            return

        # Mode specific sorting or setup handled by on_play_mode_change and start_playlist
        self.on_play_mode_change() # This will call rebuild_playlist which sorts based on mode
        self.start_playlist(video_files) # This will set up the playlist and start the first video

    def select_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv"), ("All files", "*.*")],
            parent=self.frame.winfo_toplevel()
        )
        if not filepath: return

        self.current_folder_path = None # Single file mode, no folder context
        if hasattr(self, 'btn_adjust_order'): self.btn_adjust_order.config(state=tk.DISABLED)
        if hasattr(self, 'btn_jump_to'): self.btn_jump_to.config(state=tk.DISABLED) # Only one file

        self.start_playlist([filepath])

    def update_module_title(self):
        # This method updates the title bar of the module itself using the base class mechanism
        base_title = self.module_name # Default title from base class init
        if self.is_maximized: # Module base class has is_maximized
             base_title = f"[Maximized] {base_title}"

        new_title = base_title
        if self.playlist and self.current_playlist_index != -1:
            filepath = self.playlist[self.current_playlist_index]
            playlist_info = f"({self.current_playlist_index + 1}/{len(self.playlist)})"
            new_title = f"{base_title}: {os.path.basename(filepath)} {playlist_info}"

        if hasattr(self, 'title_label') and self.title_label: # title_label is from Module base
            self.title_label.config(text=new_title)
        elif self.shared_state: # Fallback to log if title_label not found (should not happen)
            self.shared_state.log(f"VideoPlayer: Attempted to set title to '{new_title}', but title_label widget not found.", level=logging.WARNING)


    def play_current_video_in_playlist(self):
        if not self.playlist or not (0 <= self.current_playlist_index < len(self.playlist)):
            self.shared_state.log("Playlist empty or index out of bounds. Stopping video.", level=logging.DEBUG)
            self.stop_video()
            self.playlist = [] # Ensure consistent state
            self.current_playlist_index = -1
            self.update_module_title()
            if hasattr(self, 'progress_label'): self.progress_label.config(text="Ready")
            self.enable_button_states() # Renamed for clarity
            return

        filepath = self.playlist[self.current_playlist_index]
        self.video_path = filepath # Set the current video_path
        self.update_module_title()

        # Disable selection buttons during load
        if hasattr(self, 'btn_select_file'): self.btn_select_file.config(state=tk.DISABLED)
        if hasattr(self, 'btn_select_folder'): self.btn_select_folder.config(state=tk.DISABLED)
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(state=tk.DISABLED)
        self.update_nav_buttons_state() # Update prev/next based on new index

        if hasattr(self, 'progress_label'): self.progress_label.config(text="Extracting audio...")

        # Run video preparation in a separate thread to keep UI responsive
        # Ensure self.frame exists before starting thread that might call self.frame.after
        if self.frame and self.frame.winfo_exists():
            threading.Thread(target=self.prepare_video, args=(filepath,), daemon=True).start()
        else:
            self.shared_state.log("Frame does not exist, cannot start video preparation.", level=logging.ERROR)
            if hasattr(self, 'progress_label'): self.progress_label.config(text="Error: UI not ready")


    def play_next_video(self):
        if not self.playlist: return
        mode = self.play_mode_var.get()
        if mode == 'random':
            if not self.unplayed_indices:
                print("隨機播放完一輪，開始新一輪。")
                self.reset_random_playlist()
            if self.unplayed_indices:
                next_index = self.unplayed_indices.pop(0)
        if mode == 'random':
            if self.current_playlist_index != -1: # If something was playing
                 self.history_indices.append(self.current_playlist_index) # Add it to history

            if not self.unplayed_indices: # If random cycle finished
                self.shared_state.log("Random playlist cycle finished. Resetting.", level=logging.INFO)
                self.reset_random_playlist() # Reset (shuffles all, clears history)
                # After reset, if current_playlist_index was valid, it's now in history.
                # We need to pick a new one from the now repopulated unplayed_indices.

            if self.unplayed_indices: # If there are still songs to play (or after reset)
                next_idx = self.unplayed_indices.pop(0)
                self.current_playlist_index = next_idx
            else: # Playlist might be empty or something went wrong
                self.shared_state.log("No more unplayed videos in random mode, even after reset. Stopping.", level=logging.WARNING)
                self.stop_video()
                return
        else: # Sequential modes
            self.current_playlist_index = (self.current_playlist_index + 1) % len(self.playlist)

        self.shared_state.log(f"Playing next video: {os.path.basename(self.playlist[self.current_playlist_index])}", level=logging.INFO)
        self.stop_video()
        self.play_current_video_in_playlist()

    def play_previous_video(self):
        if not self.playlist: return
        mode = self.play_mode_var.get()
        if mode == 'random':
            if self.history_indices: # If there's a history to go back to
                # Current video (if playing) goes back to unplayed list (at the start for immediate replay if user toggles next/prev)
                if self.current_playlist_index != -1:
                    self.unplayed_indices.insert(0, self.current_playlist_index)

                prev_idx = self.history_indices.pop()
                self.current_playlist_index = prev_idx
            else:
                self.shared_state.log("No previous video in random mode history.", level=logging.INFO)
                return # No previous video
        else: # Sequential modes
            self.current_playlist_index = (self.current_playlist_index - 1 + len(self.playlist)) % len(self.playlist)

        self.shared_state.log(f"Playing previous video: {os.path.basename(self.playlist[self.current_playlist_index])}", level=logging.INFO)
        self.stop_video()
        self.play_current_video_in_playlist()

    def update_nav_buttons_state(self):
        # Only enable nav buttons if there's more than one video.
        # For random mode, prev button depends on history, next button on unplayed_indices.
        mode = self.play_mode_var.get()
        can_go_next = False
        can_go_prev = False

        if self.playlist:
            if mode == 'random':
                can_go_next = bool(self.unplayed_indices) or len(self.playlist) > 1 # Can always go next if >1, will reshuffle
                can_go_prev = bool(self.history_indices)
            else: # Sequential
                can_go_next = len(self.playlist) > 1
                can_go_prev = len(self.playlist) > 1

        if hasattr(self, 'btn_prev'): self.btn_prev.config(state=tk.NORMAL if can_go_prev else tk.DISABLED)
        if hasattr(self, 'btn_next'): self.btn_next.config(state=tk.NORMAL if can_go_next else tk.DISABLED)
        if hasattr(self, 'btn_jump_to'): self.btn_jump_to.config(state=tk.NORMAL if self.playlist else tk.DISABLED)


    def update_frame(self):
        # This is the main video rendering loop, called via self.frame.after
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
            else: # Single video ended, or last video in sequential playlist
                self.stop_video()
                if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(text="Play")
                if hasattr(self, 'progress_label'): self.progress_label.config(text="Finished")
            return

        if target_frame_idx != self.current_frame_idx:
            if target_frame_idx in self.frame_buffer:
                self.display_frame(target_frame_idx)
                # More aggressive cleanup: remove frames much older than current
                cleanup_threshold = target_frame_idx - int(self.buffer_size * 0.75)
                frames_to_remove = [idx for idx in self.frame_buffer.keys() if idx < cleanup_threshold]
                for idx in frames_to_remove:
                    del self.frame_buffer[idx]
                self.current_frame_idx = target_frame_idx
                self.update_timeline()

        # Schedule next frame update
        if self.frame and self.frame.winfo_exists():
             self.after_id = self.frame.after(1, self.update_frame) # Approx 1ms for smooth updates, adjust if needed

    def set_volume(self, value):
        if pygame.mixer.get_init(): # Check if mixer is initialized
            volume = float(value) / 100
            pygame.mixer.music.set_volume(volume)
        else:
            self.shared_state.log("Pygame mixer not initialized, cannot set volume.", level=logging.WARNING)


    def calculate_proportional_size(self, canvas_w, canvas_h, video_w, video_h):
        if video_w == 0 or video_h == 0 or canvas_w == 0 or canvas_h == 0:
            return (max(1, canvas_w), max(1, canvas_h)) # Avoid division by zero, return canvas size

        canvas_ratio = canvas_w / canvas_h
        video_ratio = video_w / video_h

        if canvas_ratio > video_ratio: # Canvas is wider than video (letterbox top/bottom)
            new_h = canvas_h
            new_w = int(new_h * video_ratio)
        else: # Canvas is taller than video (pillarbox left/right)
            new_w = canvas_w
            new_h = int(new_w / video_ratio)
        return (max(1, new_w), max(1, new_h)) # Ensure dimensions are at least 1

    def process_frame_batch(self, raw_frames_batch):
        results = []
        with self.canvas_size_lock: # Ensure last_known_canvas_size is read atomically
            target_width, target_height = self.last_known_canvas_size

        # Calculate new_size once per batch if video dimensions are stable
        new_size = self.calculate_proportional_size(target_width, target_height, self.video_width, self.video_height)

        for frame_index, frame_bgr in raw_frames_batch:
            try:
                if new_size[0] > 1 and new_size[1] > 1: # Ensure valid size for resize
                    cv_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(cv_image)
                    pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS) # Use LANCZOS for better quality
                    results.append((frame_index, pil_image))
            except Exception as e:
                self.shared_state.log(f"Error processing frame {frame_index}: {e}", level=logging.ERROR)
        return results

    def display_frame(self, frame_idx):
        if frame_idx in self.frame_buffer:
            pil_image = self.frame_buffer[frame_idx]

            if not (self.canvas and self.canvas.winfo_exists()): return # Canvas gone

            current_canvas_width = self.canvas.winfo_width()
            current_canvas_height = self.canvas.winfo_height()

            if current_canvas_width <= 1 or current_canvas_height <= 1 : return # Canvas not ready

            # Image should already be resized correctly by process_frame_batch
            # However, if canvas size changed *just* before display, image might be for old size.
            # For simplicity, we assume process_frame_batch uses a recent enough canvas size.
            # A more robust solution might re-check and optionally re-scale here if sizes differ significantly.

            # Create PhotoImage and display
            try:
                self.photo = ImageTk.PhotoImage(image=pil_image) # Keep reference
                self.canvas.delete("all") # Clear previous frame
                # Center the image on the canvas
                self.canvas.create_image(current_canvas_width / 2, current_canvas_height / 2, anchor=tk.CENTER, image=self.photo)
            except Exception as e: # Catch errors during PhotoImage creation or display
                 self.shared_state.log(f"Error displaying frame {frame_idx}: {e}", level=logging.ERROR)

    def prepare_video(self, filepath):
        try:
            self.stop_processing.clear() # Allow processing threads to run
            self.frame_buffer.clear()
            self.frames_processed_count = 0
            self.current_frame_idx = -1 # Reset current frame index

            self.audio_path = self.extract_audio(filepath) # Use the passed filepath

            # --- 新增: 若 FPS > 25，產生 FPS=25 的暫存影片 ---
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                raise Exception(f"Cannot open video file: {filepath}")

            orig_fps = cap.get(cv2.CAP_PROP_FPS) or 25
            self.fps = orig_fps
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_duration = self.total_frames / self.fps if self.fps > 0 else 0
            self.video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            # 新增: 若 FPS > 25，轉檔
            self.temp_video_path = None
            if orig_fps > 25:
                if not self.temp_cache_dir:
                    # 若 extract_audio 尚未建立暫存資料夾，則建立
                    video_dir = os.path.dirname(filepath)
                    self.temp_cache_dir = tempfile.mkdtemp(prefix='.vidplayer_cache_', dir=video_dir)
                self.temp_video_path = os.path.join(self.temp_cache_dir, "temp_fps25.mp4")
                # ffmpeg 指令：-r 25 -vsync 2 保持時長
                cmd = f'ffmpeg -y -loglevel error -i "{filepath}" -r 25 -vsync 2 -c:v libx264 -preset ultrafast -crf 18 -c:a copy "{self.temp_video_path}"'
                os.system(cmd)
                # 檢查檔案是否產生
                if not os.path.exists(self.temp_video_path) or os.path.getsize(self.temp_video_path) == 0:
                    raise Exception("FFmpeg failed to create FPS=25 temp video.")
                # 以暫存影片為主
                video_path_for_play = self.temp_video_path
                # 重新取得 FPS/frames/duration
                cap2 = cv2.VideoCapture(video_path_for_play)
                self.fps = cap2.get(cv2.CAP_PROP_FPS) or 25
                self.total_frames = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
                self.video_duration = self.total_frames / self.fps if self.fps > 0 else 0
                self.video_width = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.video_height = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap2.release()
            else:
                video_path_for_play = filepath

            self.video_path = video_path_for_play # 之後所有 frame 讀取都用這個

            if self.video_width == 0 or self.video_height == 0:
                raise Exception("Failed to read video dimensions.")

            self.shared_state.log(f"Video info: {self.video_width}x{self.video_height}, {self.total_frames} frames, {self.fps:.2f} FPS", level=logging.INFO)

            # Schedule UI updates on the main thread using self.frame.after
            if self.frame and self.frame.winfo_exists():
                self.frame.after(0, lambda: self.time_total_label.config(text=self.format_time(self.video_duration)))
                self.frame.after(0, lambda: self.timeline_scale.config(to=100)) # Scale is 0-100 for percentage

                # Start background threads for reading and processing frames
                self.processing_thread = threading.Thread(target=self.background_processor, daemon=True)
                self.frame_reader_thread = threading.Thread(target=self.read_frames_to_queue, daemon=True)
                self.processing_thread.start()
                self.frame_reader_thread.start()

                self.frame.after(0, lambda: self.progress_label.config(text="Buffering initial frames..."))

                # Wait for the first frame to be buffered before starting playback
                # This should be done carefully to not block the main thread for too long.
                # A better approach might be to start playback and let it catch up,
                # or show a loading indicator until frame 0 is ready.
                # For now, a brief check:
                def check_buffer_and_play():
                    if self.stop_processing.is_set(): return # Video was stopped
                    if 0 in self.frame_buffer:
                        if pygame.mixer.get_init() and self.audio_path:
                            try:
                                pygame.mixer.music.load(self.audio_path)
                                self.frame.after(0, self.start_playback) # Start playback now
                            except pygame.error as e:
                                self.shared_state.log(f"Pygame error loading audio: {e}", level=logging.ERROR)
                                messagebox.showerror("Audio Error", f"Could not load audio: {e}", parent=self.frame.winfo_toplevel())
                                # Proceed without audio or stop? For now, proceed.
                        else:
                             self.shared_state.log("Pygame mixer not init or no audio path, cannot play audio.", level=logging.WARNING)
                             self.frame.after(0, self.start_playback) # Start video playback without audio

                        self.frame.after(0, self.enable_button_states)
                        self.shared_state.log("Video ready, auto-starting playback.", level=logging.INFO)
                    elif self.frame and self.frame.winfo_exists(): # If frame 0 not ready, check again
                        self.frame.after(100, check_buffer_and_play)

                if self.frame and self.frame.winfo_exists():
                    self.frame.after(100, check_buffer_and_play)

            else: # Frame doesn't exist, cannot proceed
                 self.shared_state.log("Frame does not exist during prepare_video, cannot schedule UI updates.", level=logging.ERROR)


        except Exception as e:
            error_msg = f"Failed to load video: {e}"
            self.shared_state.log(error_msg, level=logging.ERROR)
            messagebox.showerror("Error", error_msg, parent=self.frame.winfo_toplevel() if self.frame and self.frame.winfo_exists() else None)
            if self.frame and self.frame.winfo_exists():
                self.frame.after(0, self.enable_button_states)
            self.stop_video() # Ensure cleanup
            # Try to play next if in a playlist
            if self.playlist and self.frame and self.frame.winfo_exists():
                self.frame.after(100, self.play_next_video)

    def enable_button_states(self): # Renamed from enable_button
        # Enable/disable buttons based on current state
        if hasattr(self, 'btn_select_file'): self.btn_select_file.config(state=tk.NORMAL)
        if hasattr(self, 'btn_select_folder'): self.btn_select_folder.config(state=tk.NORMAL)

        play_pause_state = tk.NORMAL if self.video_path else tk.DISABLED
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(state=play_pause_state)

        self.update_nav_buttons_state() # Handles prev/next/jump

        if hasattr(self, 'btn_adjust_order'):
            adj_order_state = tk.NORMAL if (self.play_mode_var.get() == 'json' and self.current_folder_path) else tk.DISABLED
            self.btn_adjust_order.config(state=adj_order_state)

        # Update progress label
        if hasattr(self, 'progress_label'):
            if self.is_playing and not self.is_paused:
                self.progress_label.config(text="Playing...")
            elif self.is_paused:
                self.progress_label.config(text="Paused")
            else: # Stopped or ready
                if self.playlist and self.current_playlist_index != -1:
                    playlist_info = f"({self.current_playlist_index + 1}/{len(self.playlist)})"
                    self.progress_label.config(text=f"Ready {playlist_info}")
                else:
                    self.progress_label.config(text="Ready. Select file/folder.")

    def stop_video(self):
        self.shared_state.log("Stopping video playback...", level=logging.DEBUG)
        self.is_playing = False
        self.is_paused = False
        self.stop_processing.set() # Signal background threads to stop

        if self.after_id: # Cancel pending frame updates
            if self.frame and self.frame.winfo_exists(): self.frame.after_cancel(self.after_id)
            self.after_id = None

        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            if self.temp_audio_path and os.path.exists(self.temp_audio_path):
                try:
                    # Attempt to unload. This might fail if file is still "in use" briefly by mixer.
                    pygame.mixer.music.unload()
                except pygame.error as e:
                    self.shared_state.log(f"Pygame error unloading music (common, often ignorable): {e}", level=logging.DEBUG)


        # Wait briefly for threads to finish, but don't block UI for too long
        if self.frame_reader_thread and self.frame_reader_thread.is_alive():
            self.frame_reader_thread.join(timeout=0.5)
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=0.5)

        if self.canvas and self.canvas.winfo_exists():
            self.canvas.delete("all") # Clear the canvas

        self.frame_buffer.clear()
        if hasattr(self, 'timeline_var'): self.timeline_var.set(0)
        if hasattr(self, 'time_current_label'): self.time_current_label.config(text="00:00")

        # Clear the processing queue
        while not self.processing_queue.empty():
            try:
                self.processing_queue.get_nowait()
            except queue.Empty:
                break

        self.frame_reader_thread = None
        self.processing_thread = None
        self.shared_state.log("Video stop procedure complete.", level=logging.DEBUG)


    def on_resize(self, event):
        # Called when the video canvas (self.canvas) is resized
        if event.width > 1 and event.height > 1: # Ensure valid dimensions
            new_size = (event.width, event.height)
            with self.canvas_size_lock:
                if new_size != self.last_known_canvas_size:
                    # self.canvas_width, self.canvas_height = new_size # These are not instance vars
                    self.last_known_canvas_size = new_size
                    # When canvas resizes, existing frames in buffer are for old size.
                    # Clear buffer to force reprocessing for new size.
                    self.frame_buffer.clear()
                    self.shared_state.log(f"Canvas resized to {new_size}. Frame buffer cleared.", level=logging.DEBUG)

            # If playing, try to re-display current frame (it will be reprocessed if not in buffer)
            if self.is_playing and self.current_frame_idx != -1: # and self.current_frame_idx in self.frame_buffer:
                 # This might try to display an old-sized frame if it's still in buffer before clear takes full effect.
                 # Or, if cleared, it will wait for the frame to be re-processed.
                 self.display_frame(self.current_frame_idx)


    def on_timeline_press(self, event):
        if self.total_frames > 0 and self.video_path: # Only if video is loaded
            self.seeking = True
            if self.is_playing and not self.is_paused and pygame.mixer.get_init():
                pygame.mixer.music.pause() # Pause audio during seek scrubbing

    def on_timeline_release(self, event):
        if self.seeking and self.total_frames > 0 and self.video_path:
            self.seeking = False
            progress_percent = self.timeline_var.get() # Value from 0 to 100
            target_frame = int((progress_percent / 100.0) * self.total_frames)

            # Ensure target_frame is within bounds
            target_frame = max(0, min(target_frame, self.total_frames - 1 if self.total_frames > 0 else 0))

            self.shared_state.log(f"Timeline released. Seeking to frame: {target_frame}", level=logging.DEBUG)
            # Run seek in a new thread to avoid blocking UI
            threading.Thread(target=self.seek_to_frame, args=(target_frame,), daemon=True).start()

    def on_timeline_change(self, value_str): # Scale command passes value as string
        if self.total_frames <= 0 or not self.video_path: return
        progress_percent = float(value_str)
        target_frame = int((progress_percent / 100.0) * self.total_frames)
        current_time_display = target_frame / self.fps if self.fps > 0 else 0
        if hasattr(self, 'time_current_label'):
            self.time_current_label.config(text=self.format_time(current_time_display))

    def format_time(self, seconds):
        m, s = divmod(int(seconds), 60) # Ensure integer seconds for divmod
        return f"{m:02d}:{s:02d}"

    def update_timeline(self):
        # Updates timeline slider based on current_frame_idx
        if not self.seeking and self.total_frames > 0 and self.current_frame_idx >= 0:
            progress_percent = (self.current_frame_idx / float(self.total_frames)) * 100.0
            if hasattr(self, 'timeline_var'): self.timeline_var.set(progress_percent)

            current_time_display = self.current_frame_idx / self.fps if self.fps > 0 else 0
            if hasattr(self, 'time_current_label'):
                self.time_current_label.config(text=self.format_time(current_time_display))

    def background_processor(self):
        # Processes raw frames from self.processing_queue and puts PIL Images into self.frame_buffer
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            while not self.stop_processing.is_set():
                try:
                    if self.processing_queue.empty() and not futures:
                        time.sleep(0.01) # Wait if no work
                        continue

                    # Submit new tasks if queue has items and executor has capacity
                    while not self.processing_queue.empty() and len(futures) < self.max_workers * 2 : # Keep a backlog for the executor
                        raw_frames_batch = [self.processing_queue.get_nowait()]
                        # Simple batching: take one at a time for now. Could be optimized.
                        futures.append(executor.submit(self.process_frame_batch, raw_frames_batch))
                        self.processing_queue.task_done()


                    # Process completed futures
                    done_futures = [f for f in futures if f.done()]
                    for future in done_futures:
                        futures.remove(future)
                        try:
                            processed_batch = future.result()
                            for frame_index, pil_image in processed_batch:
                                if self.stop_processing.is_set(): break
                                self.frame_buffer[frame_index] = pil_image
                                self.frames_processed_count += 1
                        except Exception as e:
                             self.shared_state.log(f"Error getting result from frame processing future: {e}", level=logging.ERROR)
                    if self.stop_processing.is_set(): break
                    time.sleep(0.005) # Small sleep to yield

                except queue.Empty:
                    time.sleep(0.01) # Wait if queue temporarily empty during batch fill
                except Exception as e:
                    if not self.stop_processing.is_set(): # Log only if not intentionally stopping
                        self.shared_state.log(f"Error in background_processor: {e}", level=logging.ERROR)
                        time.sleep(0.1) # Longer sleep on error
        self.shared_state.log("Background frame processor thread finished.", level=logging.DEBUG)


    def seek_to_frame(self, target_frame):
        if not self.video_path:
            self.shared_state.log("Seek aborted: No video path.", level=logging.WARNING)
            return

        target_frame = max(0, min(target_frame, self.total_frames - 1 if self.total_frames > 0 else 0))
        self.shared_state.log(f"Seeking to frame {target_frame}...", level=logging.DEBUG)

        was_playing_before_seek = self.is_playing and not self.is_paused
        self.is_paused = True # Pause playback logic during seek

        if self.frame and self.frame.winfo_exists() and hasattr(self, 'progress_label'):
            self.frame.after(0, lambda: self.progress_label.config(text=f"Seeking to {self.format_time(target_frame/self.fps if self.fps > 0 else 0)}..."))

        # Critical section for seek_request_frame and clearing buffer
        with self.seek_lock:
            self.seek_request_frame = target_frame
            self.frame_buffer.clear() # Clear buffer as we are jumping
            # Also clear the input queue for the processor, as old frames are not needed
            while not self.processing_queue.empty():
                try: self.processing_queue.get_nowait()
                except queue.Empty: break
            self.shared_state.log(f"Seek lock acquired. Buffer/Queue cleared. seek_request_frame set to {target_frame}", level=logging.DEBUG)


        # Wait for the target frame (or a nearby one) to appear in the buffer
        # This relies on read_frames_to_queue and background_processor to catch up
        start_wait_time = time.time()
        frame_to_display_after_seek = -1

        while time.time() - start_wait_time < 10: # Max 10 seconds wait for seek
            if self.stop_processing.is_set():
                self.shared_state.log("Seek aborted as stop_processing is set.", level=logging.INFO)
                if was_playing_before_seek: self.resume_playback()
                else: self.is_paused = False # Reset pause state
                return

            # Check if target_frame or a slightly later one is available (for read-ahead)
            for i in range(target_frame, min(target_frame + int(self.fps/2), self.total_frames)):
                if i in self.frame_buffer:
                    frame_to_display_after_seek = i
                    break
            if frame_to_display_after_seek != -1:
                break
            time.sleep(0.02) # Brief sleep while waiting

        if frame_to_display_after_seek == -1:
            self.shared_state.log(f"Seek timeout or frame {target_frame} not buffered after 10s.", level=logging.WARNING)
            # Reset states and potentially try to resume from where it was or stop
            if was_playing_before_seek: self.resume_playback()
            else: self.is_paused = False
            if hasattr(self, 'progress_label') and self.frame.winfo_exists():
                 self.frame.after(0, lambda: self.progress_label.config(text="Seek failed."))
            return

        self.current_frame_idx = frame_to_display_after_seek
        seek_time_sec = frame_to_display_after_seek / self.fps if self.fps > 0 else 0

        if self.frame and self.frame.winfo_exists():
            self.frame.after(0, self.display_frame, frame_to_display_after_seek)
            self.frame.after(0, self.update_timeline)

        self.start_time = time.time() - seek_time_sec # Adjust internal start time for timing

        if pygame.mixer.get_init() and self.audio_path:
            try:
                pygame.mixer.music.play(start=seek_time_sec)
                if not was_playing_before_seek: # If it wasn't playing before, pause audio immediately
                    pygame.mixer.music.pause()
            except pygame.error as e:
                self.shared_state.log(f"Pygame error during seek audio playback: {e}", level=logging.ERROR)

        if was_playing_before_seek:
            self.is_paused = False # Resume playback state
            if self.frame and self.frame.winfo_exists():
                 if hasattr(self, 'progress_label'): self.frame.after(0, lambda: self.progress_label.config(text="Playing..."))
                 self.frame.after(0, self.update_frame) # Restart video frame updates
        else:
            self.is_paused = False # Important: reset is_paused even if not resuming, so toggle works
            self.pause_playback() # Explicitly call pause_playback to set UI to paused state
            if hasattr(self, 'progress_label') and self.frame.winfo_exists():
                self.frame.after(0, lambda: self.progress_label.config(text="Paused"))


    def toggle_play_pause(self):
        if not self.video_path:
            self.shared_state.log("Play/Pause toggle: No video path.", level=logging.DEBUG)
            return
        if self.is_playing:
            if self.is_paused:
                self.resume_playback()
            else:
                self.pause_playback()
        else: # Was stopped, start playback
            self.start_playback()

    def pause_playback(self):
        if not self.is_playing or self.is_paused: return
        self.is_paused = True
        self.pause_time = time.time() # Record time of pause
        if pygame.mixer.get_init(): pygame.mixer.music.pause()
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(text="Play")
        if hasattr(self, 'progress_label'): self.progress_label.config(text="Paused")
        self.shared_state.log("Playback paused.", level=logging.INFO)

    def resume_playback(self):
        if not self.is_playing or not self.is_paused: return
        # Adjust start_time to account for the pause duration
        if self.pause_time and self.start_time:
            self.start_time += (time.time() - self.pause_time)

        self.is_paused = False
        self.pause_time = None
        if pygame.mixer.get_init(): pygame.mixer.music.unpause()
        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(text="Pause")
        if hasattr(self, 'progress_label'): self.progress_label.config(text="Playing...")
        self.shared_state.log("Playback resumed.", level=logging.INFO)
        if self.frame and self.frame.winfo_exists():
            self.update_frame() # Restart UI frame updates

    def start_playback(self):
        # This is called when starting from a stopped state or after loading a new video.
        if not self.video_path or self.is_playing: # Don't start if already playing
            self.shared_state.log(f"Start playback called but video_path:'{self.video_path}', is_playing:{self.is_playing}", level=logging.DEBUG)
            return

        self.is_playing = True
        self.is_paused = False

        # If current_frame_idx is -1 (e.g. new video), start from 0. Otherwise, resume from current_frame_idx.
        self.current_frame_idx = max(0, self.current_frame_idx)
        start_sec = self.current_frame_idx / self.fps if self.fps > 0 else 0

        self.start_time = time.time() - start_sec # Set/reset reference start time

        if pygame.mixer.get_init() and self.audio_path:
            try:
                # pygame.mixer.music.load(self.audio_path) # Audio should be loaded in prepare_video
                pygame.mixer.music.play(start=start_sec)
            except pygame.error as e:
                self.shared_state.log(f"Pygame error starting audio playback: {e}", level=logging.ERROR)
               
                messagebox.showerror("Audio Error", f"Could not play audio: {e}", parent=self.frame.winfo_toplevel())

        if hasattr(self, 'btn_play_pause'): self.btn_play_pause.config(text="Pause")
        if hasattr(self, 'progress_label'): self.progress_label.config(text="Playing...")
        self.shared_state.log(f"Playback started from frame {self.current_frame_idx} ({start_sec:.2f}s).", level=logging.INFO)

        if self.frame and self.frame.winfo_exists():
            self.update_frame() # Start UI frame updates

    def read_frames_to_queue(self):
        # This thread reads frames from video file and puts them into self.processing_queue
        if not self.video_path:
            self.shared_state.log("Frame reader: No video path.",level=logging.WARNING)
            return

        try:
            video_capture = cv2.VideoCapture(self.video_path)
            if not video_capture.isOpened():
                self.shared_state.log(f"Frame reader: Failed to open video {self.video_path}", level=logging.ERROR)
                return
        except Exception as e:
            self.shared_state.log(f"Frame reader: cv2.VideoCapture exception for {self.video_path}: {e}", level=logging.ERROR)
            return

        current_read_frame_idx = 0
        self.shared_state.log(f"Frame reader thread started for {self.video_path}", level=logging.DEBUG)

        while not self.stop_processing.is_set():
            with self.seek_lock: # Check if a seek is requested
                if self.seek_request_frame != -1:
                    target_seek_frame = self.seek_request_frame
                    self.shared_state.log(f"Frame reader: Seek request to frame {target_seek_frame}", level=logging.DEBUG)
                    video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_seek_frame)
                    current_read_frame_idx = target_seek_frame
                    self.seek_request_frame = -1 # Consume the seek request
                    # Frame buffer and processing queue are cleared by seek_to_frame
                    # which holds the seek_lock during that operation.

            # Buffer control: Don't overfill the queue if processing is slow
            if self.processing_queue.qsize() < self.buffer_size * 2: # Keep queue size manageable
                ret, frame = video_capture.read()
                if not ret: # End of video or error
                    self.shared_state.log(f"Frame reader: End of video or read error for {self.video_path} at frame {current_read_frame_idx}", level=logging.DEBUG)
                    break

                # Put raw frame and its index into the queue
                try:
                    self.processing_queue.put((current_read_frame_idx, frame.copy()), timeout=0.1) # Add timeout to put
                    current_read_frame_idx += 1
                except queue.Full:
                    if self.stop_processing.is_set(): break # Exit if stopping
                    time.sleep(0.01) # Queue full, wait briefly
            else:
                if self.stop_processing.is_set(): break # Exit if stopping
                time.sleep(0.01) # Queue is full, wait for processor to catch up

        video_capture.release()
        self.shared_state.log(f"Frame reader thread finished for {self.video_path}", level=logging.DEBUG)


# For standalone testing (optional)
if __name__ == '__main__':
    # This standalone test requires a mock Module class and SharedState
    # For simplicity, assume Module class is available or define a minimal mock here
    class MockSharedState:
        def log(self, message, level=logging.INFO):
            print(f"LOG ({logging.getLevelName(level)}): {message}")
        def get(self, key, default=None): return default
        def set(self, key, value): pass

    # Fallback for Module if not available (e.g. running file directly without main.py in path)
    try:
        from main import Module as MainModuleBase
    except ImportError:
        class MainModuleBase: # Minimal mock
            def __init__(self, master, shared_state, module_name="TestVideo", gui_manager=None):
                self.master = master # This is the frame_wrapper in ModularGUI context
                self.shared_state = shared_state
                self.module_name = module_name
                self.gui_manager = gui_manager
                # The module's actual content frame, child of 'master' (frame_wrapper)
                self.frame = ttk.Frame(master, borderwidth=1, relief=tk.SOLID)
                # Mock title bar elements for completeness if needed by module's update_module_title
                self.title_label = ttk.Label(self.frame, text=module_name)
                # self.title_label.pack(side=tk.TOP, fill=tk.X) # Example packing
                self.is_maximized = False # Mock attribute
                shared_state.log(f"MockModuleBase '{module_name}' initialized.")

            def get_frame(self): return self.frame
            def on_destroy(self):
                self.shared_state.log(f"MockModuleBase '{self.module_name}' on_destroy called.")

    root = tk.Tk()
    root.title("Video Player Module Standalone Test")
    root.geometry("960x700") # Give it a decent size

    mock_shared_state = MockSharedState()

    # In ModularGUI, instantiate_module creates a frame_wrapper, and module's self.frame is child of that.
    # For standalone, root can act as the container where the module's self.frame is packed.
    # So, the 'master' passed to VideoPlayerModule will be 'root'.
    # Inside VideoPlayerModule, super().__init__(root, ...) creates self.frame = ttk.Frame(root, ...)
    player_module = VideoPlayerModule(root, mock_shared_state, module_name="StandaloneVideoPlayer")

    # The module's main frame (player_module.get_frame()) needs to be packed into its master (root).
    # This is done by ModularGUI.instantiate_module usually.
    # Here, Module base class already creates self.frame but does not pack it.
    # The VideoPlayerModule's create_ui packs its content *into* its self.frame.
    # So we need to pack the self.frame itself into the root.
    player_module.get_frame().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Ensure on_destroy is called when window is closed
    root.protocol("WM_DELETE_WINDOW", lambda: (player_module.on_destroy(), root.destroy()))

    root.mainloop()