import tkinter as tk
from tkinter import ttk, messagebox
from main import Module

class TemplateModule(Module):
    def __init__(self, master, shared_state, module_name="Template", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"TemplateModule '{self.module_name}' initialized.")
        self.create_ui()

    def create_ui(self):
        """Create the user interface for the template module."""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        label = ttk.Label(main_frame, text="This is a template module.")
        label.pack(pady=10)

        button = ttk.Button(main_frame, text="Click Me!", command=self.show_message)
        button.pack(pady=10)

    def show_message(self):
        """Show a simple message box."""
        messagebox.showinfo("Template Module", "Hello from the template module!", parent=self.frame)

    def on_destroy(self):
        """Cleanup resources when the module is closed."""
        self.shared_state.log(f"TemplateModule '{self.module_name}' is being destroyed.")
        # Add any specific cleanup code here, for example:
        # - Closing files
        # - Stopping threads
        # - Releasing hardware resources
        super().on_destroy()
