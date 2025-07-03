# This module will contain functions for processing MP4 files.
#
# Required External Libraries:
# - OpenCV (cv2): pip install opencv-python
# - MoviePy: pip install moviepy
# - Tkinter (usually included with Python)

import tkinter as tk
from tkinter import filedialog, ttk
from rembg import remove
from PIL import Image
from main import Module
import os
import cv2 # For _process_to_frames
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, concatenate_videoclips # For audio extraction and splitting
from rembg import remove # For background removal
import numpy as np # For background removal

class MP4Processor(Module):
    def __init__(self, parent, shared_state, module_name, gui_manager):
        super().__init__(parent, shared_state, module_name, gui_manager)
        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.input_type_var = tk.StringVar(value="file")
        self.processing_mode_var = tk.StringVar()

        self.fps_var = tk.StringVar(value='30')
        self.segments_to_save_var = tk.StringVar()

        self.create_ui()

    def _log_status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END) # Scroll to the end
        self.status_text.update_idletasks() # Ensure UI updates
        self.status_text.config(state=tk.DISABLED)
        self.shared_state.log(message, "INFO")


    def _browse_input(self):
        current_input_type = self.input_type_var.get()
        path = ""
        if current_input_type == "file":
            path = filedialog.askopenfilename(
                title="Select MP4 File",
                filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*"))
            )
        elif current_input_type == "folder":
            path = filedialog.askdirectory(title="Select Folder Containing MP4 Files")

        if path:
            self.input_path_var.set(path)
            self.input_path_label.config(text=path)
            self._log_status(f"Input path set to: {path}")

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_path_var.set(path)
            self.output_path_label.config(text=path)
            self._log_status(f"Output path set to: {path}")

    def _on_processing_mode_changed(self, event=None):
        selected_mode = self.processing_mode_var.get()
        # self._log_status(f"Processing mode changed to: {selected_mode}") # Can be noisy, enable if needed for debug

        for widget in self.dynamic_options_frame.winfo_children():
            widget.pack_forget()

        if selected_mode == "Convert to Frames":
            self.frames_options_frame.pack(fill=tk.X, expand=True)
        elif selected_mode == "Split MP4":
            self.split_options_frame.pack(fill=tk.X, expand=True)

    def _parse_time(self, time_str):
        """Converts HH:MM:SS, MM:SS, or SS string to seconds."""
        parts = str(time_str).split(':')
        try:
            if len(parts) == 1:
                return int(parts[0])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                raise ValueError(f"Invalid time format structure: {time_str}")
        except ValueError as e: # Catch non-integer parts
            raise ValueError(f"Invalid time component in '{time_str}': {e}")


    def _process_to_frames(self, video_path, output_dir, target_fps_str, remove_bg):
        self._log_status(f"Starting 'Convert to Frames' for: {video_path}")
        cap = None
        try:
            try:
                target_fps = int(float(target_fps_str))
            except Exception:
                self._log_status(f"Invalid FPS value: {target_fps_str}, fallback to 1")
                target_fps = 1

            video_filename = os.path.splitext(os.path.basename(video_path))[0]
            frames_output_subdir = os.path.join(output_dir, f"{video_filename}_frames_fps{target_fps}")
            if not os.path.exists(frames_output_subdir):
                os.makedirs(frames_output_subdir)
                self._log_status(f"Created frames output subdirectory: {frames_output_subdir}")
            # 新增這行，讓你直接複製路徑
            self._log_status(f"Frame output directory (copy & paste in Explorer): {os.path.abspath(frames_output_subdir)}")
        except Exception as e:
            self._log_status(f"Error creating output subdirectory: {e}")
            return False

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self._log_status(f"Error: Could not open video file {video_path} with OpenCV.")
                return False

            original_fps = cap.get(cv2.CAP_PROP_FPS)
            self._log_status(f"Original video FPS: {original_fps:.2f}")

            # 修正 frame_interval 計算，確保不為0
            if original_fps <= 0 or target_fps <= 0:
                self._log_status(f"Warning: FPS invalid (original: {original_fps}, target: {target_fps}). Will save every frame.")
                frame_interval = 1
            else:
                frame_interval = max(1, int(round(original_fps / target_fps)))

            self._log_status(f"Saving 1 frame every {frame_interval} original frames to achieve ~{target_fps} FPS.")

            if remove_bg:
                self._log_status("Background removal enabled.")

            count = 0
            saved_frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    self._log_status(f"End of video or cannot read frame at count {count}.")
                    break
                if count % frame_interval == 0:
                    if remove_bg:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(frame_rgb)
                        output_pil_img = remove(pil_img)
                        frame = cv2.cvtColor(np.array(output_pil_img), cv2.COLOR_RGB2BGR)

                    frame_filename = os.path.join(frames_output_subdir, f"frame_{saved_frame_count:05d}.png")
                    success = cv2.imwrite(frame_filename, frame)
                    if not success:
                        self._log_status(f"Failed to write frame: {frame_filename}")
                    saved_frame_count += 1
                    if saved_frame_count % max(1, target_fps) == 0:
                        self._log_status(f"Saved {saved_frame_count} frames...")
                count += 1

            self._log_status(f"Successfully extracted {saved_frame_count} frames to {frames_output_subdir}")
            # 新增這行，列出前5張 frame 路徑
            if saved_frame_count > 0:
                sample_files = [os.path.join(frames_output_subdir, f) for f in sorted(os.listdir(frames_output_subdir))[:5]]
                self._log_status(f"Sample frame files: {sample_files}")
            return saved_frame_count > 0
        except cv2.error as e_cv2:
            self._log_status(f"OpenCV Error during frame extraction: {e_cv2}")
            return False
        except Exception as e:
            self._log_status(f"General Error during frame extraction: {e}")
            return False
        finally:
            if cap and cap.isOpened():
                cap.release()

    def _process_to_mp3(self, video_path, output_dir):
        self._log_status(f"Starting 'Extract to MP3' for: {video_path}")
        video_clip = None
        audio_clip = None
        try:
            video_filename_no_ext = os.path.splitext(os.path.basename(video_path))[0]
            output_mp3_path = os.path.join(output_dir, f"{video_filename_no_ext}.mp3")

            video_clip = VideoFileClip(video_path) # Critical moviepy operation
            if not video_clip.audio:
                self._log_status(f"Error: No audio track found in {video_path}")
                return False # Return False as no audio means failure for this operation

            audio_clip = video_clip.audio
            audio_clip.write_audiofile(output_mp3_path, codec='mp3') # Critical moviepy operation

            self._log_status(f"Successfully extracted MP3 to: {output_mp3_path}")
            return True
        except Exception as e:
            self._log_status(f"Error during MP3 extraction: {e}")
            return False
        finally:
            if audio_clip: audio_clip.close()
            if video_clip: video_clip.close()


    def _process_to_ogg(self, video_path, output_dir):
        self._log_status(f"Starting 'Extract to OGG' for: {video_path}")
        video_clip = None
        audio_clip = None
        try:
            video_filename_no_ext = os.path.splitext(os.path.basename(video_path))[0]
            output_ogg_path = os.path.join(output_dir, f"{video_filename_no_ext}.ogg")

            video_clip = VideoFileClip(video_path) # Critical moviepy operation
            if not video_clip.audio:
                self._log_status(f"Error: No audio track found in {video_path}")
                return False # Return False as no audio means failure

            audio_clip = video_clip.audio
            audio_clip.write_audiofile(output_ogg_path, codec='libvorbis') # Critical moviepy operation

            self._log_status(f"Successfully extracted OGG to: {output_ogg_path}")
            return True
        except Exception as e:
            self._log_status(f"Error during OGG extraction: {e}")
            return False
        finally:
            if audio_clip: audio_clip.close()
            if video_clip: video_clip.close()

    def _process_remove_background(self, video_path, output_dir):
        self._log_status(f"Starting 'Remove Background' for: {video_path}")
        cap = None
        out = None
        try:
            video_filename_no_ext = os.path.splitext(os.path.basename(video_path))[0]
            output_video_path = os.path.join(output_dir, f"{video_filename_no_ext}_no_bg.mp4")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self._log_status(f"Error: Could not open video file {video_path} with OpenCV.")
                return False

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # fallback

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = remove(frame_rgb)
                # rembg returns RGBA, convert to BGR for saving
                if result.shape[2] == 4:
                    result_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGBA2BGR)
                else:
                    result_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
                out.write(result_bgr)

                frame_count += 1
                if frame_count % int(fps) == 0:
                    self._log_status(f"Processed {frame_count} frames...")

            self._log_status(f"Successfully removed background and saved to: {output_video_path}")
            return True
        except Exception as e:
            self._log_status(f"Error during background removal: {e}")
            return False
        finally:
            if cap: cap.release()
            if out: out.release()
            cv2.destroyAllWindows()
        self._log_status(f"Starting 'Split MP4' for: {video_path}")
        main_video_clip = None
        subclip = None # Initialize for finally block

        try:
            parsed_split_points = []
            time_pairs = split_points_str.split(',')
            for i, pair_str in enumerate(time_pairs):
                pair_str = pair_str.strip()
                if not pair_str: continue
                start_str, end_str = pair_str.split('-')
                start_sec = self._parse_time(start_str.strip()) # _parse_time can raise ValueError
                end_sec = self._parse_time(end_str.strip())   # _parse_time can raise ValueError
                if start_sec >= end_sec:
                    self._log_status(f"Warning: Invalid range {pair_str} (start >= end), skipping segment {i+1}.")
                    continue
                parsed_split_points.append((start_sec, end_sec))

            if not parsed_split_points:
                self._log_status("Error: No valid split points found after parsing. Check format and values.")
                return False
            self._log_status(f"Parsed split points (seconds): {parsed_split_points}")

            segments_to_save_indices = []
            if segments_to_save_str.strip():
                try:
                    segments_to_save_indices = [int(s.strip()) -1 for s in segments_to_save_str.split(',') if s.strip()]
                    self._log_status(f"Will save specific segments (0-indexed): {segments_to_save_indices}")
                except ValueError:
                    self._log_status("Error: Invalid format for 'Segments to Save'. Use comma-separated numbers (e.g., 1,3).")
                    return False
            else:
                self._log_status("No specific segments selected, will attempt to save all parsed segments.")

            video_filename_no_ext = os.path.splitext(os.path.basename(video_path))[0]
            all_segments_successful = True

            main_video_clip = VideoFileClip(video_path) # Critical moviepy operation
            duration = main_video_clip.duration

            for i, (start_sec, end_sec) in enumerate(parsed_split_points):
                subclip = None # Reset for each segment
                if start_sec >= duration:
                    self._log_status(f"Warning: Start time {start_sec}s for segment {i+1} is beyond video duration ({duration}s). Skipping.")
                    continue
                end_sec = min(end_sec, duration)

                if not segments_to_save_indices or i in segments_to_save_indices:
                    self._log_status(f"Processing segment {i+1}: {start_sec}s - {end_sec}s")
                    output_filename = os.path.join(output_dir, f"{video_filename_no_ext}_part{i+1}.mp4")
                    try:
                        subclip = main_video_clip.subclip(start_sec, end_sec) # Critical moviepy operation
                        subclip.write_videofile(output_filename, codec="libx264", audio_codec="aac", logger=None) # Critical moviepy operation
                        self._log_status(f"Saved segment {i+1} to {output_filename}")
                    except Exception as e_subclip:
                        self._log_status(f"Error processing or writing subclip for segment {i+1} ({start_sec}s-{end_sec}s): {e_subclip}")
                        all_segments_successful = False
                    finally:
                        if subclip: subclip.close()
                else:
                    self._log_status(f"Skipping segment {i+1} as it's not in the list of segments to save.")

            if all_segments_successful:
                 self._log_status("Finished splitting MP4 successfully for all selected/valid segments.")
            else:
                 self._log_status("Finished splitting MP4 with some errors for one or more segments.")
            return all_segments_successful
        except ValueError as ve: # Catch errors from _parse_time or int conversion for segments_to_save
            self._log_status(f"Error parsing input values for splitting: {ve}")
            return False
        except Exception as e: # Catch other general errors (e.g., VideoFileClip loading)
            self._log_status(f"An error occurred during splitting setup or main video loading: {e}")
            return False
        finally:
            if main_video_clip: main_video_clip.close()
            # subclip is closed within the loop's finally


    def _start_processing(self):
        self.process_button.config(state=tk.DISABLED)

        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete("1.0", tk.END)
        self.status_text.config(state=tk.DISABLED)

        self._log_status("--- Starting processing ---")

        try:
            input_val = self.input_path_var.get()
            output_dir = self.output_path_var.get()
            mode = self.processing_mode_var.get()

            if not input_val:
                self._log_status("Error: Input path must be selected.")
                return
            if not os.path.exists(input_val):
                self._log_status(f"Error: Input path does not exist: {input_val}")
                return

            if not output_dir:
                self._log_status("Error: Output directory must be selected.")
                return
            if not os.path.isdir(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self._log_status(f"Created output directory: {output_dir}")
                except Exception as e:
                    self._log_status(f"Error: Could not create output directory {output_dir}: {e}")
                    return

            if mode == "Convert to Frames":
                fps_str = self.fps_var.get()
                try:
                    fps_int = int(fps_str)
                    if fps_int <= 0:
                        self._log_status("Error: FPS must be a positive number.")
                        return
                except ValueError:
                    self._log_status("Error: Invalid FPS value. Must be a number.")
                    return
            elif mode == "Split MP4":
                split_points_str = self.split_points_text.get("1.0", tk.END).strip()
                if not split_points_str:
                    self._log_status("Error: Split points cannot be empty for Split MP4 mode.")
                    return

            self._log_status(f"Mode selected: {mode}")

            files_to_process = []
            if self.input_type_var.get() == "file":
                files_to_process.append(input_val)
            else:
                if os.path.isdir(input_val):
                    for item in os.listdir(input_val):
                        if item.lower().endswith(".mp4"):
                            files_to_process.append(os.path.join(input_val, item))
                    if not files_to_process:
                        self._log_status(f"No MP4 files found in folder: {input_val}")
                        return
                else: # Should have been caught by os.path.exists, but as a safeguard
                    self._log_status(f"Error: Input folder not found: {input_val}")
                    return

            if not files_to_process: # Should be redundant if folder checks are done right
                self._log_status("Error: No files to process.")
                return

            all_files_processed_successfully = True
            for video_path in files_to_process:
                self._log_status(f"--- Processing file: {video_path} ---")
                current_file_success = False
                if mode == "Convert to Frames":
                    remove_bg = self.remove_bg_var.get()
                    current_file_success = self._process_to_frames(video_path, output_dir, self.fps_var.get(), remove_bg)
                elif mode == "Extract to MP3":
                    current_file_success = self._process_to_mp3(video_path, output_dir)
                elif mode == "Extract to OGG":
                    current_file_success = self._process_to_ogg(video_path, output_dir)
                elif mode == "Remove Background":
                    current_file_success = self._process_remove_background(video_path, output_dir)
                else:
                    self._log_status(f"Error: Unknown processing mode: {mode}")
                    current_file_success = False

                if not current_file_success:
                    all_files_processed_successfully = False
                    self._log_status(f"Failed to process {video_path} in {mode} mode.")
                else:
                    self._log_status(f"Successfully processed {video_path} in {mode} mode.")

            if all_files_processed_successfully:
                self._log_status("--- All processing finished successfully. ---")
            else:
                self._log_status("--- Processing finished with one or more errors. Please check logs. ---")

        except Exception as e: # Catch any unexpected errors in _start_processing itself
            self._log_status(f"Critical error in processing orchestrator: {e}")
        finally:
            self.process_button.config(state=tk.NORMAL)


    def create_ui(self):
        content_frame = self.get_frame()

        # --- Input Selection Frame ---
        input_frame = ttk.LabelFrame(content_frame, text="Input Selection", padding=(10, 5))
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        input_type_rb_frame = ttk.Frame(input_frame)
        input_type_rb_frame.pack(fill=tk.X)
        ttk.Radiobutton(input_type_rb_frame, text="Single File", variable=self.input_type_var, value="file").pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Radiobutton(input_type_rb_frame, text="Folder", variable=self.input_type_var, value="folder").pack(side=tk.LEFT, padx=5, pady=2)
        input_path_frame = ttk.Frame(input_frame)
        input_path_frame.pack(fill=tk.X, pady=(5,0))
        browse_input_btn = ttk.Button(input_path_frame, text="Browse Input", command=self._browse_input)
        browse_input_btn.pack(side=tk.LEFT, padx=5)
        self.input_path_label = ttk.Label(input_path_frame, text="No input selected", anchor=tk.W, relief=tk.SUNKEN, padding=(2,2))
        self.input_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # --- Output Location Frame ---
        output_frame = ttk.LabelFrame(content_frame, text="Output Location", padding=(10, 5))
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        output_path_browse_frame = ttk.Frame(output_frame)
        output_path_browse_frame.pack(fill=tk.X)
        browse_output_btn = ttk.Button(output_path_browse_frame, text="Browse Output", command=self._browse_output)
        browse_output_btn.pack(side=tk.LEFT, padx=5)
        self.output_path_label = ttk.Label(output_path_browse_frame, text="No output location selected", anchor=tk.W, relief=tk.SUNKEN, padding=(2,2))
        self.output_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # --- Processing Options Frame ---
        options_frame = ttk.LabelFrame(content_frame, text="Processing Options", padding=(10, 5))
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        processing_mode_label = ttk.Label(options_frame, text="Mode:")
        processing_mode_label.pack(side=tk.LEFT, padx=(0,5), pady=5)
        processing_options = ["Convert to Frames", "Extract to MP3", "Extract to OGG", "Split MP4", "Remove Background"]
        self.processing_mode_combobox = ttk.Combobox(options_frame, textvariable=self.processing_mode_var, values=processing_options, state="readonly")
        self.processing_mode_combobox.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.processing_mode_combobox.current(0)
        self.processing_mode_combobox.bind("<<ComboboxSelected>>", self._on_processing_mode_changed)

        # --- Dynamic Options Frame ---
        self.dynamic_options_frame = ttk.Frame(content_frame, padding=(5,5))
        self.dynamic_options_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        # --- Specific Controls for "Convert to Frames" ---
        self.frames_options_frame = ttk.Frame(self.dynamic_options_frame)
        fps_label = ttk.Label(self.frames_options_frame, text="Target FPS:")
        fps_label.pack(side=tk.LEFT, padx=(0,5))
        self.fps_entry = ttk.Entry(self.frames_options_frame, textvariable=self.fps_var, width=5)
        self.fps_entry.pack(side=tk.LEFT)

        self.remove_bg_var = tk.BooleanVar()
        self.check_remove_bg = ttk.Checkbutton(self.frames_options_frame, text="去背", variable=self.remove_bg_var)
        self.check_remove_bg.pack(side=tk.LEFT, padx=5)

        # --- Specific Controls for "Split MP4" ---
        self.split_options_frame = ttk.Frame(self.dynamic_options_frame)
        split_points_label_frame = ttk.Frame(self.split_options_frame)
        split_points_label_frame.pack(fill=tk.X, pady=(0,2))
        split_points_label = ttk.Label(split_points_label_frame, text="Split Points (e.g., 00:00:10-00:00:20, 00:00:30-00:00:45):")
        split_points_label.pack(side=tk.LEFT)
        self.split_points_text = tk.Text(self.split_options_frame, height=3, relief=tk.SUNKEN, borderwidth=1)
        self.split_points_text.pack(fill=tk.X, pady=(0,5))
        segments_to_save_frame = ttk.Frame(self.split_options_frame)
        segments_to_save_frame.pack(fill=tk.X)
        segments_label = ttk.Label(segments_to_save_frame, text="Segments to Save (e.g., 1,3 or blank for all):")
        segments_label.pack(side=tk.LEFT, padx=(0,5))
        self.segments_to_save_entry = ttk.Entry(segments_to_save_frame, textvariable=self.segments_to_save_var)
        self.segments_to_save_entry.pack(fill=tk.X, expand=True)

        # --- Process Button ---
        self.process_button = ttk.Button(content_frame, text="Start Processing", command=self._start_processing)
        self.process_button.pack(pady=10)

        # --- Status Display ---
        status_label_frame = ttk.Frame(content_frame)
        status_label_frame.pack(fill=tk.X, padx=5, pady=(5,0))
        status_label = ttk.Label(status_label_frame, text="Status:")
        status_label.pack(anchor=tk.W)
        self.status_text = tk.Text(content_frame, height=5, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

        self._on_processing_mode_changed()
        self.shared_state.log(f"MP4Processor UI fully created for module: {self.module_name}", "INFO")
