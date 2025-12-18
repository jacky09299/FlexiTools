import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
import threading
import sys
import re
import datetime

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class YtDlpLogger:
    def __init__(self, log_method):
        self.log_method = log_method

    def debug(self, msg):
        # Ignore debug messages (user wants failures only)
        pass

    def warning(self, msg):
        # Ignore warnings (user wants failures only)
        pass

    def error(self, msg):
        # Clean up error message for readability
        # Remove "ERROR: " prefix if present
        clean_msg = msg.replace("ERROR: ", "")
        
        # Remove [youtube] or [download] prefixes if present
        # e.g. "[youtube] b-gyr8Rubmo: Video unavailable..." -> "Video unavailable..."
        # Regex to remove [tag] ID: 
        clean_msg = re.sub(r'^\[.*?\]\s*.*?\:\s*', '', clean_msg)
        
        # If regex didn't match (no ID), try removing just [tag]
        clean_msg = re.sub(r'^\[.*?\]\s*', '', clean_msg)
        
        self.log_method(f"{clean_msg}")

class YoutubeDownloaderModule(Module):
    def __init__(self, master, shared_state, module_name="Youtube Downloader", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.url_text = None
        self.status_label = None
        self.progress_bar = None
        self.download_dir = None
        self.download_thread = None
        self.stop_download = False
        self.skip_current = False
        self.current_ydl = None
        self.current_url_index = 0  # 追蹤當前下載的 URL 索引
        self.total_urls = 0  # 總 URL 數量
        self.log_visible = False # 錯誤日誌是否可見

        # Initialize widget references
        self.folder_label = None
        self.folder_btn = None
        self.url_label = None
        self.help_text = None
        self.load_txt_btn = None
        self.format_label = None
        self.quality_label = None
        self.download_button = None
        self.skip_button = None
        self.stop_button = None
        self.log_toggle_btn = None
        self.log_text = None
        self.sidebar_frame = None
        self.main_container = None
        self.content_frame = None
        self.skip_unavailable_var = None # Checkbox variable

        self.create_ui()
        self.update_language()
        self.check_dependencies()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Main container for layout (Horizontal split)
        self.main_container = ttk.Frame(self.frame)
        self.main_container.pack(expand=True, fill=tk.BOTH)

        # Left side - Main Content
        self.content_frame = ttk.Frame(self.main_container)
        self.content_frame.pack(side=tk.LEFT, padx=10, pady=10, expand=True, fill=tk.BOTH)

        # Right side - Error Log Sidebar (initially hidden)
        self.sidebar_frame = ttk.Frame(self.main_container, width=300, relief=tk.SUNKEN, borderwidth=1)
        # Not packed initially

        # --- Sidebar Content ---
        sidebar_header = ttk.Frame(self.sidebar_frame)
        sidebar_header.pack(fill=tk.X, padx=5, pady=5)
        self.log_lbl = ttk.Label(sidebar_header, text="Error Log", font=("TkDefaultFont", 10, "bold"))
        self.log_lbl.pack(side=tk.LEFT)
        self.clear_btn = ttk.Button(sidebar_header, text="Clear", command=self.clear_log, width=6)
        self.clear_btn.pack(side=tk.RIGHT)

        self.log_text = tk.Text(self.sidebar_frame, width=40, state="disabled", font=("TkFixedFont", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- Main Content UI ---
        
        # 資料夾選擇 - 移到最上面
        folder_frame = ttk.Frame(self.content_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        self.folder_label = ttk.Label(folder_frame, text="Download Folder:")
        self.folder_label.pack(side=tk.LEFT, padx=(0, 5))
        self.folder_path_var = tk.StringVar(value="")
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path_var, state="readonly")
        folder_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.folder_btn = ttk.Button(folder_frame, text="Select...", command=self.select_download_folder)
        self.folder_btn.pack(side=tk.LEFT, padx=(5, 0))

        # URL輸入框 - 支援多行及任何類型的URL，包含播放清單項目選擇
        url_frame = ttk.Frame(self.content_frame)
        url_frame.pack(fill=tk.BOTH, pady=5, expand=True)
        
        self.url_label = ttk.Label(url_frame, text="YouTube URLs (one per line):")
        self.url_label.pack(anchor=tk.W)
        
        # 使用說明
        self.help_text = ttk.Label(url_frame, text="Format examples:\n" +
                             "• Single video: https://www.youtube.com/watch?v=VIDEO_ID\n" +
                             "• Full playlist: https://www.youtube.com/playlist?list=PLAYLIST_ID\n" +
                             "• Playlist with specific items: https://www.youtube.com/playlist?list=PLAYLIST_ID [2-5,7,10-12]",
                             font=("TkDefaultFont", 8), foreground="gray")
        self.help_text.pack(anchor=tk.W, pady=(0, 5))
        
        url_text_frame = ttk.Frame(url_frame)
        url_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.url_text = tk.Text(url_text_frame, height=8)
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        url_scrollbar = ttk.Scrollbar(url_text_frame, orient=tk.VERTICAL, command=self.url_text.yview)
        url_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_text.config(yscrollcommand=url_scrollbar.set)
        
        # 載入txt按鈕
        self.load_txt_btn = ttk.Button(url_frame, text="Load .txt", command=self.load_txt)
        self.load_txt_btn.pack(anchor=tk.E, pady=(2, 0))

        # Format Selection
        format_frame = ttk.Frame(self.content_frame)
        format_frame.pack(fill=tk.X, pady=5)
        
        self.format_label = ttk.Label(format_frame, text="Format:")
        self.format_label.pack(side=tk.LEFT, padx=(0, 5))

        self.format_var = tk.StringVar(value="mp4")
        format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, 
                                   values=["mp4", "mp3", "best"], state="readonly", width=15)
        format_combo.pack(side=tk.LEFT, padx=(0, 5))

        # Quality Selection
        self.quality_label = ttk.Label(format_frame, text="Quality:")
        self.quality_label.pack(side=tk.LEFT, padx=(10, 5))

        self.quality_var = tk.StringVar(value="best")
        quality_combo = ttk.Combobox(format_frame, textvariable=self.quality_var,
                                   values=["best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"], state="readonly", width=15)
        quality_combo.pack(side=tk.LEFT)

        # Options Checkbox
        options_frame = ttk.Frame(self.content_frame)
        options_frame.pack(fill=tk.X, pady=5)
        self.skip_unavailable_var = tk.BooleanVar(value=True)
        self.skip_unavailable_chk = ttk.Checkbutton(options_frame, text="Skip unavailable videos (Smart Playlist)", variable=self.skip_unavailable_var)
        self.skip_unavailable_chk.pack(side=tk.LEFT)

        # 下載控制按鈕
        button_frame = ttk.Frame(self.content_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.download_button = ttk.Button(button_frame, text="Download All", command=self.start_download_thread)
        self.download_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.skip_button = ttk.Button(button_frame, text="Skip Current URL", command=self.skip_current_download, state="disabled")
        self.skip_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Stop All", command=self.stop_all_downloads, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        # Toggle Log Button
        self.log_toggle_btn = ttk.Button(button_frame, text="Show Error Log", command=self.toggle_error_log)
        self.log_toggle_btn.pack(side=tk.RIGHT)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.content_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Status Label
        self.status_label = ttk.Label(self.content_frame, text="Status: Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=5)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def update_language(self):
        super().update_language()
        if not getattr(self, 'folder_label', None): return

        self.folder_label.config(text=self.tr("module_ytdl_lbl_folder", "Download Folder:"))
        self.folder_btn.config(text=self.tr("module_ytdl_btn_select", "Select..."))
        self.url_label.config(text=self.tr("module_ytdl_lbl_urls", "YouTube URLs (one per line):"))
        self.help_text.config(text=self.tr("module_ytdl_lbl_help", "Format examples:\n..."))
        self.load_txt_btn.config(text=self.tr("module_ytdl_btn_load", "Load .txt"))
        self.format_label.config(text=self.tr("module_ytdl_lbl_format", "Format:"))
        self.quality_label.config(text=self.tr("module_ytdl_lbl_quality", "Quality:"))
        self.download_button.config(text=self.tr("module_ytdl_btn_download", "Download All"))
        self.skip_button.config(text=self.tr("module_ytdl_btn_skip", "Skip Current URL"))
        self.stop_button.config(text=self.tr("module_ytdl_btn_stop", "Stop All"))
        self.skip_unavailable_chk.config(text=self.tr("module_ytdl_chk_skip_unavailable", "Skip unavailable videos (Smart Playlist)"))
        
        self.log_lbl.config(text=self.tr("module_ytdl_lbl_error_log", "Error Log"))
        self.clear_btn.config(text=self.tr("module_ytdl_btn_clear", "Clear"))

        log_btn_text = self.tr("module_ytdl_btn_hide_log", "Hide Error Log") if self.log_visible else self.tr("module_ytdl_btn_show_log", "Show Error Log")
        self.log_toggle_btn.config(text=log_btn_text)

        if self.status_label.cget("text") in ["Status: Ready", "狀態: 就緒"]:
             self.status_label.config(text=self.tr("module_ytdl_status_ready", "Status: Ready"))

    def toggle_error_log(self):
        if self.log_visible:
            self.sidebar_frame.pack_forget()
            self.log_toggle_btn.config(text=self.tr("module_ytdl_btn_show_log", "Show Error Log"))
            self.log_visible = False
        else:
            self.sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
            self.log_toggle_btn.config(text=self.tr("module_ytdl_btn_hide_log", "Hide Error Log"))
            self.log_visible = True

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def log_error(self, message):
        """Append error message to the log sidebar"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}\n"
        
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, full_msg)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
            
            # Auto-show sidebar if hidden
            if not self.log_visible:
                self.toggle_error_log()
        
        self.master.after(0, _append)

    def select_download_folder(self):
        folder = filedialog.askdirectory(parent=self.frame)
        if folder:
            self.download_dir = folder
            self.folder_path_var.set(folder)

    def load_txt(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self.frame
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.url_text.delete("1.0", tk.END)
                self.url_text.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load txt file: {e}", parent=self.frame)

    def check_dependencies(self):
        """Check if yt-dlp is available"""
        try:
            import yt_dlp
            self.ytdlp_available = True
            self.update_status(f"{self.tr('module_ytdl_status_ready', 'Status: Ready')} (yt-dlp available)")
        except ImportError:
            self.ytdlp_available = False
            self.update_status(self.tr("module_ytdl_err_ytdl", "yt-dlp not available. Please install yt-dlp."))

    def parse_url_line(self, line):
        """解析URL行，提取URL和播放清單項目範圍"""
        line = line.strip()
        if not line:
            return None, None
        
        # 檢查是否有播放清單項目指定 [項目範圍]
        playlist_range_match = re.search(r'\[([^\]]+)\]', line)
        if playlist_range_match:
            url = line[:playlist_range_match.start()].strip()
            playlist_range = playlist_range_match.group(1).strip()
            return url, playlist_range
        else:
            return line, None

    def start_download_thread(self):
        """開始下載線程"""
        if self.download_thread and self.download_thread.is_alive():
            return
            
        self.stop_download = False
        self.skip_current = False
        self.current_url_index = 0
        self.download_thread = threading.Thread(target=self.download_all)
        self.download_thread.daemon = True
        self.download_thread.start()
        
        # 更新按鈕狀態
        self.download_button.config(state="disabled")
        self.skip_button.config(state="normal")
        self.stop_button.config(state="normal")

    def skip_current_download(self):
        """跳過當前下載的 URL（包括整個播放清單）"""
        self.skip_current = True
        if self.current_ydl:
            try:
                # 強制停止 yt-dlp
                self.current_ydl._stop_download = True
            except:
                pass
        self.update_status(self.tr("module_ytdl_status_skipping", "Status: Skipping URL {0}/{1}...").format(self.current_url_index, self.total_urls))

    def stop_all_downloads(self):
        """停止所有下載"""
        self.stop_download = True
        self.skip_current = True
        if self.current_ydl:
            try:
                self.current_ydl._stop_download = True
            except:
                pass
        self.update_status(self.tr("module_ytdl_status_stopping", "Status: Stopping all downloads..."))
        
        # 重置按鈕狀態
        self.download_button.config(state="normal")
        self.skip_button.config(state="disabled")
        self.stop_button.config(state="disabled")

    def download_all(self):
        """統一下載函數，使用yt-dlp處理所有類型的URL"""
        try:
            if not self.ytdlp_available:
                messagebox.showerror("Error", self.tr("module_ytdl_err_ytdl", "yt-dlp is not available."), parent=self.frame)
                return
                
            # 取得所有URL
            urls_text = self.url_text.get("1.0", tk.END).strip()
            if not urls_text:
                messagebox.showerror("Error", self.tr("module_ytdl_err_no_url", "Please enter at least one YouTube URL."), parent=self.frame)
                return
            
            if not self.download_dir:
                messagebox.showerror("Error", self.tr("module_ytdl_err_no_folder", "Please select a download folder."), parent=self.frame)
                return

            lines = [line.strip() for line in urls_text.splitlines() if line.strip()]
            if not lines:
                messagebox.showerror("Error", self.tr("module_ytdl_err_no_url", "Please enter at least one YouTube URL."), parent=self.frame)
                return

            self.total_urls = len(lines)
            errors = []  # 收集所有錯誤
            
            for idx, line in enumerate(lines, 1):
                # 檢查是否需要停止所有下載
                if self.stop_download:
                    self.update_status(self.tr("module_ytdl_status_stopped_user", "Status: Download stopped by user."))
                    break
                    
                # 更新當前 URL 索引
                self.current_url_index = idx
                
                url, playlist_range = self.parse_url_line(line)
                if not url:
                    continue
                    
                self.update_status(self.tr("module_ytdl_status_processing", "Status: Processing URL {0}/{1}: {2}...").format(idx, self.total_urls, url[:50]))
                self.progress_bar['value'] = 0
                
                # 重置跳過標記（每個新 URL 開始時重置）
                self.skip_current = False
                
                try:
                    success = self.download_with_ytdlp(url, playlist_range)
                    
                    # 如果這個 URL 被跳過，繼續下一個
                    if self.skip_current:
                        self.update_status(self.tr("module_ytdl_status_skipped_idx", "Status: Skipped URL {0}/{1}").format(idx, self.total_urls))
                        continue
                        
                    if not success:
                        self.log_error(f"Failed: {line}")
                        errors.append(f"Failed to download: {line}")
                        
                except Exception as e:
                    if not self.stop_download and not self.skip_current:
                        self.log_error(f"Error: {line} - {str(e)}")
                        errors.append(f"Error downloading {line}: {str(e)}")
                        self.shared_state.log(f"Error downloading {line}: {e}", level=logging.ERROR)

            # 所有下載完成後處理
            if not self.stop_download:
                if errors:
                    # Don't show popup if log is used, or show a small notification?
                    # User requested log, so maybe just update status
                    self.update_status(self.tr("module_ytdl_status_completed_errors", "Status: Completed with {0} errors. Check log.").format(len(errors)))
                    if not self.log_visible:
                         self.master.after(0, self.toggle_error_log)
                else:
                    self.update_status(self.tr("module_ytdl_status_completed_success", "Status: All downloads completed successfully!"))
        
        finally:
            # 重置按鈕狀態
            self.master.after(0, lambda: self.download_button.config(state="normal"))
            self.master.after(0, lambda: self.skip_button.config(state="disabled"))
            self.master.after(0, lambda: self.stop_button.config(state="disabled"))
            self.current_ydl = None

    def download_with_ytdlp(self, url, playlist_range=None):
        """使用yt-dlp下載（支援單一影片和播放清單）"""
        try:
            import yt_dlp
            
            # 檢查是否需要停止或跳過
            if self.stop_download or self.skip_current:
                return False
            
            format_choice = self.format_var.get()
            quality = self.quality_var.get()
            
            # 設定yt-dlp選項
            ydl_opts = {
                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [self.on_progress_ytdlp],
                # Add options to fix 403 Forbidden errors and improve stability
                'force_ipv4': True,
                'hls_prefer_native': True,
                'concurrent_fragment_downloads': 16,
                'merge_output_format': 'mp4',
                'ignoreerrors': True,  # Continue downloading even if one video fails
                'logger': YtDlpLogger(self.log_error), # Use custom logger
            }
            
            # 根據格式設定
            if format_choice == "mp3":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                if quality == "best":
                    # Use robust format selector
                    format_selector = "bv*[protocol=m3u8]+ba[protocol=m3u8]/best"
                elif quality.endswith("p") and quality[:-1].isdigit():
                    format_selector = (
                        f"bestvideo[height={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        f"best[ext=mp4]/best"
                    )
                else:
                    format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                
                ydl_opts['format'] = format_selector
            
            # 檢查是否為播放清單URL
            is_playlist_url = self.is_playlist_url(url)
            
            if is_playlist_url:
                if self.skip_unavailable_var.get():
                    # Smart Mode: Filter unavailable videos first
                    self.update_status(self.tr("module_ytdl_status_fetching_meta", "Status: Fetching playlist metadata (Smart Mode)..."))
                    
                    # 1. Fetch metadata
                    meta_opts = ydl_opts.copy()
                    meta_opts['extract_flat'] = True
                    with yt_dlp.YoutubeDL(meta_opts) as ydl:
                         info = ydl.extract_info(url, download=False)
                    
                    if not info or 'entries' not in info:
                        self.log_error("Failed to fetch playlist metadata.")
                        return False

                    all_entries = info['entries']
                    
                    # 2. Filter available entries and map logical index to original index
                    # Logical Index (1-based) -> Original Entry (1-based Index)
                    valid_entries_map = [] 
                    for i, entry in enumerate(all_entries):
                        # Simple check: if title indicates private/deleted or if entry is None
                        # Note: extract_flat=True might return minimal info. 
                        # yt-dlp usually marks unavailable videos with specific titles or nulls.
                        if entry:
                            title = entry.get('title', '')
                            if title not in ["[Private video]", "[Deleted video]", "[Unavailable video]"]:
                                valid_entries_map.append(i + 1) # Store 1-based original index
                    
                    # 3. Determine items to download
                    items_to_download = [] # List of original indices (1-based)
                    
                    if playlist_range:
                        # Parse range string "1-5,7-9"
                        ranges = playlist_range.split(',')
                        for r in ranges:
                            r = r.strip()
                            if '-' in r:
                                start, end = map(int, r.split('-'))
                                # Map logical range to original indices
                                # Logical indices are 1-based
                                for logical_idx in range(start, end + 1):
                                    if 1 <= logical_idx <= len(valid_entries_map):
                                        original_idx = valid_entries_map[logical_idx - 1]
                                        items_to_download.append(original_idx)
                            else:
                                logical_idx = int(r)
                                if 1 <= logical_idx <= len(valid_entries_map):
                                    original_idx = valid_entries_map[logical_idx - 1]
                                    items_to_download.append(original_idx)
                    else:
                        # Download all valid entries
                        items_to_download = valid_entries_map
                    
                    # 4. Download specific items
                    if not items_to_download:
                        self.log_error(self.tr("module_ytdl_err_no_valid_videos", "No valid videos found to download in the specified range."))
                        return False
                        
                    # Convert list of indices to string for playlist_items
                    # e.g., [1, 2, 4, 5] -> "1,2,4,5"
                    ydl_opts['playlist_items'] = ",".join(map(str, items_to_download))
                    
                elif playlist_range:
                    # Standard Mode with range
                    ydl_opts['playlist_items'] = playlist_range
            
            elif not is_playlist_url:
                # 確保只下載單一影片（不是播放清單）
                ydl_opts['noplaylist'] = True
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.current_ydl = ydl
                
                # 在下載過程中定期檢查跳過標記
                def check_skip_hook(d):
                    if self.skip_current or self.stop_download:
                        # 如果需要跳過，拋出異常來中斷下載
                        raise yt_dlp.DownloadError("Download skipped by user")
                    return self.on_progress_ytdlp(d)
                
                # 替換進度回調
                ydl_opts['progress_hooks'] = [check_skip_hook]
                ydl = yt_dlp.YoutubeDL(ydl_opts)
                self.current_ydl = ydl
                
                # 檢查下載前是否需要停止
                if self.stop_download or self.skip_current:
                    return False
                    
                ydl.download([url])
                
                # 檢查下載後是否被中斷
                if self.skip_current:
                    return False
            
            return True
            
        except yt_dlp.DownloadError as e:
            # 如果是用戶主動跳過或停止，不記錄為錯誤
            if self.stop_download or self.skip_current or "skipped by user" in str(e):
                return False
            self.log_error(f"Download Error ({url}): {e}")
            self.shared_state.log(f"yt-dlp download error from {url}: {e}", level=logging.ERROR)
            return False
        except Exception as e:
            # 如果是用戶主動停止，不記錄為錯誤
            if self.stop_download or self.skip_current:
                return False
            self.log_error(f"Error ({url}): {e}")
            self.shared_state.log(f"yt-dlp error downloading from {url}: {e}", level=logging.ERROR)
            return False
        finally:
            self.current_ydl = None

    def is_playlist_url(self, url):
        """判斷URL是否為播放清單"""
        playlist_indicators = ['playlist?list=', '/playlist?', 'list=']
        return any(indicator in url.lower() for indicator in playlist_indicators)

    def on_progress_ytdlp(self, d):
        """yt-dlp進度回調"""
        # 在進度回調中也檢查跳過標記
        if self.skip_current or self.stop_download:
            return
            
        if d['status'] == 'downloading':
            # 顯示目前下載檔名
            filename = d.get('filename')
            if filename:
                basename = os.path.basename(filename)
                status_msg = self.tr("module_ytdl_status_downloading", "Status: [{0}/{1}] Downloading {2}").format(self.current_url_index, self.total_urls, basename)
                self.master.after(0, lambda: self.status_label.config(text=status_msg))
            if 'total_bytes' in d:
                percentage = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.master.after(0, lambda: self.progress_bar.config(value=percentage))
            elif '_percent_str' in d:
                try:
                    percentage = float(d['_percent_str'].replace('%', ''))
                    self.master.after(0, lambda: self.progress_bar.config(value=percentage))
                except:
                    pass
        elif d['status'] == 'finished':
            filename = d.get('filename')
            if filename:
                basename = os.path.basename(filename)
                status_msg = self.tr("module_ytdl_status_finished_file", "Status: [{0}/{1}] Finished downloading {2}").format(self.current_url_index, self.total_urls, basename)
                self.master.after(0, lambda: self.status_label.config(text=status_msg))

    def update_status(self, message):
        """更新狀態"""
        self.master.after(0, lambda: self.status_label.config(text=message))

    def on_destroy(self):
        """清理 - 模組關閉時停止下載"""
        # 停止所有下載
        self.stop_download = True
        self.skip_current = True
        
        if self.current_ydl:
            try:
                self.current_ydl._stop_download = True
            except:
                pass
        
        # 等待下載線程結束（最多等待2秒）
        if self.download_thread and self.download_thread.is_alive():
            self.download_thread.join(timeout=2.0)
        
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")