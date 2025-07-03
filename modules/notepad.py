import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class NotepadModule(Module):
    def __init__(self, master, shared_state, module_name="Notepad", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.text_area = None
        self.current_file_path = None
        self.create_ui()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Main content frame should allow text_area to expand
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)
        content_frame.rowconfigure(1, weight=1) # Text area row
        content_frame.columnconfigure(0, weight=1) # Text area column

        # Button bar
        button_bar = ttk.Frame(content_frame)
        button_bar.grid(row=0, column=0, sticky="ew", pady=(0,5))

        open_button = ttk.Button(button_bar, text="Open", command=self.open_file)
        open_button.pack(side=tk.LEFT, padx=(0,5))

        save_button = ttk.Button(button_bar, text="Save", command=self.save_file)
        save_button.pack(side=tk.LEFT, padx=(0,5))

        save_as_button = ttk.Button(button_bar, text="Save As...", command=self.save_file_as)
        save_as_button.pack(side=tk.LEFT)

        # Text Area with Scrollbars
        text_frame = ttk.Frame(content_frame) # Frame to hold text and scrollbars
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.text_area = tk.Text(text_frame, wrap=tk.WORD, undo=True, borderwidth=0) # borderwidth 0 for Text if frame has it
        self.text_area.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar
        v_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.text_area.config(yscrollcommand=v_scroll.set)

        # Horizontal scrollbar (optional, but good for plain text)
        h_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.text_area.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.text_area.config(xscrollcommand=h_scroll.set, wrap=tk.NONE) # Use tk.NONE for horizontal scroll

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)
        self._update_title()


    def _update_title(self):
        base_name = "Notepad"
        if self.current_file_path:
            file_name = os.path.basename(self.current_file_path)
            self.title_label.config(text=f"{base_name} - {file_name}")
        else:
            self.title_label.config(text=f"{base_name} - Untitled")


    def open_file(self):
        # Consider asking to save current changes if any
        # For simplicity, this version will discard unsaved changes on open.
        filepath = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            parent=self.frame
        )
        if filepath:
            try:
                with open(filepath, "r", encoding='utf-8') as f:
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert("1.0", f.read())
                self.current_file_path = filepath
                self._update_title()
                self.shared_state.log(f"Opened file: {filepath}", level=logging.INFO)
            except Exception as e:
                messagebox.showerror("Error Opening File", f"Could not open file: {e}", parent=self.frame)
                self.shared_state.log(f"Error opening file {filepath}: {e}", level=logging.ERROR)

    def save_file(self):
        if self.current_file_path:
            try:
                with open(self.current_file_path, "w", encoding='utf-8') as f:
                    f.write(self.text_area.get("1.0", tk.END).strip()) # Use strip to remove trailing newline often added by Text widget
                self.shared_state.log(f"Saved file: {self.current_file_path}", level=logging.INFO)
            except Exception as e:
                messagebox.showerror("Error Saving File", f"Could not save file: {e}", parent=self.frame)
                self.shared_state.log(f"Error saving file {self.current_file_path}: {e}", level=logging.ERROR)
        else:
            self.save_file_as() # If no current path, prompt for one

    def save_file_as(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="Untitled.txt" if not self.current_file_path else os.path.basename(self.current_file_path),
            parent=self.frame
        )
        if filepath:
            try:
                with open(filepath, "w", encoding='utf-8') as f:
                    f.write(self.text_area.get("1.0", tk.END).strip())
                self.current_file_path = filepath
                self._update_title()
                self.shared_state.log(f"Saved file as: {filepath}", level=logging.INFO)
            except Exception as e:
                messagebox.showerror("Error Saving File", f"Could not save file: {e}", parent=self.frame)
                self.shared_state.log(f"Error saving file as {filepath}: {e}", level=logging.ERROR)

    def on_destroy(self):
        # Could add a "do you want to save changes?" dialog here if text_area is modified
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
