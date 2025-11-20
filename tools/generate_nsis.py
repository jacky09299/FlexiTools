import os
import sys

def generate_nsis(template_path, output_path, modules_dir):
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    modules = []
    if os.path.exists(modules_dir):
        for filename in os.listdir(modules_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                modules.append(filename)

    modules.sort()

    # Generate Sections
    sections_code = []
    descriptions_code = []

    visibility_logic = []
    visibility_logic.append("Function ShowModules")
    for i in range(len(modules)):
        section_id = f"SEC_MOD_{i}"
        module_name = os.path.splitext(modules[i])[0]
        visibility_logic.append(f'  SectionSetText ${{{section_id}}} "{module_name}"')
    visibility_logic.append("FunctionEnd")

    visibility_logic.append("Function HideModules")
    for i in range(len(modules)):
        section_id = f"SEC_MOD_{i}"
        visibility_logic.append(f'  SectionSetText ${{{section_id}}} ""')
    visibility_logic.append("FunctionEnd")

    for i, module_file in enumerate(modules):
        module_name = os.path.splitext(module_file)[0]
        section_id = f"SEC_MOD_{i}"

        # Section definition
        # We assume the module file ends up in _internal/modules/ in the dist folder
        section = f"""
Section "{module_name}" {section_id}
  SetOutPath "$INSTDIR\\_internal\\modules"
  File "dist\\FlexiTools\\_internal\\modules\\{module_file}"
SectionEnd
"""
        sections_code.append(section)

        # Description
        description = f"""  !insertmacro MUI_DESCRIPTION_TEXT ${{{section_id}}} "Install {module_name} module" """
        descriptions_code.append(description)

    # Inject into template
    # We look for specific markers

    final_content = template_content.replace("; <<GENERATED_MODULE_SECTIONS>>", "\n".join(sections_code))
    final_content = final_content.replace("; <<GENERATED_MODULE_DESCRIPTIONS>>", "\n".join(descriptions_code))
    final_content = final_content.replace("; <<GENERATED_VISIBILITY_LOGIC>>", "\n".join(visibility_logic))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Generated {output_path} with {len(modules)} modules.")

if __name__ == "__main__":
    # Default paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template = os.path.join(base_dir, "installer.nsi.template")
    output = os.path.join(base_dir, "installer.nsi")
    modules_dir = os.path.join(base_dir, "modules")

    if not os.path.exists(template):
        print(f"Error: Template not found at {template}")
        sys.exit(1)

    generate_nsis(template, output, modules_dir)
