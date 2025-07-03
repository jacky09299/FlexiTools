import tkinter as tk
from tkinter import ttk
import time
import logging # Added for logging constants
# Assuming main.py (and thus the Module class definition) is in the parent directory
# For direct execution or if modules are treated as part of a package, adjust imports.
# For now, this import might fail if run directly, but works when loaded by main.py
from main import Module # Or from module_base import Module if we create it

class ClockModule(Module):
    def __init__(self, master, shared_state, module_name="Clock", gui_manager=None): # Added gui_manager
        super().__init__(master, shared_state, module_name, gui_manager) # Pass gui_manager
        self.time_label = None
        self.after_id = None # For storing the 'after' call ID
        self.create_ui() # Call create_ui from __init__

    def create_ui(self):
        # The module's frame (self.frame) is already created by the base Module class.
        # It is equivalent to 'master' passed in __init__ of Module base class.
        # Configure self.frame directly if needed, e.g. self.frame.config(...)
        # Then, pack/grid all UI elements into self.frame.

        # Example styling for the module's main frame (self.frame)
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Main content for the clock, goes into self.frame
        content_frame = ttk.Frame(self.frame) # Parent is self.frame
        content_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        self.time_label = ttk.Label(content_frame, text="", font=("Helvetica", 24))
        self.time_label.pack(expand=True)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO) # Use logging constant
        self.update_time()

    def update_time(self):
        current_time = time.strftime('%H:%M:%S')
        if self.time_label and self.time_label.winfo_exists(): # Check if widget exists
            self.time_label.config(text=current_time)
            # Use self.frame for 'after' as it's a persistent widget within the module
            self.after_id = self.frame.after(1000, self.update_time)
        else:
            # If label doesn't exist, stop trying to update.
            self.after_id = None

    def on_destroy(self):
        if self.after_id:
            self.frame.after_cancel(self.after_id)
            self.after_id = None
        super().on_destroy() # Call base class on_destroy
        self.shared_state.log(f"{self.module_name} instance and timer destroyed.")

# To make it runnable standalone for testing (optional)
if __name__ == '__main__':
    # This standalone test requires a mock Module class and SharedState if not importing from main
    # For simplicity, assume Module class is available or define a minimal mock here
    # Fallback for Module if not available (e.g. running file directly)
    try:
        from main import Module as MainModule
    except ImportError:
        class MainModule: # Minimal mock if main.Module is not found
            def __init__(self, master, shared_state, module_name="Test", gui_manager=None): # Added gui_manager
                self.master = master
                self.shared_state = shared_state
                self.module_name = module_name
                self.gui_manager = gui_manager
                # master IS the frame in this context for standalone test
                self.frame = ttk.Frame(master)
                # self.frame.pack(fill=tk.BOTH, expand=True) # Crucial for visibility
                self.shared_state.log(f"MockModule '{self.module_name}' initialized.")
            def get_frame(self): return self.frame
            def create_ui(self):
                ttk.Label(self.frame, text=f"Content for {self.module_name}").pack()
            def on_destroy(self):
                self.shared_state.log(f"MockModule '{self.module_name}' destroyed.")
        globals()['Module'] = MainModule # Make this mock available as 'Module'


    class MockSharedState:
        def log(self, message, level=logging.INFO): print(f"LOG ({logging.getLevelName(level)}): {message}") # Use getLevelName
        def get(self, key, default=None): return default
        def set(self, key, value): pass

    root = tk.Tk()
    root.title("Clock Module Test")
    root.geometry("250x150")

    mock_shared_state = MockSharedState()

    # In standalone test, the module_master_frame is where ClockModule's self.frame will be placed.
    # ClockModule's __init__ takes this 'module_master_frame' as its 'master'.
    # Then, super().__init__(master,...) in ClockModule passes this to Module base.
    # Module base then creates self.frame = ttk.Frame(master), so self.frame IS module_master_frame.
    # This seems a bit off. The 'master' for a Module instance should be the container it places its *own* frame into.
    # For the actual app, 'frame_wrapper' is passed as master. Module base class does self.frame = ttk.Frame(frame_wrapper).
    # So the module's content is built into this self.frame. This self.frame (frame_wrapper) is then added to PanedWindow.
    # For standalone:
    # 1. Create a main window (root).
    # 2. Create a frame in root that acts as the 'master' where the module will be placed.
    #    This 'master' is what `frame_wrapper` would be in `ModularGUI`.
    module_container_frame = ttk.Frame(root, padding=10) # This is the equivalent of frame_wrapper
    module_container_frame.pack(fill=tk.BOTH, expand=True)

    # ClockModule's master is module_container_frame.
    # Inside ClockModule, self.frame is created as a child of module_container_frame.
    clock_module = ClockModule(module_container_frame, mock_shared_state, module_name="TestClock", gui_manager=None) # Pass gui_manager

    # The module's own frame (clock_module.get_frame()) must be packed into its master (module_container_frame).
    # This is typically done by ModularGUI.instantiate_module.
    # For standalone test, we replicate it here if Module.__init__ or ClockModule.create_ui doesn't pack self.frame.
    # The current Module base class does NOT pack self.frame. ClockModule packs content INTO self.frame.
    # So, self.frame itself needs to be packed into its master (module_container_frame)
    clock_module.get_frame().pack(fill=tk.BOTH, expand=True)

    root.mainloop()
