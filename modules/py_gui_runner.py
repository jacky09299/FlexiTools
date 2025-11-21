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

        if self.gui_manager and hasattr(self.gui_manager, 'saves_dir'):
             self.scripts_dir = os.path.join(self.gui_manager.saves_dir, "py_gui_runners")
        else:
             self.scripts_dir = os.path.join("modules", "saves", "py_gui_runners")

        os.makedirs(self.scripts_dir, exist_ok=True)

        # Initialize widget references
        self.add_button = None
        self.delete_button = None
        self.select_button = None
        self.file_label = None
        self.inputs_frame = None
        self.output_frame = None
        self.run_button = None
        self.script_combo = None

        self.create_ui()
        self.update_language()

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

        self.add_button = ttk.Button(script_frame, text="Add to Pool", command=self.add_script_to_pool, state=tk.DISABLED)
        self.add_button.grid(row=0, column=0, padx=(0, 5))

        self.script_var = tk.StringVar()
        self.script_combo = ttk.Combobox(script_frame, textvariable=self.script_var, state="readonly")
        self.script_combo.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.script_combo.bind("<<ComboboxSelected>>", self.on_script_select)

        self.delete_button = ttk.Button(script_frame, text="Delete Selected", command=self.delete_selected_script)
        self.delete_button.grid(row=0, column=2, padx=(0, 5))
        
        self.populate_scripts_dropdown()

        # Top frame for file selection
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)

        self.select_button = ttk.Button(top_frame, text="Select External .py", command=self.select_file)
        self.select_button.grid(row=0, column=0, padx=(0, 10))

        self.file_label = ttk.Label(top_frame, text="No file selected", anchor="w")
        self.file_label.grid(row=0, column=1, sticky="ew")

        # Frame for dynamic input fields
        self.inputs_frame = ttk.LabelFrame(main_frame, text="Input Parameters", padding="10")
        self.inputs_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Frame for output
        self.output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        self.output_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.output_frame.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(self.output_frame, wrap=tk.WORD, state=tk.DISABLED, height=10)
        self.output_text.grid(row=0, column=0, sticky="nsew")

        # Bottom frame for execution button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)

        self.run_button = ttk.Button(bottom_frame, text="Run", command=self.run_script, state=tk.DISABLED)
        self.run_button.grid(row=0, column=0)

    def update_language(self):
        super().update_language()
        if not getattr(self, 'add_button', None): return

        self.add_button.config(text=self.tr("module_pyguirunner_btn_add", "Add to Pool"))
        self.delete_button.config(text=self.tr("module_pyguirunner_btn_delete", "Delete Selected"))
        self.select_button.config(text=self.tr("module_pyguirunner_btn_select", "Select External .py"))
        if self.file_label.cget("text") in ["No file selected", "尚未選擇檔案"]:
             self.file_label.config(text=self.tr("module_pyguirunner_lbl_no_file", "No file selected"))
        self.inputs_frame.config(text=self.tr("module_pyguirunner_grp_inputs", "Input Parameters"))
        self.output_frame.config(text=self.tr("module_pyguirunner_grp_output", "Output"))
        self.run_button.config(text=self.tr("module_pyguirunner_btn_run", "Run"))

        # Update dropdown placeholder if empty
        if not self.script_var.get() or self.script_var.get() in ["No scripts in pool", "程式組中沒有腳本"]:
             self.populate_scripts_dropdown() # Will refresh the "No scripts" message

    def add_script_to_pool(self):
        if not self.target_file or not self.is_external_script:
            messagebox.showwarning("Warning", self.tr("module_pyguirunner_msg_no_script", "Please select an external script file first."), parent=self.frame)
            return

        filename = os.path.basename(self.target_file)
        dest_path = os.path.join(self.scripts_dir, filename)

        if os.path.exists(dest_path):
            msg = self.tr("module_pyguirunner_msg_file_exists", "File '{0}' already exists in pool. Overwrite?").format(filename)
            if not messagebox.askyesno("Confirm", msg, parent=self.frame):
                return
        
        try:
            shutil.copy(self.target_file, dest_path)
            msg = self.tr("module_pyguirunner_msg_added", "Script '{0}' added successfully.").format(filename)
            messagebox.showinfo("Success", msg, parent=self.frame)
            
            self.target_file = dest_path
            self.is_external_script = False
            self.add_button.config(state=tk.DISABLED)
            
            self.populate_scripts_dropdown()
            self.script_var.set(filename)

        except Exception as e:
            msg = self.tr("module_pyguirunner_msg_copy_fail", "Failed to copy file to pool:\n{0}").format(e)
            messagebox.showerror("Error", msg, parent=self.frame)

    def populate_scripts_dropdown(self):
        try:
            scripts = [f for f in os.listdir(self.scripts_dir) if f.endswith(".py")]
            self.script_combo['values'] = sorted(scripts)
            if not scripts:
                self.script_var.set(self.tr("module_pyguirunner_lbl_no_scripts", "No scripts in pool"))
            else:
                if self.script_var.get() not in scripts:
                    self.script_var.set("")
        except Exception as e:
            self.shared_state.log(f"Error populating scripts dropdown: {e}")
            self.script_combo['values'] = []
            self.script_var.set("Error")

    def on_script_select(self, event=None):
        selected_script = self.script_var.get()
        no_scripts_msg = self.tr("module_pyguirunner_lbl_no_scripts", "No scripts in pool")
        if not selected_script or selected_script == no_scripts_msg:
            return
        
        self.is_external_script = False
        self.add_button.config(state=tk.DISABLED)
        filepath = os.path.join(self.scripts_dir, selected_script)
        self.load_script(filepath)

    def delete_selected_script(self):
        selected_script = self.script_var.get()
        no_scripts_msg = self.tr("module_pyguirunner_lbl_no_scripts", "No scripts in pool")
        if not selected_script or selected_script == no_scripts_msg:
            messagebox.showwarning("Warning", self.tr("module_pyguirunner_msg_select_first", "Please select a script first."), parent=self.frame)
            return

        msg = self.tr("module_pyguirunner_msg_confirm_delete", "Delete script '{0}'? Cannot be undone.").format(selected_script)
        if not messagebox.askyesno("Confirm", msg, parent=self.frame):
            return

        filepath = os.path.join(self.scripts_dir, selected_script)
        try:
            os.remove(filepath)
            msg = self.tr("module_pyguirunner_msg_deleted", "Script '{0}' deleted.").format(selected_script)
            messagebox.showinfo("Success", msg, parent=self.frame)
            self.populate_scripts_dropdown()
            self.target_file = ""
            self.file_label.config(text=self.tr("module_pyguirunner_lbl_no_file", "No file selected"))
            self.add_button.config(state=tk.DISABLED)
            self.is_external_script = False
            self.run_button.config(state=tk.DISABLED)
            for widget in self.inputs_frame.winfo_children():
                widget.destroy()
            self.input_widgets.clear()
            self.script_var.set("")
        except Exception as e:
            msg = self.tr("module_pyguirunner_msg_delete_fail", "Could not delete file:\n{0}").format(e)
            messagebox.showerror("Error", msg, parent=self.frame)

    def select_file(self):
        filepath = filedialog.askopenfilename(
            title=self.tr("module_pyguirunner_btn_select", "Select External .py"),
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
                ttk.Label(self.inputs_frame, text="No input parameters detected.").pack(pady=5)
                self.run_button.config(state=tk.NORMAL)
            else:
                for prompt in prompts:
                    self._create_input_widget(prompt)
                self.run_button.config(state=tk.NORMAL)

        except Exception as e:
            msg = self.tr("module_pyguirunner_msg_read_error", "Failed to read or parse file:\n{0}").format(e)
            messagebox.showerror("Error", msg, parent=self.frame)
            self.file_label.config(text="Error")
            self.add_button.config(state=tk.DISABLED)
            self.is_external_script = False

    def _create_input_widget(self, prompt):
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
                    type_name = f"{', '.join(ext.upper() for ext in extensions)} Files"
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
        widget_frame = ttk.Frame(parent)
        widget_frame.grid(row=0, column=1, sticky="ew")
        widget_frame.columnconfigure(0, weight=1)

        entry = ttk.Entry(widget_frame, state="readonly")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        button_text = self.tr("module_pyguirunner_btn_select_folder", "Select Folder") if dialog_type == "folder" else self.tr("module_pyguirunner_btn_select_file", "Select File")
        command = lambda e=entry, f=filetypes: self._open_dialog(e, dialog_type, f)
        
        browse_button = ttk.Button(widget_frame, text=button_text, command=command)
        browse_button.grid(row=0, column=1)
        
        return entry

    def _open_dialog(self, entry_widget, dialog_type, filetypes=None):
        path = ""
        if dialog_type == "file":
            path = filedialog.askopenfilename(title="Select File", filetypes=filetypes, parent=self.frame)
        elif dialog_type == "folder":
            path = filedialog.askdirectory(title="Select Folder", parent=self.frame)
        
        if path:
            entry_widget.config(state="normal")
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)
            entry_widget.config(state="readonly")


    def run_script(self):
        if not self.target_file:
            messagebox.showwarning("Warning", self.tr("module_pyguirunner_msg_no_file", "Please select a .py file first."), parent=self.frame)
            return

        self.run_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"Running {os.path.basename(self.target_file)}...\n\n")
        self.output_text.config(state=tk.DISABLED)

        inputs = [widget.get() for widget, _ in self.input_widgets]
        input_string = "\n".join(inputs)

        thread = threading.Thread(target=self._execute_in_thread, args=(self.target_file, input_string))
        thread.daemon = True
        thread.start()

    def _execute_in_thread(self, filepath, input_data):
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
                full_output = "Process finished with no output."

        except FileNotFoundError:
            full_output = f"Error: Interpreter '{sys.executable}' or script '{os.path.basename(filepath)}' not found."
        except Exception as e:
            full_output = f"Unexpected error during execution:\n{e}"

        self.master.after(0, self._update_output, full_output)

    def _update_output(self, result):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, result)
        self.output_text.config(state=tk.DISABLED)
        self.run_button.config(state=tk.NORMAL)

    def on_destroy(self):
        self.shared_state.log(f"PyGuiRunner '{self.module_name}' is being destroyed.")
        super().on_destroy()