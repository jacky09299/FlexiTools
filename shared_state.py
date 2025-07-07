import logging

class SharedState:
    def __init__(self):
        self.variables = {}
        self.observers = {}
        self.log_callback = None
        self.splash_log_callback = None
        self.splash_progress_callback = None # Added for progress bar
        self._setup_logging()

    def set_log_callback(self, callback):
        self.log_callback = callback

    def set_splash_log_callback(self, callback):
        self.splash_log_callback = callback

    def clear_splash_log_callback(self):
        self.splash_log_callback = None

    def set_splash_progress_callback(self, callback):
        self.splash_progress_callback = callback

    def clear_splash_progress_callback(self):
        self.splash_progress_callback = None

    def update_splash_progress(self, value: int):
        if self.splash_progress_callback:
            try:
                self.splash_progress_callback(value)
            except Exception as e:
                self.logger.error(f"Error in splash_progress_callback: {e}")

    def _setup_logging(self):
        self.logger = logging.getLogger("ModularGUI")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.log("SharedState initialized")

    def get(self, key, default=None):
        return self.variables.get(key, default)

    def set(self, key, value):
        self.variables[key] = value
        self.log(f"Set variable '{key}' to '{value}'")
        self.notify_observers(key, value)

    def log(self, message, level=logging.INFO):
        log_entry = f"{logging.getLevelName(level)}: {message}"
        if level == logging.DEBUG:
            self.logger.debug(message)
        elif level == logging.INFO:
            self.logger.info(message)
        elif level == logging.WARNING:
            self.logger.warning(message)
        elif level == logging.ERROR:
            self.logger.error(message)
        elif level == logging.CRITICAL:
            self.logger.critical(message)

        if self.log_callback:
            try:
                self.log_callback(log_entry)
            except Exception as e:
                self.logger.error(f"Error in log_callback: {e}")

        if self.splash_log_callback:
            try:
                # We only want the message part for the splash, not the level
                self.splash_log_callback(message)
            except Exception as e:
                self.logger.error(f"Error in splash_log_callback: {e}")

    def add_observer(self, key, callback):
        if key not in self.observers:
            self.observers[key] = []
        self.observers[key].append(callback)
        self.log(f"Added observer for variable '{key}'")

    def remove_observer(self, key, callback):
        if key in self.observers and callback in self.observers[key]:
            self.observers[key].remove(callback)
            if not self.observers[key]:
                del self.observers[key]
            self.log(f"Removed observer for variable '{key}'")

    def notify_observers(self, key, value):
        if key in self.observers:
            for callback in self.observers[key]:
                try:
                    callback(key, value)
                except Exception as e:
                    self.log(f"Error notifying observer for '{key}': {e}", level=logging.ERROR)

if __name__ == '__main__':
    # Example Usage
    shared_state = SharedState()

    # Set some variables
    shared_state.set("username", "Alice")
    shared_state.set("theme", "dark")

    # Get variables
    print(f"Username: {shared_state.get('username')}")
    print(f"Theme: {shared_state.get('theme')}")
    print(f"NonExistent: {shared_state.get('non_existent_key', 'default_value')}")

    # Logging
    shared_state.log("This is an info message.")
    shared_state.log("This is a warning message.", level=logging.WARNING)

    # Observer pattern
    def theme_observer(key, value):
        print(f"OBSERVER: Theme changed! New theme: {value}")

    shared_state.add_observer("theme", theme_observer)
    shared_state.set("theme", "light") # This should trigger the observer

    # Example of using SharedState without saving/loading config
    new_shared_state = SharedState()
    new_shared_state.set("username", "Bob") # This will not persist anywhere
    print(f"Username from new_shared_state: {new_shared_state.get('username')}")
    print(f"Username from original shared_state: {shared_state.get('username')}") # Still "Alice"
