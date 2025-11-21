import json
import os
import sys
import time
import requests
import glob

def translate_segment(text, target_lang):
    """
    Translates a text segment using Google Translate API (free tier logic from modules/translator.py).
    """
    try:
        # Construct translation request
        base_url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'auto',
            'tl': target_lang,
            'dt': 't',
            'q': text
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(base_url, params=params, headers=headers, timeout=15)

        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translated_text = ''.join([item[0] for item in result[0] if item[0]])
                return translated_text
            else:
                print(f"  [Error] Translation failed: Unable to parse response for '{text}'")
                return None
        else:
            print(f"  [Error] Translation failed: HTTP {response.status_code} for '{text}'")
            return None

    except Exception as e:
        print(f"  [Error] Translation exception: {str(e)} for '{text}'")
        return None

def get_target_lang_code(filename):
    """
    Maps locale filename to Google Translate language code.
    e.g., 'zh_TW.json' -> 'zh-tw'
          'en_US.json' -> 'en'
    """
    basename = os.path.basename(filename).replace('.json', '')

    # Specific mappings
    mapping = {
        'zh_TW': 'zh-tw',
        'zh_CN': 'zh-cn',
        'en_US': 'en',
        'ja_JP': 'ja',
        'ko_KR': 'ko'
    }

    if basename in mapping:
        return mapping[basename]

    # Fallback: replace underscore with hyphen and take the first part if it looks like a standard locale
    if '_' in basename:
        parts = basename.split('_')
        return parts[0] # e.g., fr_FR -> fr

    return basename

def main():
    input_file = 'new_translations.json'
    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Input file '{input_file}' not found.")
        print("Please create a JSON file with the new translations.")
        print("Format example:")
        print("""{
    "new_key_1": {
        "en_US": "English Text",
        "zh_TW": "Chinese Text"
    },
    "new_key_2": {
        "en_US": "Text to be auto-translated"
    }
}""")
        sys.exit(1)

    # Load new translations
    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            new_translations = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error parsing input JSON: {e}")
            sys.exit(1)

    # Find all locale files
    locale_files = glob.glob('locales/*.json')
    if not locale_files:
        print("No locale files found in 'locales/' directory.")
        sys.exit(1)

    print(f"Found {len(locale_files)} locale files.")

    # Process each locale file
    for locale_file in locale_files:
        print(f"\nProcessing {locale_file}...")

        target_lang_code = get_target_lang_code(locale_file)
        locale_key = os.path.basename(locale_file).replace('.json', '') # e.g., zh_TW

        with open(locale_file, 'r', encoding='utf-8') as f:
            try:
                current_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"  [Error] Could not read {locale_file}: {e}")
                continue

        modified = False

        for key, trans_data in new_translations.items():
            # 1. Check if key already exists
            if key in current_data:
                print(f"  [Skip] Key '{key}' already exists.")
                continue

            # 2. Determine the text to use
            text_to_use = None

            # Check if explicit translation exists for this locale key (e.g. "zh_TW")
            if locale_key in trans_data:
                 text_to_use = trans_data[locale_key]
                 print(f"  [Add] '{key}': Using provided translation.")

            # Check if explicit translation exists for the lang code (e.g. "zh-tw" or "en") - less likely but good fallback
            elif target_lang_code in trans_data:
                text_to_use = trans_data[target_lang_code]
                print(f"  [Add] '{key}': Using provided translation (by code).")

            # Auto-translate
            else:
                # Find a source text (prefer en_US, then en, then first available)
                source_text = trans_data.get('en_US') or trans_data.get('en')
                if not source_text:
                     # Pick first available value that is a string
                     for v in trans_data.values():
                         if isinstance(v, str):
                             source_text = v
                             break

                if source_text:
                    print(f"  [Translating] '{key}': '{source_text}' -> {target_lang_code}...")
                    translated = translate_segment(source_text, target_lang_code)
                    if translated:
                        text_to_use = translated
                        # Sleep briefly to be nice to the API
                        time.sleep(0.5)
                    else:
                        print(f"  [Warn] Failed to translate '{key}'. Skipping.")
                        continue
                else:
                    print(f"  [Warn] No source text found for '{key}'. Skipping.")
                    continue

            if text_to_use:
                current_data[key] = text_to_use
                modified = True

        if modified:
            # Write back to file
            with open(locale_file, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=4)
            print(f"  [Saved] Updated {locale_file}")
        else:
            print(f"  [No Change] {locale_file} is up to date.")

if __name__ == "__main__":
    main()
