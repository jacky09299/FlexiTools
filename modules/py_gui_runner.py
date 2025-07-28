import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import re
import subprocess
import sys
import threading
import shutil
from main import Module

class PyGuiRunner(Module):
    def __init__(self, master, shared_state, module_name="Py GUI Runner", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"PyGuiRunner '{self.module_name}' initialized.")
        self.target_file = ""
        self.is_external_script = False
        self.input_widgets = []
        self.scripts_dir = os.path.join("modules", "saves", "py_gui_runners")
        os.makedirs(self.scripts_dir, exist_ok=True)
        self.create_ui()

    def create_ui(self):
        """Create the user interface for the module."""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Top frame for script management
        script_frame = ttk.Frame(main_frame)
        script_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        script_frame.columnconfigure(1, weight=1)

        self.add_button = ttk.Button(script_frame, text="加入程式組", command=self.add_script_to_pool, state=tk.DISABLED)
        self.add_button.grid(row=0, column=0, padx=(0, 5))

        self.script_var = tk.StringVar()
        self.script_combo = ttk.Combobox(script_frame, textvariable=self.script_var, state="readonly")
        self.script_combo.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.script_combo.bind("<<ComboboxSelected>>", self.on_script_select)

        delete_button = ttk.Button(script_frame, text="刪除選定", command=self.delete_selected_script)
        delete_button.grid(row=0, column=2, padx=(0, 5))
        
        self.populate_scripts_dropdown()

        # Top frame for file selection
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)

        select_button = ttk.Button(top_frame, text="選擇外部 .py 檔案", command=self.select_file)
        select_button.grid(row=0, column=0, padx=(0, 10))

        self.file_label = ttk.Label(top_frame, text="尚未選擇檔案", anchor="w")
        self.file_label.grid(row=0, column=1, sticky="ew")

        # Frame for dynamic input fields
        self.inputs_frame = ttk.LabelFrame(main_frame, text="輸入參數", padding="10")
        self.inputs_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Frame for output
        output_frame = ttk.LabelFrame(main_frame, text="輸出結果", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED, height=10)
        self.output_text.grid(row=0, column=0, sticky="nsew")

        # Bottom frame for execution button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)

        self.run_button = ttk.Button(bottom_frame, text="執行", command=self.run_script, state=tk.DISABLED)
        self.run_button.grid(row=0, column=0)

    def add_script_to_pool(self):
        """Adds the currently loaded external script to the scripts directory."""
        if not self.target_file or not self.is_external_script:
            messagebox.showwarning("沒有外部腳本", "請先選擇一個外部腳本檔案。", parent=self.frame)
            return

        filename = os.path.basename(self.target_file)
        dest_path = os.path.join(self.scripts_dir, filename)

        if os.path.exists(dest_path):
            if not messagebox.askyesno("檔案已存在", f"檔案 '{filename}' 已存在於程式組中。要覆蓋它嗎？", parent=self.frame):
                return
        
        try:
            shutil.copy(self.target_file, dest_path)
            messagebox.showinfo("成功", f"腳本 '{filename}' 已成功加入。", parent=self.frame)
            
            self.target_file = dest_path
            self.is_external_script = False
            self.add_button.config(state=tk.DISABLED)
            
            self.populate_scripts_dropdown()
            self.script_var.set(filename)

        except Exception as e:
            messagebox.showerror("複製失敗", f"無法將檔案複製到程式組資料夾：\n{e}", parent=self.frame)

    def populate_scripts_dropdown(self):
        """Scans the scripts directory and populates the dropdown."""
        try:
            scripts = [f for f in os.listdir(self.scripts_dir) if f.endswith(".py")]
            self.script_combo['values'] = sorted(scripts)
            if not scripts:
                self.script_var.set("程式組中沒有腳本")
            else:
                if self.script_var.get() not in scripts:
                    self.script_var.set("")
        except Exception as e:
            self.shared_state.log(f"Error populating scripts dropdown: {e}")
            self.script_combo['values'] = []
            self.script_var.set("讀取腳本失敗")

    def on_script_select(self, event=None):
        """Handles the selection of a script from the dropdown."""
        selected_script = self.script_var.get()
        if not selected_script or selected_script == "程式組中沒有腳本":
            return
        
        self.is_external_script = False
        self.add_button.config(state=tk.DISABLED)
        filepath = os.path.join(self.scripts_dir, selected_script)
        self.load_script(filepath)

    def delete_selected_script(self):
        """Deletes the currently selected script from the pool."""
        selected_script = self.script_var.get()
        if not selected_script or selected_script == "程式組中沒有腳本":
            messagebox.showwarning("沒有選擇", "請先從下拉清單中選擇一個腳本。", parent=self.frame)
            return

        if not messagebox.askyesno("確認刪除", f"您確定要刪除腳本 '{selected_script}' 嗎？此操作無法復原。", parent=self.frame):
            return

        filepath = os.path.join(self.scripts_dir, selected_script)
        try:
            os.remove(filepath)
            messagebox.showinfo("成功", f"腳本 '{selected_script}' 已被刪除。", parent=self.frame)
            self.populate_scripts_dropdown()
            self.target_file = ""
            self.file_label.config(text="尚未選擇檔案")
            self.add_button.config(state=tk.DISABLED)
            self.is_external_script = False
            self.run_button.config(state=tk.DISABLED)
            for widget in self.inputs_frame.winfo_children():
                widget.destroy()
            self.input_widgets.clear()
            self.script_var.set("")
        except Exception as e:
            messagebox.showerror("刪除失敗", f"無法刪除檔案：\n{e}", parent=self.frame)

    def select_file(self):
        """Open a file dialog to select an external .py file."""
        filepath = filedialog.askopenfilename(
            title="選擇一個 Python 檔案",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            parent=self.frame
        )
        if not filepath:
            return
        
        self.script_var.set("")
        self.is_external_script = True
        self.add_button.config(state=tk.NORMAL)
        self.load_script(filepath)

    def load_script(self, filepath):
        """Loads and parses a script file to generate the UI for inputs."""
        self.target_file = filepath
        self.file_label.config(text=os.path.basename(filepath))
        self.run_button.config(state=tk.DISABLED)

        for widget in self.inputs_frame.winfo_children():
            widget.destroy()
        self.input_widgets.clear()

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            prompts = re.findall(r'input\s*\(\s*["\\](.*?)["\\]\s*\)', content)

            if not prompts:
                ttk.Label(self.inputs_frame, text="此程式不需輸入參數。").pack(pady=5)
                self.run_button.config(state=tk.NORMAL)
            else:
                for prompt in prompts:
                    self._create_input_widget(prompt)
                self.run_button.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("讀取錯誤", f"無法讀取或解析檔案：\n{e}", parent=self.frame)
            self.file_label.config(text="檔案讀取失敗")
            self.add_button.config(state=tk.DISABLED)
            self.is_external_script = False

    def _create_input_widget(self, prompt):
        """Creates an appropriate input widget based on the prompt text."""
        row_frame = ttk.Frame(self.inputs_frame)
        row_frame.pack(fill=tk.X, pady=2, expand=True)
        row_frame.columnconfigure(1, weight=1)

        label = ttk.Label(row_frame, text=prompt, anchor="w")
        label.grid(row=0, column=0, padx=(0, 5), sticky="w")

        file_keywords = ['檔名', '檔案', 'file', 'filename', 'path', '路徑', '選擇', '載入', '讀取', '儲存']
        folder_keywords = ['資料夾', 'folder', 'directory', '目錄', '資料目錄']
        prompt_lower = prompt.lower()

        if any(keyword in prompt_lower for keyword in folder_keywords):
            widget = self._create_dialog_widget(row_frame, "folder")
            self.input_widgets.append((widget, "path"))
            return

        ext_match = re.search(r'\(\s*([.\w\s,*/]+)\s*\)', prompt)
        if any(keyword in prompt_lower for keyword in file_keywords) or ext_match:
            filetypes = []
            if ext_match:
                extensions = re.findall(r'(\.?\w+)', ext_match.group(1))
                if extensions:
                    type_name = f"{', '.join(ext.upper() for ext in extensions)} 檔案"
                    patterns = [f"*{ext}" if not ext.startswith('.') else f"*{ext}" for ext in extensions]
                    filetypes.append((type_name, " ".join(patterns)))
            filetypes.append(("All files", "*.*"))

            widget = self._create_dialog_widget(row_frame, "file", filetypes=filetypes)
            self.input_widgets.append((widget, "path"))
            return

        entry = ttk.Entry(row_frame)
        entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.input_widgets.append((entry, "entry"))


    def _create_dialog_widget(self, parent, dialog_type, filetypes=None):
        """Helper to create a frame with an entry and a browse button."""
        widget_frame = ttk.Frame(parent)
        widget_frame.grid(row=0, column=1, sticky="ew")
        widget_frame.columnconfigure(0, weight=1)

        entry = ttk.Entry(widget_frame, state="readonly")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        button_text = "選擇資料夾" if dialog_type == "folder" else "選擇檔案"
        command = lambda e=entry, f=filetypes: self._open_dialog(e, dialog_type, f)
        
        browse_button = ttk.Button(widget_frame, text=button_text, command=command)
        browse_button.grid(row=0, column=1)
        
        return entry

    def _open_dialog(self, entry_widget, dialog_type, filetypes=None):
        """Opens a file or folder dialog and updates the entry widget."""
        path = ""
        if dialog_type == "file":
            path = filedialog.askopenfilename(title="選擇檔案", filetypes=filetypes, parent=self.frame)
        elif dialog_type == "folder":
            path = filedialog.askdirectory(title="選擇資料夾", parent=self.frame)
        
        if path:
            entry_widget.config(state="normal")
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)
            entry_widget.config(state="readonly")


    def run_script(self):
        """Execute the selected script with inputs from the entry fields."""
        if not self.target_file:
            messagebox.showwarning("沒有檔案", "請先選擇一個 .py 檔案。", parent=self.frame)
            return

        self.run_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"正在執行 {os.path.basename(self.target_file)}...\n\n")
        self.output_text.config(state=tk.DISABLED)

        inputs = [widget.get() for widget, _ in self.input_widgets]
        input_string = "\n".join(inputs)

        thread = threading.Thread(target=self._execute_in_thread, args=(self.target_file, input_string))
        thread.daemon = True
        thread.start()

    def _execute_in_thread(self, filepath, input_data):
        """The actual subprocess execution, run in a thread."""
        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            process = subprocess.run(
                [sys.executable, filepath],
                input=input_data,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
                env=env
            )
            output = process.stdout
            error = process.stderr

            full_output = ""
            if output:
                full_output += "--- STDOUT ---\n"
                full_output += output
            if error:
                full_output += "\n--- STDERR ---\n"
                full_output += error

            if not full_output.strip():
                full_output = "程式執行完畢，沒有任何輸出。"

        except FileNotFoundError:
            full_output = f"錯誤：找不到直譯器 '{sys.executable}' 或腳本 '{os.path.basename(filepath)}'。"
        except Exception as e:
            full_output = f"執行期間發生未預期的錯誤：\n{e}"

        self.master.after(0, self._update_output, full_output)

    def _update_output(self, result):
        """Update the output text area and re-enable the run button."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, result)
        self.output_text.config(state=tk.DISABLED)
        self.run_button.config(state=tk.NORMAL)

    def on_destroy(self):
        """Cleanup resources when the module is closed."""
        self.shared_state.log(f"PyGuiRunner '{self.module_name}' is being destroyed.")
        super().on_destroy()