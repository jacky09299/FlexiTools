import os
import json
import shutil
import zipfile

def package_plugins():
    modules_dir = "modules"
    docs_dir = "docs"
    plugins_base_dir = os.path.join(docs_dir, "plugins")
    catalog_path = os.path.join(docs_dir, "plugins.json")

    # Base URL for GitHub Pages
    base_url = "https://jacky09299.github.io/FlexiTools/plugins"

    # Load existing catalog if it exists
    catalog = {"plugins": []}
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing catalog: {e}")

    # Helper to find plugin entry in catalog
    def get_plugin_entry(name):
        for p in catalog["plugins"]:
            if p.get("id") == name:
                return p
        return None

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

                    # Directory for this module's zips
                    module_plugin_dir = os.path.join(plugins_base_dir, module_name)
                    if not os.path.exists(module_plugin_dir):
                        os.makedirs(module_plugin_dir)

                    # Zip Filename: module_version.zip
                    zip_filename = f"{module_name}_{version}.zip"
                    zip_path = os.path.join(module_plugin_dir, zip_filename)

                    # Create Zip if it doesn't exist (or force update? simpler to recreate)
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for root, dirs, files in os.walk(item_path):
                            if "__pycache__" in dirs:
                                dirs.remove("__pycache__")
                            for file in files:
                                if file == "__init__.py" or file == "manifest.json" or file.endswith(".json") or file.endswith(".py") or file.endswith(".png"):
                                    file_path = os.path.join(root, file)
                                    rel_path = os.path.relpath(file_path, modules_dir) # e.g. module_name/init.py
                                    zf.write(file_path, rel_path)

                    print(f"Packaged {module_name} v{version} to {zip_path}")

                    # Update Catalog
                    entry = get_plugin_entry(module_name)
                    if not entry:
                        entry = {
                            "id": module_name,
                            "title": manifest.get("title", module_name),
                            "description": manifest.get("description", ""),
                            "author": manifest.get("author", ""),
                            "latest_version": version,
                            "versions": []
                        }
                        catalog["plugins"].append(entry)

                    # Update metadata (title/desc might change)
                    entry["title"] = manifest.get("title", entry["title"])
                    entry["description"] = manifest.get("description", entry["description"])
                    entry["author"] = manifest.get("author", entry["author"])
                    entry["latest_version"] = version # Assuming source is always latest

                    # Add version to list if not present
                    version_url = f"{base_url}/{module_name}/{zip_filename}"
                    version_exists = False
                    for v in entry["versions"]:
                        if v["version"] == version:
                            v["url"] = version_url # Update URL just in case
                            version_exists = True
                            break

                    if not version_exists:
                        entry["versions"].append({
                            "version": version,
                            "url": version_url
                        })

                    # Sort versions (simple string sort, could be improved to semver)
                    # entry["versions"].sort(key=lambda x: x["version"], reverse=True)

                except Exception as e:
                    print(f"Error processing {item}: {e}")

    # Write catalog
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Catalog updated at {catalog_path}")

if __name__ == "__main__":
    package_plugins()
