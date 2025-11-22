import json
import os
import logging

class LocalizationManager:
    def __init__(self, shared_state, locale_dir="locales", modules_dir="modules", default_locale="zh_TW"):
        self.shared_state = shared_state
        self.locale_dir = locale_dir
        self.modules_dir = modules_dir
        self.current_locale = default_locale
        self.translations = {}

        # Ensure locale directory exists
        if not os.path.exists(self.locale_dir):
            os.makedirs(self.locale_dir)
            self.shared_state.log(f"Created locale directory: {self.locale_dir}", logging.INFO)

        # Load the default locale initially
        self.load_locale(self.current_locale)

        # Subscribe to language changes
        self.shared_state.add_observer("language", self._on_language_changed)

    def _on_language_changed(self, key, new_locale):
        if key == "language":
            self.load_locale(new_locale)

    def load_locale(self, locale_code):
        self.current_locale = locale_code
        file_path = os.path.join(self.locale_dir, f"{locale_code}.json")

        # 1. Load main locale file
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                self.shared_state.log(f"Loaded main locale: {locale_code}", logging.INFO)
            except Exception as e:
                self.shared_state.log(f"Failed to load locale {locale_code}: {e}", logging.ERROR)
                self.translations = {}
        else:
            self.shared_state.log(f"Locale file not found: {file_path}", logging.WARNING)
            self.translations = {}
            # Fallback logic could be here, but for now we just start empty

        # 2. Load and merge module locales
        self.load_module_locales(locale_code)

    def load_module_locales(self, locale_code):
        if not os.path.exists(self.modules_dir):
            return

        # Iterate over directories in modules_dir
        for module_name in os.listdir(self.modules_dir):
            module_path = os.path.join(self.modules_dir, module_name)
            if os.path.isdir(module_path):
                module_locale_path = os.path.join(module_path, "locales", f"{locale_code}.json")
                if os.path.exists(module_locale_path):
                    try:
                        with open(module_locale_path, 'r', encoding='utf-8') as f:
                            module_translations = json.load(f)
                            # Merge into main translations. Keys from module overwrite main if duplicates exist.
                            self.translations.update(module_translations)
                        # self.shared_state.log(f"Loaded module locale for {module_name}: {locale_code}", logging.DEBUG)
                    except Exception as e:
                        self.shared_state.log(f"Failed to load module locale for {module_name}: {e}", logging.ERROR)

    def get(self, key, default=None, **kwargs):
        """
        Get a translated string.
        Supports string formatting via kwargs.
        Example: get("welcome_message", user="Alice") -> "Welcome, Alice!"
        """
        val = self.translations.get(key, default if default is not None else key)
        if val and isinstance(val, str) and kwargs:
            try:
                return val.format(**kwargs)
            except Exception as e:
                self.shared_state.log(f"Error formatting string '{key}': {e}", logging.ERROR)
                return val
        return val
