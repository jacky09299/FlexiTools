import yaml
import requests
import json
import os

def get_pypi_metadata(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            info = data.get('info', {})
            return {
                'Name': info.get('name', package_name),
                'Version': info.get('version', ''),
                'License': info.get('license', 'Unknown'),
                'Classifiers': info.get('classifiers', []),
                'Home-page': info.get('home_page', ''),
                'Project-URL': info.get('project_url', ''),
                'Summary': info.get('summary', '')
            }
    except Exception as e:
        print(f"Error fetching {package_name}: {e}")
    return None

def parse_environment_yml(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        env = yaml.safe_load(f)

    dependencies = env.get('dependencies', [])
    pip_packages = []

    for dep in dependencies:
        if isinstance(dep, dict) and 'pip' in dep:
            pip_packages.extend(dep['pip'])

    # Clean up package names (remove version specifiers for lookup)
    cleaned_packages = []
    for pkg in pip_packages:
        # Handle 'package==version', 'package>=version', etc.
        # specific logic for environment.yml which usually uses ==
        name = pkg.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
        version = pkg.split('==')[1] if '==' in pkg else None
        cleaned_packages.append((name, version))

    return cleaned_packages

def infer_license_from_classifiers(classifiers):
    license_name = "Unknown"
    for c in classifiers:
        if c.startswith("License :: OSI Approved ::"):
            license_name = c.split("::")[-1].strip()
            break
    return license_name

def main():
    packages = parse_environment_yml('environment.yml')
    results = []

    print(f"Found {len(packages)} packages in environment.yml")

    for name, version in packages:
        print(f"Fetching metadata for {name}...")
        metadata = get_pypi_metadata(name)

        entry = {
            'Name': name,
            'Version': version if version else 'Unknown',
            'License': 'Unknown',
            'URL': ''
        }

        if metadata:
            # Try to get license from explicit field first, then classifiers
            lic = metadata.get('License', '')
            if not lic or lic == "UNKNOWN":
                lic = infer_license_from_classifiers(metadata.get('Classifiers', []))

            entry['License'] = lic
            entry['URL'] = metadata.get('Home-page') or metadata.get('Project-URL') or ""
            entry['Summary'] = metadata.get('Summary', '')

        results.append(entry)

    with open('licenses_pypi.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print("Done. Saved to licenses_pypi.json")

if __name__ == "__main__":
    main()
