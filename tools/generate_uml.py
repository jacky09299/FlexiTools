import ast
import os
import json
import sys

def get_classes_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            node = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return []

    classes = []
    for n in node.body:
        if isinstance(n, ast.ClassDef):
            bases = []
            for base in n.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)

            methods = []
            for item in n.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)

            classes.append({
                "name": n.name,
                "bases": bases,
                "methods": methods,
                "filepath": filepath
            })
    return classes

def get_all_structure():
    core_files = [
        "main.py", "ui.py", "shared_state.py",
        "update_manager.py", "style_manager.py", "splash_ui.py"
    ]

    modules_dir = "modules"
    module_files = []
    if os.path.exists(modules_dir):
        module_files = [os.path.join(modules_dir, f) for f in os.listdir(modules_dir) if f.endswith(".py")]

    all_data = {"core": [], "modules": []}

    for f in core_files:
        if os.path.exists(f):
            all_data["core"].extend(get_classes_from_file(f))

    for f in module_files:
        if os.path.exists(f):
            all_data["modules"].extend(get_classes_from_file(f))

    return all_data

def generate_mermaid_core(data):
    lines = ["classDiagram"]

    # Add Core classes
    for cls in data["core"]:
        name = cls["name"]
        # Clean up name if needed? usually fine.
        lines.append(f"    class {name} {{")
        for m in cls["methods"]:
            if not m.startswith("_") or m == "__init__":
                 lines.append(f"        +{m}()")
        lines.append("    }")

        # Relationships
        for base in cls["bases"]:
            if base != "object":
                lines.append(f"    {base} <|-- {name}")

    return "\n".join(lines)

def generate_mermaid_modules(data):
    lines = ["classDiagram"]

    # Define Base Module class first (it's in core, but referenced here)
    lines.append("    class Module {")
    lines.append("        +create_ui()")
    lines.append("        +on_destroy()")
    lines.append("    }")

    count = 0
    for cls in data["modules"]:
        name = cls["name"]
        if "Module" in cls["bases"] or name.endswith("Module") or name == "Module":
             # Only include classes that look like modules or inherit from Module
             pass
        else:
             # Maybe helper classes? Include them but connect them if possible
             pass

        lines.append(f"    class {name} {{")
        # Limit methods to avoid huge diagram
        method_count = 0
        for m in cls["methods"]:
            if m == "__init__" or m == "create_ui" or m == "on_destroy":
                lines.append(f"        +{m}()")
            elif not m.startswith("_") and method_count < 5:
                lines.append(f"        +{m}()")
                method_count += 1
        if len(cls["methods"]) > 8:
            lines.append("        +...")
        lines.append("    }")

        for base in cls["bases"]:
            lines.append(f"    {base} <|-- {name}")

    return "\n".join(lines)

def generate_mermaid_architecture():
    return """graph TD
    subgraph "Entry Point"
        Main[main.py]
        Splash[splash_ui.py]
    end

    subgraph "Core System"
        UI[ui.py / ModularGUI]
        SharedState[shared_state.py]
        UpdateMgr[update_manager.py]
        StyleMgr[style_manager.py]
    end

    subgraph "Modules Layer"
        ModulesFolder[modules/]
        BaseModule[Module Class]
    end

    subgraph "Storage"
        Config[layout_config.json]
        Saves[saves/ directory]
    end

    Main -->|Initializes| SharedState
    Main -->|Launches| Splash
    Main -->|Starts| UI
    UI -->|Uses| SharedState
    UI -->|Uses| StyleMgr
    UI -->|Checks| UpdateMgr
    UI -->|Loads| ModulesFolder
    ModulesFolder -.->|Inherits| BaseModule
    UI -->|Reads/Writes| Config
    ModulesFolder -->|Reads/Writes| Saves
    """

def generate_html(core_mermaid, modules_mermaid, arch_mermaid):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlexiTools UML Documentation</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #1e1e1e; color: #e0e0e0; }}
        .nav-tabs .nav-link {{ color: #aaa; }}
        .nav-tabs .nav-link.active {{ background-color: #2d2d2d; color: #fff; border-color: #444 #444 #2d2d2d; }}
        .tab-content {{ background-color: #2d2d2d; padding: 20px; border: 1px solid #444; border-top: none; }}
        .mermaid {{ background-color: #fff; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        h1 {{ margin-top: 20px; margin-bottom: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>FlexiTools UML Diagrams</h1>

        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="arch-tab" data-bs-toggle="tab" data-bs-target="#arch" type="button" role="tab">System Architecture</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="core-tab" data-bs-toggle="tab" data-bs-target="#core" type="button" role="tab">Core Classes</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="modules-tab" data-bs-toggle="tab" data-bs-target="#modules" type="button" role="tab">Modules Structure</button>
            </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            <div class="tab-pane fade show active" id="arch" role="tabpanel">
                <div class="mermaid">
{arch_mermaid}
                </div>
            </div>
            <div class="tab-pane fade" id="core" role="tabpanel">
                <div class="mermaid">
{core_mermaid}
                </div>
            </div>
            <div class="tab-pane fade" id="modules" role="tabpanel">
                <div class="mermaid">
{modules_mermaid}
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>
"""

def main():
    print("Analyzing structure...")
    data = get_all_structure()

    print("Generating Core Diagram...")
    core_mermaid = generate_mermaid_core(data)

    print("Generating Modules Diagram...")
    modules_mermaid = generate_mermaid_modules(data)

    print("Generating Architecture Diagram...")
    arch_mermaid = generate_mermaid_architecture()

    print("Building HTML...")
    html_content = generate_html(core_mermaid, modules_mermaid, arch_mermaid)

    output_path = os.path.join("docs", "uml.html")
    if not os.path.exists("docs"):
        os.makedirs("docs")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Done! Saved to {output_path}")

if __name__ == "__main__":
    main()
