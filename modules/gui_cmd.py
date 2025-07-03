import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import subprocess
import os
import sys
import queue
import re
# Removed filedialog import from here as it's already imported above with messagebox
from main import Module

# Windows signal constants (避免 subprocess 沒有定義)
if os.name == "nt":
    CTRL_C_EVENT = 0
    CTRL_BREAK_EVENT = 1

class CMDModule(Module):
    def __init__(self, master, shared_state, module_name="CMD Emulator", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        # Initialize attributes that were in the old __init__ here, if they are needed before create_ui
        self.process = None
        self.command_history = []
        self.history_index = -1
        self.output_queue = queue.Queue()
        self.is_running = True # Will be set to False in on_destroy

        self.envs = [] # Will be populated in create_ui
        self.selected_env = tk.StringVar() # Will be set in create_ui

        self.create_ui()

    def create_ui(self):
        # All widget creation and packing logic moved here
        self.main_frame = tk.Frame(self.frame, bg='black') # Parent is self.frame
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area = scrolledtext.ScrolledText(
            self.main_frame,
            bg='black',
            fg='#00ff00',
            font=('Consolas', 11),
            insertbackground='white',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        self.command_entry = tk.Entry(
            self.main_frame,
            bg='black',
            fg='white',
            font=('Consolas', 11),
            insertbackground='white',
            relief=tk.FLAT,
            bd=0
        )
        self.command_entry.pack(fill=tk.X, pady=(5, 0))
        self.command_entry.bind('<Return>', self.execute_command)
        self.command_entry.bind('<Up>', self.history_up)
        self.command_entry.bind('<Down>', self.history_down)
        self.command_entry.focus_set()

        self.button_frame = tk.Frame(self.main_frame, bg='black')
        self.button_frame.pack(fill=tk.X, pady=(5, 0))

        self.deactivate_btn = tk.Button(
            self.button_frame, text="切換為正常CMD",
            command=self.conda_deactivate,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.deactivate_btn.pack(side=tk.LEFT, padx=5)

        self.activate_btn = tk.Button(
            self.button_frame, text="切換為Conda(base)",
            command=self.conda_activate_base,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.activate_btn.pack(side=tk.LEFT, padx=5)

        self.envs = self.detect_conda_envs()
        self.selected_env = tk.StringVar()
        if self.envs:
            self.selected_env.set(self.envs[0])
        else:
            self.selected_env.set('base') # Default if no envs detected

        self.env_menu = tk.OptionMenu(
            self.button_frame, self.selected_env, *(self.envs if self.envs else ['base'])
        )
        self.env_menu.config(bg='#222', fg='white', font=('Consolas', 10))
        self.env_menu.pack(side=tk.LEFT, padx=5)

        self.activate_env_btn = tk.Button(
            self.button_frame, text="切換",
            command=self.conda_activate_selected,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.activate_env_btn.pack(side=tk.LEFT, padx=5)

        self.cd_btn = tk.Button(
            self.button_frame, text="切換目錄",
            command=self.change_directory,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.cd_btn.pack(side=tk.LEFT, padx=5)

        # 新增：執行Python檔案按鈕
        self.run_py_btn = tk.Button(
            self.button_frame, text="執行Python檔",
            command=self.run_python_file,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.run_py_btn.pack(side=tk.LEFT, padx=5)

        # 新增：安裝Conda環境按鈕
        self.create_env_btn = tk.Button(
            self.button_frame, text="安裝Conda環境",
            command=self.open_create_env_dialog,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.create_env_btn.pack(side=tk.LEFT, padx=5)

        # 新增：強制結束指令按鈕
        self.force_terminate_btn = tk.Button(
            self.button_frame, text="強制結束指令",
            command=self.force_terminate_command,
            bg='#a00', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.force_terminate_btn.pack(side=tk.LEFT, padx=5)
        
        self.init_cmd_process()
        self.start_output_threads()
        
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing) # Removed
        
        self.append_output("=== CMD Emulator Module Loaded ===\n")
        self.append_output("Supports conda, python, cd, dir and all other native commands.\n\n")

    def init_cmd_process(self):
        try:
            # 設定環境變數，確保 conda 可以被找到
            # 這一步很重要，特別是如果 conda 不在系統預設的 PATH 中
            env = os.environ.copy()
            # 如果你的 conda 不在預設路徑，可能需要手動添加 conda 的 Scripts 路徑
            # 例如: env['PATH'] = 'C:\\path\\to\\anaconda3\\Scripts;' + env['PATH']
            
            self.process = subprocess.Popen(
                ['cmd.exe'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
                text=True,
                encoding='utf-8', # 明確指定編碼
                errors='replace', # 處理潛在的編碼錯誤
                bufsize=1,  # 行緩衝
                cwd=os.getcwd(), # Consider using a configurable initial directory
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                env=env
            )
            # 啟動時發送一個 enter，讓初始提示符顯示出來
            self.process.stdin.write('\n')
            self.process.stdin.flush()

        except Exception as e:
            # Use append_output for errors if GUI is already partially set up
            self.append_output(f"Error: Could not start CMD process: {str(e)}\n")
            if self.master: # If master exists, it means UI might be there
                messagebox.showerror("Error", f"Could not start CMD process: {str(e)}")
            # sys.exit(1) # Avoid exiting the whole app
            # self.master.destroy() # Avoid destroying the main window directly
    
    def start_output_threads(self):
        if hasattr(self, 'output_thread') and self.output_thread.is_alive():
            # Avoid starting multiple threads if this method is called again
            return
        self.output_thread = threading.Thread(target=self.read_output, daemon=True)
        self.output_thread.start()
        
        if hasattr(self, 'display_thread') and self.display_thread.is_alive():
            # Avoid starting multiple threads
            return
        self.display_thread = threading.Thread(target=self.process_output, daemon=True)
        self.display_thread.start()
    
    def read_output(self):
        # 使用 iter 來讀取輸出，這比 read(1) 更高效且不易出錯
        try:
            if not self.process or not self.process.stdout:
                return
            for char in iter(lambda: self.process.stdout.read(1), ''):
                if not self.is_running:
                    break
                self.output_queue.put(char)
        except Exception as e: # Can include ValueError if stdout is closed
            if self.is_running:
                # Using print for thread-internal errors, or log to a file
                print(f"Error reading CMD output: {e}")

    def process_output(self):
        """處理輸出隊列，不再進行複雜的清理"""
        while self.is_running:
            try:
                # 從隊列中一次性獲取所有可用數據，減少 GUI 更新次數
                output_chunk = self.output_queue.get(block=True, timeout=0.1) # block with timeout
                while not self.output_queue.empty():
                    try:
                        output_chunk += self.output_queue.get_nowait() # non-blocking
                    except queue.Empty:
                        break # Should not happen if not empty, but good practice
                
                if output_chunk:
                    # --- [修改 2] 簡化清理邏輯 ---
                    # 我們只做最基本的清理，不再過濾提示符
                    cleaned_output = self.clean_output(output_chunk)
                    self.append_output(cleaned_output) # This will use self.master.after
                    
            except queue.Empty:
                continue # Timeout occurred, loop again
            except Exception as e:
                if self.is_running:
                    print(f"Error processing CMD output: {e}")
                break # Exit thread on other exceptions
    
    # --- [修改 3] 大幅簡化 clean_output ---
    def clean_output(self, output):
        """只進行最基本的清理，例如統一換行符"""
        # cmd.exe 在互動模式下通常使用 \r\n，但有時也可能混雜其他東西
        # 我們把 \r\n 轉成 \n，並移除單獨的 \r
        output = output.replace('\r\n', '\n')
        output = output.replace('\r', '')
        return output
    
    def append_output(self, text):
        # Ensure text_area is available and master is valid
        if not hasattr(self, 'text_area') or not self.master:
            print("Debug (append_output): text_area or master not available yet.")
            return

        def update_text():
            if not self.is_running: # Check if we are shutting down
                 return
            try:
                self.text_area.config(state=tk.NORMAL)
                self.text_area.insert(tk.END, text)
                self.text_area.see(tk.END)
                self.text_area.config(state=tk.DISABLED)
            except tk.TclError as e:
                # This can happen if the widget is destroyed
                if self.is_running:
                    print(f"TclError in append_output: {e}")

        # Always use `self.master.after` for thread safety with Tkinter
        # self.master refers to the root Tk window of the main application
        self.master.after(0, update_text)
    
    # --- [修改 4] 移除 update_prompt 方法，不再需要 ---
    
    def execute_command(self, event):
        command = self.command_entry.get().strip()
        if not command:
            # 如果用戶只按 enter，我們也發送一個換行符到 cmd
            # 這樣可以觸發 cmd 顯示一個新的提示符，體驗更流暢
            if self.process and self.process.poll() is None:
                self.process.stdin.write('\n')
                self.process.stdin.flush()
            return
        
        if command not in self.command_history:
            self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        self.command_entry.delete(0, tk.END)
        
        # --- [修改 5] 不再手動顯示 "prompt + command" ---
        # cmd.exe 自己會回顯(echo)命令，我們不需要再畫蛇添足。
        # self.append_output(f"{prompt} {command}\n") # <--- 移除此行
        
        try:
            if self.process and self.process.poll() is None:
                self.process.stdin.write(command + '\n')
                self.process.stdin.flush()
                
                # --- [修改 6] 移除對 'cd' 的特殊處理，不再需要 ---
            else:
                self.append_output("\n錯誤: CMD 進程未運行。正在嘗試重啟...\n")
                self.restart_cmd_process()
        except Exception as e:
            self.append_output(f"\n命令執行錯誤: {str(e)}\n")
            self.restart_cmd_process()
    
    def restart_cmd_process(self):
        try:
            if self.process:
                self.process.terminate()
            self.init_cmd_process()
            self.append_output("\n=== CMD 進程已重啟 ===\n")
        except Exception as e:
            self.append_output(f"重啟進程失敗: {str(e)}\n")
    
    def history_up(self, event):
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.history_index])
    
    def history_down(self, event):
        if self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_entry.delete(0, tk.END)
                self.command_entry.insert(0, self.command_history[self.history_index])
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.command_entry.delete(0, tk.END)
    
    # --- 新增: 按鈕事件處理 ---
    def conda_deactivate(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write('conda deactivate\n')
                self.process.stdin.flush()
            except Exception as e:
                self.append_output(f"\n執行 conda deactivate 時出錯: {str(e)}\n")
                self.restart_cmd_process()

    def conda_activate_base(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write('conda activate base\n')
                self.process.stdin.flush()
            except Exception as e:
                self.append_output(f"\n執行 conda activate base 時出錯: {str(e)}\n")
                self.restart_cmd_process()

    # --- 新增: 偵測 conda 環境 ---
    def detect_conda_envs(self):
        try:
            # 只取名稱欄位
            result = subprocess.run(
                ['conda', 'env', 'list'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            envs = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # 解析格式: env_name [*] path
                m = re.match(r'^([^\s*]+)', line)
                if m:
                    envs.append(m.group(1))
            # base 環境優先
            if 'base' in envs:
                envs.remove('base')
                envs.insert(0, 'base')
            return envs if envs else ['base']
        except Exception as e:
            return ['base']

    # --- 新增: 切換到選擇的 conda 環境 ---
    def conda_activate_selected(self):
        env = self.selected_env.get()
        if env:
            if self.process and self.process.poll() is None:
                try:
                    self.process.stdin.write(f'conda activate {env}\n')
                    self.process.stdin.flush()
                except Exception as e:
                    self.append_output(f"\n執行 conda activate {env} 時出錯: {str(e)}\n")
                    self.restart_cmd_process()

    # --- 新增: 切換目錄功能 ---
    def change_directory(self):
        folder = filedialog.askdirectory(title="選擇目錄")
        if folder:
            if self.process and self.process.poll() is None:
                try:
                    self.process.stdin.write(f'cd /d "{folder}"\n')
                    self.process.stdin.flush()
                except Exception as e:
                    self.append_output(f"\n切換目錄時出錯: {str(e)}\n")
                    self.restart_cmd_process()

    # 新增：彈出建立Conda環境的對話框
    def open_create_env_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("建立Conda環境")
        dialog.grab_set()
        dialog.resizable(False, False)

        tk.Label(dialog, text="環境名稱:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        name_entry = tk.Entry(dialog, width=20)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(dialog, text="Python版本 (可選):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        python_entry = tk.Entry(dialog, width=20)
        python_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(dialog, text="套件 (以空格分隔，可選):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        pkgs_entry = tk.Entry(dialog, width=30)
        pkgs_entry.grid(row=2, column=1, padx=5, pady=5)

        def on_create():
            env_name = name_entry.get().strip()
            python_ver = python_entry.get().strip()
            pkgs = pkgs_entry.get().strip()
            if not env_name:
                messagebox.showerror("錯誤", "請輸入環境名稱")
                return
            args = [env_name]
            if python_ver:
                args.append(f"python={python_ver}")
            if pkgs:
                args.extend(pkgs.split())
            self.create_conda_env(args)
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="建立", command=on_create, width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=5)

    # 新增：執行 conda create 指令
    def create_conda_env(self, args):
        self.append_output(f"\n[建立Conda環境] 執行: conda create -y -n {' '.join(args)}\n")
        def run_create():
            try:
                cmd = ['conda', 'create', '-y', '-n'] + args
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8'
                )
                for line in proc.stdout:
                    self.append_output(line)
                proc.wait()
                if proc.returncode == 0:
                    self.append_output("[建立Conda環境] 完成。\n")
                    # 重新載入環境列表
                    self.envs = self.detect_conda_envs()
                    menu = self.env_menu['menu']
                    menu.delete(0, 'end')
                    for env in self.envs:
                        menu.add_command(label=env, command=lambda v=env: self.selected_env.set(v))
                else:
                    self.append_output(f"[建立Conda環境] 發生錯誤，請檢查訊息。\n")
            except Exception as e:
                self.append_output(f"[建立Conda環境] 執行失敗: {str(e)}\n")
        threading.Thread(target=run_create, daemon=True).start()

    # 新增：執行Python檔案功能
    def run_python_file(self):
        file_path = filedialog.askopenfilename(
            title="選擇Python檔案",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        if file_path:
            cmd = f'python "{file_path}"'
            if self.process and self.process.poll() is None:
                try:
                    self.process.stdin.write(cmd + '\n')
                    self.process.stdin.flush()
                except Exception as e:
                    self.append_output(f"\n執行Python檔案時出錯: {str(e)}\n")
                    self.restart_cmd_process()

    # 新增：強制結束指令功能 (模擬 Ctrl+C)
    def force_terminate_command(self):
        if self.process and self.process.poll() is None:
            try:
                if os.name == "nt":
                    # 0 = CTRL_C_EVENT, 1 = CTRL_BREAK_EVENT
                    self.process.send_signal(CTRL_C_EVENT)
                    self.append_output("\n[強制結束] 已發送 Ctrl+C 給 CMD 進程。\n")
                else:
                    self.append_output("\n[強制結束] 僅支援 Windows 平台的 CMD。\n")
            except Exception as e:
                self.append_output(f"\n[強制結束] 發送 Ctrl+C 失敗: {str(e)}\n")

    def on_destroy(self): # Renamed from on_closing, will be called by Module base class
        self.is_running = False # Signal threads to stop

        # Give threads a moment to stop
        if hasattr(self, 'output_thread') and self.output_thread.is_alive():
            self.output_thread.join(timeout=0.2)
        if hasattr(self, 'display_thread') and self.display_thread.is_alive():
            self.display_thread.join(timeout=0.2)

        try:
            if self.process and self.process.poll() is None:
                # Politely ask cmd.exe to exit first
                try:
                    self.process.stdin.write('exit\n')
                    self.process.stdin.flush()
                except (OSError, ValueError): # stdin might be closed
                    pass

                # Wait a bit for cmd.exe to exit on its own
                try:
                    self.process.wait(timeout=0.5) # Wait for half a second
                except subprocess.TimeoutExpired:
                    # If it doesn't exit, then force kill
                    print("CMD process did not exit gracefully, attempting to kill.")
                    # Using taskkill for Windows to ensure child processes (like conda) are also handled.
                    # CREATE_NEW_PROCESS_GROUP was used, so process.kill() might not be enough.
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except FileNotFoundError: # taskkill might not be available on all systems/PATH
                        self.process.kill() # Fallback to simple kill
                except Exception as e:
                    print(f"Error during process wait/kill: {e}")

            # Ensure stdin, stdout, stderr are closed if they exist
            if self.process:
                for pipe in [self.process.stdin, self.process.stdout, self.process.stderr]:
                    if pipe:
                        try:
                            pipe.close()
                        except OSError:
                            pass # Ignore errors on close, pipe might be already closed

        except Exception as e:
            # Log any other errors during shutdown
            print(f"Error during CMD module shutdown: {e}")

        # The Module base class will handle destroying self.frame
        # No need to call self.master.destroy() or self.frame.destroy() here
        super().on_destroy() # Call base class on_destroy if it has one

# Removed main() and if __name__ == "__main__": block
# This class is now intended to be used as a module within a larger application.