import tkinter as tk
from tkinter import ttk
import random
import logging

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class RecipeWheelModule(Module):
    def __init__(self, master, shared_state, module_name="RecipeWheel", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.recipes = [
            {"name": "Spaghetti Aglio e Olio",
             "ingredients": ["Spaghetti", "Garlic", "Olive Oil", "Red Pepper Flakes", "Parsley"],
             "steps": "1. Cook spaghetti. 2. Sauté garlic in olive oil. 3. Toss spaghetti with oil, garlic, pepper flakes. 4. Garnish with parsley."},
            {"name": "Scrambled Eggs",
             "ingredients": ["Eggs", "Butter", "Milk (optional)", "Salt", "Pepper"],
             "steps": "1. Whisk eggs, milk (if using), salt, pepper. 2. Melt butter in pan. 3. Pour egg mixture and cook, stirring gently."},
            {"name": "Grilled Cheese Sandwich",
             "ingredients": ["Bread slices", "Cheese slices", "Butter"],
             "steps": "1. Butter one side of each bread slice. 2. Place cheese between unbuttered sides. 3. Grill until golden brown and cheese is melted."},
            {"name": "Chicken Stir-fry",
             "ingredients": ["Chicken breast", "Mixed Vegetables (broccoli, carrots, bell peppers)", "Soy Sauce", "Ginger", "Garlic", "Rice"],
             "steps": "1. Cook rice. 2. Stir-fry chicken. 3. Add vegetables, ginger, garlic. 4. Add soy sauce. Serve over rice."},
            {"name": "Quesadillas",
             "ingredients": ["Tortillas", "Shredded Cheese", "Optional: Cooked Chicken, Beans, Salsa, Sour Cream"],
             "steps": "1. Place cheese (and other fillings) on one half of a tortilla. 2. Fold tortilla. 3. Cook on griddle or pan until golden and cheese is melted. 4. Serve with salsa/sour cream."},
            {"name": "Oatmeal",
             "ingredients": ["Rolled Oats", "Water or Milk", "Optional: Fruits, Nuts, Sweetener"],
             "steps": "1. Combine oats and liquid in a pot. 2. Bring to a boil, then simmer until creamy. 3. Add toppings as desired."},
            {"name": "Pancakes",
             "ingredients": ["Flour", "Baking Powder", "Salt", "Sugar", "Egg", "Milk", "Butter"],
             "steps": "1. Mix dry ingredients. 2. Mix wet ingredients. 3. Combine wet and dry. 4. Cook on a griddle."},
            {"name": "Caprese Salad",
             "ingredients": ["Tomatoes", "Fresh Mozzarella", "Fresh Basil", "Olive Oil", "Balsamic Glaze"],
             "steps": "1. Slice tomatoes and mozzarella. 2. Arrange with basil leaves. 3. Drizzle with olive oil and balsamic glaze."},
            {"name": "Tuna Salad Sandwich",
             "ingredients": ["Canned Tuna", "Mayonnaise", "Celery (optional)", "Onion (optional)", "Bread", "Lettuce"],
             "steps": "1. Mix tuna, mayonnaise, and chopped celery/onion. 2. Serve on bread with lettuce."},
            {"name": "Instant Noodles",
             "ingredients": ["Instant Ramen Pack", "Water", "Optional: Egg, Green Onions"],
             "steps": "1. Boil water. 2. Add noodles and seasoning. 3. Cook for 2-3 minutes. 4. Add optional toppings."},
            {"name": "Fruit Smoothie",
             "ingredients": ["Mixed Fruits (berries, banana, mango)", "Yogurt or Milk", "Optional: Honey, Spinach"],
             "steps": "1. Combine all ingredients in a blender. 2. Blend until smooth."},
            {"name": "Avocado Toast",
             "ingredients": ["Bread", "Avocado", "Salt", "Pepper", "Optional: Egg, Red Pepper Flakes"],
             "steps": "1. Toast bread. 2. Mash avocado and spread on toast. 3. Season with salt and pepper. Add optional toppings."},
            {"name": "Pasta with Tomato Sauce",
             "ingredients": ["Pasta", "Canned Tomato Sauce", "Onion", "Garlic", "Olive Oil", "Herbs (oregano, basil)"],
             "steps": "1. Cook pasta. 2. Sauté onion and garlic in olive oil. 3. Add tomato sauce and herbs, simmer. 4. Toss with pasta."},
            {"name": "Baked Potato",
             "ingredients": ["Potato", "Optional toppings: Butter, Sour Cream, Cheese, Bacon bits, Chives"],
             "steps": "1. Pierce potato with a fork. 2. Bake at 200°C (400°F) for 45-60 mins or microwave. 3. Add toppings."},
            {"name": "Simple Green Salad",
             "ingredients": ["Mixed Greens", "Cucumber", "Cherry Tomatoes", "Salad Dressing (e.g., vinaigrette)"],
             "steps": "1. Wash and combine greens, cucumber, tomatoes. 2. Toss with dressing before serving."},
            {"name": "Popcorn",
            "ingredients": ["Popcorn Kernels", "Oil or Butter", "Salt"],
            "steps": "1. Heat oil in a pot. 2. Add kernels, cover. 3. Shake until popping stops. 4. Season with salt/butter."},
            {"name": "Nachos",
            "ingredients": ["Tortilla Chips", "Shredded Cheese", "Optional: Jalapenos, Beans, Salsa, Guacamole"],
            "steps": "1. Spread chips on a baking sheet. 2. Top with cheese and other toppings. 3. Bake until cheese melts."},
            {"name": "Yogurt Parfait",
            "ingredients": ["Yogurt", "Granola", "Berries"],
            "steps": "1. Layer yogurt, granola, and berries in a glass."},
            {"name": "Hot Dog",
            "ingredients": ["Hot Dog Buns", "Sausages", "Optional: Ketchup, Mustard, Onions, Relish"],
            "steps": "1. Cook sausages (boil, grill, or pan-fry). 2. Place in buns with desired condiments."},
            {"name": "Peanut Butter Banana Sandwich",
            "ingredients": ["Bread", "Peanut Butter", "Banana (sliced)"],
            "steps": "1. Spread peanut butter on bread. 2. Top with banana slices. 3. Add another slice of bread."}
        ]

        self.wheel_label = None
        self.recipe_name_label = None
        self.ingredients_text = None
        self.steps_text = None

        self.spin_after_id = None
        self.current_spin_recipe_idx = 0
        self.spin_count = 0

        self.create_ui()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        content_frame = ttk.Frame(self.frame, padding="10")
        content_frame.pack(expand=True, fill=tk.BOTH)
        content_frame.columnconfigure(0, weight=1) # Make column 0 expandable

        # Wheel display (Label that changes rapidly)
        self.wheel_label = ttk.Label(content_frame, text="Recipe Wheel!", font=("Helvetica", 18, "bold"), anchor="center")
        self.wheel_label.grid(row=0, column=0, pady=10, sticky="ew")

        # Spin button
        spin_button = ttk.Button(content_frame, text="Spin the Wheel!", command=self.start_spin)
        spin_button.grid(row=1, column=0, pady=10)

        # Separator
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, sticky="ew", pady=10)

        # Selected Recipe Display Area
        recipe_display_frame = ttk.Frame(content_frame)
        recipe_display_frame.grid(row=3, column=0, sticky="nsew")
        recipe_display_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(3, weight=1) # Allow recipe display to expand

        self.recipe_name_label = ttk.Label(recipe_display_frame, text="Recipe: ", font=("Helvetica", 14, "underline"))
        self.recipe_name_label.grid(row=0, column=0, sticky="w", pady=(0,5))

        # Ingredients
        ttk.Label(recipe_display_frame, text="Ingredients:", font=("Helvetica", 12, "bold")).grid(row=1, column=0, sticky="w", pady=(5,2))

        ing_frame = ttk.Frame(recipe_display_frame) # Frame for text and scrollbar
        ing_frame.grid(row=2, column=0, sticky="nsew", pady=(0,5))
        ing_frame.columnconfigure(0, weight=1)
        ing_frame.rowconfigure(0, weight=1)
        recipe_display_frame.rowconfigure(2, weight=1)


        self.ingredients_text = tk.Text(ing_frame, wrap=tk.WORD, height=4, borderwidth=1, relief="solid")
        self.ingredients_text.grid(row=0, column=0, sticky="nsew")
        ing_scroll = ttk.Scrollbar(ing_frame, orient=tk.VERTICAL, command=self.ingredients_text.yview)
        ing_scroll.grid(row=0, column=1, sticky="ns")
        self.ingredients_text.config(yscrollcommand=ing_scroll.set)


        # Steps
        ttk.Label(recipe_display_frame, text="Steps:", font=("Helvetica", 12, "bold")).grid(row=3, column=0, sticky="w", pady=(5,2))

        steps_frame = ttk.Frame(recipe_display_frame) # Frame for text and scrollbar
        steps_frame.grid(row=4, column=0, sticky="nsew")
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.rowconfigure(0, weight=1)
        recipe_display_frame.rowconfigure(4, weight=1)


        self.steps_text = tk.Text(steps_frame, wrap=tk.WORD, height=6, borderwidth=1, relief="solid")
        self.steps_text.grid(row=0, column=0, sticky="nsew")
        steps_scroll = ttk.Scrollbar(steps_frame, orient=tk.VERTICAL, command=self.steps_text.yview)
        steps_scroll.grid(row=0, column=1, sticky="ns")
        self.steps_text.config(yscrollcommand=steps_scroll.set)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def start_spin(self):
        if self.spin_after_id: # Prevent multiple spins
            self.frame.after_cancel(self.spin_after_id)
            self.spin_after_id = None

        self.spin_count = 0
        self.current_spin_recipe_idx = random.randint(0, len(self.recipes) - 1) # Start from a random recipe
        self._perform_spin_animation()

    def _perform_spin_animation(self):
        if not self.recipes:
            self.wheel_label.config(text="No Recipes!")
            return

        self.wheel_label.config(text=self.recipes[self.current_spin_recipe_idx]["name"])
        self.current_spin_recipe_idx = (self.current_spin_recipe_idx + 1) % len(self.recipes)
        self.spin_count += 1

        if self.spin_count < 20 + random.randint(0,10): # Spin for about 20-30 steps
            delay = 50 + self.spin_count * 5 # Slow down the spin gradually
            self.spin_after_id = self.frame.after(delay, self._perform_spin_animation)
        else:
            self.spin_after_id = None
            final_recipe_index = random.randint(0, len(self.recipes) - 1)
            self.display_recipe(self.recipes[final_recipe_index])

    def display_recipe(self, recipe):
        self.wheel_label.config(text=recipe["name"]) # Final selected name on wheel
        self.recipe_name_label.config(text=f"Recipe: {recipe['name']}")

        self.ingredients_text.config(state=tk.NORMAL)
        self.ingredients_text.delete('1.0', tk.END)
        for item in recipe["ingredients"]:
            self.ingredients_text.insert(tk.END, f"- {item}\n")
        self.ingredients_text.config(state=tk.DISABLED)

        self.steps_text.config(state=tk.NORMAL)
        self.steps_text.delete('1.0', tk.END)
        self.steps_text.insert(tk.END, recipe["steps"])
        self.steps_text.config(state=tk.DISABLED)

        self.shared_state.log(f"Recipe selected: {recipe['name']}", level=logging.INFO)

    def on_destroy(self):
        if self.spin_after_id:
            self.frame.after_cancel(self.spin_after_id)
            self.spin_after_id = None
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
