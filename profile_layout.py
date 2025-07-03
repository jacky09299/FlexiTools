print("profile_layout.py: SCRIPT EXECUTION STARTED", flush=True)
import tkinter as tk
from tkinter import ttk
import cProfile
import pstats

# Attempt to import from main.py and shared_state.py
# These files are expected to be in the same directory
try:
    from main import ModularGUI, CustomLayoutManager, Module
    from shared_state import SharedState
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Please ensure main.py and shared_state.py are in the same directory as profile_layout.py")
    exit(1)

print("Successfully imported modules from main.py and shared_state.py")

def main():
    print("Setting up Tkinter root window and ModularGUI...")
    root = tk.Tk()
    root.title("Profiling Layout")
    # Hide the window as it's not needed for profiling widget creation logic
    root.withdraw()

    # SharedState for DummyModules, ModularGUI will create its own
    shared_state_for_dummies = SharedState()
    gui_manager = ModularGUI(root) # ModularGUI initializes its own SharedState
    # Correctly access main_layout_manager as defined in ModularGUI
    custom_layout_manager = gui_manager.main_layout_manager
    print("ModularGUI and CustomLayoutManager instantiated.")

    # Define DummyModule
    class DummyModule(Module):
        def __init__(self, parent_frame, shared_state, module_name, gui_manager):
            super().__init__(parent_frame, shared_state, module_name, gui_manager)
            self.parent_frame = parent_frame # Keep a reference to the wrapper
            # print(f"DummyModule '{module_name}' initialized.") # Reduced verbosity

        def create_ui(self):
            """Creates a minimal UI for the dummy module."""
            label = ttk.Label(self.content_frame, text=f"Dummy: {self.module_name}")
            label.pack(padx=5, pady=5)
            # print(f"UI created for DummyModule '{self.module_name}'. Content frame: {self.content_frame}") # Reduced verbosity
            return self.content_frame # Important: return the content_frame

    # Store created modules and their wrappers
    created_modules = []

    num_modules = 5 # Reduced from 50 to 5 to prevent timeout
    print(f"Creating and adding {num_modules} dummy modules...")
    for i in range(num_modules):
        module_name = f"DummyModule_{i+1}"

        # Create a frame_wrapper for each module, parented to the CustomLayoutManager's main frame
        # Ensure custom_layout_manager (which is gui_manager.main_layout_manager) is used for parenting
        frame_wrapper = ttk.Frame(gui_manager.main_layout_manager, relief=tk.RIDGE, borderwidth=1)

        module_instance = DummyModule(frame_wrapper, shared_state_for_dummies, module_name, gui_manager)

        # Ensure create_ui is called and the content_frame is packed into its frame_wrapper
        # The Module base class __init__ calls create_ui,
        # and get_frame() returns the content_frame from create_ui.
        content_frame = module_instance.get_frame()
        if content_frame:
             content_frame.pack(fill=tk.BOTH, expand=True) # Pack content_frame into frame_wrapper
        else:
            print(f"Warning: content_frame not returned from create_ui for {module_name}")

        created_modules.append({'wrapper': frame_wrapper, 'instance': module_instance})

        # Use the layout_manager instance obtained from gui_manager
        gui_manager.main_layout_manager.add_module(frame_wrapper, module_name, width=150, height=100)
        # print(f"Added '{module_name}' to CustomLayoutManager.") # Reduced verbosity

    print(f"{num_modules} dummy modules created and added.") # This one is fine (outside loop)

    # Profiling
    print("Starting profiling of reflow_layout()...")
    profiler = cProfile.Profile()
    profiler.enable()

    gui_manager.main_layout_manager.reflow_layout() # Call reflow_layout on the correct instance

    profiler.disable()
    print("Profiling finished.")

    # Print stats
    print("\nProfiling Statistics (sorted by cumulative time):")
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats()

    # Optional: Clean up Tkinter window if it were shown
    # root.destroy() # Not strictly necessary as it was withdrawn and script exits

if __name__ == "__main__":
    main()
    print("profile_layout.py script finished.")
