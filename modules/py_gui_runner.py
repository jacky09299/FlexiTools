import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import re
import subprocess
import sys
import threading
from main import Module

class PyGuiRunner(Module):
    def __init__(self, master, shared_state, module_name="Py GUI Runner", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"PyGuiRunner '{self.module_name}' initialized.")
        self.target_file = ""
        self.input_entries = []
        self.create_ui()

    def create_ui(self):
        """Create the user interface for the module."""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Top frame for file selection
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)

        select_button = ttk.Button(top_frame, text="選擇 .py 檔案", command=self.select_file)
        select_button.grid(row=0, column=0, padx=(0, 10))

        self.file_label = ttk.Label(top_frame, text="尚未選擇檔案", anchor="w")
        self.file_label.grid(row=0, column=1, sticky="ew")

        # Frame for dynamic input fields
        self.inputs_frame = ttk.LabelFrame(main_frame, text="輸入參數", padding="10")
        self.inputs_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Frame for output
        output_frame = ttk.LabelFrame(main_frame, text="輸出結果", padding="10")
        output_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED, height=10)
        self.output_text.grid(row=0, column=0, sticky="nsew")

        # Bottom frame for execution button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1) # Center the button

        self.run_button = ttk.Button(bottom_frame, text="執行", command=self.run_script, state=tk.DISABLED)
        self.run_button.grid(row=0, column=0)

    def select_file(self):
        """Open a file dialog to select a .py file and parse it for input() calls."""
        filepath = filedialog.askopenfilename(
            title="選擇一個 Python 檔案",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not filepath:
            return

        self.target_file = filepath
        self.file_label.config(text=os.path.basename(filepath))
        self.run_button.config(state=tk.DISABLED)

        # Clear previous input fields
        for widget in self.inputs_frame.winfo_children():
            widget.destroy()
        self.input_entries.clear()

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all input prompts
            prompts = re.findall(r'input\s*\(\s*["\'](.*?)["\']\s*\)', content)

            if not prompts:
                ttk.Label(self.inputs_frame, text="此程式不需輸入參數。").pack(pady=5)
                self.run_button.config(state=tk.NORMAL)
            else:
                for i, prompt in enumerate(prompts):
                    row_frame = ttk.Frame(self.inputs_frame)
                    row_frame.pack(fill=tk.X, pady=2)

                    label = ttk.Label(row_frame, text=prompt, width=20, anchor="w")
                    label.pack(side=tk.LEFT, padx=(0, 5))

                    entry = ttk.Entry(row_frame)
                    entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
                    self.input_entries.append(entry)

                self.run_button.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("讀取錯誤", f"無法讀取或解析檔案：\n{e}", parent=self.frame)
            self.file_label.config(text="檔案讀取失敗")

    def run_script(self):
        """Execute the selected script with inputs from the entry fields."""
        if not self.target_file:
            messagebox.showwarning("沒有檔案", "請先選擇一個 .py 檔案。", parent=self.frame)
            return

        # 1. Disable UI elements
        self.run_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"正在執行 {os.path.basename(self.target_file)}...\n\n")
        self.output_text.config(state=tk.DISABLED)

        # 2. Get inputs from entries
        inputs = [entry.get() for entry in self.input_entries]
        input_string = "\n".join(inputs)

        # 3. Run the script in a separate thread
        thread = threading.Thread(target=self._execute_in_thread, args=(self.target_file, input_string))
        thread.daemon = True
        thread.start()

    def _execute_in_thread(self, filepath, input_data):
        """The actual subprocess execution, run in a thread."""
        try:
            # 6. Use sys.executable and subprocess.run
            process = subprocess.run(
                [sys.executable, filepath],
                input=input_data,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False  # Don't raise exception for non-zero exit codes
            )
            output = process.stdout
            error = process.stderr

            # Combine output and error for display
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

        # Schedule the UI update on the main thread
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
