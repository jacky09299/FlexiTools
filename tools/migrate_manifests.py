import os
import json
import importlib.util

def migrate_manifests():
    modules_dir = "modules"
    if not os.path.exists(modules_dir):
        print(f"Error: Directory '{modules_dir}' not found.")
        return

    for item in os.listdir(modules_dir):
        item_path = os.path.join(modules_dir, item)

        # Only process directories that have __init__.py
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
            manifest_path = os.path.join(item_path, "manifest.json")

            # Default values
            version = "1.0.0"
            description = f"The {item} module."
            title = item.replace("_", " ").title()
            author = "李紘宇"

            # Try to extract from __init__.py
            try:
                init_path = os.path.join(item_path, "__init__.py")
                spec = importlib.util.spec_from_file_location(item, init_path)
                if spec:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, "__version__"):
                        version = module.__version__

                    if module.__doc__:
                        description = module.__doc__.strip()

            except Exception as e:
                print(f"Warning: Could not parse {init_path} for metadata: {e}")

            manifest_data = {
                "name": item,
                "version": version,
                "title": title,
                "description": description,
                "author": author
            }

            # Write manifest.json
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)

            print(f"Created manifest for '{item}': {manifest_data}")

if __name__ == "__main__":
    migrate_manifests()
