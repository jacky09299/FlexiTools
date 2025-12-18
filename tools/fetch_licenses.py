import os
import requests
import json
import sys

# Mapping of SPDX identifiers or common names to directory names in LICENSES/
LICENSE_DIR_MAP = {
    'MIT': 'MIT_LICENSE',
    'BSD': 'BSD_LICENSES',
    'BSD-3-Clause': 'BSD_LICENSES',
    'BSD-2-Clause': 'BSD_LICENSES',
    'Apache-2.0': 'Apache_LICENSES',
    'Apache Software License': 'Apache_LICENSES',
    'LGPL': 'LGPL_LICENSE',
    'GPL': 'GPL_LICENSE',
    'GPL-2.0': 'GPL_LICENSE',
    'GPLv2': 'GPL_LICENSE',
    'GPL-3.0': 'GPL_LICENSE',
    'MPL-2.0': 'MPL2.0_LICENSE',
    'PSF': 'PSF_LICENSE',
    'Unlicense': 'Unlicense_LICENSE', # Need to create if not exists
}

PACKAGES_TO_FETCH = {
    'prettytable': 'BSD-3-Clause',
    'wcwidth': 'MIT',
    'tomli': 'MIT',
    'yt-dlp': 'Unlicense',
    'pyinstaller': 'GPL-2.0',
    'pyinstaller-hooks-contrib': 'Apache-2.0'
}

def main():
    base_dir = "LICENSES"

    # Ensure base dirs exist
    for subdir in LICENSE_DIR_MAP.values():
        path = os.path.join(base_dir, subdir)
        os.makedirs(path, exist_ok=True)

    for pkg, license_type in PACKAGES_TO_FETCH.items():
        print(f"Processing {pkg} ({license_type})...")

        # Determine target directory
        target_subdir = LICENSE_DIR_MAP.get(license_type)
        if not target_subdir:
            if 'BSD' in license_type: target_subdir = 'BSD_LICENSES'
            elif 'GPL' in license_type: target_subdir = 'GPL_LICENSE'
            elif 'MIT' in license_type: target_subdir = 'MIT_LICENSE'
            elif 'Apache' in license_type: target_subdir = 'Apache_LICENSES'
            else: target_subdir = 'Other_LICENSES'

        target_dir = os.path.join(base_dir, target_subdir)
        os.makedirs(target_dir, exist_ok=True)

        filename = f"LICENSE_{pkg}.txt"
        filepath = os.path.join(target_dir, filename)

        # Skip if already exists
        if os.path.exists(filepath):
            print(f"  {filename} already exists. Skipping.")
            continue

        # Corrected URLs based on research
        license_urls = {
            'prettytable': 'https://raw.githubusercontent.com/prettytable/prettytable/main/LICENSE',
            'wcwidth': 'https://raw.githubusercontent.com/jquast/wcwidth/master/LICENSE',
            'tomli': 'https://raw.githubusercontent.com/hukkin/tomli/master/LICENSE',
            'yt-dlp': 'https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/LICENSE',
            'pyinstaller': 'https://raw.githubusercontent.com/pyinstaller/pyinstaller/develop/COPYING.txt',
            'pyinstaller-hooks-contrib': 'https://raw.githubusercontent.com/pyinstaller/pyinstaller-hooks-contrib/master/LICENSE'
        }

        url = license_urls.get(pkg)
        if url:
            try:
                print(f"  Fetching from {url}...")
                resp = requests.get(url)
                if resp.status_code == 200:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(resp.text)
                    print(f"  Saved to {filepath}")
                else:
                    print(f"  Failed to fetch from {url} (Status: {resp.status_code})")
            except Exception as e:
                print(f"  Error fetching {url}: {e}")
        else:
            print(f"  No known URL for {pkg}")

if __name__ == "__main__":
    main()
