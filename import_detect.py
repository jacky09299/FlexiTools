import os
import re
from pathlib import Path

# 設定要掃描的資料夾
target_folder = r"C:\Users\Jacky\Downloads\import"  # 例如 "C:/Users/Jacky/Desktop/FlexiTools"

# 正則表達式：抓出 import 與 from 語法
import_pattern = re.compile(r'^\s*(import|from)\s+([\w\.]+)', re.MULTILINE)

# 儲存所有模組名稱（不重複）
all_imports = set()

# 遍歷所有 .py 檔案
for root, _, files in os.walk(target_folder):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            try:
                content = Path(path).read_text(encoding='utf-8')
                for match in import_pattern.findall(content):
                    module = match[1].split('.')[0]  # 取最上層模組
                    all_imports.add(module)
            except Exception as e:
                print(f"⚠️ 無法讀取 {path}: {e}")

# 輸出模組列表（排序）
for module in sorted(all_imports):
    print(module)
