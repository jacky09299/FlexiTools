import os
import json
import shutil
import zipfile

def package_plugins():
    modules_dir = "modules"
    docs_dir = "docs"
    plugins_dir = os.path.join(docs_dir, "plugins")

    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)

    catalog = {"plugins": []}
    base_url = "https://jacky09299.github.io/FlexiTools/plugins"

    for item in os.listdir(modules_dir):
        item_path = os.path.join(modules_dir, item)

        if os.path.isdir(item_path):
            manifest_path = os.path.join(item_path, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)

                    module_name = manifest.get("name", item)
                    version = manifest.get("version", "1.0.0")

                    # Create Zip
                    zip_filename = f"{module_name}.zip"
                    zip_path = os.path.join(plugins_dir, zip_filename)

                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        # Walk through the module directory and add files
                        # Structure in zip should be module_name/file.py
                        for root, dirs, files in os.walk(item_path):
                            # Skip __pycache__
                            if "__pycache__" in dirs:
                                dirs.remove("__pycache__")

                            for file in files:
                                if file == "__init__.py" or file == "manifest.json" or file.endswith(".json") or file.endswith(".py") or file.endswith(".png"):
                                    file_path = os.path.join(root, file)
                                    # Calculate relative path for archive
                                    rel_path = os.path.relpath(file_path, modules_dir)
                                    zf.write(file_path, rel_path)

                    print(f"Packaged {module_name} to {zip_path}")

                    # Add to catalog
                    manifest["url"] = f"{base_url}/{zip_filename}"
                    catalog["plugins"].append(manifest)

                except Exception as e:
                    print(f"Error processing {item}: {e}")

    # Write catalog
    catalog_path = os.path.join(docs_dir, "plugins.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Catalog generated at {catalog_path}")

if __name__ == "__main__":
    package_plugins()
