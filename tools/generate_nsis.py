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

    # Lists to hold lines for generated functions
    show_modules_lines = []
    hide_modules_lines = []
    init_modules_lines = []

    for i, module_file in enumerate(modules):
        module_name = os.path.splitext(module_file)[0]
        section_id = f"SEC_MOD_{i}"

        # Section definition
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

        # Logic for Show/Hide functions
        show_modules_lines.append(f"  SectionSetText ${{{section_id}}} \"{module_name}\"") # Show by setting text
        # To hide a section in NSIS, you set its text to ""
        hide_modules_lines.append(f"  SectionSetText ${{{section_id}}} \"\"")

        # Logic for InitModuleSelection (Update Mode)
        # If module file exists, select it (check it). If not, uncheck it.
        # But SectionSetFlags requires calculation of flags.
        # Simplest is to use macros from Sections.nsh but we are generating raw logic here.
        # Or use SectionSetFlags with ${SF_SELECTED} (1) or not.
        # ${SF_SELECTED} is usually 1. Unselected is 0.

        # We need to verify if the file exists on the target system (during install)
        # $INSTDIR points to target.

        init_lines = f"""
  ; Check {module_name}
  IfFileExists "$INSTDIR\\_internal\\modules\\{module_file}" 0 +3
    SectionSetFlags ${{{section_id}}} 1
    Goto +2
    SectionSetFlags ${{{section_id}}} 0
"""
        init_modules_lines.append(init_lines)


    # Construct the generated functions
    visibility_functions = f"""
Function ShowModuleSections
{chr(10).join(show_modules_lines)}
FunctionEnd

Function HideModuleSections
{chr(10).join(hide_modules_lines)}
FunctionEnd

Function InitModuleSelection
  ; Initialize module selection based on existing files in update mode
  ; First unselect all to be safe? The loop handles both 0 and 1 cases.
{chr(10).join(init_modules_lines)}
FunctionEnd
"""

    # Inject into template
    final_content = template_content.replace("; <<GENERATED_MODULE_SECTIONS>>", "\n".join(sections_code))
    final_content = final_content.replace("; <<GENERATED_MODULE_DESCRIPTIONS>>", "\n".join(descriptions_code))
    final_content = final_content.replace("; <<GENERATED_VISIBILITY_FUNCTIONS>>", visibility_functions)

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
