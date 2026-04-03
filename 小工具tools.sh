#!/bin/bash

# 啟動 Conda
source ~/anaconda3/etc/profile.d/conda.sh
conda activate tools

# 執行 Python 程式（終端會顯示輸出）
python3 main.py

# 結束後暫停，讓你看到程式輸出
echo "程式結束，按任意鍵退出..."
read -n 1
