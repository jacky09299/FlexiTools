import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import re
from main import Module

class CSVProcessorApp(Module):
    def __init__(self, master, shared_state, module_name="SplitPara", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        
        # Variables
        self.input_file_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=os.getcwd())
        self.status_var = tk.StringVar(value="Ready to process data")
        # 新增可自訂前綴、切割參數、後綴
        self.prefix_var = tk.StringVar(value="filter_N5_63_06")
        self.split_param_var = tk.StringVar(value="d")
        self.split_param_label_var = tk.StringVar(value="d")  # 新增：檔名顯示用
        self.suffix_var = tk.StringVar(value="t40")
        # 預設切割值
        self.split_values = ['1um', '2um', '3um', '4um'] + [f'{i}um' for i in range(5, 151, 5)]
        self.selected_values = {v: tk.BooleanVar(value=True) for v in self.split_values}
        
        # Create UI
        self.create_ui()
    
    def create_ui(self):
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input file section
        file_frame = ttk.LabelFrame(main_frame, text="Input/Output Settings", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Input CSV File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.input_file_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self.browse_input_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)
        
        # 新增自訂參數區
        params_frame = ttk.LabelFrame(main_frame, text="Filename Parameters", padding="10")
        params_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(params_frame, text="Prefix:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(params_frame, textvariable=self.prefix_var, width=18).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(params_frame, text="Split Param:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(20,0))
        ttk.Entry(params_frame, textvariable=self.split_param_var, width=10).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(params_frame, text="Param Label:").grid(row=0, column=4, sticky=tk.W, pady=5, padx=(20,0))
        ttk.Entry(params_frame, textvariable=self.split_param_label_var, width=10).grid(row=0, column=5, sticky=tk.W, padx=5, pady=5)
        ttk.Label(params_frame, text="Suffix:").grid(row=0, column=6, sticky=tk.W, pady=5, padx=(20,0))
        ttk.Entry(params_frame, textvariable=self.suffix_var, width=10).grid(row=0, column=7, sticky=tk.W, padx=5, pady=5)
        # 移除 L 與 t 輸入框
        
        # 切割值選擇區
        self.values_frame = ttk.LabelFrame(main_frame, text=f"{self.split_param_var.get()} Values to Process", padding="10")
        self.values_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.create_values_checkboxes()
        
        # 監聽 split_param_var 變動，更新 checkbox 標題
        self.split_param_var.trace_add("write", self.update_values_frame_title)
        
        # Bottom section: Process button and status
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Process Data", command=self.process_data).pack(side=tk.LEFT, padx=5)
        # Removed Exit button
        
        # Status bar
        status_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W, padx=5)
    
    def create_values_checkboxes(self):
        # 清空舊內容
        for widget in self.values_frame.winfo_children():
            widget.destroy()
        # scrollable
        canvas = tk.Canvas(self.values_frame)
        scrollbar = ttk.Scrollbar(self.values_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # Buttons for selecting/deselecting all
        buttons_frame = ttk.Frame(scrollable_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        ttk.Button(buttons_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Deselect All", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        # Add checkboxes
        values_container = ttk.Frame(scrollable_frame)
        values_container.pack(fill=tk.BOTH, expand=True, pady=5)
        row, col = 0, 0
        for v in self.split_values:
            ttk.Checkbutton(
                values_container, 
                text=v, 
                variable=self.selected_values[v]
            ).grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def update_values_frame_title(self, *args):
        self.values_frame.config(text=f"{self.split_param_var.get()} Values to Process")
    
    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="Select Input CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=self.frame
        )
        if filename:
            self.input_file_var.set(filename)
            # 不再自動填 L
            # try:
            #     match = re.search(r'L(.+)\.csv', os.path.basename(filename))
            #     if match:
            #         self.L_var.set(match.group(1))
            # except:
            #     pass
    
    def browse_output_dir(self):
        dirname = filedialog.askdirectory(
            title="Select Output Directory",
            parent=self.frame
        )
        if dirname:
            self.output_dir_var.set(dirname)
    
    def select_all(self):
        for var in self.selected_values.values():
            var.set(True)
    
    def deselect_all(self):
        for var in self.selected_values.values():
            var.set(False)
    
    def process_data(self):
        input_file = self.input_file_var.get()
        output_dir = self.output_dir_var.get()
        prefix = self.prefix_var.get()
        split_param = self.split_param_var.get()
        split_param_label = self.split_param_label_var.get()
        suffix = self.suffix_var.get()
        
        # Validation
        if not input_file:
            messagebox.showerror("Error", "Please select an input CSV file", parent=self.frame)
            return
        
        # 不再檢查 L
        selected_values = [v for v in self.split_values if self.selected_values[v].get()]
        if not selected_values:
            messagebox.showerror("Error", "Please select at least one value", parent=self.frame)
            return
        
        try:
            self.status_var.set(f"Reading file: {input_file}")
            # self.root.update() # Removed
            data = pd.read_csv(input_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}", parent=self.frame)
            self.status_var.set("Error reading file")
            return
        
        success_count = 0
        error_count = 0
        
        for v in selected_values:
            try:
                freq_col = "Freq [GHz]"
                re_col = f"re(S(1,2)) [] - ${split_param}='{v}'"
                im_col = f"im(S(1,2)) [] - ${split_param}='{v}'"
                
                # Check if columns exist
                if re_col not in data.columns or im_col not in data.columns:
                    self.status_var.set(f"Skipping {v}: Missing required columns")
                    # self.root.update() # Removed
                    error_count += 1
                    continue
                
                output_data = data[[freq_col, re_col, im_col]].copy()
                output_data.columns = ["Freq [GHz]", "re(S(1,2)) []", "im(S(1,2)) []"]
                input_filename = os.path.splitext(os.path.basename(input_file))[0]
                # 使用 split_param_label 作為檔名參數
                output_file = os.path.join(
                    output_dir,
                    f"{prefix}_{input_filename}_{split_param_label}{v}_{suffix}.csv"
                )
                output_data.to_csv(output_file, index=False)
                
                success_count += 1
                self.status_var.set(f"Processed: {v} ({success_count}/{len(selected_values)})")
                # self.root.update() # Removed
                
            except Exception as e:
                error_count += 1
                self.status_var.set(f"Error processing {v}: {str(e)}")
                # self.root.update() # Removed
        
        # Final status
        if error_count == 0:
            self.status_var.set(f"Completed! {success_count} files processed successfully")
            messagebox.showinfo("Success", f"All {success_count} files were processed successfully.", parent=self.frame)
        else:
            self.status_var.set(f"Completed with errors. {success_count} successful, {error_count} errors")
            messagebox.showwarning("Warning", f"Completed with {error_count} errors. {success_count} files were processed successfully.", parent=self.frame)

# if __name__ == "__main__":
#     root = tk.Tk()
#     app = CSVProcessorApp(root)
#     root.mainloop()