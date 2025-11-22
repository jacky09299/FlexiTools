import tkinter as tk
from tkinter import ttk, messagebox
from main import Module

class TemplateModule(Module):
    def __init__(self, master, shared_state, module_name="Template", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"TemplateModule '{self.module_name}' initialized.")

        # Initialize widget references to None
        self.main_label = None
        self.action_button = None

        self.create_ui()

        # Apply initial translations
        self.update_language()

    def create_ui(self):
        """Create the user interface for the template module."""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Create widgets (initially empty or default text)
        # We save references (self.main_label) to update them later.
        self.main_label = ttk.Label(main_frame, text="")
        self.main_label.pack(pady=10)

        self.action_button = ttk.Button(main_frame, text="", command=self.show_message)
        self.action_button.pack(pady=10)

    def update_language(self):
        """
        Update the UI text when the language changes.
        This method is called automatically by the main window.
        """
        # Always call super() first to update the module title
        super().update_language()

        # Guard clause: Ensure widgets exist before trying to configure them
        if not getattr(self, 'main_label', None):
            return

        # 2. Update widget text using self.tr(key, default_text)
        # You need to add these keys to locales/en_US.json and zh_TW.json
        self.main_label.config(text=self.tr("module_template_label", "This is a template module."))
        self.action_button.config(text=self.tr("module_template_btn", "Click Me!"))

    def show_message(self):
        """Show a simple message box."""
        # For dialogs, we fetch the translation immediately when showing
        title = self.tr("module_template_msg_title", "Template Module")
        msg = self.tr("module_template_msg_body", "Hello from the template module!")
        messagebox.showinfo(title, msg, parent=self.frame)

    def on_destroy(self):
        """Cleanup resources when the module is closed."""
        self.shared_state.log(f"TemplateModule '{self.module_name}' is being destroyed.")
        # Add any specific cleanup code here, for example:
        # - Closing files
        # - Stopping threads
        # - Releasing hardware resources
        super().on_destroy()
