#!/bin/bash
# release.sh - Bash script to automate creating/switching release branches and tags

# Check if whiptail is available (usually installed by default on Ubuntu/Debian)
if command -v whiptail &> /dev/null; then
    VERSION=$(whiptail --inputbox "請輸入要發布的版本號 (例如: v1.4.0)" 8 39 --title "發布版本號" 3>&1 1>&2 2>&3)
else
    read -p "請輸入要發布的版本號 (例如: v1.4.0): " VERSION
fi

if [ -z "$VERSION" ]; then
    echo "未輸入版本號，操作已取消。"
    exit 1
fi

set -e
BRANCH="release/$VERSION"

# Get script directory and cd to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

echo "開始發布版本 $VERSION"
echo "Fetching remote branches and tags..."
git fetch origin --prune

# Get current branch
CURRENT=$(git rev-parse --abbrev-ref HEAD || true)
if [ -z "$CURRENT" ]; then
    echo "無法取得當前分支，請確保在一個 git 倉庫中執行本腳本。"
    exit 1
fi

if [ "$CURRENT" = "$BRANCH" ]; then
    echo "已經在分支 '$BRANCH'，跳過切換。"
else
    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
        echo "切換到本地分支 '$BRANCH'..."
        git checkout "$BRANCH"
    elif git ls-remote --exit-code --heads origin "$BRANCH" > /dev/null 2>&1; then
        echo "從遠端建立並切換到 '$BRANCH'..."
        git checkout -b "$BRANCH" "origin/$BRANCH"
    else
        LOCAL_BRANCHES=$(git branch --format="%(refname:short)")
        REMOTE_BRANCHES=$(git branch -r --format="%(refname:short)")

        if echo "$LOCAL_BRANCHES" | grep -q "^develop$"; then
            BASE_BRANCH="develop"
            echo "使用本地 develop 分支作為基準"
        elif echo "$REMOTE_BRANCHES" | grep -q "^origin/develop$"; then
            echo "從遠端建立本地 develop 分支..."
            git checkout -b develop origin/develop
            BASE_BRANCH="develop"
        else
            echo "本地和遠端都沒有 'develop' 分支，嘗試使用當前分支作為基準..."
            BASE_BRANCH=$CURRENT
        fi

        echo "基於 '$BASE_BRANCH' 建立新分支 '$BRANCH'..."
        git checkout "$BASE_BRANCH"
        git pull origin "$BASE_BRANCH" || true
        git checkout -b "$BRANCH"
    fi
fi

# Push branch
git push origin "$BRANCH"

# Tag processing
if git tag -l | grep -q "^$VERSION$"; then
    echo "Tag '$VERSION' 已存在，刪除舊標籤..."
    git tag -d "$VERSION"
    git push origin --delete "$VERSION" || true
fi

# Create and push new tag
git tag "$VERSION"
git push origin "$VERSION"

echo "發布完成! 版本: $VERSION, 分支: $BRANCH"
if command -v whiptail &> /dev/null; then
    whiptail --msgbox "發布完成!\n版本: $VERSION\n分支: $BRANCH" 8 39 --title "完成"
fi
