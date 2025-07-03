import tkinter as tk
from tkinter import ttk, messagebox
import random
import logging

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class SudokuStudioModule(Module):
    def __init__(self, master, shared_state, module_name="SudokuStudio", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.grid_vars = [[tk.StringVar(value="") for _ in range(9)] for _ in range(9)]
        self.grid_entries = [[None for _ in range(9)] for _ in range(9)]
        self.initial_puzzle = None # Stores the puzzle with 0s for empty cells
        self.solution = None # Stores the solved puzzle

        # Using a fixed known solvable puzzle and its solution for simplicity
        # In a real app, this would involve a generation algorithm.
        self.predefined_puzzles = [
            {
                "puzzle": [
                    [5, 3, 0, 0, 7, 0, 0, 0, 0],
                    [6, 0, 0, 1, 9, 5, 0, 0, 0],
                    [0, 9, 8, 0, 0, 0, 0, 6, 0],
                    [8, 0, 0, 0, 6, 0, 0, 0, 3],
                    [4, 0, 0, 8, 0, 3, 0, 0, 1],
                    [7, 0, 0, 0, 2, 0, 0, 0, 6],
                    [0, 6, 0, 0, 0, 0, 2, 8, 0],
                    [0, 0, 0, 4, 1, 9, 0, 0, 5],
                    [0, 0, 0, 0, 8, 0, 0, 7, 9]
                ],
                "solution": [
                    [5, 3, 4, 6, 7, 8, 9, 1, 2],
                    [6, 7, 2, 1, 9, 5, 3, 4, 8],
                    [1, 9, 8, 3, 4, 2, 5, 6, 7],
                    [8, 5, 9, 7, 6, 1, 4, 2, 3],
                    [4, 2, 6, 8, 5, 3, 7, 9, 1],
                    [7, 1, 3, 9, 2, 4, 8, 5, 6],
                    [9, 6, 1, 5, 3, 7, 2, 8, 4],
                    [2, 8, 7, 4, 1, 9, 6, 3, 5],
                    [3, 4, 5, 2, 8, 6, 1, 7, 9]
                ]
            }
            # Can add more predefined puzzles here
        ]

        self.create_ui()
        self.load_new_game()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        content_frame = ttk.Frame(self.frame, padding="5")
        content_frame.pack(expand=True, fill=tk.BOTH)
        content_frame.columnconfigure(0, weight=1) # Sudoku grid column
        content_frame.columnconfigure(1, weight=0) # Button column
        content_frame.rowconfigure(0, weight=1)    # Sudoku grid row

        # Sudoku Grid Frame
        grid_frame_container = ttk.Frame(content_frame, relief="sunken", borderwidth=1)
        grid_frame_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Make grid_frame_container's cells responsive if window is resized
        for i in range(9):
            grid_frame_container.rowconfigure(i, weight=1, minsize=20) # minsize for cells
            grid_frame_container.columnconfigure(i, weight=1, minsize=20)


        validate_cmd = self.frame.register(self.validate_input)

        for r in range(9):
            for c in range(9):
                entry = ttk.Entry(grid_frame_container, textvariable=self.grid_vars[r][c],
                                  font=('Helvetica', 12, 'bold' if self.initial_puzzle and self.initial_puzzle[r][c] != 0 else 'normal'),
                                  width=2, justify='center',
                                  validate='key', validatecommand=(validate_cmd, '%P'))
                entry.grid(row=r, column=c, sticky="nsew", padx=0, pady=0)
                self.grid_entries[r][c] = entry

                # Add thicker lines for 3x3 blocks
                # This is tricky with just grid; often done by drawing on a canvas or multiple frames
                # Simple visual separation using padding (less ideal than lines)
                padx_config = (1, 1 if (c+1)%3 != 0 else 3)
                pady_config = (1, 1 if (r+1)%3 != 0 else 3)
                entry.grid_configure(padx=padx_config, pady=pady_config)


        # Controls Frame (Buttons)
        controls_frame = ttk.Frame(content_frame, padding="5")
        controls_frame.grid(row=0, column=1, sticky="ns", padx=5, pady=5)

        new_game_button = ttk.Button(controls_frame, text="New Game", command=self.load_new_game)
        new_game_button.pack(pady=5, fill=tk.X)

        check_button = ttk.Button(controls_frame, text="Check Solution", command=self.check_solution)
        check_button.pack(pady=5, fill=tk.X)

        reset_button = ttk.Button(controls_frame, text="Reset Puzzle", command=self.reset_puzzle)
        reset_button.pack(pady=5, fill=tk.X)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def validate_input(self, P):
        # Allow empty string (for clearing) or a single digit from 1-9
        if P == "" or (P.isdigit() and len(P) == 1 and '1' <= P <= '9'):
            return True
        return False

    def load_new_game(self):
        # For now, always loads the first predefined puzzle
        chosen_puzzle_set = random.choice(self.predefined_puzzles)
        self.initial_puzzle = [row[:] for row in chosen_puzzle_set["puzzle"]] # Deep copy
        self.solution = chosen_puzzle_set["solution"]
        self.reset_puzzle() # This will populate the grid
        self.shared_state.log("New Sudoku game loaded.", level=logging.INFO)

    def reset_puzzle(self):
        if not self.initial_puzzle:
            self.shared_state.log("No puzzle loaded to reset.", level=logging.WARNING)
            return

        for r in range(9):
            for c in range(9):
                val = self.initial_puzzle[r][c]
                entry = self.grid_entries[r][c]
                if val != 0:
                    self.grid_vars[r][c].set(str(val))
                    entry.config(state='readonly', font=('Helvetica', 12, 'bold'), style="") # Reset style
                else:
                    self.grid_vars[r][c].set("")
                    entry.config(state='normal', font=('Helvetica', 12, 'normal'), style="") # Reset style
        self.shared_state.log("Puzzle reset to initial state.", level=logging.DEBUG)

    def check_solution(self):
        if not self.solution:
            messagebox.showwarning("No Solution", "No puzzle solution is loaded.", parent=self.frame)
            return

        is_complete = True
        is_correct = True

        # Define styles for correct and incorrect entries temporarily
        s = ttk.Style()
        s.configure("Correct.TEntry", fieldbackground="lightgreen")
        s.configure("Incorrect.TEntry", fieldbackground="pink")
        s.configure("Normal.TEntry", fieldbackground="white") # Assuming default is white

        for r in range(9):
            for c in range(9):
                entry_val_str = self.grid_vars[r][c].get()
                entry_widget = self.grid_entries[r][c]

                if not entry_val_str: # Cell is empty
                    is_complete = False
                    entry_widget.config(style="Normal.TEntry") # No specific style for empty, or choose one
                    continue

                try:
                    entry_val = int(entry_val_str)
                    if entry_val == self.solution[r][c]:
                        if self.initial_puzzle[r][c] == 0: # Only style user-entered cells
                             entry_widget.config(style="Correct.TEntry")
                        else: # Pre-filled cell, should always be correct
                             entry_widget.config(style="") # Default style
                    else:
                        is_correct = False
                        if self.initial_puzzle[r][c] == 0:
                            entry_widget.config(style="Incorrect.TEntry")
                        else: # Pre-filled cell is somehow wrong (should not happen with predefined)
                            entry_widget.config(style="Incorrect.TEntry")
                except ValueError: # Should not happen with validation
                    is_correct = False
                    if self.initial_puzzle[r][c] == 0:
                        entry_widget.config(style="Incorrect.TEntry")


        if not is_complete and is_correct: # Partially filled but all entries so far are correct
            messagebox.showinfo("In Progress", "So far so good! Keep going.", parent=self.frame)
        elif not is_correct:
            messagebox.showerror("Incorrect", "Some numbers are incorrect. Check the highlighted cells.", parent=self.frame)
        elif is_complete and is_correct:
            messagebox.showinfo("Congratulations!", "You solved the Sudoku puzzle correctly!", parent=self.frame)

        self.shared_state.log(f"Solution check: Complete={is_complete}, Correct={is_correct}", level=logging.DEBUG)


    def on_destroy(self):
        # Clean up grid_vars and grid_entries if necessary, though Python's GC should handle it
        self.grid_vars.clear()
        self.grid_entries.clear()
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
