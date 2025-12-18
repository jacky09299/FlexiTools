import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import io # Added for BytesIO for reportlab
import logging # Added for consistency with other modules
from PIL import Image # For Image to PDF

# PyPDF2 for PDF manipulation
from PyPDF2 import PdfReader, PdfWriter
# reportlab for creating watermark PDFs
from reportlab.pdfgen import canvas as reportlab_canvas
# from reportlab.lib.pagesizes import letter # Not strictly needed if using dynamic page sizes
from reportlab.lib.colors import Color as ReportlabColor
# from reportlab.lib.units import inch # Not strictly needed for this implementation

# pypdfium2 for PDF to image conversion
try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None
    logging.error("pypdfium2 is not installed. PDF to Image functionality will be disabled.")


# Import the base Module class
# Assuming main.py (and thus the Module class definition) is in the parent directory.
# Adjust the import path if your project structure is different.
try:
    from main import Module
except ImportError:
    # Fallback for cases where main.py might not be directly in the parent
    # This might happen if the module is run standalone or if the path setup is different.
    # A more robust solution might involve sys.path manipulation or a proper package structure.
    logging.warning("Could not import Module from main. Attempting relative import for Module.")
    from ..main import Module


class PdfProcessorModule(Module):
    def __init__(self, master, shared_state, module_name="PDF Processor", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"PDF Processor Module '{self.module_name}' initialized.")
        self.current_input_pdf_path = None
        self.current_output_dir = None # For operations that produce multiple files like split

        # Initialize UI
        self.create_ui()

    def create_ui(self):
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)

        # Create the Notebook (tabbed interface)
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(expand=True, fill=tk.BOTH)

        # Create frames for each tab
        self.tab_split = ttk.Frame(self.notebook)
        self.tab_merge = ttk.Frame(self.notebook)
        self.tab_compress = ttk.Frame(self.notebook)
        # self.tab_rotate = ttk.Frame(self.notebook) # SKIPPED
        self.tab_watermark = ttk.Frame(self.notebook)
        self.tab_extract_text = ttk.Frame(self.notebook)
        self.tab_to_image_pdf = ttk.Frame(self.notebook)
        self.tab_images_to_pdf = ttk.Frame(self.notebook) # New Tab for Images -> PDF


        # Add tabs to the notebook
        self.notebook.add(self.tab_split, text="Split PDF") # Text will be updated in update_language
        self.notebook.add(self.tab_merge, text="Merge PDFs")
        self.notebook.add(self.tab_compress, text="Compress PDF")
        self.notebook.add(self.tab_watermark, text="Add Watermark")
        self.notebook.add(self.tab_extract_text, text="Extract Text")
        self.notebook.add(self.tab_to_image_pdf, text="To Image PDF")
        self.notebook.add(self.tab_images_to_pdf, text="Images to PDF")

        # --- Convert to Image PDF Tab ---
        if pdfium:
            to_image_frame = ttk.Frame(self.tab_to_image_pdf, padding="10")
            to_image_frame.pack(expand=True, fill=tk.BOTH)

            # Input PDF
            self.lbl_to_img_input = ttk.Label(to_image_frame, text="Input PDF:")
            self.lbl_to_img_input.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            self.to_img_input_pdf_path_var = tk.StringVar()
            ttk.Entry(to_image_frame, textvariable=self.to_img_input_pdf_path_var, width=50, state="readonly").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.btn_to_img_browse_in = ttk.Button(to_image_frame, text="Browse...", command=self._select_input_pdf_to_image)
            self.btn_to_img_browse_in.grid(row=0, column=2, padx=5, pady=5)

            # Output PDF
            self.lbl_to_img_output = ttk.Label(to_image_frame, text="Output Image PDF:")
            self.lbl_to_img_output.grid(row=1, column=0, padx=5, pady=5, sticky="w")
            self.to_img_output_pdf_path_var = tk.StringVar()
            ttk.Entry(to_image_frame, textvariable=self.to_img_output_pdf_path_var, width=50, state="readonly").grid(row=1, column=1, padx=5, pady=5, sticky="ew")
            self.btn_to_img_browse_out = ttk.Button(to_image_frame, text="Browse...", command=self._select_output_pdf_to_image)
            self.btn_to_img_browse_out.grid(row=1, column=2, padx=5, pady=5)

            # DPI Setting
            self.lbl_to_img_dpi = ttk.Label(to_image_frame, text="Image Quality (DPI):")
            self.lbl_to_img_dpi.grid(row=2, column=0, padx=5, pady=5, sticky="w")
            self.to_img_dpi_var = tk.StringVar(value="300")
            ttk.Entry(to_image_frame, textvariable=self.to_img_dpi_var, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="w")

            # Execute Button
            self.btn_to_img_execute = ttk.Button(to_image_frame, text="Convert to Image PDF", command=self._execute_convert_to_image_pdf)
            self.btn_to_img_execute.grid(row=3, column=1, padx=5, pady=10)

            # Status Label
            self.to_img_status_var = tk.StringVar()
            ttk.Label(to_image_frame, textvariable=self.to_img_status_var, wraplength=400).grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="w")

            to_image_frame.columnconfigure(1, weight=1)
        else:
            # Display a message if pypdfium2 is not installed
            disabled_label = ttk.Label(self.tab_to_image_pdf, text="This feature is disabled because pypdfium2 is not installed.", style="Error.TLabel")
            disabled_label.pack(padx=20, pady=20)


        # --- Split PDF Tab ---
        # Clear placeholder
        for widget in self.tab_split.winfo_children():
            widget.destroy()

        split_frame = ttk.Frame(self.tab_split, padding="10")
        split_frame.pack(expand=True, fill=tk.BOTH)

        # Input PDF
        self.lbl_split_input = ttk.Label(split_frame, text="Input PDF:")
        self.lbl_split_input.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.split_input_pdf_path_var = tk.StringVar()
        ttk.Entry(split_frame, textvariable=self.split_input_pdf_path_var, width=50, state="readonly").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_split_browse = ttk.Button(split_frame, text="Browse...", command=self._select_input_pdf_split)
        self.btn_split_browse.grid(row=0, column=2, padx=5, pady=5)

        # Page Ranges
        self.lbl_split_ranges = ttk.Label(split_frame, text="Page Ranges (e.g., 1-5, 8, 10-12):")
        self.lbl_split_ranges.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.split_page_ranges_var = tk.StringVar()
        ttk.Entry(split_frame, textvariable=self.split_page_ranges_var, width=50).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Output Folder Selection
        self.lbl_split_out_folder = ttk.Label(split_frame, text="Output Folder:")
        self.lbl_split_out_folder.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.split_output_folder_var = tk.StringVar()
        ttk.Entry(split_frame, textvariable=self.split_output_folder_var, width=50, state="readonly").grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.btn_split_choose_folder = ttk.Button(split_frame, text="Choose Folder...", command=self._select_split_output_folder)
        self.btn_split_choose_folder.grid(row=3, column=2, padx=5, pady=5)

        # Output Naming Pattern
        self.lbl_split_pattern = ttk.Label(split_frame, text="Output Pattern:")
        self.lbl_split_pattern.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.split_output_pattern_var = tk.StringVar(value="{basename}_part{i}.pdf") # Changed default
        ttk.Entry(split_frame, textvariable=self.split_output_pattern_var, width=50).grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        self.lbl_split_placeholders = ttk.Label(split_frame, text="Placeholders: {i}, {filename}, {basename}, {start}, {end}")
        self.lbl_split_placeholders.grid(row=5, column=1, padx=5, pady=2, sticky="w")


        # Split Button
        self.btn_split_execute = ttk.Button(split_frame, text="Split PDF", command=self._execute_split_pdf)
        self.btn_split_execute.grid(row=6, column=1, padx=5, pady=10)

        # Status Label
        self.split_status_var = tk.StringVar()
        ttk.Label(split_frame, textvariable=self.split_status_var, wraplength=400).grid(row=7, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        split_frame.columnconfigure(1, weight=1) # Allow entry fields to expand

        # --- Merge PDFs Tab ---
        for widget in self.tab_merge.winfo_children():
            widget.destroy()

        merge_frame = ttk.Frame(self.tab_merge, padding="10")
        merge_frame.pack(expand=True, fill=tk.BOTH)

        # PDF Listbox and controls
        list_controls_frame = ttk.Frame(merge_frame)
        list_controls_frame.pack(fill=tk.X, pady=5)

        self.btn_merge_add = ttk.Button(list_controls_frame, text="Add PDF(s)...", command=self._add_pdfs_to_merge_list)
        self.btn_merge_add.pack(side=tk.LEFT, padx=2)
        self.btn_merge_remove = ttk.Button(list_controls_frame, text="Remove Selected", command=self._remove_selected_pdf_from_merge_list)
        self.btn_merge_remove.pack(side=tk.LEFT, padx=2)
        self.btn_merge_up = ttk.Button(list_controls_frame, text="Move Up", command=lambda: self._move_merge_list_item(-1))
        self.btn_merge_up.pack(side=tk.LEFT, padx=2)
        self.btn_merge_down = ttk.Button(list_controls_frame, text="Move Down", command=lambda: self._move_merge_list_item(1))
        self.btn_merge_down.pack(side=tk.LEFT, padx=2)

        self.merge_pdf_listbox = tk.Listbox(merge_frame, selectmode=tk.SINGLE, width=70, height=10)
        self.merge_pdf_listbox.pack(pady=5, fill=tk.BOTH, expand=True)
        # Scrollbar for listbox (optional but good)
        merge_list_scrollbar = ttk.Scrollbar(self.merge_pdf_listbox, orient=tk.VERTICAL, command=self.merge_pdf_listbox.yview)
        self.merge_pdf_listbox.config(yscrollcommand=merge_list_scrollbar.set)
        # merge_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y) # This needs to be packed relative to listbox or its frame

        # Output File
        output_frame_merge = ttk.Frame(merge_frame)
        output_frame_merge.pack(fill=tk.X, pady=5)
        self.lbl_merge_out = ttk.Label(output_frame_merge, text="Output Merged PDF:")
        self.lbl_merge_out.pack(side=tk.LEFT, padx=5)
        self.merge_output_pdf_path_var = tk.StringVar()
        ttk.Entry(output_frame_merge, textvariable=self.merge_output_pdf_path_var, width=50, state="readonly").pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.btn_merge_browse = ttk.Button(output_frame_merge, text="Browse...", command=self._select_output_merged_pdf)
        self.btn_merge_browse.pack(side=tk.LEFT, padx=5)

        # Merge Button
        self.btn_merge_execute = ttk.Button(merge_frame, text="Merge PDFs", command=self._execute_merge_pdfs)
        self.btn_merge_execute.pack(pady=10)

        # Status Label
        self.merge_status_var = tk.StringVar()
        ttk.Label(merge_frame, textvariable=self.merge_status_var, wraplength=400).pack(pady=5, fill=tk.X)

        # Initialize internal list for merge files
        self.merge_file_paths = []

        # --- Compress PDF Tab ---
        for widget in self.tab_compress.winfo_children():
            widget.destroy()

        compress_frame = ttk.Frame(self.tab_compress, padding="10")
        compress_frame.pack(expand=True, fill=tk.BOTH)

        # Input PDF
        self.lbl_comp_input = ttk.Label(compress_frame, text="Input PDF:")
        self.lbl_comp_input.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.compress_input_pdf_path_var = tk.StringVar()
        ttk.Entry(compress_frame, textvariable=self.compress_input_pdf_path_var, width=50, state="readonly").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_comp_browse_in = ttk.Button(compress_frame, text="Browse...", command=self._select_input_pdf_compress)
        self.btn_comp_browse_in.grid(row=0, column=2, padx=5, pady=5)

        # Output PDF
        self.lbl_comp_output = ttk.Label(compress_frame, text="Output Compressed PDF:")
        self.lbl_comp_output.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.compress_output_pdf_path_var = tk.StringVar()
        ttk.Entry(compress_frame, textvariable=self.compress_output_pdf_path_var, width=50, state="readonly").grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.btn_comp_browse_out = ttk.Button(compress_frame, text="Browse...", command=self._select_output_compressed_pdf)
        self.btn_comp_browse_out.grid(row=1, column=2, padx=5, pady=5)

        # Compress options (placeholder for future, e.g., remove metadata checkbox)
        # self.compress_remove_metadata_var = tk.BooleanVar(value=False)
        # ttk.Checkbutton(compress_frame, text="Attempt to remove all metadata", variable=self.compress_remove_metadata_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Compress Button
        self.btn_comp_execute = ttk.Button(compress_frame, text="Compress PDF", command=self._execute_compress_pdf)
        self.btn_comp_execute.grid(row=3, column=1, padx=5, pady=10)

        # Status Label
        self.compress_status_var = tk.StringVar()
        ttk.Label(compress_frame, textvariable=self.compress_status_var, wraplength=400).grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        compress_frame.columnconfigure(1, weight=1)

        # Add placeholder content to other tabs for now
        # ttk.Label(self.tab_rotate, text="Rotate Pages functionality will be here.").pack(padx=10, pady=10) # SKIPPED

        # --- Add Watermark Tab ---
        for widget in self.tab_watermark.winfo_children():
            widget.destroy()

        water_frame = ttk.Frame(self.tab_watermark, padding="10")
        water_frame.pack(expand=True, fill=tk.BOTH)

        # Input PDF
        self.lbl_wm_input = ttk.Label(water_frame, text="Input PDF:")
        self.lbl_wm_input.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.watermark_input_pdf_path_var = tk.StringVar()
        ttk.Entry(water_frame, textvariable=self.watermark_input_pdf_path_var, width=40, state="readonly").grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.btn_wm_browse_in = ttk.Button(water_frame, text="Browse...", command=self._select_input_pdf_watermark)
        self.btn_wm_browse_in.grid(row=0, column=3, padx=5, pady=5)

        # Watermark Text
        self.lbl_wm_text = ttk.Label(water_frame, text="Watermark Text:")
        self.lbl_wm_text.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.watermark_text_var = tk.StringVar(value="CONFIDENTIAL")
        ttk.Entry(water_frame, textvariable=self.watermark_text_var, width=50).grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Font Options Frame
        self.font_opts_frame = ttk.LabelFrame(water_frame, text="Formatting", padding="5")
        self.font_opts_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        self.lbl_wm_font = ttk.Label(self.font_opts_frame, text="Font:")
        self.lbl_wm_font.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.watermark_font_var = tk.StringVar(value="Helvetica")
        self.watermark_font_combo = ttk.Combobox(self.font_opts_frame, textvariable=self.watermark_font_var, values=["Helvetica", "Times-Roman", "Courier", "Helvetica-Bold", "Times-Bold"], state="readonly", width=15)
        self.watermark_font_combo.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        self.lbl_wm_size = ttk.Label(self.font_opts_frame, text="Size:")
        self.lbl_wm_size.grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.watermark_fontsize_var = tk.StringVar(value="48")
        ttk.Entry(self.font_opts_frame, textvariable=self.watermark_fontsize_var, width=5).grid(row=0, column=3, padx=5, pady=2, sticky="w")

        self.lbl_wm_opacity = ttk.Label(self.font_opts_frame, text="Opacity (0.1-1.0):")
        self.lbl_wm_opacity.grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.watermark_opacity_var = tk.StringVar(value="0.3") # String for Entry
        ttk.Entry(self.font_opts_frame, textvariable=self.watermark_opacity_var, width=5).grid(row=0, column=5, padx=5, pady=2, sticky="w")

        # Page Selection
        self.lbl_wm_pages = ttk.Label(water_frame, text="Pages (e.g., all, 1, 3-5):")
        self.lbl_wm_pages.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.watermark_pages_var = tk.StringVar(value="all")
        ttk.Entry(water_frame, textvariable=self.watermark_pages_var, width=50).grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Output PDF
        self.lbl_wm_out = ttk.Label(water_frame, text="Output PDF:")
        self.lbl_wm_out.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.watermark_output_pdf_path_var = tk.StringVar()
        ttk.Entry(water_frame, textvariable=self.watermark_output_pdf_path_var, width=40, state="readonly").grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.btn_wm_browse_out = ttk.Button(water_frame, text="Browse...", command=self._select_output_watermarked_pdf)
        self.btn_wm_browse_out.grid(row=4, column=3, padx=5, pady=5)

        # Add Watermark Button
        self.btn_wm_execute = ttk.Button(water_frame, text="Add Watermark", command=self._execute_add_watermark)
        self.btn_wm_execute.grid(row=5, column=1, columnspan=2, padx=5, pady=10)

        # Status Label
        self.watermark_status_var = tk.StringVar()
        ttk.Label(water_frame, textvariable=self.watermark_status_var, wraplength=450).grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky="w")

        water_frame.columnconfigure(1, weight=1)
        water_frame.columnconfigure(2, weight=1) # Allow some expansion for entries

        # --- Extract Text Tab ---
        for widget in self.tab_extract_text.winfo_children():
            widget.destroy()

        extract_frame = ttk.Frame(self.tab_extract_text, padding="10")
        extract_frame.pack(expand=True, fill=tk.BOTH)

        # Input PDF
        self.lbl_ext_input = ttk.Label(extract_frame, text="Input PDF:")
        self.lbl_ext_input.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.extract_input_pdf_path_var = tk.StringVar()
        ttk.Entry(extract_frame, textvariable=self.extract_input_pdf_path_var, width=50, state="readonly").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_ext_browse_in = ttk.Button(extract_frame, text="Browse...", command=self._select_input_pdf_extract_text)
        self.btn_ext_browse_in.grid(row=0, column=2, padx=5, pady=5)

        # Page Ranges for Extract
        self.lbl_ext_pages = ttk.Label(extract_frame, text="Pages (e.g., all, 1-5, 8, 10-12):")
        self.lbl_ext_pages.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.extract_page_ranges_var = tk.StringVar(value="all")
        ttk.Entry(extract_frame, textvariable=self.extract_page_ranges_var, width=50).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Output TXT File
        self.lbl_ext_out = ttk.Label(extract_frame, text="Output Text File (.txt):")
        self.lbl_ext_out.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.extract_output_txt_path_var = tk.StringVar()
        ttk.Entry(extract_frame, textvariable=self.extract_output_txt_path_var, width=50, state="readonly").grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.btn_ext_browse_out = ttk.Button(extract_frame, text="Browse...", command=self._select_output_txt_file_extract_text)
        self.btn_ext_browse_out.grid(row=2, column=2, padx=5, pady=5)

        # Extract Text Button
        self.btn_ext_execute = ttk.Button(extract_frame, text="Extract Text to File", command=self._execute_extract_text)
        self.btn_ext_execute.grid(row=3, column=1, padx=5, pady=10)

        # Status Label
        self.extract_status_var = tk.StringVar()
        ttk.Label(extract_frame, textvariable=self.extract_status_var, wraplength=400).grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        extract_frame.columnconfigure(1, weight=1)

        # --- Images to PDF Tab ---
        for widget in self.tab_images_to_pdf.winfo_children():
            widget.destroy()

        img_to_pdf_frame = ttk.Frame(self.tab_images_to_pdf, padding="10")
        img_to_pdf_frame.pack(expand=True, fill=tk.BOTH)

        # Image Listbox and controls
        img_list_controls_frame = ttk.Frame(img_to_pdf_frame)
        img_list_controls_frame.pack(fill=tk.X, pady=5)

        self.btn_img_add = ttk.Button(img_list_controls_frame, text="Add Images...", command=self._add_images_to_list)
        self.btn_img_add.pack(side=tk.LEFT, padx=2)
        self.btn_img_remove = ttk.Button(img_list_controls_frame, text="Remove Selected", command=self._remove_selected_image)
        self.btn_img_remove.pack(side=tk.LEFT, padx=2)
        self.btn_img_up = ttk.Button(img_list_controls_frame, text="Move Up", command=lambda: self._move_image_list_item(-1))
        self.btn_img_up.pack(side=tk.LEFT, padx=2)
        self.btn_img_down = ttk.Button(img_list_controls_frame, text="Move Down", command=lambda: self._move_image_list_item(1))
        self.btn_img_down.pack(side=tk.LEFT, padx=2)

        self.img_listbox = tk.Listbox(img_to_pdf_frame, selectmode=tk.SINGLE, width=70, height=10)
        self.img_listbox.pack(pady=5, fill=tk.BOTH, expand=True)
        img_list_scrollbar = ttk.Scrollbar(self.img_listbox, orient=tk.VERTICAL, command=self.img_listbox.yview)
        self.img_listbox.config(yscrollcommand=img_list_scrollbar.set)

        # Output Mode
        self.img_output_mode_var = tk.StringVar(value="merge")
        mode_frame = ttk.Frame(img_to_pdf_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        self.rb_img_merge = ttk.Radiobutton(mode_frame, text="Merge into one PDF", variable=self.img_output_mode_var, value="merge")
        self.rb_img_merge.pack(side=tk.LEFT, padx=10)
        self.rb_img_separate = ttk.Radiobutton(mode_frame, text="Convert to separate PDFs", variable=self.img_output_mode_var, value="separate")
        self.rb_img_separate.pack(side=tk.LEFT, padx=10)

        # Output Selection
        output_frame_img = ttk.Frame(img_to_pdf_frame)
        output_frame_img.pack(fill=tk.X, pady=5)
        self.lbl_img_out = ttk.Label(output_frame_img, text="Output:")
        self.lbl_img_out.pack(side=tk.LEFT, padx=5)
        self.img_output_path_var = tk.StringVar()
        ttk.Entry(output_frame_img, textvariable=self.img_output_path_var, width=50, state="readonly").pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.btn_img_browse = ttk.Button(output_frame_img, text="Browse...", command=self._select_output_images_to_pdf)
        self.btn_img_browse.pack(side=tk.LEFT, padx=5)

        # Execute Button
        self.btn_img_execute = ttk.Button(img_to_pdf_frame, text="Convert to PDF", command=self._execute_images_to_pdf)
        self.btn_img_execute.pack(pady=10)

        # Status Label
        self.img_status_var = tk.StringVar()
        ttk.Label(img_to_pdf_frame, textvariable=self.img_status_var, wraplength=400).pack(pady=5, fill=tk.X)

        self.img_file_paths = []

        self.shared_state.log(f"Tabbed UI for {self.module_name} created.")
        self.update_language()

    def update_language(self):
        super().update_language()
        if not getattr(self, 'notebook', None): return

        # Update Tab Titles
        self.notebook.tab(self.tab_split, text=self.tr("module_pdf_tab_split", "Split PDF"))
        self.notebook.tab(self.tab_merge, text=self.tr("module_pdf_tab_merge", "Merge PDFs"))
        self.notebook.tab(self.tab_compress, text=self.tr("module_pdf_tab_compress", "Compress PDF"))
        self.notebook.tab(self.tab_watermark, text=self.tr("module_pdf_tab_watermark", "Add Watermark"))
        self.notebook.tab(self.tab_extract_text, text=self.tr("module_pdf_tab_extract", "Extract Text"))
        if pdfium:
            self.notebook.tab(self.tab_to_image_pdf, text=self.tr("module_pdf_tab_to_image_pdf", "To Image PDF"))

        # To Image PDF Tab
        if pdfium:
            self.lbl_to_img_input.config(text=self.tr("module_pdf_lbl_input_pdf", "Input PDF:"))
            self.btn_to_img_browse_in.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
            self.lbl_to_img_output.config(text=self.tr("module_pdf_lbl_out_image_pdf", "Output Image PDF:"))
            self.btn_to_img_browse_out.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
            self.lbl_to_img_dpi.config(text=self.tr("module_pdf_lbl_dpi", "Image Quality (DPI):"))
            self.btn_to_img_execute.config(text=self.tr("module_pdf_btn_convert_to_image", "Convert to Image PDF"))

        # Split Tab
        self.lbl_split_input.config(text=self.tr("module_pdf_lbl_input_pdf", "Input PDF:"))
        self.btn_split_browse.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.lbl_split_ranges.config(text=self.tr("module_pdf_lbl_ranges", "Page Ranges (e.g., 1-5, 8):"))
        self.lbl_split_out_folder.config(text=self.tr("module_pdf_lbl_out_folder", "Output Folder:"))
        self.btn_split_choose_folder.config(text=self.tr("module_pdf_btn_choose_folder", "Choose Folder..."))
        self.lbl_split_pattern.config(text=self.tr("module_pdf_lbl_pattern", "Output Pattern:"))
        self.lbl_split_placeholders.config(text=self.tr("module_pdf_lbl_placeholders", "Placeholders: {i}, {filename}, {basename}, {start}, {end}"))
        self.btn_split_execute.config(text=self.tr("module_pdf_btn_split", "Split PDF"))

        # Merge Tab
        self.btn_merge_add.config(text=self.tr("module_pdf_btn_add_pdfs", "Add PDF(s)..."))
        self.btn_merge_remove.config(text=self.tr("module_pdf_btn_remove_sel", "Remove Selected"))
        self.btn_merge_up.config(text=self.tr("module_pdf_btn_move_up", "Move Up"))
        self.btn_merge_down.config(text=self.tr("module_pdf_btn_move_down", "Move Down"))
        self.lbl_merge_out.config(text=self.tr("module_pdf_lbl_out_merged", "Output Merged PDF:"))
        self.btn_merge_browse.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.btn_merge_execute.config(text=self.tr("module_pdf_btn_merge", "Merge PDFs"))

        # Compress Tab
        self.lbl_comp_input.config(text=self.tr("module_pdf_lbl_input_pdf", "Input PDF:"))
        self.btn_comp_browse_in.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.lbl_comp_output.config(text=self.tr("module_pdf_lbl_out_compressed", "Output Compressed PDF:"))
        self.btn_comp_browse_out.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.btn_comp_execute.config(text=self.tr("module_pdf_btn_compress", "Compress PDF"))

        # Watermark Tab
        self.lbl_wm_input.config(text=self.tr("module_pdf_lbl_input_pdf", "Input PDF:"))
        self.btn_wm_browse_in.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.lbl_wm_text.config(text=self.tr("module_pdf_lbl_wm_text", "Watermark Text:"))
        self.font_opts_frame.config(text=self.tr("module_pdf_grp_formatting", "Formatting"))
        self.lbl_wm_font.config(text=self.tr("module_pdf_lbl_font", "Font:"))
        self.lbl_wm_size.config(text=self.tr("module_pdf_lbl_size", "Size:"))
        self.lbl_wm_opacity.config(text=self.tr("module_pdf_lbl_opacity", "Opacity (0.1-1.0):"))
        self.lbl_wm_pages.config(text=self.tr("module_pdf_lbl_pages", "Pages (e.g., all, 1, 3-5):"))
        self.lbl_wm_out.config(text=self.tr("module_pdf_lbl_out_pdf", "Output PDF:"))
        self.btn_wm_browse_out.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.btn_wm_execute.config(text=self.tr("module_pdf_btn_watermark", "Add Watermark"))

        # Extract Tab
        self.lbl_ext_input.config(text=self.tr("module_pdf_lbl_input_pdf", "Input PDF:"))
        self.btn_ext_browse_in.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.lbl_ext_pages.config(text=self.tr("module_pdf_lbl_pages", "Pages (e.g., all, 1-5):"))
        self.lbl_ext_out.config(text=self.tr("module_pdf_lbl_out_txt", "Output Text File (.txt):"))
        self.btn_ext_browse_out.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.btn_ext_execute.config(text=self.tr("module_pdf_btn_extract", "Extract Text to File"))

        # Images to PDF Tab
        self.notebook.tab(self.tab_images_to_pdf, text=self.tr("module_pdf_tab_img_to_pdf", "Images to PDF"))
        self.btn_img_add.config(text=self.tr("module_pdf_btn_add_imgs", "Add Images..."))
        self.btn_img_remove.config(text=self.tr("module_pdf_btn_remove_sel", "Remove Selected"))
        self.btn_img_up.config(text=self.tr("module_pdf_btn_move_up", "Move Up"))
        self.btn_img_down.config(text=self.tr("module_pdf_btn_move_down", "Move Down"))
        self.rb_img_merge.config(text=self.tr("module_pdf_rb_merge_imgs", "Merge into one PDF"))
        self.rb_img_separate.config(text=self.tr("module_pdf_rb_separate_pdfs", "Convert to separate PDFs"))
        self.lbl_img_out.config(text=self.tr("module_pdf_lbl_out_general", "Output:"))
        self.btn_img_browse.config(text=self.tr("module_pdf_btn_browse", "Browse..."))
        self.btn_img_execute.config(text=self.tr("module_pdf_btn_convert_imgs", "Convert to PDF"))

    # Methods for PDF operations (split, merge, compress, rotate, watermark, extract) will be added later.

    def _select_input_pdf_split(self):
        filepath = filedialog.askopenfilename(
            title="Select Input PDF for Splitting",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self.frame
        )
        if filepath:
            self.current_input_pdf_path = filepath # Store this for the actual operation
            self.split_input_pdf_path_var.set(filepath)
            self.split_status_var.set(f"Selected: {os.path.basename(filepath)}")
            self.shared_state.log(f"Split Tab: Input PDF selected: {filepath}")
        else:
            self.split_status_var.set("Input PDF selection cancelled.")

    def _parse_page_ranges(self, ranges_str, total_pages):
        parsed_ranges = []
        if not ranges_str.strip():
            self.split_status_var.set("Error: Page ranges cannot be empty.")
            self.shared_state.log("Split Tab: Page ranges string is empty.", "ERROR")
            return None

        parts = ranges_str.split(',')
        for part in parts:
            part = part.strip()
            if not part: continue
            if '-' in part:
                try:
                    start_str, end_str = part.split('-', 1)
                    start = int(start_str)
                    end = int(end_str)
                except ValueError:
                    self.split_status_var.set(f"Error: Invalid range format '{part}'. Use numbers like '1-5'.")
                    self.shared_state.log(f"Split Tab: Invalid page range format '{part}'.", "ERROR")
                    return None

                if not (1 <= start <= end <= total_pages):
                    self.split_status_var.set(f"Error: Range '{part}' ({start}-{end}) is invalid for PDF with {total_pages} pages.")
                    self.shared_state.log(f"Split Tab: Page range {start}-{end} out of bounds for {total_pages} pages.", "ERROR")
                    return None
                parsed_ranges.append((start - 1, end - 1)) # Convert to 0-indexed
            else:
                try:
                    page = int(part)
                except ValueError:
                    self.split_status_var.set(f"Error: Invalid page number '{part}'. Must be a number.")
                    self.shared_state.log(f"Split Tab: Invalid page number '{part}'.", "ERROR")
                    return None

                if not (1 <= page <= total_pages):
                    self.split_status_var.set(f"Error: Page number '{page}' is invalid for PDF with {total_pages} pages.")
                    self.shared_state.log(f"Split Tab: Page number {page} out of bounds for {total_pages} pages.", "ERROR")
                    return None
                parsed_ranges.append((page - 1, page - 1))

        if not parsed_ranges:
            self.split_status_var.set("Error: No valid page ranges found after parsing.")
            self.shared_state.log("Split Tab: No valid page ranges parsed.", "ERROR")
            return None

        # 移除自動合併區間的邏輯，直接回傳所有區間
        return parsed_ranges


    def _execute_split_pdf(self):
        self.shared_state.log("Split Tab: Attempting to execute PDF split.")
        self.split_status_var.set("Processing...")

        input_pdf = self.current_input_pdf_path # Use the stored path
        if not input_pdf or not os.path.exists(input_pdf):
            self.split_status_var.set("Error: Input PDF not selected or not found.")
            messagebox.showerror("Error", "Please select a valid input PDF file first.", parent=self.tab_split)
            self.shared_state.log("Split Tab: Input PDF not valid.", "ERROR")
            return

        page_ranges_str = self.split_page_ranges_var.get()
        output_pattern_str = self.split_output_pattern_var.get()

        if not output_pattern_str.strip():
            self.split_status_var.set("Error: Output pattern cannot be empty.")
            messagebox.showerror("Error", "Please provide an output naming pattern.", parent=self.tab_split)
            self.shared_state.log("Split Tab: Output pattern is empty.", "ERROR")
            return

        try:
            reader = PdfReader(input_pdf)
            total_pages = len(reader.pages)
        except Exception as e:
            self.split_status_var.set(f"Error reading PDF: {e}")
            messagebox.showerror("PDF Error", f"Could not read the input PDF: {e}", parent=self.tab_split)
            self.shared_state.log(f"Split Tab: Error reading PDF '{input_pdf}': {e}", "ERROR")
            return

        page_ranges = self._parse_page_ranges(page_ranges_str, total_pages)
        if not page_ranges:
            # Error message likely already set by _parse_page_ranges
            messagebox.showerror("Invalid Page Ranges", self.split_status_var.get() or "Failed to parse page ranges.", parent=self.tab_split)
            return

        # Output directory logic
        output_folder = self.split_output_folder_var.get()
        if output_folder:
            self.current_output_dir = output_folder
        else:
            default_output_root = os.path.join(os.path.expanduser("~"), "pdf_processor_outputs")
            self.current_output_dir = os.path.join(default_output_root, "split_files")
            if hasattr(self.gui_manager, 'saves_dir') and self.gui_manager.saves_dir:
                app_specific_output_dir = os.path.join(self.gui_manager.saves_dir, "pdf_processor_module", "split_files")
                self.current_output_dir = app_specific_output_dir

        try:
            os.makedirs(self.current_output_dir, exist_ok=True)
            self.shared_state.log(f"Split Tab: Output directory confirmed: {self.current_output_dir}")
        except OSError as e:
            self.split_status_var.set(f"Error creating output directory: {e}")
            messagebox.showerror("Directory Error", f"Could not create output directory: {self.current_output_dir}\n{e}", parent=self.tab_split)
            self.shared_state.log(f"Split Tab: Error creating output directory '{self.current_output_dir}': {e}", "ERROR")
            return


        base_filename_ext = os.path.basename(input_pdf)
        base_filename_no_ext = os.path.splitext(base_filename_ext)[0]

        try:
            num_files_created = 0
            for i, (start_page, end_page) in enumerate(page_ranges):
                writer = PdfWriter()
                for page_num in range(start_page, end_page + 1):
                    writer.add_page(reader.pages[page_num])

                format_dict = {
                    'i': i + 1,
                    'filename': base_filename_ext,
                    'basename': base_filename_no_ext,
                    'start': start_page + 1,
                    'end': end_page + 1
                }
                try:
                    # Ensure the pattern doesn't create problematic filenames (basic check)
                    temp_output_filename = output_pattern_str.format(**format_dict)
                except KeyError as e_key:
                    self.split_status_var.set(f"Error: Invalid placeholder {e_key} in output pattern.")
                    messagebox.showerror("Output Pattern Error", f"Invalid placeholder {e_key} in the output pattern. Available: {{i}}, {{filename}}, {{basename}}, {{start}}, {{end}}", parent=self.tab_split)
                    self.shared_state.log(f"Split Tab: Invalid placeholder in output pattern: {e_key}", "ERROR")
                    return

                # Sanitize output_filename (very basic, consider a library for robust sanitization if needed)
                # Remove path components and limit character set
                safe_filename = os.path.basename(temp_output_filename) # remove any path components
                safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in (' ', '.', '-', '_')).strip()
                safe_filename = safe_filename.replace(" ", "_")

                if not safe_filename: # Handle case where sanitization results in empty string
                    safe_filename = f"default_part_{format_dict['i']}.pdf"

                if not safe_filename.lower().endswith(".pdf"):
                    safe_filename += ".pdf"

                output_path = os.path.join(self.current_output_dir, safe_filename)

                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
                self.shared_state.log(f"Split Tab: Created split file: {output_path} (Pages {start_page+1}-{end_page+1})")
                num_files_created += 1

            final_message = f"Successfully split into {num_files_created} PDF(s) in '{os.path.abspath(self.current_output_dir)}'."
            self.split_status_var.set(final_message)
            messagebox.showinfo("Split Successful", final_message, parent=self.tab_split)
            self.shared_state.log(f"Split Tab: {final_message}")

        except Exception as e_split:
            error_msg = f"Error during PDF splitting operation: {e_split}"
            self.split_status_var.set(error_msg)
            messagebox.showerror("Splitting Error", error_msg, parent=self.tab_split)
            self.shared_state.log(f"Split Tab: {error_msg}", "ERROR")

    def _add_pdfs_to_merge_list(self):
        filepaths = filedialog.askopenfilenames(
            title="Select PDF Files to Merge",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self.tab_merge
        )
        if filepaths:
            added_count = 0
            for fp in filepaths:
                if fp not in self.merge_file_paths: # Avoid duplicates
                    self.merge_file_paths.append(fp)
                    self.merge_pdf_listbox.insert(tk.END, os.path.basename(fp))
                    added_count +=1
            self.merge_status_var.set(f"Added {added_count} PDF(s) to the list.")
            self.shared_state.log(f"Merge Tab: Added {added_count} PDFs. Current list size: {len(self.merge_file_paths)}")
        else:
            self.merge_status_var.set("No PDFs selected or selection cancelled.")

    def _remove_selected_pdf_from_merge_list(self):
        selected_indices = self.merge_pdf_listbox.curselection()
        if not selected_indices:
            self.merge_status_var.set("No PDF selected to remove.")
            messagebox.showwarning("Selection Error", "Please select a PDF from the list to remove.", parent=self.tab_merge)
            return

        # Remove in reverse order to maintain correct indices
        for index in sorted(selected_indices, reverse=True):
            self.merge_pdf_listbox.delete(index)
            removed_path = self.merge_file_paths.pop(index)
            self.shared_state.log(f"Merge Tab: Removed '{removed_path}' from merge list.")
        self.merge_status_var.set(f"Removed {len(selected_indices)} PDF(s) from the list.")
        if not self.merge_file_paths:
            self.merge_status_var.set("Merge list is now empty.")


    def _move_merge_list_item(self, direction): # direction: -1 for up, 1 for down
        selected_indices = self.merge_pdf_listbox.curselection()
        if not selected_indices:
            self.merge_status_var.set("No PDF selected to move.")
            messagebox.showwarning("Selection Error", "Please select a PDF from the list to move.", parent=self.tab_merge)
            return

        idx = selected_indices[0] # Only move one at a time for simplicity

        if direction == -1 and idx == 0: # Already at top
            self.merge_status_var.set("Selected PDF is already at the top.")
            return
        if direction == 1 and idx == len(self.merge_file_paths) - 1: # Already at bottom
            self.merge_status_var.set("Selected PDF is already at the bottom.")
            return

        new_idx = idx + direction

        # Swap in the internal list
        self.merge_file_paths[idx], self.merge_file_paths[new_idx] = self.merge_file_paths[new_idx], self.merge_file_paths[idx]

        # Update listbox
        self.merge_pdf_listbox.delete(0, tk.END)
        for fp in self.merge_file_paths:
            self.merge_pdf_listbox.insert(tk.END, os.path.basename(fp))

        self.merge_pdf_listbox.selection_set(new_idx)
        self.merge_pdf_listbox.activate(new_idx)
        self.merge_status_var.set(f"Moved '{os.path.basename(self.merge_file_paths[new_idx])}' {'up' if direction == -1 else 'down'}.")
        self.shared_state.log(f"Merge Tab: Moved item to index {new_idx}.")


    def _select_output_merged_pdf(self):
        initial_name = "merged_output.pdf"
        if self.merge_file_paths:
            first_basename = os.path.splitext(os.path.basename(self.merge_file_paths[0]))[0]
            count = len(self.merge_file_paths)
            if count > 1:
                initial_name = f"{first_basename}_and_{count - 1}_more_merged.pdf"
            else:
                initial_name = f"{first_basename}_merged.pdf"

        filepath = filedialog.asksaveasfilename(
            title="Save Merged PDF As...",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=initial_name,
            parent=self.tab_merge
        )
        if filepath:
            self.merge_output_pdf_path_var.set(filepath)
            self.merge_status_var.set(f"Output will be saved as: {os.path.basename(filepath)}")
            self.shared_state.log(f"Merge Tab: Output merged PDF path set to: {filepath}")
        else:
            self.merge_status_var.set("Output PDF save location not set.")

    def _execute_merge_pdfs(self):
        self.shared_state.log("Merge Tab: Attempting to execute PDF merge.")
        self.merge_status_var.set("Processing merge...")

        if not self.merge_file_paths or len(self.merge_file_paths) < 2:
            self.merge_status_var.set("Error: Please add at least two PDF files to merge.")
            messagebox.showerror("Merge Error", "You need to select at least two PDF files to merge.", parent=self.tab_merge)
            self.shared_state.log("Merge Tab: Not enough PDFs to merge.", "ERROR")
            return

        output_pdf_path = self.merge_output_pdf_path_var.get()
        if not output_pdf_path:
            self.merge_status_var.set("Error: Output PDF file path not specified.")
            messagebox.showerror("Merge Error", "Please specify an output file path for the merged PDF.", parent=self.tab_merge)
            self.shared_state.log("Merge Tab: Output path not specified.", "ERROR")
            return

        # Ensure output directory exists
        output_dir = os.path.dirname(output_pdf_path)
        if output_dir and not os.path.exists(output_dir): # Check if output_dir is not empty (can happen if just filename is given)
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.shared_state.log(f"Merge Tab: Created output directory: {output_dir}")
            except OSError as e:
                self.merge_status_var.set(f"Error creating output directory: {e}")
                messagebox.showerror("Directory Error", f"Could not create output directory: {output_dir}\n{e}", parent=self.tab_merge)
                self.shared_state.log(f"Merge Tab: Error creating output directory '{output_dir}': {e}", "ERROR")
                return


        merger = PdfWriter() # Use PdfWriter for merging
        try:
            for i, pdf_path in enumerate(self.merge_file_paths):
                self.merge_status_var.set(f"Processing '{os.path.basename(pdf_path)}' ({i+1}/{len(self.merge_file_paths)})...")
                self.tab_merge.update_idletasks() # Update UI
                try:
                    reader = PdfReader(pdf_path)
                    merger.append(reader) # append() is the modern way for PdfWriter
                    self.shared_state.log(f"Merge Tab: Appended '{pdf_path}' to merger.")
                except Exception as e_read:
                    # If append fails, or for more control, could iterate pages:
                    # for page_num in range(len(reader.pages)):
                    #     merger.add_page(reader.pages[page_num])
                    error_msg = f"Error reading or appending '{os.path.basename(pdf_path)}': {e_read}. Skipping this file."
                    self.shared_state.log(f"Merge Tab: {error_msg}", "WARNING")
                    messagebox.showwarning("File Error", error_msg, parent=self.tab_merge)
                    # Decide if you want to continue or stop on error. Here we skip.

            if not merger.pages: # Check if any pages were actually added
                 self.merge_status_var.set("Error: No pages were successfully merged. Check input PDF files.")
                 messagebox.showerror("Merge Error", "No pages could be merged. Ensure input PDFs are valid and not empty/corrupted.", parent=self.tab_merge)
                 self.shared_state.log("Merge Tab: No pages in PdfWriter after attempting merge.", "ERROR")
                 return

            with open(output_pdf_path, "wb") as output_file:
                merger.write(output_file)

            final_message = f"Successfully merged {len(self.merge_file_paths)} PDF(s) into '{os.path.basename(output_pdf_path)}'."
            self.merge_status_var.set(final_message)
            messagebox.showinfo("Merge Successful", final_message, parent=self.tab_merge)
            self.shared_state.log(f"Merge Tab: {final_message} created at {output_pdf_path}")

        except Exception as e_merge:
            error_msg = f"Error during PDF merging operation: {e_merge}"
            self.merge_status_var.set(error_msg)
            messagebox.showerror("Merging Error", error_msg, parent=self.tab_merge)
            self.shared_state.log(f"Merge Tab: {error_msg}", "ERROR")
        finally:
            merger.close() # Good practice to close the writer

    def _select_input_pdf_compress(self):
        filepath = filedialog.askopenfilename(
            title="Select Input PDF for Compression",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self.tab_compress
        )
        if filepath:
            self.compress_input_pdf_path_var.set(filepath)
            try:
                original_size = os.path.getsize(filepath)
                self.compress_status_var.set(f"Selected: {os.path.basename(filepath)} (Size: {original_size / 1024:.2f} KB)")
            except OSError:
                 self.compress_status_var.set(f"Selected: {os.path.basename(filepath)}")
            self.shared_state.log(f"Compress Tab: Input PDF selected: {filepath}")
        else:
            self.compress_status_var.set("Input PDF selection cancelled.")

    def _select_output_compressed_pdf(self):
        input_path = self.compress_input_pdf_path_var.get()
        initial_name = "compressed_output.pdf"
        if input_path:
            base, ext = os.path.splitext(os.path.basename(input_path))
            initial_name = f"{base}_compressed{ext}"

        filepath = filedialog.asksaveasfilename(
            title="Save Compressed PDF As...",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=initial_name,
            parent=self.tab_compress
        )
        if filepath:
            self.compress_output_pdf_path_var.set(filepath)
            self.compress_status_var.set(f"Compressed PDF will be saved as: {os.path.basename(filepath)}")
            self.shared_state.log(f"Compress Tab: Output compressed PDF path set to: {filepath}")
        else:
            self.compress_status_var.set("Output PDF save location not set for compression.")

    def _execute_compress_pdf(self):
        self.shared_state.log("Compress Tab: Attempting to execute PDF compression.")
        self.compress_status_var.set("Processing compression...")
        self.tab_compress.update_idletasks()


        input_pdf_path = self.compress_input_pdf_path_var.get()
        output_pdf_path = self.compress_output_pdf_path_var.get()

        if not input_pdf_path or not os.path.exists(input_pdf_path):
            self.compress_status_var.set("Error: Input PDF not selected or not found.")
            messagebox.showerror("Compression Error", "Please select a valid input PDF file.", parent=self.tab_compress)
            self.shared_state.log("Compress Tab: Input PDF not valid.", "ERROR")
            return

        if not output_pdf_path:
            self.compress_status_var.set("Error: Output PDF file path not specified.")
            messagebox.showerror("Compression Error", "Please specify an output file path for the compressed PDF.", parent=self.tab_compress)
            self.shared_state.log("Compress Tab: Output path not specified.", "ERROR")
            return

        # Ensure output directory exists
        output_dir = os.path.dirname(output_pdf_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                self.compress_status_var.set(f"Error creating output directory: {e}")
                messagebox.showerror("Directory Error", f"Could not create output directory: {output_dir}\n{e}", parent=self.tab_compress)
                return

        writer = PdfWriter()
        try:
            reader = PdfReader(input_pdf_path)

            # Add all pages from reader to writer
            for page in reader.pages:
                writer.add_page(page)

            # PyPDF2's PdfWriter can apply some optimizations by default when writing.
            # For more explicit control over stream compression (often default in modern PyPDF2):
            # writer.compress_content_streams = True # May not be needed or available depending on version.

            # If you wanted to remove metadata (example, not enabled by default here):
            # if self.compress_remove_metadata_var.get():
            #    writer.add_metadata({}) # This replaces existing metadata with an empty dict
            #    self.shared_state.log("Compress Tab: Attempting to remove metadata.")


            with open(output_pdf_path, "wb") as output_file:
                writer.write(output_file)

            original_size = os.path.getsize(input_pdf_path)
            new_size = os.path.getsize(output_pdf_path)
            size_reduction = original_size - new_size
            percentage_reduction = (size_reduction / original_size * 100) if original_size > 0 else 0

            final_message = (
                f"Compression complete: '{os.path.basename(output_pdf_path)}'.\n"
                f"Original size: {original_size / 1024:.2f} KB. "
                f"New size: {new_size / 1024:.2f} KB.\n"
                f"Reduction: {size_reduction / 1024:.2f} KB ({percentage_reduction:.2f}%)."
            )
            self.compress_status_var.set(final_message)
            messagebox.showinfo("Compression Successful", final_message, parent=self.tab_compress)
            self.shared_state.log(f"Compress Tab: {final_message}")

        except Exception as e_compress:
            error_msg = f"Error during PDF compression: {e_compress}"
            self.compress_status_var.set(error_msg)
            messagebox.showerror("Compression Error", error_msg, parent=self.tab_compress)
            self.shared_state.log(f"Compress Tab: {error_msg}", "ERROR")
        finally:
            writer.close()

    def _select_input_pdf_watermark(self):
        filepath = filedialog.askopenfilename(
            title="Select Input PDF for Watermark",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self.tab_watermark
        )
        if filepath:
            self.watermark_input_pdf_path_var.set(filepath)
            self.watermark_status_var.set(f"Selected for watermark: {os.path.basename(filepath)}")
            self.shared_state.log(f"Watermark Tab: Input PDF selected: {filepath}")
        else:
            self.watermark_status_var.set("Input PDF selection cancelled for watermark.")

    def _select_output_watermarked_pdf(self):
        input_path = self.watermark_input_pdf_path_var.get()
        initial_name = "watermarked_output.pdf"
        if input_path:
            base, ext = os.path.splitext(os.path.basename(input_path))
            initial_name = f"{base}_watermarked{ext}"
        filepath = filedialog.asksaveasfilename(
            title="Save Watermarked PDF As...",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=initial_name,
            parent=self.tab_watermark
        )
        if filepath:
            self.watermark_output_pdf_path_var.set(filepath)
            self.watermark_status_var.set(f"Watermarked PDF will be saved as: {os.path.basename(filepath)}")
            self.shared_state.log(f"Watermark Tab: Output watermarked PDF path set: {filepath}")
        else:
            self.watermark_status_var.set("Output PDF save location not set for watermark.")

    def _parse_pages_for_watermarking(self, pages_str, total_pages):
        target_pages = set()
        pages_str = pages_str.strip().lower()

        if pages_str == "all":
            return set(range(total_pages))

        parts = pages_str.split(',')
        for part_item in parts:
            part_item = part_item.strip()
            if not part_item: continue
            if '-' in part_item:
                try:
                    start_str, end_str = part_item.split('-', 1)
                    start = int(start_str)
                    end = int(end_str)
                except ValueError:
                    self.watermark_status_var.set(f"Error: Invalid range format '{part_item}'.")
                    return None
                if not (1 <= start <= end <= total_pages):
                    self.watermark_status_var.set(f"Error: Range '{part_item}' invalid for {total_pages} pages.")
                    return None
                for i in range(start - 1, end):
                    target_pages.add(i)
            else:
                try:
                    page = int(part_item)
                except ValueError:
                    self.watermark_status_var.set(f"Error: Invalid page number '{part_item}'.")
                    return None
                if not (1 <= page <= total_pages):
                    self.watermark_status_var.set(f"Error: Page number '{page}' invalid for {total_pages} pages.")
                    return None
                target_pages.add(page - 1)

        if not target_pages and pages_str:
             self.watermark_status_var.set("Error: No valid pages found in selection string.")
             return None
        return target_pages

    def _create_watermark_layer(self, text, font_name, font_size_pt, opacity_float, page_width, page_height, color_tuple=(0,0,0)):
        packet = io.BytesIO()
        # Canvas using page dimensions from the actual PDF page for accurate placement
        can = reportlab_canvas.Canvas(packet, pagesize=(page_width, page_height))

        # Font and Color with Alpha
        # Reportlab colors are 0-1 for RGB
        r, g, b = color_tuple[0]/255.0, color_tuple[1]/255.0, color_tuple[2]/255.0
        can.setFillColorRGB(r, g, b, alpha=opacity_float)
        try:
            can.setFont(font_name, font_size_pt)
        except Exception as e: # Handle missing fonts gracefully
            self.shared_state.log(f"Watermark: Font '{font_name}' not found, defaulting to Helvetica. Error: {e}", "WARNING")
            can.setFont("Helvetica", font_size_pt)


        # Position watermark (e.g., centered and rotated)
        can.translate(page_width / 2, page_height / 2) # Move origin to center
        can.rotate(45) # Rotate counter-clockwise

        # Adjust text anchor and position for better centering after rotation
        text_width = can.stringWidth(text, font_name, font_size_pt)
        can.drawCentredString(0, - (font_size_pt / 2.5) , text) # x, y relative to translated origin

        can.save()
        packet.seek(0)
        return PdfReader(packet)


    def _execute_add_watermark(self):
        self.shared_state.log("Watermark Tab: Attempting to add watermark.")
        self.watermark_status_var.set("Processing watermark...")
        self.tab_watermark.update_idletasks()

        input_pdf_path = self.watermark_input_pdf_path_var.get()
        output_pdf_path = self.watermark_output_pdf_path_var.get()
        watermark_text = self.watermark_text_var.get()
        font_name = self.watermark_font_var.get()

        try:
            font_size = int(self.watermark_fontsize_var.get())
            opacity = float(self.watermark_opacity_var.get())
            if not (0.0 <= opacity <= 1.0):
                raise ValueError("Opacity must be between 0.0 and 1.0")
        except ValueError as e:
            self.watermark_status_var.set(f"Error: Invalid font size or opacity: {e}")
            messagebox.showerror("Input Error", f"Invalid font size or opacity: {e}", parent=self.tab_watermark)
            return

        pages_to_watermark_str = self.watermark_pages_var.get()

        if not all([input_pdf_path, output_pdf_path, watermark_text, font_name]):
            messagebox.showerror("Input Error", "Please fill all required fields.", parent=self.tab_watermark)
            self.watermark_status_var.set("Error: Missing required fields.")
            return
        if not os.path.exists(input_pdf_path):
            messagebox.showerror("File Error", "Input PDF not found.", parent=self.tab_watermark)
            self.watermark_status_var.set("Error: Input PDF not found.")
            return

        output_dir = os.path.dirname(output_pdf_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                self.watermark_status_var.set(f"Error creating output directory: {e}")
                messagebox.showerror("Directory Error", f"Could not create directory: {output_dir}\n{e}", parent=self.tab_watermark)
                return

        writer = PdfWriter()
        reader = None
        watermark_pdf_reader = None

        try:
            reader = PdfReader(input_pdf_path)
            total_pages = len(reader.pages)

            target_page_indices = self._parse_pages_for_watermarking(pages_to_watermark_str, total_pages)
            if target_page_indices is None:
                messagebox.showerror("Page Selection Error", self.watermark_status_var.get() or "Invalid page selection.", parent=self.tab_watermark)
                return

            # Create watermark for the first page to get its dimensions for canvas
            # This assumes all pages have similar dimensions for watermark placement, or watermark is generic enough.
            # A more robust solution might create watermark per page if dimensions vary significantly.
            if not reader.pages:
                messagebox.showerror("PDF Error", "Input PDF has no pages.", parent=self.tab_watermark)
                self.watermark_status_var.set("Error: Input PDF is empty.")
                return

            first_page_for_dims = reader.pages[0]
            page_width = float(first_page_for_dims.mediabox.width)
            page_height = float(first_page_for_dims.mediabox.height)

            watermark_pdf_reader = self._create_watermark_layer(watermark_text, font_name, font_size, opacity, page_width, page_height)
            watermark_page = watermark_pdf_reader.pages[0]

            for i, page in enumerate(reader.pages):
                if i in target_page_indices:
                    # Use PyPDF2's merge_page for watermarking
                    page.merge_page(watermark_page)
                    self.shared_state.log(f"Watermark Tab: Watermarking page {i+1}.")
                writer.add_page(page) # Add original or merged page

            with open(output_pdf_path, "wb") as output_file:
                writer.write(output_file)

            final_message = f"Successfully watermarked '{os.path.basename(output_pdf_path)}'."
            self.watermark_status_var.set(final_message)
            messagebox.showinfo("Watermark Successful", final_message, parent=self.tab_watermark)
            self.shared_state.log(f"Watermark Tab: {final_message}")

        except Exception as e_watermark:
            error_msg = f"Error during watermarking: {e_watermark}"
            self.watermark_status_var.set(error_msg)
            messagebox.showerror("Watermarking Error", error_msg, parent=self.tab_watermark)
            self.shared_state.log(f"Watermark Tab: {error_msg}", "ERROR")
        finally:
            writer.close()
            # No explicit close for PdfReader from BytesIO needed in the same way
            # as file streams, it will be garbage collected.

    def _select_input_pdf_extract_text(self):
        filepath = filedialog.askopenfilename(
            title="Select Input PDF for Text Extraction",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self.tab_extract_text
        )
        if filepath:
            self.extract_input_pdf_path_var.set(filepath)
            self.extract_status_var.set(f"Selected for text extraction: {os.path.basename(filepath)}")
            self.shared_state.log(f"Extract Text Tab: Input PDF selected: {filepath}")
        else:
            self.extract_status_var.set("Input PDF selection cancelled for text extraction.")

    def _select_output_txt_file_extract_text(self):
        input_path = self.extract_input_pdf_path_var.get()
        initial_name = "extracted_text.txt"
        if input_path:
            base, _ = os.path.splitext(os.path.basename(input_path))
            initial_name = f"{base}_extracted.txt"

        filepath = filedialog.asksaveasfilename(
            title="Save Extracted Text As...",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=initial_name,
            parent=self.tab_extract_text
        )
        if filepath:
            self.extract_output_txt_path_var.set(filepath)
            self.extract_status_var.set(f"Extracted text will be saved as: {os.path.basename(filepath)}")
            self.shared_state.log(f"Extract Text Tab: Output TXT path set to: {filepath}")
        else:
            self.extract_status_var.set("Output TXT file save location not set.")

    def _parse_page_ranges_for_extract(self, ranges_str, total_pages):
        """Parse page ranges for extract text, return a sorted list of 0-based page indices."""
        ranges_str = ranges_str.strip().lower()
        if ranges_str == "all":
            return list(range(total_pages))
        indices = set()
        parts = ranges_str.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                try:
                    start_str, end_str = part.split('-', 1)
                    start = int(start_str)
                    end = int(end_str)
                except ValueError:
                    return None
                if not (1 <= start <= end <= total_pages):
                    return None
                indices.update(range(start - 1, end))
            else:
                try:
                    page = int(part)
                except ValueError:
                    return None
                if not (1 <= page <= total_pages):
                    return None
                indices.add(page - 1)
        return sorted(indices) if indices else None

    def _execute_extract_text(self):
        self.shared_state.log("Extract Text Tab: Attempting to extract text.")
        self.extract_status_var.set("Processing text extraction...")
        self.tab_extract_text.update_idletasks()

        input_pdf_path = self.extract_input_pdf_path_var.get()
        output_txt_path = self.extract_output_txt_path_var.get()
        page_ranges_str = self.extract_page_ranges_var.get()

        if not input_pdf_path or not os.path.exists(input_pdf_path):
            self.extract_status_var.set("Error: Input PDF not selected or not found.")
            messagebox.showerror("Extraction Error", "Please select a valid input PDF file.", parent=self.tab_extract_text)
            return

        if not output_txt_path:
            self.extract_status_var.set("Error: Output .txt file path not specified.")
            messagebox.showerror("Extraction Error", "Please specify an output .txt file path.", parent=self.tab_extract_text)
            return

        output_dir = os.path.dirname(output_txt_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                self.extract_status_var.set(f"Error creating output directory: {e}")
                messagebox.showerror("Directory Error", f"Could not create directory: {output_dir}\n{e}", parent=self.tab_extract_text)
                return

        try:
            reader = PdfReader(input_pdf_path)
            num_pages = len(reader.pages)

            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                    self.shared_state.log("Extract Text Tab: PDF was encrypted, attempted decryption with empty password.")
                except Exception as e_decrypt:
                    self.extract_status_var.set(f"Warning: PDF is encrypted and decryption failed ({e_decrypt}). Text might be incomplete.")
                    self.shared_state.log(f"Extract Text Tab: PDF decryption failed: {e_decrypt}", "WARNING")

            # Parse page ranges
            page_indices = self._parse_page_ranges_for_extract(page_ranges_str, num_pages)
            if page_indices is None:
                self.extract_status_var.set("Error: Invalid page range format or out of bounds.")
                messagebox.showerror("Page Range Error", "Invalid page range format or out of bounds.", parent=self.tab_extract_text)
                return

            extracted_text_parts = []
            for idx, page_num in enumerate(page_indices):
                self.extract_status_var.set(f"Extracting text from page {page_num+1} ({idx+1}/{len(page_indices)})...")
                self.tab_extract_text.update_idletasks()
                try:
                    text = reader.pages[page_num].extract_text()
                    if text:
                        extracted_text_parts.append(text)
                except Exception as e_page_extract:
                    self.shared_state.log(f"Extract Text Tab: Error extracting text from page {page_num+1}: {e_page_extract}", "WARNING")
                    extracted_text_parts.append(f"[ERROR EXTRACTING PAGE {page_num+1}: {e_page_extract}]\n")

            full_text = "\n\n".join(extracted_text_parts)

            with open(output_txt_path, "w", encoding="utf-8") as output_file:
                output_file.write(full_text)

            final_message = f"Successfully extracted text to '{os.path.basename(output_txt_path)}'."
            if not full_text.strip():
                final_message += " (Note: No text content found in the PDF or PDF is image-based)."
            self.extract_status_var.set(final_message)
            messagebox.showinfo("Extraction Successful", final_message, parent=self.tab_extract_text)
            self.shared_state.log(f"Extract Text Tab: {final_message}")

        except Exception as e_extract:
            error_msg = f"Error during text extraction: {e_extract}"
            self.extract_status_var.set(error_msg)
            messagebox.showerror("Extraction Error", error_msg, parent=self.tab_extract_text)
            self.shared_state.log(f"Extract Text Tab: {error_msg}", "ERROR")

    def on_destroy(self):
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")

    def _select_input_pdf_to_image(self):
        filepath = filedialog.askopenfilename(
            title="Select Input PDF to Convert",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self.tab_to_image_pdf
        )
        if filepath:
            self.to_img_input_pdf_path_var.set(filepath)
            self.to_img_status_var.set(f"Selected: {os.path.basename(filepath)}")
            self.shared_state.log(f"To Image PDF Tab: Input PDF selected: {filepath}")
        else:
            self.to_img_status_var.set("Input PDF selection cancelled.")

    def _select_output_pdf_to_image(self):
        input_path = self.to_img_input_pdf_path_var.get()
        initial_name = "image_version.pdf"
        if input_path:
            base, ext = os.path.splitext(os.path.basename(input_path))
            initial_name = f"{base}_image{ext}"

        filepath = filedialog.asksaveasfilename(
            title="Save Image PDF As...",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=initial_name,
            parent=self.tab_to_image_pdf
        )
        if filepath:
            self.to_img_output_pdf_path_var.set(filepath)
            self.to_img_status_var.set(f"Output will be saved as: {os.path.basename(filepath)}")
            self.shared_state.log(f"To Image PDF Tab: Output path set to: {filepath}")
        else:
            self.to_img_status_var.set("Output PDF save location not set.")

    def _execute_convert_to_image_pdf(self):
        self.shared_state.log("To Image PDF Tab: Attempting to execute conversion.")
        self.to_img_status_var.set("Processing...")
        self.tab_to_image_pdf.update_idletasks()

        input_pdf_path = self.to_img_input_pdf_path_var.get()
        output_pdf_path = self.to_img_output_pdf_path_var.get()

        if not input_pdf_path or not os.path.exists(input_pdf_path):
            self.to_img_status_var.set("Error: Input PDF not selected or not found.")
            messagebox.showerror("Error", "Please select a valid input PDF file.", parent=self.tab_to_image_pdf)
            return

        if not output_pdf_path:
            self.to_img_status_var.set("Error: Output PDF file path not specified.")
            messagebox.showerror("Error", "Please specify an output file path.", parent=self.tab_to_image_pdf)
            return

        try:
            dpi = int(self.to_img_dpi_var.get())
            if dpi <= 0:
                raise ValueError("DPI must be a positive number.")
        except ValueError:
            self.to_img_status_var.set("Error: Invalid DPI. Please enter a positive number.")
            messagebox.showerror("Error", "Invalid DPI value. Please enter a positive integer.", parent=self.tab_to_image_pdf)
            return

        output_dir = os.path.dirname(output_pdf_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                self.to_img_status_var.set(f"Error creating output directory: {e}")
                messagebox.showerror("Directory Error", f"Could not create output directory: {output_dir}\n{e}", parent=self.tab_to_image_pdf)
                return

        # Prepare ReportLab Canvas for Output
        try:
            # Open input PDF with pypdfium2
            pdf = pdfium.PdfDocument(input_pdf_path)

            # Create a temporary canvas
            c = reportlab_canvas.Canvas(output_pdf_path)

            num_pages = len(pdf)
            for i in range(num_pages):
                self.to_img_status_var.set(f"Processing page {i + 1}/{num_pages}...")
                self.tab_to_image_pdf.update_idletasks()

                # Get page from pypdfium2
                page = pdf[i]

                # Render page to PIL image
                # Scale calculation: DPI / 72 (since PDF base unit is 1/72 inch)
                scale = dpi / 72.0
                bitmap = page.render(scale=scale)
                pil_image = bitmap.to_pil()

                # Get dimensions
                width, height = page.get_size() # In PDF points

                # Set page size for ReportLab
                c.setPageSize((width, height))

                # ReportLab draws images. We need to pass the PIL image.
                from reportlab.lib.utils import ImageReader

                img_reader = ImageReader(pil_image)

                # Draw the image covering the entire page
                c.drawImage(img_reader, 0, 0, width=width, height=height)

                c.showPage()

                # Cleanup bitmap to free memory
                bitmap.close()

            c.save()

            final_message = f"Successfully converted to image PDF: '{os.path.basename(output_pdf_path)}'."
            self.to_img_status_var.set(final_message)
            messagebox.showinfo("Conversion Successful", final_message, parent=self.tab_to_image_pdf)
            self.shared_state.log(f"To Image PDF Tab: {final_message}")

        except Exception as e:
            error_msg = f"An error occurred during conversion: {e}"
            self.to_img_status_var.set(error_msg)
            messagebox.showerror("Conversion Error", error_msg, parent=self.tab_to_image_pdf)
            self.shared_state.log(f"To Image PDF Tab: {error_msg}", "ERROR")


    def _select_split_output_folder(self):
        folder_selected = filedialog.askdirectory(
            title="Select Output Folder for Split PDFs",
            parent=self.tab_split
        )
        if folder_selected:
            self.split_output_folder_var.set(folder_selected)
            self.split_status_var.set(f"Output folder set: {folder_selected}")
            self.shared_state.log(f"Split Tab: Output folder selected: {folder_selected}")
        else:
            self.split_status_var.set("Output folder selection cancelled.")

    # --- Images to PDF Logic ---

    def _add_images_to_list(self):
        filepaths = filedialog.askopenfilenames(
            title="Select Images to Convert",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff"), ("All Files", "*.*")],
            parent=self.tab_images_to_pdf
        )
        if filepaths:
            added_count = 0
            for fp in filepaths:
                if fp not in self.img_file_paths:
                    self.img_file_paths.append(fp)
                    self.img_listbox.insert(tk.END, os.path.basename(fp))
                    added_count += 1
            self.img_status_var.set(f"Added {added_count} image(s). Total: {len(self.img_file_paths)}")
            self.shared_state.log(f"Img->PDF Tab: Added {added_count} images.")
        else:
            self.img_status_var.set("No images selected.")

    def _remove_selected_image(self):
        selected_indices = self.img_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select an image to remove.", parent=self.tab_images_to_pdf)
            return
        for index in sorted(selected_indices, reverse=True):
            self.img_listbox.delete(index)
            removed = self.img_file_paths.pop(index)
            self.shared_state.log(f"Img->PDF Tab: Removed {removed}")
        self.img_status_var.set(f"Removed {len(selected_indices)} image(s).")

    def _move_image_list_item(self, direction):
        selected_indices = self.img_listbox.curselection()
        if not selected_indices: return
        idx = selected_indices[0]
        if (direction == -1 and idx == 0) or (direction == 1 and idx == len(self.img_file_paths) - 1): return
        new_idx = idx + direction
        self.img_file_paths[idx], self.img_file_paths[new_idx] = self.img_file_paths[new_idx], self.img_file_paths[idx]
        self.img_listbox.delete(0, tk.END)
        for fp in self.img_file_paths:
            self.img_listbox.insert(tk.END, os.path.basename(fp))
        self.img_listbox.selection_set(new_idx)
        self.img_listbox.activate(new_idx)

    def _select_output_images_to_pdf(self):
        mode = self.img_output_mode_var.get()
        if mode == "merge":
            initial_name = "images_merged.pdf"
            if self.img_file_paths:
                base = os.path.splitext(os.path.basename(self.img_file_paths[0]))[0]
                count = len(self.img_file_paths)
                initial_name = f"{base}_{count}_images.pdf" if count > 1 else f"{base}.pdf"
            filepath = filedialog.asksaveasfilename(
                title="Save Merged PDF As...",
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")],
                initialfile=initial_name,
                parent=self.tab_images_to_pdf
            )
            if filepath:
                self.img_output_path_var.set(filepath)
                self.img_status_var.set(f"Output: {os.path.basename(filepath)}")
        else: # separate
            folderpath = filedialog.askdirectory(title="Select Output Folder", parent=self.tab_images_to_pdf)
            if folderpath:
                self.img_output_path_var.set(folderpath)
                self.img_status_var.set(f"Output Folder: {folderpath}")

    def _execute_images_to_pdf(self):
        if not self.img_file_paths:
            messagebox.showerror("Error", "No images selected.", parent=self.tab_images_to_pdf)
            return

        out_path = self.img_output_path_var.get()
        if not out_path:
            messagebox.showerror("Error", "Please select an output location.", parent=self.tab_images_to_pdf)
            return

        mode = self.img_output_mode_var.get()
        self.img_status_var.set("Converting...")
        self.tab_images_to_pdf.update_idletasks()

        try:
            images = []
            # Open images and convert to RGB
            for fp in self.img_file_paths:
                try:
                    img = Image.open(fp)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    self.shared_state.log(f"Img->PDF Tab: Failed to open image {fp}: {e}", "ERROR")
                    messagebox.showwarning("Image Error", f"Skipping invalid image: {os.path.basename(fp)}", parent=self.tab_images_to_pdf)

            if not images:
                self.img_status_var.set("Error: No valid images to process.")
                return

            if mode == "merge":
                images[0].save(out_path, save_all=True, append_images=images[1:])
                self.img_status_var.set("Success: Merged PDF created.")
                messagebox.showinfo("Success", f"Merged PDF saved to:\n{out_path}", parent=self.tab_images_to_pdf)
                self.shared_state.log(f"Img->PDF Tab: Merged {len(images)} images to {out_path}")
            else:
                count = 0
                for i, img in enumerate(images):
                     try:
                        # Find original path to get filename
                        # This works assuming images list and img_file_paths are synced index-wise BUT some might have been skipped.
                        # So we can't use 'i' directly mapping if failures happened.
                        # Safer to re-open or map correctly. 
                        # Given the snippet above: images.append(img) only on success.
                        # Ideally should keep tuples (img, filename).
                        pass
                     except: pass
                
                # Refined separate loop:
                count = 0
                for fp in self.img_file_paths:
                     try:
                        img = Image.open(fp)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        base_name = os.path.splitext(os.path.basename(fp))[0]
                        save_path = os.path.join(out_path, f"{base_name}.pdf")
                        img.save(save_path)
                        count += 1
                     except Exception as e:
                         self.shared_state.log(f"Img->PDF Tab: Failed to convert {fp}: {e}", "ERROR")
                
                self.img_status_var.set(f"Success: Converted {count} images.")
                messagebox.showinfo("Success", f"Converted {count} images to PDFs in:\n{out_path}", parent=self.tab_images_to_pdf)
                self.shared_state.log(f"Img->PDF Tab: Converted {count} images to separate PDFs.")

        except Exception as e:
            self.img_status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"Conversion failed: {e}", parent=self.tab_images_to_pdf)
            self.shared_state.log(f"Img->PDF Tab: Conversion error: {e}", "ERROR")

if __name__ == '__main__':
    # This section is for testing the module standalone if needed.
    # It requires a bit more setup to run a single module outside the main ModularGUI.
    root = tk.Tk()
    root.title("PDF Processor Module Test")
    root.geometry("600x400")

    # Mock SharedState for standalone testing
    class MockSharedState:
        def log(self, message, level="INFO"):
            print(f"[{level}] {message}")

    shared_state_mock = MockSharedState()

    # The module expects a master frame from the ModularGUI.
    # For standalone, we can just use the root window or a frame within it.
    module_frame = ttk.Frame(root, borderwidth=1, relief=tk.SOLID)
    module_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # Instantiate the module
    # Note: gui_manager would normally be an instance of ModularGUI
    app = PdfProcessorModule(master=module_frame, shared_state=shared_state_mock, gui_manager=None)

    # The Module class itself packs its internal frame (self.frame) into its master.
    # And Module.create_ui() populates self.frame.
    # The `app.frame` is already packed into `module_frame` by the Module's __init__ if master is correct.

    root.mainloop()
