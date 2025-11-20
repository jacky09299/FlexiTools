import ast
import os
import json
import sys

def get_all_python_files():
    files = []
    # Root files
    for f in os.listdir('.'):
        if f.endswith('.py') and f not in ['import_detect.py', 'extract_uml_info.py']: # Exclude utils that are not part of core app logic
             files.append(f)

    # Modules files
    if os.path.exists('modules'):
        for f in os.listdir('modules'):
            if f.endswith('.py'):
                files.append(os.path.join('modules', f))

    return files

def extract_info_from_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding if utf-8 fails (though unlikely for python files)
        with open(filepath, 'r', encoding='cp950') as f: # traditional chinese windows default
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return [], []

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error parsing {filepath}: {e}")
        return [], []

    classes = []
    imports = []

    # Helper to get attributes from __init__ and other methods
    def get_attributes(class_node):
        attrs = set()
        for node in ast.walk(class_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                        attrs.add(target.attr)
            elif isinstance(node, ast.AnnAssign):
                 if isinstance(node.target, ast.Attribute) and isinstance(node.target.value, ast.Name) and node.target.value.id == 'self':
                        attrs.add(node.target.attr)
        return list(attrs)

    # Helper to get methods
    def get_methods(class_node):
        methods = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                methods.append(node.name)
        return methods

    # Scan for imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    # Scan for classes
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                "id": node.name,
                "name": node.name,
                "file": filepath.replace('\\', '/'),
                "type": "class",
                "description": ast.get_docstring(node) or "No description available.",
                "attributes": get_attributes(node),
                "methods": get_methods(node),
                "bases": [base.id for base in node.bases if isinstance(base, ast.Name)]
            }
            classes.append(class_info)

    # If no classes found, but it's a python file, maybe treat it as a module if it has functions
    if not classes:
        functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
        if functions:
             # Check if it's a standalone module file like style_manager.py
             module_name = os.path.basename(filepath).replace('.py', '')
             # Convert filename to CamelCase id if possible, or just use filename
             module_id = ''.join(x.capitalize() or '_' for x in module_name.split('_'))

             classes.append({
                 "id": module_id,
                 "name": module_name,
                 "file": filepath.replace('\\', '/'),
                 "type": "module",
                 "description": ast.get_docstring(tree) or "Module containing utility functions.",
                 "attributes": [],
                 "methods": functions
             })

    return classes, imports

def main():
    files = get_all_python_files()
    all_classes = []
    all_imports = {} # file -> list of imports

    for f in files:
        classes, imports = extract_info_from_file(f)
        all_classes.extend(classes)
        all_imports[f.replace('\\', '/')] = imports

    # Build relationships
    relationships = []

    # 1. Inheritance
    class_map = {c['id']: c for c in all_classes}
    for c in all_classes:
        if 'bases' in c:
            for base in c['bases']:
                if base in class_map:
                    relationships.append({
                        "source": c['id'],
                        "target": base,
                        "type": "inheritance",
                        "label": "extends"
                    })

    # 2. Dependency/Association (simple guess based on file imports)
    # This is loose. If file A imports module B, and module B defines Class B, we assume Class A (in file A) might use Class B.
    # Or more simply: Class A (in file A) -> Class B (if file A imports file B's module)

    # Map module names to files?
    # modules/notepad.py -> module 'modules.notepad' or 'notepad' (depending on sys.path)
    # In this project, root is added to sys.path probably.

    # Let's look at explicit relationships we can infer.
    # If 'SharedState' is imported, it's a dependency.

    for c in all_classes:
        file_imports = all_imports.get(c['file'], [])
        for imp in file_imports:
            # If import matches a known class name or module name
            # Check against all class IDs
            for target_c in all_classes:
                if target_c['id'] == c['id']: continue

                # Exact match of class name in imports
                if target_c['id'] in imp or imp.endswith(target_c['name']):
                     relationships.append({
                        "source": c['id'],
                        "target": target_c['id'],
                        "type": "dependency",
                        "label": "imports"
                    })
                # Or if import matches the filename of the target class
                elif target_c['file'].endswith(imp + '.py') or target_c['file'].endswith(imp.split('.')[-1] + '.py'):
                     relationships.append({
                        "source": c['id'],
                        "target": target_c['id'],
                        "type": "dependency",
                        "label": "imports"
                    })

    # Deduplicate relationships
    unique_rels = []
    seen_rels = set()
    for r in relationships:
        key = f"{r['source']}-{r['target']}-{r['type']}"
        if key not in seen_rels:
            seen_rels.add(key)
            unique_rels.append(r)

    output = {
        "classes": all_classes,
        "relationships": unique_rels
    }

    # Clean up 'bases' field from classes in output if we don't want it in final json (though it's useful info)
    # The requested format doesn't explicitly forbid extra fields, but let's keep it clean.
    for c in output['classes']:
        if 'bases' in c:
            del c['bases']

    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
