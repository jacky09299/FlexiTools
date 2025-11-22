import os
import json
import zipfile
import argparse
import sys

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return {}

def get_plugin_map(catalog):
    """Converts catalog list to a dict: {name: {'version': v, 'data': plugin_obj}}"""
    pmap = {}
    if 'plugins' not in catalog:
        return pmap

    for p in catalog['plugins']:
        name = p.get('name') or p.get('id') # Handle both existing format styles if mixed
        version = p.get('latest_version') or p.get('version')
        if name and version:
            pmap[name] = {'version': version, 'data': p}
    return pmap

def package_plugin(name, version, modules_dir, output_dir):
    """Zips the module directory."""
    source_dir = os.path.join(modules_dir, name)
    if not os.path.isdir(source_dir):
        print(f"Warning: Module directory not found: {source_dir}")
        return False

    # Ensure output directory exists: output_dir/docs/plugins/<name>/
    plugin_out_dir = os.path.join(output_dir, "docs", "plugins", name)
    os.makedirs(plugin_out_dir, exist_ok=True)

    zip_filename = f"{name}_{version}.zip"
    zip_path = os.path.join(plugin_out_dir, zip_filename)

    print(f"Packaging {name} v{version} -> {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                if "__pycache__" in dirs:
                    dirs.remove("__pycache__")

                for file in files:
                    # Filter out unnecessary files if needed, similar to original script
                    if file.endswith(".pyc"):
                        continue

                    file_path = os.path.join(root, file)
                    # Relpath should preserve the module folder: e.g. clock/main.py
                    rel_path = os.path.relpath(file_path, modules_dir)
                    zf.write(file_path, rel_path)
        return True
    except Exception as e:
        print(f"Failed to zip {name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Package changed plugins based on JSON diff.")
    parser.add_argument("--old", required=True, help="Path to old plugins.json")
    parser.add_argument("--new", required=True, help="Path to new plugins.json")
    parser.add_argument("--modules", default="modules", help="Path to modules directory")
    parser.add_argument("--output", default="dist", help="Output directory for zips")

    args = parser.parse_args()

    old_catalog = load_json(args.old)
    new_catalog = load_json(args.new)

    old_map = get_plugin_map(old_catalog)
    new_map = get_plugin_map(new_catalog)

    changed_count = 0

    for name, info in new_map.items():
        new_version = info['version']
        should_package = False

        if name not in old_map:
            print(f"New plugin detected: {name} (v{new_version})")
            should_package = True
        else:
            old_version = old_map[name]['version']
            if old_version != new_version:
                print(f"Version update detected for {name}: {old_version} -> {new_version}")
                should_package = True

        if should_package:
            if package_plugin(name, new_version, args.modules, args.output):
                changed_count += 1

    if changed_count == 0:
        print("No plugin changes detected.")
    else:
        print(f"Successfully packaged {changed_count} plugins.")

if __name__ == "__main__":
    main()
