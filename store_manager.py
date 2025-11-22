import os
import json
import shutil
import zipfile
import threading
import logging

# Try importing requests, but handle if not available (though it should be for store to work)
try:
    import requests
except ImportError:
    requests = None

class StoreManager:
    CATALOG_URL = "https://jacky09299.github.io/FlexiTools/plugins.json"

    def __init__(self, modules_dir, shared_state):
        self.modules_dir = modules_dir
        self.shared_state = shared_state
        self.catalog = {}

    def fetch_catalog(self):
        if not requests:
            self.shared_state.log("Requests library not found. Cannot fetch catalog.", "ERROR")
            return None
        try:
            self.shared_state.log(f"Fetching catalog from {self.CATALOG_URL}...")
            response = requests.get(self.CATALOG_URL, timeout=10)
            response.raise_for_status()
            self.catalog = response.json()
            self.shared_state.log(f"Fetched catalog with {len(self.catalog.get('plugins', []))} plugins.")
            return self.catalog
        except Exception as e:
            self.shared_state.log(f"Error fetching catalog: {e}", "ERROR")
            return None

    def get_installed_modules_info(self):
        """Returns a dict of installed modules and their versions."""
        installed = {}
        if not os.path.exists(self.modules_dir):
            return installed

        for item in os.listdir(self.modules_dir):
            manifest_path = os.path.join(self.modules_dir, item, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        installed[item] = data.get("version", "0.0.0")
                except:
                    pass
        return installed

    def install_plugin(self, module_name, url, callback=None):
        if not requests:
            if callback: callback(False, "Requests library missing")
            return

        def _install_thread():
            try:
                self.shared_state.log(f"Downloading {module_name} from {url}...")
                r = requests.get(url, stream=True)
                r.raise_for_status()

                zip_path = os.path.join(self.modules_dir, f"{module_name}.zip")
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

                self.shared_state.log(f"Extracting {module_name}...")

                # Validate Zip Structure before extracting?
                # Assuming zip contains "module_name/..." based on our CI script plan.

                # Safety: remove existing directory if present
                target_dir = os.path.join(self.modules_dir, module_name)
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.modules_dir)

                os.remove(zip_path)
                self.shared_state.log(f"Installed {module_name} successfully.")
                if callback: callback(True, f"Installed {module_name}")
            except Exception as e:
                self.shared_state.log(f"Failed to install {module_name}: {e}", "ERROR")
                # Clean up zip if failed
                if os.path.exists(zip_path):
                    try: os.remove(zip_path)
                    except: pass
                if callback: callback(False, str(e))

        threading.Thread(target=_install_thread, daemon=True).start()

    def uninstall_plugin(self, module_name):
        path = os.path.join(self.modules_dir, module_name)
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                self.shared_state.log(f"Uninstalled {module_name}.")
                return True, "Uninstalled successfully"
            except Exception as e:
                self.shared_state.log(f"Error uninstalling {module_name}: {e}", "ERROR")
                return False, str(e)
        return False, "Module not found"
