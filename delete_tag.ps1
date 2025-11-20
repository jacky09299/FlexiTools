<#
.SYNOPSIS
    Delete local and remote Git tags safely.
#>

function Write-Status ($Message, $Color = "Cyan") {
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Write-ErrorMsg ($Message) {
    Write-Host "Error: $Message" -ForegroundColor Red
}

# 1. Input Tag Name
$tagName = Read-Host -Prompt "Enter the Tag name to delete"

if ([string]::IsNullOrWhiteSpace($tagName)) {
    Write-ErrorMsg "No tag name entered. Exiting."
    exit
}

# 2. Confirmation
$confirmation = Read-Host -Prompt "Are you sure you want to delete tag '$tagName' (Local & Remote)? [Y/N]"
if ($confirmation -ne "Y" -and $confirmation -ne "y") {
    Write-Status "Operation cancelled." "Yellow"
    exit
}

Write-Host "----------------------------------------"

# 3. Delete Local Tag
Write-Status "Deleting local tag: $tagName ..."
$localResult = git tag -d $tagName 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Status "Local tag deleted successfully." "Green"
} else {
    Write-ErrorMsg "Failed to delete local tag. Git says: $localResult"
    # Ask to continue even if local fails
    $continueRemote = Read-Host -Prompt "Local delete failed. Try deleting remote anyway? [Y/N]"
    if ($continueRemote -ne "Y" -and $continueRemote -ne "y") { exit }
}

# 4. Delete Remote Tag
Write-Status "Deleting remote (origin) tag: $tagName ..."
$remoteResult = git push origin --delete $tagName 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Status "Remote tag deleted and pushed successfully!" "Green"
} else {
    Write-ErrorMsg "Failed to delete remote tag."
    Write-Host $remoteResult -ForegroundColor DarkGray
}

Write-Host "----------------------------------------"
Write-Status "Done."
pause