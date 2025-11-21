# Localization Workflow for Developers

This guide describes a simple workflow to add multi-language support (Localization/L10n) to your FlexiTools modules. The goal is to allow you to focus on feature development first, and then "enable" languages at the end.

## The Workflow: "Develop First, Localize Later"

### Step 1: Develop Your Feature (In English)
Write your module as you normally would. Don't worry about translation files or keys yet. Just put English text directly in your code.

**Example Code (`modules/my_module.py`):**
```python
class MyModule(Module):
    def create_ui(self):
        # Save reference to label so we can update it later
        self.greeting_label = ttk.Label(self.frame, text="Hello World")
        self.greeting_label.pack()
```

### Step 2: Identify User-Visible Strings
Once your feature works, look through your code for any string that a user will see (labels, button text, window titles, error messages).

*   `"Hello World"` -> Needs translation.
*   `"internal_id"` -> No translation needed.

### Step 3: Create Translation Keys
Open `locales/en_US.json` and `locales/zh_TW.json`. Add a unique key for your string. A good naming convention is: `module_<module_name>_<element>_<description>`.

**`locales/en_US.json`:**
```json
{
    ...
    "module_mymod_lbl_hello": "Hello World"
}
```

**`locales/zh_TW.json`:**
```json
{
    ...
    "module_mymod_lbl_hello": "你好，世界"
}
```

### Step 4: Replace Hardcoded Strings
Go back to your Python code and replace the hardcoded string with a call to `self.tr()`.

**Updated Code:**
```python
    def create_ui(self):
        # Use the key you just created
        text = self.tr("module_mymod_lbl_hello", default="Hello World")
        self.greeting_label = ttk.Label(self.frame, text=text)
        self.greeting_label.pack()
```

### Step 5: Implement `update_language`
To support *instant* language switching (without restarting the app), you must tell the module how to refresh its text. Override the `update_language` method.

**Add this method to your class:**
```python
    def update_language(self):
        # 1. Call the base method to update the module title automatically
        super().update_language()

        # 2. Check if UI is initialized (Guard Clause)
        if not getattr(self, 'greeting_label', None):
            return

        # 3. Update your widgets with the new translated text
        self.greeting_label.config(text=self.tr("module_mymod_lbl_hello"))
```

---

## Summary Checklist
1.  [ ] Feature works with English text.
2.  [ ] Strings added to `locales/*.json`.
3.  [ ] Code uses `self.tr("key")`.
4.  [ ] `update_language()` implemented to refresh widgets.
