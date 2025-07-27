# release.ps1 - PowerShell GUI 化自动化创建/切换 release 分支并打 tag
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

# 弹出输入框获取版本号
$Version = [Microsoft.VisualBasic.Interaction]::InputBox("请输入要发布的版本号 (例如: v1.4.0)", "发布版本号")
if ([string]::IsNullOrWhiteSpace($Version)) {
    [System.Windows.Forms.MessageBox]::Show("未输入版本号，操作已取消。", "取消", 'OK', 'Warning')
    exit 1
}

$ErrorActionPreference = 'Stop'
$branch = "release/$Version"

# 获取脚本所在目录，切换到该目录执行
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# 弹窗提示正在执行
[System.Windows.Forms.MessageBox]::Show("开始发布版本 $Version", "开始发布")

# Fetch
Write-Host "Fetching remote branches and tags..."
git fetch origin --prune

# 获取当前分支
try {
    $current = git rev-parse --abbrev-ref HEAD 2>$null
} catch {
    [System.Windows.Forms.MessageBox]::Show("无法获取当前分支，请确保在一个 git 仓库中执行本脚本。", "错误", 'OK', 'Error')
    exit 1
}

# 分支处理
if ($current -eq $branch) {
    Write-Host "已经在分支 '$branch'，跳过切换。"
} else {
    # 本地存在
    if (git show-ref --verify --quiet "refs/heads/$branch") {
        Write-Host "切换到本地分支 '$branch'..."
        git checkout $branch
    } elseif ((git ls-remote --exit-code --heads origin $branch) -eq 0) {
        Write-Host "从远端创建并切换到 '$branch'..."
        git checkout -b $branch origin/$branch
    } else {
        # 检查 develop 分支是否存在
        if (git show-ref --verify --quiet "refs/heads/develop") { 
            $baseBranch = 'develop' 
        } else {
            [System.Windows.Forms.MessageBox]::Show("本地没有 'develop' 分支，无法创建 release 分支。", "错误", 'OK', 'Error')
            exit 1
        }
        Write-Host "基于 '$baseBranch' 创建新分支 '$branch'..."
        git checkout $baseBranch
        git pull origin $baseBranch
        git checkout -b $branch
    }
}

# 推送分支
git push origin $branch

# Tag 处理
if (git tag -l $Version) {
    Write-Host "Tag '$Version' 已存在，删除旧标签..."
    git tag -d $Version
    git push origin --delete $Version -ErrorAction SilentlyContinue
}

# 创建并推送新 Tag
git tag $Version
git push origin $Version

[System.Windows.Forms.MessageBox]::Show("发布完成!`n版本: $Version`n分支: $branch", "完成", 'OK', 'Information')