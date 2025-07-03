import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os

# Assuming main.py (and thus the Module class definition) is in the parent directory
# Adjust the import path if your project structure is different.
try:
    from main import Module
    from shared_state import SharedState # If used by Module or needed directly
except ImportError:
    # Fallback for cases where main.py might be in a different relative path
    # This might happen if image_editor.py is run directly for testing (though not typical for modules)
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from main import Module
    from shared_state import SharedState


class ImageEditorModule(Module):
    def __init__(self, master, shared_state: SharedState, module_name="ImageEditor", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"ImageEditorModule '{module_name}' initialized.")

        # TODO: Initialize image variables, drawing tools, states, etc.
        self.image_path = None
        self.original_image = None # Stores the pristine loaded image
        self.displayed_image_tk = None # For Tkinter canvas
        self.current_image_pil = None # PIL image currently being worked on (after rotations, crops, etc.)

        self.edit_mode_active = False
        self.crop_mode_active = False

        self.drawing_tools_frame = None # For drawing tool buttons
        # UI Elements that need to be accessed later
        self.canvas = None
        self.crop_rect_id = None # Canvas ID for the crop rectangle
        self.crop_start_coords = None # For drawing crop rectangle
        self.open_button = None
        self.edit_button = None
        self.rotate_button = None
        self.crop_button = None
        self.save_button = None
        self.cancel_button = None
        self.status_bar_label = None

        # Drawing related
        self.draw_start_coords = None # For storing (x,y) of mouse press on canvas
        self.current_drawing_tool = "line"
        self.drawing_color = "red"
        self.drawn_items = [] # List to store drawn shapes/text objects (deferred for full object model)
        self.active_drawing_item_id = None # Canvas ID for temporary shape preview
        self.image_draw_layer = None # PIL ImageDraw object for drawing on edit_buffer_image
        self.edit_buffer_image = None # PIL image copy for drawing during an edit session

        # Zoom/Pan related
        self.zoom_factor = 1.0
        self.pan_start_x = None
        self.pan_start_y = None
        self.canvas_image_x = 0 # Top-left x of image on canvas
        self.pan_view_start_x = 0 # Original canvas_image_x at pan start
        self.pan_view_start_y = 0 # Original canvas_image_y at pan start
        self.canvas_image_y = 0 # Top-left y of image on canvas


        self.create_ui()
        self.update_button_states() # Initial state of buttons

    def create_ui(self):
        self.shared_state.log("ImageEditorModule: Creating UI...")
        # The main frame for this module is self.frame (from Module base class)

        # Top bar for main controls
        top_controls_frame = ttk.Frame(self.frame)
        top_controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.open_button = ttk.Button(top_controls_frame, text="開啟圖片", command=self.open_image_action)
        self.open_button.pack(side=tk.LEFT, padx=2)

        self.edit_button = ttk.Button(top_controls_frame, text="🔧 編輯模式", command=self.toggle_edit_mode_action)
        self.edit_button.pack(side=tk.LEFT, padx=2)

        self.rotate_button = ttk.Button(top_controls_frame, text="🔁 旋轉", command=self.rotate_action)
        self.rotate_button.pack(side=tk.LEFT, padx=2)

        self.crop_button = ttk.Button(top_controls_frame, text="✂️ 裁剪", command=self.toggle_crop_mode_action)
        self.crop_button.pack(side=tk.LEFT, padx=2)

        self.save_button = ttk.Button(top_controls_frame, text="💾 儲存", command=self.save_action)
        self.save_button.pack(side=tk.LEFT, padx=2)

        self.cancel_button = ttk.Button(top_controls_frame, text="❌ 取消", command=self.cancel_action)
        self.cancel_button.pack(side=tk.LEFT, padx=2)

        # Drawing tools frame (initially hidden)
        self.drawing_tools_frame = ttk.Frame(self.frame)
        # Packed/unpacked in toggle_edit_mode_action, not here directly

        ttk.Button(self.drawing_tools_frame, text="Line", command=lambda: self._set_drawing_tool("line")).pack(side=tk.LEFT)
        ttk.Button(self.drawing_tools_frame, text="Rect", command=lambda: self._set_drawing_tool("rectangle")).pack(side=tk.LEFT)
        ttk.Button(self.drawing_tools_frame, text="Oval", command=lambda: self._set_drawing_tool("oval")).pack(side=tk.LEFT)
        # ttk.Button(self.drawing_tools_frame, text="Text", command=lambda: self._set_drawing_tool("text")).pack(side=tk.LEFT) # Text later
        self.color_button_preview = tk.Frame(self.drawing_tools_frame, width=20, height=20, bg=self.drawing_color, relief=tk.SUNKEN, borderwidth=1)
        self.color_button_preview.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.drawing_tools_frame, text="Color", command=self._choose_drawing_color).pack(side=tk.LEFT)


        # Edit mode specific controls (e.g., line width, font selector) could go here too
        # For now, keeping it simple with tool type and color.

        # Canvas for image display
        # Ensure drawing_tools_frame is packed *before* the canvas if it's supposed to be on top of it or in sequence
        # If it's a separate bar, its pack order relative to top_controls_frame and canvas matters.
        # Let's pack it after top_controls and before canvas.
        # Canvas for image display
        self.canvas = tk.Canvas(self.frame, bg="lightgrey", relief="sunken", borderwidth=1)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status bar
        self.status_bar_label = ttk.Label(self.frame, text="請先載入圖片", anchor=tk.W)
        self.status_bar_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0,5))

        self.shared_state.log("ImageEditorModule: UI creation mostly complete.")
        # Bind zoom and pan events later, only when an image is loaded

    def update_button_states(self):
        self.shared_state.log("ImageEditorModule: Updating button states...")
        if self.current_image_pil is None: # No image loaded
            self.open_button.config(state=tk.NORMAL)
            self.edit_button.config(state=tk.DISABLED)
            self.rotate_button.config(state=tk.DISABLED)
            self.crop_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            self.set_status("請先載入圖片")
        else: # Image is loaded
            self.open_button.config(state=tk.NORMAL) # Or some other logic like "Open Another"

            if self.edit_mode_active:
                self.edit_button.config(text="💾 儲存繪圖", state=tk.NORMAL) # Becomes "Save Drawing"
                self.rotate_button.config(state=tk.DISABLED)
                self.crop_button.config(state=tk.DISABLED)
                self.save_button.config(state=tk.DISABLED) # Main save disabled
                self.cancel_button.config(text="❌ 取消繪圖", state=tk.NORMAL) # Becomes "Cancel Drawing"
                self.set_status("繪圖/打字模式中")
            elif self.crop_mode_active:
                self.edit_button.config(state=tk.DISABLED)
                self.rotate_button.config(state=tk.DISABLED)
                self.crop_button.config(text="✅ 確認裁剪", state=tk.NORMAL) # Becomes "Confirm Crop"
                self.save_button.config(state=tk.DISABLED) # Main save disabled
                self.cancel_button.config(text="❌ 取消裁剪", state=tk.NORMAL) # Becomes "Cancel Crop"
                self.set_status("裁剪模式中")
            else: # Normal state with image loaded
                self.edit_button.config(text="🔧 編輯模式", state=tk.NORMAL)
                self.rotate_button.config(state=tk.NORMAL)
                self.crop_button.config(text="✂️ 裁剪", state=tk.NORMAL)
                self.save_button.config(state=tk.NORMAL)
                self.cancel_button.config(text="❌ 取消", state=tk.NORMAL) # General cancel/undo
                self.set_status("圖片已載入")
        self.shared_state.log("ImageEditorModule: Button states updated.")

    def set_status(self, message):
        if self.status_bar_label:
            self.status_bar_label.config(text=message)
            self.shared_state.log(f"Status bar: {message}", level="DEBUG")

    def open_image_action(self):
        self.shared_state.log("ImageEditorModule: 'Open Image' action triggered.")
        file_types = [
            ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp"),
            ("All files", "*.*")
        ]
        path = filedialog.askopenfilename(parent=self.frame, title="Select an image", filetypes=file_types)
        if not path:
            self.shared_state.log("ImageEditorModule: No image selected.", "DEBUG")
            return

        try:
            self.image_path = path
            pil_image = Image.open(self.image_path)
            pil_image = pil_image.convert("RGBA") # Ensure RGBA for consistency
            self.original_image = pil_image.copy()
            self.current_image_pil = pil_image.copy()

            # Reset states for the new image
            self.drawn_items = []
            self.zoom_factor = 1.0
            self.canvas_image_x = 0 # Reset pan position
            self.canvas_image_y = 0
            self.pan_start_x = None # Ensure pan state is reset
            self.pan_start_y = None

            self._display_image_on_canvas()
            self.update_button_states()
            self.set_status(f"Image loaded: {os.path.basename(self.image_path)}")

            # Bind zoom and pan events only after an image is successfully loaded
            self.canvas.bind("<MouseWheel>", self._on_mouse_wheel) # For Windows/macOS
            self.canvas.bind("<Button-4>", self._on_mouse_wheel) # For Linux (scroll up)
            self.canvas.bind("<Button-5>", self._on_mouse_wheel) # For Linux (scroll down)

            self.canvas.bind("<Shift-ButtonPress-1>", self._on_pan_start)
            self.canvas.bind("<Shift-B1-Motion>", self._on_pan_motion)
            self.canvas.bind("<Shift-ButtonRelease-1>", self._on_pan_end)

        except Exception as e:
            self.shared_state.log(f"ImageEditorModule: Error opening image '{path}': {e}", "ERROR")
            messagebox.showerror("Error Opening Image", f"Could not open image file: {e}", parent=self.frame)
            self.current_image_pil = None
            self.original_image = None
            self.image_path = None
            self.canvas.delete("all")
            self.update_button_states()

    def _unbind_zoom_pan(self):
        self.canvas.unbind("<MouseWheel>")
        self.canvas.unbind("<Button-4>")
        self.canvas.unbind("<Button-5>")
        self.canvas.unbind("<Shift-ButtonPress-1>")
        self.canvas.unbind("<Shift-B1-Motion>")
        self.canvas.unbind("<Shift-ButtonRelease-1>")

    def toggle_edit_mode_action(self):
        self.shared_state.log(f"ImageEditorModule: 'Toggle Edit Mode' action triggered. Current edit_mode_active: {self.edit_mode_active}")
        if self.edit_mode_active: # Was in edit mode, now saving/exiting
            self.edit_mode_active = False
            if self.edit_buffer_image:
                self.current_image_pil = self.edit_buffer_image.copy() # Bake drawing
                self.shared_state.log("Drawings baked into current_image_pil.")
            self.edit_buffer_image = None
            self.image_draw_layer = None

            self.drawing_tools_frame.pack_forget()
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            # Re-bind pan if it was unbound
            self.canvas.bind("<Shift-ButtonPress-1>", self._on_pan_start)
            self.canvas.bind("<Shift-B1-Motion>", self._on_pan_motion)
            self.canvas.bind("<Shift-ButtonRelease-1>", self._on_pan_end)

            self._display_image_on_canvas() # Show the baked image
            self.set_status("繪圖儲存完畢")
        else: # Entering edit mode
            if self.current_image_pil is None:
                messagebox.showwarning("無圖片", "請先載入圖片才能進入編輯模式。", parent=self.frame)
                return
            self.edit_mode_active = True
            self.edit_buffer_image = self.current_image_pil.copy()
            self.image_draw_layer = ImageDraw.Draw(self.edit_buffer_image) # Draw on the buffer

            self.drawing_tools_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0,5), before=self.canvas) # Show tools
            # Unbind pan to avoid conflict, or make drawing take precedence.
            self.canvas.unbind("<Shift-ButtonPress-1>")
            self.canvas.unbind("<Shift-B1-Motion>")
            self.canvas.unbind("<Shift-ButtonRelease-1>")
            self.canvas.bind("<ButtonPress-1>", self._edit_on_press)
            self.canvas.bind("<B1-Motion>", self._edit_on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._edit_on_release)
            self.set_status("繪圖模式中，選擇工具開始繪圖")
        self.update_button_states()

    def rotate_action(self):
        if not self.current_image_pil:
            messagebox.showwarning("無圖片", "請先載入圖片才能旋轉。", parent=self.frame)
            return

        self.shared_state.log("ImageEditorModule: 'Rotate' action triggered.")

        # Simple dialog for choosing rotation
        dialog = tk.Toplevel(self.frame)
        dialog.title("選擇旋轉角度")
        dialog.geometry("250x200") # Increased height for buttons
        dialog.resizable(False, False)
        dialog.grab_set() # Make it modal

        ttk.Label(dialog, text="請選擇或輸入旋轉角度:").pack(pady=10)

        # angle_var = tk.StringVar() # Not directly used with this button approach

        def apply_rotation(angle_degrees):
            # Check if dialog is still alive, could be destroyed if custom dialog was cancelled.
            if not dialog.winfo_exists() and not isinstance(angle_degrees, float): # Custom dialog was closed, angle not yet set
                 # If angle_degrees is None from simpledialog cancel, it will be handled below
                 pass
            elif dialog.winfo_exists(): # Only destroy if not custom simpledialog path
                dialog.destroy()

            if angle_degrees is None: # User cancelled custom input or closed main dialog prematurely
                self.shared_state.log("Rotation cancelled or angle not provided.", "DEBUG")
                self.set_status("旋轉已取消")
                return
            try:
                angle = float(angle_degrees)
                # PIL rotates counter-clockwise.
                self.current_image_pil = self.current_image_pil.rotate(angle, expand=True, fillcolor=(0,0,0,0))
                # Reset zoom and pan after rotation for simplicity, as dimensions change
                self.zoom_factor = 1.0
                self.canvas_image_x = 0
                self.canvas_image_y = 0
                self._display_image_on_canvas()
                self.set_status(f"圖片已旋轉 {angle}°")
                self.shared_state.log(f"Image rotated by {angle} degrees.")
            except ValueError:
                messagebox.showerror("無效角度", "請輸入有效的數字角度。", parent=self.frame)
                self.set_status("無效的旋轉角度")
            except Exception as e:
                messagebox.showerror("旋轉錯誤", f"旋轉圖片時發生錯誤: {e}", parent=self.frame)
                self.shared_state.log(f"Error during rotation: {e}", "ERROR")
                self.set_status("旋轉時發生錯誤")
            finally:
                # Ensure main dialog is closed if an error occurred after simpledialog
                if dialog.winfo_exists():
                    dialog.destroy()


        ttk.Button(dialog, text="90° (順時針)", command=lambda: apply_rotation(-90.0)).pack(fill=tk.X, padx=20, pady=2)
        ttk.Button(dialog, text="180°", command=lambda: apply_rotation(180.0)).pack(fill=tk.X, padx=20, pady=2)
        ttk.Button(dialog, text="90° (逆時針)", command=lambda: apply_rotation(90.0)).pack(fill=tk.X, padx=20, pady=2)

        custom_frame = ttk.Frame(dialog)
        custom_frame.pack(fill=tk.X, padx=15, pady=5, side=tk.BOTTOM, anchor=tk.S) # Ensure it's at bottom

        def ask_custom_angle():
            # Dialog is parent here, so simpledialog will be on top of it.
            custom_angle = simpledialog.askfloat("自訂角度", "輸入角度 (逆時針為正):", parent=dialog, minvalue=-360.0, maxvalue=360.0)
            # apply_rotation will handle None if cancelled
            apply_rotation(custom_angle)

        ttk.Button(custom_frame, text="自訂角度...", command=ask_custom_angle).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(custom_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, expand=True, padx=5)


    def toggle_crop_mode_action(self):
        self.shared_state.log(f"ImageEditorModule: 'Toggle Crop Mode' action triggered. Current crop_mode_active: {self.crop_mode_active}")
        if self.crop_mode_active:
            # --- 直接執行裁剪 ---
            if not self.crop_rect_id:
                messagebox.showwarning("未選擇區域", "請先在圖片上拖曳選擇裁剪區域，再按確認裁剪。", parent=self.frame)
                self.set_status("請先選擇裁剪區域")
                return
            if self.current_image_pil:
                try:
                    c_coords = self.canvas.coords(self.crop_rect_id)
                    if len(c_coords) != 4:
                        messagebox.showwarning("裁剪區域錯誤", "裁剪區域座標無效，請重新選擇。", parent=self.frame)
                        self.set_status("裁剪區域座標無效")
                        return
                    # Ensure correct order: left_can = min(x1_can, x2_can), etc.
                    left_can, top_can, right_can, bottom_can = min(c_coords[0], c_coords[2]), min(c_coords[1], c_coords[3]), max(c_coords[0], c_coords[2]), max(c_coords[1], c_coords[3])
                    self.shared_state.log(f"[CropDebug] Ordered canvas coords: L:{left_can}, T:{top_can}, R:{right_can}, B:{bottom_can}", "DEBUG")
                    self.shared_state.log(f"[CropDebug] View state: canvas_image_x:{self.canvas_image_x}, canvas_image_y:{self.canvas_image_y}, zoom_factor:{self.zoom_factor}", "DEBUG")

                    img_left = (left_can - self.canvas_image_x) / self.zoom_factor
                    img_top = (top_can - self.canvas_image_y) / self.zoom_factor
                    img_right = (right_can - self.canvas_image_x) / self.zoom_factor
                    img_bottom = (bottom_can - self.canvas_image_y) / self.zoom_factor
                    self.shared_state.log(f"[CropDebug] Calculated img coords (before clamp): L:{img_left}, T:{img_top}, R:{img_right}, B:{img_bottom}", "DEBUG")

                    # Clamp to image boundaries
                    img_w, img_h = self.current_image_pil.size
                    self.shared_state.log(f"[CropDebug] Original image_pil size: W:{img_w}, H:{img_h}", "DEBUG")

                    img_left = max(0, img_left)
                    img_top = max(0, img_top)
                    img_right = min(img_w, img_right)
                    img_bottom = min(img_h, img_bottom)
                    self.shared_state.log(f"[CropDebug] Clamped img coords: L:{img_left}, T:{img_top}, R:{img_right}, B:{img_bottom}", "DEBUG")

                    is_valid_crop_area = img_left < img_right and img_top < img_bottom
                    self.shared_state.log(f"[CropDebug] Is valid crop area (L<R and T<B): {is_valid_crop_area}", "DEBUG")

                    if is_valid_crop_area:
                        crop_box = (int(img_left), int(img_top), int(img_right), int(img_bottom))
                        self.shared_state.log(f"[CropDebug] Integer crop_box for Pillow: {crop_box}", "DEBUG")

                        # Additional check after int conversion for zero-dimension images
                        if crop_box[0] < crop_box[2] and crop_box[1] < crop_box[3]:
                            self.current_image_pil = self.current_image_pil.crop(crop_box)
                            # 更新原始圖片（可選，讓取消時能回復到裁剪前）
                            self.original_image = self.current_image_pil.copy()
                            self.zoom_factor = 1.0
                            self.canvas_image_x = 0
                            self.canvas_image_y = 0
                            self.set_status("圖片裁剪成功")
                        else:
                            messagebox.showwarning("裁剪區域無效", "選擇的裁剪區域經轉換後寬度或高度為零。", parent=self.frame)
                            self.set_status("裁剪失敗：選擇區域尺寸為零")
                    else:
                        messagebox.showwarning("裁剪區域無效", "選擇的裁剪區域太小或無效。", parent=self.frame)
                        self.set_status("裁剪失敗：選擇區域無效")
                except Exception as e:
                    messagebox.showerror("裁剪錯誤", f"裁剪圖片時發生錯誤: {e}", parent=self.frame)
                    self.set_status("裁剪時發生錯誤")
            self.crop_mode_active = False
            if self.crop_rect_id:
                self.canvas.delete(self.crop_rect_id)
                self.crop_rect_id = None
            self.crop_start_coords = None
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            self._bind_pan_events()
            self._display_image_on_canvas()
        else:
            if not self.current_image_pil:
                messagebox.showwarning("無圖片", "請先載入圖片才能進行裁剪。", parent=self.frame)
                return
            self.crop_mode_active = True
            self._unbind_pan_events()
            self.canvas.bind("<ButtonPress-1>", self._crop_on_press)
            self.canvas.bind("<B1-Motion>", self._crop_on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._crop_on_release)
            self.set_status("請在圖片上拖曳以選擇裁剪區域")
        self.update_button_states()

    def save_action(self):
        if not self.current_image_pil:
            messagebox.showwarning("無可儲存圖片", "目前沒有圖片可供儲存。", parent=self.frame)
            return

        self.shared_state.log("ImageEditorModule: 'Save' action triggered.")

        default_filename = "untitled.png"
        if self.image_path:
            base, ext = os.path.splitext(os.path.basename(self.image_path))
            default_filename = f"{base}_edited.png" # Suggest a new name

        file_types = [
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg;*.jpeg"),
            ("BMP files", "*.bmp"),
            ("All files", "*.*")
        ]

        filepath = filedialog.asksaveasfilename(
            parent=self.frame,
            title="儲存圖片為",
            initialfile=default_filename,
            defaultextension=".png",
            filetypes=file_types
        )

        if not filepath:
            self.shared_state.log("Save action cancelled by user.", "DEBUG")
            return

        try:
            image_to_save = self.current_image_pil
            file_ext = os.path.splitext(filepath)[1].lower()

            if file_ext in ['.jpg', '.jpeg'] and image_to_save.mode == 'RGBA':
                self.shared_state.log("Converting RGBA image to RGB for JPEG save.", "DEBUG")
                # JPEG doesn't support alpha, so convert to RGB
                # Create a white background image
                background = Image.new("RGB", image_to_save.size, (255, 255, 255))
                background.paste(image_to_save, mask=image_to_save.split()[3]) # Paste using alpha channel as mask
                image_to_save = background
            elif file_ext == '.bmp' and image_to_save.mode == 'RGBA':
                 # BMP typically doesn't handle RGBA well in all viewers, convert to RGB
                self.shared_state.log("Converting RGBA image to RGB for BMP save.", "DEBUG")
                background = Image.new("RGB", image_to_save.size, (255, 255, 255))
                background.paste(image_to_save, mask=image_to_save.split()[3])
                image_to_save = background

            image_to_save.save(filepath)
            self.set_status(f"圖片已儲存至: {os.path.basename(filepath)}")
            self.shared_state.log(f"Image saved to {filepath}")
            messagebox.showinfo("儲存成功", f"圖片已成功儲存至:\n{filepath}", parent=self.frame)
        except Exception as e:
            self.shared_state.log(f"Error saving image to {filepath}: {e}", "ERROR")
            messagebox.showerror("儲存失敗", f"儲存圖片時發生錯誤: {e}", parent=self.frame)
            self.set_status(f"儲存失敗: {e}")

    def cancel_action(self):
        self.shared_state.log(f"ImageEditorModule: 'Cancel' action triggered. Edit mode: {self.edit_mode_active}, Crop mode: {self.crop_mode_active}")
        # Placeholder
        action_cancelled = False
        if self.edit_mode_active:
            self.edit_mode_active = False
            self.edit_buffer_image = None # Discard buffer
            self.image_draw_layer = None
            if self.active_drawing_item_id: # Clear temporary shape from canvas
                self.canvas.delete(self.active_drawing_item_id)
                self.active_drawing_item_id = None

            self.drawing_tools_frame.pack_forget() # Hide tools
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            self._bind_pan_events() # Re-bind pan

            self.set_status("Drawing cancelled (placeholder).")
            action_cancelled = True
        elif self.crop_mode_active:
            self.crop_mode_active = False
            if self.crop_rect_id:
                self.canvas.delete(self.crop_rect_id)
                self.crop_rect_id = None
            self.crop_start_coords = None
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            self._bind_pan_events() # Re-bind pan
            self.set_status("Cropping cancelled (placeholder).")
            action_cancelled = True # To trigger redraw and remove visual artifacts
        else:
            # TODO: General cancel/undo logic if applicable (e.g., undo last rotation)
            # For now, maybe revert to original image if one exists
            if self.original_image:
                if self.current_image_pil.tobytes() != self.original_image.tobytes():
                    self.current_image_pil = self.original_image.copy()
                    # Baked-in drawings are part of original_image if they were saved before this cancel.
                    # If drawn_items were for a separate object layer, this would be different.
                    # For now, current_image_pil holds everything.
                    self.drawn_items = [] # Reset if we had a separate drawing layer concept

                    self.zoom_factor = 1.0
                    self.canvas_image_x = 0
                    self.canvas_image_y = 0

                    action_cancelled = True
                    self.set_status("變更已還原至原始載入圖片")
                else:
                    self.set_status("目前圖片與原始載入版本相同，無操作取消。")
            else:
                self.set_status("沒有原始圖片可供還原。")

        if action_cancelled:
            self._display_image_on_canvas() # Refresh to show state before cancel
        self.update_button_states()

    def _display_image_on_canvas(self, use_edit_buffer=False): # Added use_edit_buffer
        self.canvas.delete("all") # Clear previous image/drawings/crop_rect

        if self.current_image_pil and self.canvas:
            try:
                # Apply zoom
                zoomed_width = int(self.current_image_pil.width * self.zoom_factor)
                zoomed_height = int(self.current_image_pil.height * self.zoom_factor)
            except (ValueError, OverflowError): # Catches potential errors if zoom_factor is NaN or Inf or too large
                self.shared_state.log(f"Invalid zoom_factor: {self.zoom_factor}. Resetting to 1.0", "WARNING")
                self.zoom_factor = 1.0
                zoomed_width = self.current_image_pil.width
                zoomed_height = self.current_image_pil.height

            image_to_display_pil = self.current_image_pil
            if use_edit_buffer and self.edit_buffer_image:
                image_to_display_pil = self.edit_buffer_image
                # Apply zoom to the buffer for display
                zoomed_width = int(image_to_display_pil.width * self.zoom_factor)
                zoomed_height = int(image_to_display_pil.height * self.zoom_factor)


            if zoomed_width <= 0 or zoomed_height <= 0:
                self.shared_state.log(f"Image dimensions too small after zoom: {zoomed_width}x{zoomed_height}. Current zoom: {self.zoom_factor}. Skipping display.", "WARNING")
                return

            img_for_display = image_to_display_pil.resize((zoomed_width, zoomed_height), Image.LANCZOS)

            self.displayed_image_tk = ImageTk.PhotoImage(img_for_display)

            # Calculate centered position or use pan coordinates
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # If canvas dimensions are not yet known (e.g. during init), use arbitrary non-zero values
            if canvas_width <= 1: canvas_width = 600
            if canvas_height <= 1: canvas_height = 400

            # self.canvas_image_x and self.canvas_image_y are the top-left coords of the image on the canvas
            # When an image is first loaded or zoom changes significantly, we might want to re-center.
            # For simplicity now, (0,0) if not panned, or current pan values.
            # A more robust solution would center if image is smaller than canvas.

            # The self.canvas_image_x/y is the offset of the image's top-left corner
            # relative to the canvas's top-left corner.
            self.canvas.create_image(self.canvas_image_x, self.canvas_image_y, anchor=tk.NW, image=self.displayed_image_tk, tags="image")

            # TODO: Redraw persistent drawings (self.drawn_items) respecting zoom/pan

            log_msg_suffix = " (Edit Buffer)" if use_edit_buffer and self.edit_buffer_image else ""
            self.shared_state.log(f"Image displayed on canvas{log_msg_suffix}. Zoomed Size: {zoomed_width}x{zoomed_height} at ({self.canvas_image_x},{self.canvas_image_y}). Zoom: {self.zoom_factor}", "DEBUG")
        elif self.canvas:
            self.shared_state.log("No image to display or canvas not ready. Cleared canvas.", "DEBUG")

    def _set_drawing_tool(self, tool_name):
        self.current_drawing_tool = tool_name
        self.set_status(f"工具已選擇: {tool_name}")
        self.shared_state.log(f"Drawing tool set to: {self.current_drawing_tool}")

    def _choose_drawing_color(self):
        try:
            color_code = colorchooser.askcolor(title="選擇繪圖顏色", initialcolor=self.drawing_color, parent=self.frame)
            if color_code and color_code[1]:
                self.drawing_color = color_code[1]
                self.color_button_preview.config(bg=self.drawing_color)
                self.shared_state.log(f"Drawing color changed to: {self.drawing_color}")
        except Exception as e:
            self.shared_state.log(f"Error in color chooser: {e}", "ERROR")
            messagebox.showerror("顏色選擇錯誤", f"無法開啟顏色選擇器: {e}", parent=self.frame)

    def _edit_on_press(self, event):
        if not self.edit_mode_active or not self.edit_buffer_image: return
        self.draw_start_coords = (event.x, event.y)
        # self.shared_state.log(f"Draw press at canvas ({event.x},{event.y})")

    def _edit_on_drag(self, event):
        if not self.edit_mode_active or self.draw_start_coords is None or not self.edit_buffer_image: return

        if self.active_drawing_item_id:
            self.canvas.delete(self.active_drawing_item_id)

        x0, y0 = self.draw_start_coords
        x1, y1 = event.x, event.y

        if self.current_drawing_tool == "line":
            self.active_drawing_item_id = self.canvas.create_line(x0, y0, x1, y1, fill=self.drawing_color, width=2)
        elif self.current_drawing_tool == "rectangle":
            self.active_drawing_item_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline=self.drawing_color, width=2)
        elif self.current_drawing_tool == "oval":
            self.active_drawing_item_id = self.canvas.create_oval(x0, y0, x1, y1, outline=self.drawing_color, width=2)
        # self.shared_state.log(f"Draw drag to canvas ({x1},{y1})")

    def _edit_on_release(self, event):
        if not self.edit_mode_active or self.draw_start_coords is None or not self.image_draw_layer: return

        if self.active_drawing_item_id:
            self.canvas.delete(self.active_drawing_item_id)
            self.active_drawing_item_id = None

        # Convert canvas view coordinates to image buffer coordinates
        img_x0 = (self.draw_start_coords[0] - self.canvas_image_x) / self.zoom_factor
        img_y0 = (self.draw_start_coords[1] - self.canvas_image_y) / self.zoom_factor
        img_x1 = (event.x - self.canvas_image_x) / self.zoom_factor
        img_y1 = (event.y - self.canvas_image_y) / self.zoom_factor

        if self.current_drawing_tool == "line":
            self.image_draw_layer.line([(img_x0, img_y0), (img_x1, img_y1)], fill=self.drawing_color, width=int(2 / self.zoom_factor) if self.zoom_factor > 0 else 2)
        elif self.current_drawing_tool == "rectangle":
            self.image_draw_layer.rectangle([(img_x0, img_y0), (img_x1, img_y1)], outline=self.drawing_color, width=int(2 / self.zoom_factor) if self.zoom_factor > 0 else 2)
        elif self.current_drawing_tool == "oval":
            self.image_draw_layer.ellipse([(img_x0, img_y0), (img_x1, img_y1)], outline=self.drawing_color, width=int(2 / self.zoom_factor) if self.zoom_factor > 0 else 2)

        self.draw_start_coords = None
        self._display_image_on_canvas(use_edit_buffer=True) # Refresh canvas with drawings from buffer
        self.shared_state.log(f"Drawn {self.current_drawing_tool} on buffer. Coords (img): ({img_x0},{img_y0}) to ({img_x1},{img_y1})")

    def _crop_on_press(self, event):
        if not self.crop_mode_active: return
        self.crop_start_coords = (event.x, event.y)
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None
        self.shared_state.log(f"Crop press at canvas ({event.x},{event.y})")

    def _crop_on_drag(self, event):
        if not self.crop_mode_active or self.crop_start_coords is None: return
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)

        x0, y0 = self.crop_start_coords
        x1, y1 = event.x, event.y
        # Draw dashed rectangle for crop selection
        self.crop_rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="yellow", dash=(5,3), width=1)

    def _crop_on_release(self, event):
        if not self.crop_mode_active or self.crop_start_coords is None: return
        # Finalize crop rectangle on canvas. Actual crop happens on confirm.
        x0, y0 = self.crop_start_coords
        x1, y1 = event.x, event.y
        if self.crop_rect_id: # Update final coords
             self.canvas.coords(self.crop_rect_id, x0, y0, x1, y1)
        self.shared_state.log(f"Crop selection finalized on canvas at ({x0},{y0}) to ({x1},{y1})")

    def _on_mouse_wheel(self, event):
        if not self.current_image_pil:
            return

        zoom_delta = 0.1
        # 取得滑鼠在canvas上的座標
        mouse_x, mouse_y = event.x, event.y

        # 計算滑鼠在圖片上的相對座標（未縮放前）
        img_x_before = (mouse_x - self.canvas_image_x) / self.zoom_factor
        img_y_before = (mouse_y - self.canvas_image_y) / self.zoom_factor

        # Linux uses event.num (4 for up, 5 for down)
        # Windows/macOS use event.delta (positive for up, negative for down)
        if getattr(event, 'num', None) == 4 or (hasattr(event, 'delta') and event.delta > 0):
            new_zoom = self.zoom_factor * (1 + zoom_delta)
        elif getattr(event, 'num', None) == 5 or (hasattr(event, 'delta') and event.delta < 0):
            new_zoom = self.zoom_factor / (1 + zoom_delta)
        else:
            new_zoom = self.zoom_factor

        # Zoom limits
        new_zoom = max(0.1, min(new_zoom, 5.0))

        # 計算縮放後，讓滑鼠指向的圖片點仍在滑鼠座標下，調整canvas_image_x/y
        self.canvas_image_x = mouse_x - img_x_before * new_zoom
        self.canvas_image_y = mouse_y - img_y_before * new_zoom
        self.zoom_factor = new_zoom

        self.shared_state.log(f"Zoom event. New factor: {self.zoom_factor}", "DEBUG")
        self._display_image_on_canvas()

    def _on_pan_start(self, event):
        if not self.current_image_pil: return
        self.shared_state.log(f"Pan start at ({event.x}, {event.y}). Current image offset: ({self.canvas_image_x}, {self.canvas_image_y})", "DEBUG")
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        # Store the view's state at the beginning of the pan
        self.pan_view_start_x = self.canvas_image_x
        self.pan_view_start_y = self.canvas_image_y
        self.canvas.config(cursor="fleur")

    def _on_pan_motion(self, event):
        if self.pan_start_x is None or self.pan_start_y is None or not self.current_image_pil:
            return

        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y

        # Update image's top-left position on canvas based on original position + delta
        self.canvas_image_x = self.pan_view_start_x + dx
        self.canvas_image_y = self.pan_view_start_y + dy

        self._display_image_on_canvas()

    def _on_pan_end(self, event):
        if not self.current_image_pil: return
        self.shared_state.log("Pan end.", "DEBUG")
        self.pan_start_x = None
        self.pan_start_y = None
        self.canvas.config(cursor="")

    def _bind_pan_events(self):
        self.canvas.bind("<Shift-ButtonPress-1>", self._on_pan_start)
        self.canvas.bind("<Shift-B1-Motion>", self._on_pan_motion)
        self.canvas.bind("<Shift-ButtonRelease-1>", self._on_pan_end)
        self.shared_state.log("Pan events bound.", "DEBUG")

    def _unbind_pan_events(self):
        self.canvas.unbind("<Shift-ButtonPress-1>")
        self.canvas.unbind("<Shift-B1-Motion>")
        self.canvas.unbind("<Shift-ButtonRelease-1>")
        self.shared_state.log("Pan events unbound.", "DEBUG")


    def on_destroy(self):
        # Clean up resources, if any (e.g., close files, stop timers)
        self.shared_state.log(f"ImageEditorModule '{self.module_name}' is being destroyed.")
        super().on_destroy()

# Example of how it might be added to main.py (for testing, not part of the module itself)
if __name__ == '__main__':
    # This block is for direct testing of the module, if needed.
    # It requires main.py and shared_state.py to be in the Python path.
    root = tk.Tk()
    root.geometry("800x600")

    # Mock SharedState and GUIManager for standalone testing if necessary
    class MockGUIManager:
        def hide_module(self, module_name):
            print(f"MockGUIManager: Hide module {module_name}")
        def maximize_module(self, module_name):
            print(f"MockGUIManager: Maximize module {module_name}")
        def restore_modules(self):
            print(f"MockGUIManager: Restore modules")

    mock_shared_state = SharedState(log_level="DEBUG")
    mock_gui_manager = MockGUIManager()

    # The module's frame will be parented to 'root' directly in this test setup
    editor_module = ImageEditorModule(root, mock_shared_state, gui_manager=mock_gui_manager)

    # In the actual application, the module's frame (editor_module.frame) would be
    # managed by the ModularGUI's layout manager.
    # For this test, we pack it directly if it's not already part of the root's layout.
    # The Module base class creates 'self.frame'. We need to make sure it's displayed.

    # To simulate how ModularGUI would handle it, we can pack the module's main frame:
    editor_module.frame.pack(fill=tk.BOTH, expand=True)

    root.title("Image Editor Module Test")
    root.mainloop()
    root.title("Image Editor Module Test")
    root.mainloop()
