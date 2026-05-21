param (
    [Parameter(Mandatory=$true)]
    [string]$Message
)

# Check if we are in a git repo
if (-not (Test-Path .git)) {
    Write-Error "Not a git repository."
    exit 1
}

# Check for staged changes
$staged = git diff --cached --name-only
if ($staged) {
    Write-Host "Found staged changes. Creating a WIP commit instead of stash." -ForegroundColor Yellow
    git commit -m "WIP: CHECKPOINT: $Message"
} else {
    Write-Host "Creating git stash checkpoint..." -ForegroundColor Cyan
    git stash push -m "CHECKPOINT: $Message"
}

Write-Host "Checkpoint created: $Message" -ForegroundColor Green
