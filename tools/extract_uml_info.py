import ast
import os
import json
import sys
from collections import defaultdict

# --- Data Structures ---

class ClassInfo:
    def __init__(self, name, filepath, docstring):
        self.id = name
        self.name = name
        self.file = filepath.replace('\\', '/')
        self.type = "class"
        self.description = docstring or "No description available."
        self.attributes = set()
        self.methods = []
        self.bases = []
        self.module_name = os.path.splitext(os.path.basename(filepath))[0]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "file": self.file,
            "type": self.type,
            "description": self.description,
            "attributes": list(self.attributes),
            "methods": self.methods,
            "bases": self.bases
        }

class Relationship:
    def __init__(self, source, target, rel_type, label):
        self.source = source
        self.target = target
        self.type = rel_type
        self.label = label

    def to_dict(self):
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "label": self.label
        }

    def __eq__(self, other):
        return (self.source == other.source and
                self.target == other.target and
                self.type == other.type)

    def __hash__(self):
        return hash((self.source, self.target, self.type))

# --- Helpers ---

def get_all_python_files():
    files = []
    # Root files
    for f in os.listdir('.'):
        if f.endswith('.py') and f not in ['extract_uml_info.py', 'generate_nsis.py']:
             files.append(f)

    # Modules files
    if os.path.exists('modules'):
        for f in os.listdir('modules'):
            if f.endswith('.py'):
                files.append(os.path.join('modules', f))

    return files

def resolve_name(name, imports, module_aliases):
    """
    Resolve a name (e.g., 'Module', 'tk.Frame') to its potential full name or origin.
    """
    parts = name.split('.')
    root = parts[0]

    candidates = []

    # 1. Check explicit imports: from X import Y
    if root in imports:
        origin_module = imports[root]
        candidates.append(origin_module + "." + root)

    # 2. Check module aliases: import tkinter as tk
    if root in module_aliases:
        real_module = module_aliases[root]
        if len(parts) > 1:
            candidates.append(real_module + "." + ".".join(parts[1:]))
        else:
            candidates.append(real_module)

    # 3. As is
    candidates.append(name)

    return candidates

# --- Analysis Visitors ---

class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = {} # name -> source_module (e.g. 'Module' -> 'main')
        self.module_aliases = {} # alias -> module_name (e.g. 'tk' -> 'tkinter')

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.module_aliases[asname] = name

    def visit_ImportFrom(self, node):
        module = node.module or ''
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.imports[asname] = module

class ClassVisitor(ast.NodeVisitor):
    def __init__(self, filepath, imports, module_aliases):
        self.filepath = filepath
        self.imports = imports
        self.module_aliases = module_aliases
        self.classes = {} # class_name -> ClassInfo

    def visit_ClassDef(self, node):
        docstring = ast.get_docstring(node)
        class_info = ClassInfo(node.name, self.filepath, docstring)

        # Bases (Inheritance)
        for base in node.bases:
            if isinstance(base, ast.Name):
                class_info.bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                parts = []
                curr = base
                while isinstance(curr, ast.Attribute):
                    parts.insert(0, curr.attr)
                    curr = curr.value
                if isinstance(curr, ast.Name):
                    parts.insert(0, curr.id)
                class_info.bases.append(".".join(parts))

        # Methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                class_info.methods.append(item.name)

        self.classes[node.name] = class_info

class RelationshipVisitor(ast.NodeVisitor):
    def __init__(self, current_class, all_classes_names, imports, module_aliases):
        self.current_class = current_class
        self.all_classes_names = all_classes_names
        self.imports = imports
        self.module_aliases = module_aliases

        self.relationships = []
        self.init_args = {} # arg_name -> type_annotation

        # Track structural relationships to avoid duplicate weak dependencies
        self.structural_targets = set()

    def _is_known_class(self, name):
        if not name: return None
        if name in self.all_classes_names:
            return name
        candidates = resolve_name(name, self.imports, self.module_aliases)
        for cand in candidates:
            simple = cand.split('.')[-1]
            if simple in self.all_classes_names:
                return simple
        return None

    def _add_rel(self, target, rtype, label):
        if target and target != self.current_class.name:
            self.relationships.append(Relationship(self.current_class.name, target, rtype, label))
            if rtype in ['composition', 'aggregation', 'association', 'inheritance']:
                self.structural_targets.add(target)

    def visit_ClassDef(self, node):
        # Class Level Associations (AnnAssign)
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign):
                annotation = self._get_full_name(stmt.annotation)
                target = self._is_known_class(annotation)
                if target:
                    self._add_rel(target, "association", "associated-with")

        # Process methods
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                self.visit_FunctionDef(stmt)

    def visit_FunctionDef(self, node):
        if node.name == '__init__':
            # 1. Parse Arguments for Aggregation
            for arg in node.args.args:
                if arg.arg == 'self': continue
                annotation = None
                if arg.annotation:
                    annotation = self._get_full_name(arg.annotation)

                self.init_args[arg.arg] = annotation

                target = self._is_known_class(annotation)
                if target:
                    self._add_rel(target, "aggregation", "has-a (param)")

            # 2. Walk body for Composition/Aggregation/Association
            for stmt in node.body:
                self.visit_init_stmt(stmt)
        else:
            # 3. Other methods -> Dependency
            self.visit_method_body(node)

    def _get_full_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_full_name(node.value) + "." + node.attr
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value # Handle forward references in string
        return ""

    def visit_init_stmt(self, node):
        target_attr = None
        value = None
        annotation = None

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                    target_attr = target.attr
            value = node.value
        elif isinstance(node, ast.AnnAssign):
             if isinstance(node.target, ast.Attribute) and isinstance(node.target.value, ast.Name) and node.target.value.id == 'self':
                target_attr = node.target.attr
             value = node.value
             annotation = self._get_full_name(node.annotation)

        if target_attr:
            self.current_class.attributes.add(target_attr)

            # Logic for relationship type

            # 1. Association via Type Hint (weakest)
            if annotation:
                target = self._is_known_class(annotation)
                if target:
                    self._add_rel(target, "association", "associated-with")

            if value:
                # 2. Composition: self.x = Class(...)
                if isinstance(value, ast.Call):
                    func_name = self._get_full_name(value.func)
                    target = self._is_known_class(func_name)
                    if target:
                        self._add_rel(target, "composition", "composed-of")

                # 3. Aggregation: self.x = arg
                elif isinstance(value, ast.Name):
                    if value.id in self.init_args:
                        # Already handled if type hint existed in args
                        # If no type hint in args, try heuristic
                        heuristic = self._heuristic_name_match(value.id)
                        if heuristic and heuristic not in self.structural_targets:
                             self._add_rel(heuristic, "aggregation", "has-a (arg)")

    def visit_method_body(self, node):
        for child in ast.walk(node):
            # Instantiation -> Dependency
            if isinstance(child, ast.Call):
                func_name = self._get_full_name(child.func)
                target = self._is_known_class(func_name)
                if target:
                    self._add_rel(target, "dependency", "uses")

            # Type hint -> Dependency
            if isinstance(child, ast.AnnAssign):
                annotation = self._get_full_name(child.annotation)
                target = self._is_known_class(annotation)
                if target:
                    self._add_rel(target, "dependency", "uses (var)")

    def _heuristic_name_match(self, var_name):
        camel = "".join(x.capitalize() or '_' for x in var_name.split('_'))
        if camel in self.all_classes_names: return camel
        cap = var_name.capitalize()
        if cap in self.all_classes_names: return cap
        return None

# --- Main Execution ---

def main():
    files = get_all_python_files()
    all_classes_info = {}
    all_imports = {}

    # Pass 1: Collect
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            tree = ast.parse(content)

            imp = ImportVisitor()
            imp.visit(tree)
            all_imports[filepath] = {"imports": imp.imports, "aliases": imp.module_aliases}

            cv = ClassVisitor(filepath, imp.imports, imp.module_aliases)
            cv.visit(tree)
            for name, info in cv.classes.items():
                all_classes_info[name] = info
        except: continue

    all_class_names = set(all_classes_info.keys())
    final_relationships = set()
    structural_map = defaultdict(set) # source -> set(targets) for inheritance/comp/agg/assoc

    # Pass 2: Analyze
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            tree = ast.parse(content)
        except: continue

        imports_data = all_imports.get(filepath, {"imports":{}, "aliases":{}})

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name not in all_classes_info: continue

                # Inheritance
                for base in all_classes_info[node.name].bases:
                    simple = base.split('.')[-1]
                    if simple in all_class_names:
                         rel = Relationship(node.name, simple, "inheritance", "extends")
                         final_relationships.add(rel)
                         structural_map[node.name].add(simple)

                # Visitor for others
                rv = RelationshipVisitor(all_classes_info[node.name], all_class_names, imports_data["imports"], imports_data["aliases"])
                rv.visit(node) # Visit ClassDef to catch class-level attributes and methods

                for rel in rv.relationships:
                    final_relationships.add(rel)
                    if rel.type != 'dependency':
                        structural_map[node.name].add(rel.target)

    # Filter Dependencies if Stronger Relationship Exists
    cleaned_relationships = []
    for rel in final_relationships:
        if rel.type == 'dependency':
            # If there is already a structural relationship, skip dependency
            if rel.target in structural_map[rel.source]:
                continue
        cleaned_relationships.append(rel.to_dict())

    output = {
        "classes": [c.to_dict() for c in all_classes_info.values()],
        "relationships": cleaned_relationships
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
