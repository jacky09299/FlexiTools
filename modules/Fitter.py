import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import subprocess
import threading
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import lmfit
from main import Module

class ResonatorAnalyzer:
    """
    Class for analyzing resonator data with both magnitude and phase fitting.
    Provides modular functions for data processing, fitting, and visualization.
    """

    def __init__(self, output_dir="Q_plot"):
        """Initialize the analyzer with output directory"""
        self.plot_dir = Path(output_dir)
        self.plot_dir.mkdir(exist_ok=True)

        # Initialize default parameters
        self.f_r = None
        self.Q = None
        self.phi = None
        self.a = None
        self.alpha = None
        self.tau = None

        # Results
        self.magnitude_result = None
        self.circle_result = None

    def load_data(self, file_path, manual_left=None, manual_right=None):
        """
        Load and preprocess data from CSV file

        Parameters:
        file_path (str): Path to the CSV file
        manual_left (float, optional): Manual left frequency boundary in Hz
        manual_right (float, optional): Manual right frequency boundary in Hz
        """
        self.file_path = file_path
        self.file_name = Path(file_path).stem

        # Load data
        re_im_data = pd.read_csv(file_path)
        self.freq_re_im = re_im_data['Freq [GHz]'].to_numpy() * 1e9  # Convert to Hz
        self.re_s12_full = re_im_data['re(S(1,2)) []'].to_numpy()
        self.im_s12_full = re_im_data['im(S(1,2)) []'].to_numpy()
        self.s12_magnitude_full = np.sqrt(self.re_s12_full**2 + self.im_s12_full**2)

        # Find and apply frequency range
        if manual_left is None or manual_right is None:
            left, right = self.find_sharpest_peak_range(self.freq_re_im, self.s12_magnitude_full)
        if manual_left is not None:
            left = manual_left
        if manual_right is not None:
            right = manual_right

        self.mask_re_im = (self.freq_re_im >= left) & (self.freq_re_im <= right)

        # Apply mask to get data within range
        self.freq_re_im_masked = self.freq_re_im[self.mask_re_im]
        self.re_s12 = self.re_s12_full[self.mask_re_im]
        self.im_s12 = self.im_s12_full[self.mask_re_im]
        self.s12_magnitude = np.sqrt(self.re_s12**2 + self.im_s12**2)

        return self

    @staticmethod
    def resonator_model_abs(f, f_r, Q, phi, a, alpha):
        """Model function for magnitude fitting"""
        exp_phi = np.exp(1j * phi)
        exp_alpha = a * np.exp(1j * alpha)
        denominator = 1 + 2j * Q * (f / f_r - 1)
        s12_complex = exp_alpha * (1 - exp_phi / denominator)
        return np.abs(s12_complex)

    @staticmethod
    def circle_model(alpha, a, phi, f, tau, x, y):
        """Model function for circle fitting"""
        # Combine original data (x, y) into complex data
        z = x + 1j * y
        # Remove cable delay correction
        correction = np.exp(1j * 2 * np.pi * f * tau)
        z_corr = z * correction
        # Extract corrected real and imaginary parts
        x_corr = np.real(z_corr)
        y_corr = np.imag(z_corr)
        # Calculate circle center position
        x_center = a * np.cos(alpha) - 0.5 * np.cos(alpha + phi)
        y_center = a * np.sin(alpha) - 0.5 * np.sin(alpha + phi)
        # Calculate residuals as deviation from ideal radius 0.5
        residuals = np.sqrt((x_corr - x_center)**2 + (y_corr - y_center)**2) - 0.5
        return residuals

    @staticmethod
    def circle_fit_func(params, f, x, y):
        """Function for lmfit to minimize"""
        alpha = params['alpha']
        a = params['a']
        phi = params['phi']
        tau = params['tau']
        return ResonatorAnalyzer.circle_model(alpha, a, phi, f, tau, x, y)

    @staticmethod
    def find_sharpest_peak_range(freq, magnitude, curvature_threshold=1e-18):
        """Find the frequency range around the sharpest peak in the magnitude data"""
        # First derivative
        magnitude_diff = np.gradient(magnitude, freq)

        # Second derivative
        magnitude_diff2 = np.gradient(magnitude_diff, freq)

        # Find local minima as peak candidates
        minima_idx = (np.r_[True, magnitude_diff[1:] > magnitude_diff[:-1]] &
                      np.r_[magnitude_diff[:-1] < magnitude_diff[1:], True])
        minima_idx = np.where(minima_idx)[0]

        if len(minima_idx) == 0:
            # If no minima found, use full range
            return freq.min(), freq.max()

        # Choose the sharpest peak (maximum curvature)
        sharpest_idx = minima_idx[np.argmax(np.abs(magnitude_diff2[minima_idx]))]

        # Find left boundary
        left_idx = sharpest_idx
        while left_idx > 0 and np.abs(magnitude_diff2[left_idx]) > curvature_threshold:
            left_idx -= 1

        # Find right boundary
        right_idx = sharpest_idx
        while right_idx < len(freq) - 1 and np.abs(magnitude_diff2[right_idx]) > curvature_threshold:
            right_idx += 1

        return freq[left_idx], freq[right_idx]

    def create_full_magnitude_plot(self):
        """Create the full S12 magnitude data plot figure"""
        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_subplot(111)

        plt.plot(self.freq_re_im / 1e9, 20 * np.log10(self.s12_magnitude_full), '.', label="Simulated data")

        # Highlight the selected region
        plt.axvspan(self.freq_re_im_masked.min() / 1e9, self.freq_re_im_masked.max() / 1e9,
                    alpha=0.2, color='r', label="Fitted region")

        plt.xlabel("Frequency (GHz)")
        plt.ylabel("$|S_{12}|$ (dB)")
        plt.legend()
        plt.title("$|S_{12}|$ Magnitude")
        plt.grid()
        plt.tight_layout()

        # Add coordinate display text box
        coordinate_text = ax.text(0.98, 0.98, "", transform=ax.transAxes,
                                  horizontalalignment='right', verticalalignment='top',
                                  bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'),
                                  fontsize=15, color='black')

        # Store coordinate_text in the figure for later access
        fig.coordinate_text = coordinate_text

        return fig

    def perform_magnitude_fit(self):
        """Perform magnitude fitting to extract resonator parameters"""
        # Create ResonatorModel class
        class ResonatorModel(lmfit.model.Model):
            def __init__(self, *args, **kwargs):
                super().__init__(ResonatorAnalyzer.resonator_model_abs, *args, **kwargs)
                self.set_param_hint('Q', min=0)  # Quality factor must be positive
                self.set_param_hint('a', min=0)  # Amplitude must be positive

            def guess(self, data, f=None, **kwargs):
                if f is None:
                    return
                f_r_guess = f[np.argmin(data)]
                Q_guess = 10 * (f_r_guess / (f.max() - f.min()))
                phi_guess = 0
                a_guess = 10 ** (data.max() / 20) # Adjusted guess based on dB
                alpha_guess = 0
                params = self.make_params(f_r=f_r_guess, Q=Q_guess, phi=phi_guess, a=a_guess, alpha=alpha_guess)
                return params

        # Fit using ResonatorModel
        resonator_model = ResonatorModel()
        # Use 20*log10(s12_magnitude) for guess if a_guess is based on dB, but fit on linear magnitude
        guess = resonator_model.guess(self.s12_magnitude, f=self.freq_re_im_masked)
        result = resonator_model.fit(self.s12_magnitude, params=guess, f=self.freq_re_im_masked)
        self.magnitude_params = result.params
        self.magnitude_result = result

        # Extract parameters
        self.f_r = self.magnitude_params['f_r'].value
        self.Q = self.magnitude_params['Q'].value
        self.phi = self.magnitude_params['phi'].value
        self.a = self.magnitude_params['a'].value
        self.alpha = self.magnitude_params['alpha'].value

        return self

    def create_magnitude_fit_plot(self):
        """Create the magnitude fit results plot figure"""
        if self.magnitude_result is None:
            raise ValueError("Magnitude fitting has not been performed yet")

        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_subplot(111)

        plt.plot(self.freq_re_im_masked / 1e9, 20 * np.log10(self.s12_magnitude), '.', label="Simulated data")

        fine_freq = np.linspace(self.freq_re_im_masked.min(), self.freq_re_im_masked.max(), 1000)
        fine_fit = ResonatorAnalyzer.resonator_model_abs(
            fine_freq,
            self.f_r,
            self.Q,
            self.phi,
            self.a,
            self.alpha
        )

        plt.plot(fine_freq / 1e9, 20 * np.log10(fine_fit), '-', label="Fitted curve")
        plt.xlabel("Frequency (GHz)")
        plt.ylabel("$|S_{12}|$ (dB)")
        plt.legend()
        plt.title("$|S_{12}|$ Magnitude Fitting")
        plt.grid()
        plt.tight_layout()

        # Add coordinate display text box
        coordinate_text = ax.text(0.98, 0.98, "", transform=ax.transAxes,
                                  horizontalalignment='right', verticalalignment='top',
                                  bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'),
                                  fontsize=15, color='black')

        # Store coordinate_text in the figure for later access
        fig.coordinate_text = coordinate_text

        # Save the figure to file
        magnitude_plot_filename = self.plot_dir / f"{self.file_name}_magnitude.png"
        fig.savefig(magnitude_plot_filename)

        return fig

    def perform_circle_fit(self, tau_min=-0.1, tau_max=4.0, tau_step=0.01, r=0.5):
        """Perform circle fitting with grid search for tau"""
        if self.magnitude_result is None:
            raise ValueError("Magnitude fitting must be performed before circle fitting")

        # Prepare lmfit parameters
        circle_params = lmfit.Parameters()
        circle_params.add('alpha', value=0, min=-np.pi, max=np.pi)  # angle is free to adjust
        circle_params.add('tau', value=0, vary=False)                # tau will be grid-searched
        circle_params.add('a', value=self.a, vary=False)
        circle_params.add('phi', value=self.phi, vary=False)
        circle_params.add('r', value=r, vary=False) # r is fixed for this model based on the derivation

        # Grid search for best tau
        tau_candidates = np.arange(tau_min, tau_max + tau_step/2, tau_step)
        best_chisqr = np.inf
        best_result = None
        best_tau = None

        for tau_candidate in tau_candidates:
            # Copy parameters to avoid interference
            params_grid = circle_params.copy()
            params_grid['tau'].set(value=tau_candidate, vary=False)

            # Perform fitting: f is in GHz (because tau is in ns)
            result_temp = lmfit.minimize(
                self.circle_fit_func,
                params_grid,
                args=(self.freq_re_im_masked*1e-9, self.re_s12, self.im_s12)
            )

            if result_temp.chisqr < best_chisqr:
                best_chisqr = result_temp.chisqr
                best_tau = tau_candidate
                best_result = result_temp

        self.tau = best_tau
        self.circle_result = best_result
        self.circle_alpha = best_result.params['alpha'].value

        return self

    @staticmethod
    def calculate_circle_center(alpha, a, phi, r=0.5):
        """Calculate the center of the fitted circle"""
        x_center = a * np.cos(alpha) - r * np.cos(alpha + phi)
        y_center = a * np.sin(alpha) - r * np.sin(alpha + phi)
        return x_center, y_center

    def create_circle_fit_plot(self, r=0.5):
        """Create the circle fit results plot figure"""
        if self.circle_result is None:
            raise ValueError("Circle fitting has not been performed yet")

        # Calculate circle center
        x_center, y_center = self.calculate_circle_center(self.circle_alpha, self.a, self.phi, r)

        # Generate points for the circle
        theta = np.linspace(0, 2 * np.pi, 100)
        circle_x = x_center + r * np.cos(theta)
        circle_y = y_center + r * np.sin(theta)

        # Original complex data
        z_original = self.re_s12 + 1j * self.im_s12

        # Calculate correction factor (frequency from Hz to GHz)
        correction = np.exp(1j * 2 * np.pi * (self.freq_re_im_masked / 1e9) * self.tau)

        # Correct original data
        z_corrected = z_original * correction

        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_subplot(111)

        plt.scatter(self.re_s12, self.im_s12, label="Simulated data", color='blue')
        plt.scatter(np.real(z_corrected), np.imag(z_corrected), label="Calibrated data", color='orange')
        plt.plot(circle_x, circle_y, label="Fitted circle", color='red')
        plt.xlabel("Re($S_{12}$)")
        plt.ylabel("Im($S_{12}$)")
        plt.legend()
        plt.title("Phase Fitting")
        plt.grid(True)
        plt.axis('equal')
        plt.tight_layout()

        # Add coordinate display text box
        coordinate_text = ax.text(0.98, 0.98, "", transform=ax.transAxes,
                                  horizontalalignment='right', verticalalignment='top',
                                  bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'),
                                  fontsize=15, color='black')

        # Store coordinate_text in the figure for later access
        fig.coordinate_text = coordinate_text

        # Save the figure to file
        phase_plot_filename = self.plot_dir / f"{self.file_name}_phase.png"
        fig.savefig(phase_plot_filename)

        return fig

    def get_final_report(self):
        """Get the final fitting report with all parameters"""
        if self.circle_result is None or self.magnitude_result is None:
            raise ValueError("Both magnitude and circle fitting must be performed before printing the final report")

        magnitude_report = self.magnitude_result.fit_report()
        # For circle_result, lmfit.fit_report expects the MinimizerResult object directly
        circle_report = lmfit.fit_report(self.circle_result)

        return f"Magnitude Fit Results:\n\n{magnitude_report}\n\nCircle Fit Results:\n\n{circle_report}"

class FitterModule(Module):
    def __init__(self, master, shared_state, module_name="Fitter", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        # Initialize variables that were in ResonatorAnalyzerGUI.__init__
        self.file_path = tk.StringVar()
        self.left_freq = tk.StringVar()
        self.right_freq = tk.StringVar()
        self.output_dir = tk.StringVar(value="Q_plot") # Default value
        self.check_only = tk.BooleanVar(value=False)
        self.current_dir = os.getcwd() # Or handle default path better
        self.plot_canvases = {}
        self.figures = [] # Keep track of figures
        self.analyzer = None
        # self.status_var = tk.StringVar(value="Initializing...") # Module class has self.update_status

        self.shared_state.log(f"FitterModule '{self.module_name}' initialized.")
        self.create_ui()

    def create_ui(self):
        # Create a main content frame within self.frame
        # This new frame will house all module-specific UI elements,
        # allowing the base Module class to manage its title bar and resize handle
        # without interference.
        module_main_content_frame = ttk.Frame(self.frame)
        module_main_content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Styles - consider if this is needed or handled by main.py
        # self.style = ttk.Style() # If enabling, ensure it doesn't clash with main.py
        # self.style.configure("TButton", font=("Arial", 10))
        # ... other style configurations

        # 文件框架 - now parented to module_main_content_frame
        file_frame = ttk.LabelFrame(module_main_content_frame, text="檔案選擇", padding=(10, 5))
        file_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(file_frame, text="檔案路徑:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=50)
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        file_frame.grid_columnconfigure(1, weight=1) # Make entry expand

        self.browse_button = ttk.Button(file_frame, text="瀏覽...", command=self.browse_file)
        self.browse_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # 參數框架 - now parented to module_main_content_frame
        params_frame = ttk.LabelFrame(module_main_content_frame, text="分析參數", padding=(10, 5))
        params_frame.pack(fill="x", padx=10, pady=5)

        # 檢查模式
        ttk.Checkbutton(params_frame, text="僅檢查模式 (--check)", variable=self.check_only).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=5, pady=5) # Span 3 columns

        # 頻率範圍
        ttk.Label(params_frame, text="左側頻率邊界 (GHz):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.left_freq_entry = ttk.Entry(params_frame, textvariable=self.left_freq, width=15)
        self.left_freq_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(params_frame, text="右側頻率邊界 (GHz):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.right_freq_entry = ttk.Entry(params_frame, textvariable=self.right_freq, width=15)
        self.right_freq_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # 清空邊界按鈕
        self.clear_boundaries_button = ttk.Button(params_frame, text="清空邊界", command=self.clear_frequency_boundaries)
        self.clear_boundaries_button.grid(row=1, column=2, rowspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(params_frame, text="輸出目錄:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.output_dir_entry = ttk.Entry(params_frame, textvariable=self.output_dir, width=15) # Renamed to avoid conflict if any
        self.output_dir_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        # 按鈕框架 - now parented to module_main_content_frame
        button_frame = ttk.Frame(module_main_content_frame)
        button_frame.pack(fill="x", pady=10, padx=10)

        self.run_button = ttk.Button(button_frame, text="執行分析", command=self.run_analysis)
        self.run_button.pack(side="right", padx=5)

        # 圖形和輸出框架（使用Notebook） - now parented to module_main_content_frame
        self.notebook = ttk.Notebook(module_main_content_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # 全頻譜圖標籤頁
        self.full_spectrum_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.full_spectrum_frame, text="全頻譜圖")

        # 振幅擬合圖標籤頁
        self.magnitude_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.magnitude_frame, text="振幅擬合")

        # 相位擬合圖標籤頁
        self.phase_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.phase_frame, text="相位擬合")

        # 輸出日誌標籤頁
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="輸出日誌")

        # 輸出文字區域
        self.output_text = tk.Text(self.log_frame, wrap=tk.WORD)
        self.output_text.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(self.log_frame, command=self.output_text.yview)
        scrollbar.pack(fill="y", side="right")
        self.output_text.config(yscrollcommand=scrollbar.set)

        # Bindings
        self.frame.bind("<F1>", self.show_help)
        self.frame.bind('<Return>', lambda event: self.run_analysis())

        self.shared_state.log(f"FitterModule '{self.module_name}' UI constructed.")

    def on_destroy(self):
        # Resource cleanup, e.g., closing plots
        self.clear_plots() # ensure this is the FitterModule's clear_plots
        plt.close('all') # Ensure all matplotlib figures are closed
        self.shared_state.log(f"FitterModule '{self.module_name}' is being destroyed.")
        super().on_destroy()

    def browse_file(self):
        """瀏覽並選擇檔案"""
        # Use self.frame as parent for dialog if needed, though filedialog usually handles this
        temp_file_path = filedialog.askopenfilename(
            initialdir=self.current_dir,
            title="選擇共振器數據檔案",
            filetypes=(("CSV檔案", "*.csv"), ("所有檔案", "*.*"))
        )
        if temp_file_path:
            self.file_path.set(temp_file_path)
            self.current_dir = str(Path(temp_file_path).parent)
            self.shared_state.log(f"File selected: {temp_file_path}")

    def run_analysis(self):
        """執行共振器分析"""
        file_path_str = self.file_path.get().strip()
        if not file_path_str:
            messagebox.showerror("錯誤", "請選擇一個數據檔案", parent=self.frame)
            return

        if not os.path.exists(file_path_str):
            messagebox.showerror("錯誤", f"檔案不存在: {file_path_str}", parent=self.frame)
            return

        self.clear_plots()
        self.output_text.delete(1.0, tk.END)
        self.shared_state.log("Fitter: 正在分析...", level="INFO")
        if hasattr(self, 'run_button'): # Check if run_button exists
            self.run_button.config(state="disabled")

        check_only_val = self.check_only.get()
        output_dir_val = self.output_dir.get().strip()

        left_freq_val = None
        if self.left_freq.get().strip():
            try:
                left_freq_val = float(self.left_freq.get().strip())
            except ValueError:
                messagebox.showerror("錯誤", "左側頻率必須是一個有效的數字", parent=self.frame)
                if hasattr(self, 'run_button'): self.run_button.config(state="normal")
                self.shared_state.log("Fitter: 錯誤: 左側頻率無效", level="ERROR")
                return

        right_freq_val = None
        if self.right_freq.get().strip():
            try:
                right_freq_val = float(self.right_freq.get().strip())
            except ValueError:
                messagebox.showerror("錯誤", "右側頻率必須是一個有效的數字", parent=self.frame)
                if hasattr(self, 'run_button'): self.run_button.config(state="normal")
                self.shared_state.log("Fitter: 錯誤: 右側頻率無效", level="ERROR")
                return

        self.shared_state.log(f"Running analysis for {file_path_str}. Output: {output_dir_val}, Check only: {check_only_val}, L-Freq: {left_freq_val}, R-Freq: {right_freq_val}")
        threading.Thread(target=self.run_analysis_thread,
                         args=(file_path_str, check_only_val, output_dir_val, left_freq_val, right_freq_val),
                         daemon=True).start()

    def clear_frequency_boundaries(self):
        """清空左右頻率邊界輸入框"""
        self.left_freq.set("")
        self.right_freq.set("")
        self.shared_state.log("Frequency boundaries cleared.")

    def run_analysis_thread(self, file_path, check_only, output_dir, left_freq, right_freq):
        """在單獨的線程中執行分析"""
        try:
            self.analyzer = ResonatorAnalyzer(output_dir=output_dir)
            manual_left = left_freq * 1e9 if left_freq is not None else None
            manual_right = right_freq * 1e9 if right_freq is not None else None
            self.analyzer.load_data(file_path, manual_left=manual_left, manual_right=manual_right)

            self.frame.after(0, self.create_and_display_full_spectrum)

            if check_only:
                self.frame.after(0, lambda: self.shared_state.log("Fitter: 分析完成 (僅檢查模式)", level="DEBUG"))
                if hasattr(self, 'run_button'): self.frame.after(0, lambda: self.run_button.config(state="normal"))
                if hasattr(self, 'notebook') and hasattr(self, 'full_spectrum_frame'): self.frame.after(0, lambda: self.notebook.select(self.full_spectrum_frame))
                self.shared_state.log("Analysis complete (check only mode).")
                return

            self.analyzer.perform_magnitude_fit()
            self.log_message("|S_{12}| fit report:\n")
            self.log_message(self.analyzer.magnitude_result.fit_report() + "\n")
            self.frame.after(0, self.create_and_display_magnitude_fit)

            self.analyzer.perform_circle_fit()
            self.log_message("\nBest tau from grid search: " + str(self.analyzer.tau) + "\n")
            self.log_message("Grid search fit report:\n")
            self.log_message(lmfit.fit_report(self.analyzer.circle_result) + "\n")
            self.frame.after(0, self.create_and_display_circle_fit)

            self.frame.after(0, lambda: self.shared_state.log("Fitter: 分析完成", level="INFO"))
            if hasattr(self, 'notebook') and hasattr(self, 'full_spectrum_frame'): self.frame.after(0, lambda: self.notebook.select(self.full_spectrum_frame))
            self.shared_state.log("Analysis complete.")

        except Exception as e:
            import traceback
            error_message = f"執行時發生錯誤: {str(e)}\n詳細錯誤: {traceback.format_exc()}\n"
            self.log_message(error_message)
            self.frame.after(0, lambda: self.shared_state.log("Fitter: 發生錯誤", level="ERROR"))
            self.shared_state.log(f"Error during analysis: {error_message}", level="error")
        finally:
            if hasattr(self, 'run_button'): self.frame.after(0, lambda: self.run_button.config(state="normal"))

    def create_and_display_full_spectrum(self):
        """在主線程中創建並顯示全頻譜圖"""
        if self.analyzer:
            try:
                full_spectrum_fig = self.analyzer.create_full_magnitude_plot()
                self.display_plot(full_spectrum_fig, self.full_spectrum_frame, "全頻譜圖")
            except Exception as e:
                error_msg = f"創建全頻譜圖時發生錯誤: {e}\n"
                self.log_message(error_msg)
                self.shared_state.log("Fitter: 創建全頻譜圖錯誤", level="ERROR")
                self.shared_state.log(error_msg, level="error") # This logs the detailed error too


    def create_and_display_magnitude_fit(self):
        """在主線程中創建並顯示振幅擬合圖"""
        if self.analyzer and self.analyzer.magnitude_result:
            try:
                magnitude_fig = self.analyzer.create_magnitude_fit_plot()
                self.display_plot(magnitude_fig, self.magnitude_frame, "振幅擬合")
            except Exception as e:
                error_msg = f"創建振幅擬合圖時發生錯誤: {e}\n"
                self.log_message(error_msg)
                self.shared_state.log("Fitter: 創建振幅擬合圖錯誤", level="ERROR")
                self.shared_state.log(error_msg, level="error") # This logs the detailed error too

    def create_and_display_circle_fit(self):
        """在主線程中創建並顯示相位擬合圖"""
        if self.analyzer and self.analyzer.circle_result:
            try:
                circle_fig = self.analyzer.create_circle_fit_plot()
                self.display_plot(circle_fig, self.phase_frame, "相位擬合")
            except Exception as e:
                error_msg = f"創建相位擬合圖時發生錯誤: {e}\n"
                self.log_message(error_msg)
                self.shared_state.log("Fitter: 創建相位擬合圖錯誤", level="ERROR")
                self.shared_state.log(error_msg, level="error") # This logs the detailed error too

    def display_plot(self, figure, frame, title):
        """在指定的框架中顯示圖形"""
        for widget in frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(figure, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        def update_coordinates(event):
            if event.inaxes:
                if title == "全頻譜圖" or title == "振幅擬合":
                    coord_text = f"x: {event.xdata:.4f} GHz\ny: {event.ydata:.2f} dB"
                else:
                    coord_text = f"x: {event.xdata:.4f}\ny: {event.ydata:.4f}"
                if hasattr(figure, 'coordinate_text'): # Check if text object exists
                    figure.coordinate_text.set_text(coord_text)
                    figure.coordinate_text.set_visible(True)
                    canvas.draw_idle()
            else:
                if hasattr(figure, 'coordinate_text'):
                    figure.coordinate_text.set_visible(False)
                    canvas.draw_idle()
        
        def on_plot_click(event):
            if event.inaxes and (title == "全頻譜圖" or title == "振幅擬合"):
                x_coord_ghz = event.xdata 
                if event.button == 1:
                    self.left_freq.set(f"{x_coord_ghz:.6f}")
                elif event.button == 3:
                    self.right_freq.set(f"{x_coord_ghz:.6f}")

        canvas.mpl_connect('motion_notify_event', update_coordinates)
        canvas.mpl_connect('button_press_event', on_plot_click)
        self.plot_canvases[title] = canvas
        self.figures.append(figure) # Keep track of figure for explicit closing if needed

    def clear_plots(self):
        """清空所有圖形"""
        if hasattr(self, 'full_spectrum_frame') and self.full_spectrum_frame:
             frames_to_clear = [self.full_spectrum_frame, self.magnitude_frame, self.phase_frame]
             for frame in frames_to_clear:
                 if frame: # Ensure frame exists before trying to access its children
                    for widget in frame.winfo_children():
                        widget.destroy()

        for fig in self.figures: # Close matplotlib figures explicitly
            plt.close(fig)
        self.figures = []

        self.plot_canvases = {}
        # plt.close('all') # This is broad; specific figure closing is better
        self.shared_state.log("Plots cleared.")


    def log_message(self, message):
        """向輸出框添加消息"""
        def update_log():
            if hasattr(self, 'output_text') and self.output_text: # Check if output_text exists
                self.output_text.insert(tk.END, message)
                self.output_text.see(tk.END)
        # self.root.after(0, update_log) # Replaced
        if hasattr(self, 'frame') and self.frame: # Check if frame exists
            self.frame.after(0, update_log)


    def show_help(self, event=None):
        """顯示說明信息"""
        help_text = """使用說明:

1. 檔案選擇: 點擊"瀏覽..."按鈕選擇要分析的CSV檔案。
2. 分析參數:
   - 僅檢查模式: 勾選後只會顯示全頻譜圖而不進行擬合。
   - 左側/右側頻率: 設置擬合的頻率範圍(單位:GHz)，留空表示自動檢測。
     - 新功能: 在「全頻譜圖」或「振幅擬合」圖上，左鍵點擊可設定左邊界，右鍵點擊可設定右邊界。
   - 輸出目錄: 設置圖像輸出的目錄。
   - 清空邊界: 點擊按鈕可同時清空左右邊界的輸入值。
3. 點擊"執行分析"或按 Enter 鍵開始處理。
4. 在標籤頁中可查看不同的圖形結果和分析日誌。
5. 您可以連續分析多個檔案，無需關閉程序。
6. 將滑鼠移至圖上時，右上角會顯示當前坐標位置。

提示: 完整分析會生成多個圖像，包括振幅擬合和相位擬合結果，這些圖形會顯示在不同標籤頁中，並同時保存到指定目錄。
"""
        messagebox.showinfo("使用說明", help_text, parent=self.frame)
