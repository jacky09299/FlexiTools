import tkinter as tk
from tkinter import ttk, messagebox
import logging
# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class TodoListModule(Module):
    def __init__(self, master, shared_state, module_name="TodoList", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.tasks = []
        self.task_listbox = None
        self.task_entry = None
        self.create_ui()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Main content frame
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH) # Reduced padding slightly

        # Input frame for adding tasks
        input_frame = ttk.Frame(content_frame)
        input_frame.pack(fill=tk.X, pady=(0, 5))

        self.task_entry = ttk.Entry(input_frame, width=30) # Specify width
        self.task_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        self.task_entry.bind("<Return>", self.add_task_event)

        add_button = ttk.Button(input_frame, text="Add Task", command=self.add_task_event)
        add_button.pack(side=tk.LEFT)

        # Listbox frame for displaying tasks
        listbox_frame = ttk.Frame(content_frame)
        listbox_frame.pack(expand=True, fill=tk.BOTH, pady=(0,5))

        self.task_listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE, height=5) # Specify height
        self.task_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0,5))

        # Scrollbar for the listbox
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.task_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.task_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons frame for actions like remove
        buttons_frame = ttk.Frame(content_frame)
        buttons_frame.pack(fill=tk.X)

        remove_button = ttk.Button(buttons_frame, text="Remove Selected", command=self.remove_task)
        remove_button.pack(side=tk.LEFT, padx=(0,5))

        # (Optional) Clear all button
        # clear_all_button = ttk.Button(buttons_frame, text="Clear All", command=self.clear_all_tasks)
        # clear_all_button.pack(side=tk.LEFT)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)
        self.refresh_task_list() # Populate listbox if there are any initial tasks

    def add_task_event(self, event=None): # Can be called by button or Enter key
        task_text = self.task_entry.get().strip()
        if task_text:
            if task_text not in self.tasks: # Prevent duplicate exact matches
                self.tasks.append(task_text)
                self.refresh_task_list()
                self.task_entry.delete(0, tk.END)
                self.shared_state.log(f"Task added: {task_text}", level=logging.DEBUG)
            else:
                # Optionally inform user about duplicate
                # messagebox.showinfo("Duplicate Task", "This task is already in the list.", parent=self.frame)
                self.shared_state.log(f"Attempted to add duplicate task: {task_text}", level=logging.DEBUG)
                self.task_entry.delete(0, tk.END) # Clear entry even if duplicate
        else:
            # Optionally inform user that task cannot be empty
            # messagebox.showwarning("Empty Task", "Task description cannot be empty.", parent=self.frame)
            pass

    def remove_task(self):
        selected_index = self.task_listbox.curselection()
        if selected_index:
            task_text = self.task_listbox.get(selected_index)
            self.tasks.pop(selected_index[0])
            self.refresh_task_list()
            self.shared_state.log(f"Task removed: {task_text}", level=logging.DEBUG)
        else:
            # messagebox.showwarning("No Task Selected", "Please select a task to remove.", parent=self.frame)
            self.shared_state.log("Remove task called but no task selected.", level=logging.DEBUG)


    def clear_all_tasks(self):
        # if messagebox.askyesno("Confirm Clear", "Are you sure you want to remove all tasks?", parent=self.frame):
        self.tasks.clear()
        self.refresh_task_list()
        self.shared_state.log("All tasks cleared.", level=logging.DEBUG)

    def refresh_task_list(self):
        if self.task_listbox and self.task_listbox.winfo_exists():
            self.task_listbox.delete(0, tk.END)
            for task in self.tasks:
                self.task_listbox.insert(tk.END, task)

    def on_destroy(self):
        # No specific resources to clean up like timers for this module
        # If tasks were saved to a file, this would be a place to ensure they are saved.
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
