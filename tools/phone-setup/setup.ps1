# Quiet Money phone lane: set this Windows PC up to drive the phone (skill faceless-phone). Run from the repo folder:
#   powershell -ExecutionPolicy Bypass -File tools\phone-setup\setup.ps1
# It installs only what is missing, builds the phone server, adds it to Claude Code, and runs the doctor. Safe to run again.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\..")

$installed = $false
function Need($cmd, $id) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { Write-Host "ok      $cmd"; return }
  Write-Host "install $id"
  winget install --id $id -e --accept-package-agreements --accept-source-agreements
  $script:installed = $true
}
Need git    Git.Git
Need node   OpenJS.NodeJS.LTS
Need python Python.Python.3.12
Need adb    Google.PlatformTools
if ($installed) {
  Write-Host "`nSomething was installed. Close this window, open a new PowerShell in the repo folder, and run this script again."
  exit 0
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { npm install -g "@anthropic-ai/claude-code" }
python -m pip install --quiet requests pillow

Push-Location tools\open-device-mcp
npm ci
npm run build
npm link
Pop-Location

claude mcp add open-device -- open-device-mcp serve 2>$null
Write-Host "`n--- open-device-mcp doctor ---"
open-device-mcp doctor
Write-Host "`nNext: plug the phone in with USB debugging on, tap Allow, and follow tools\phone-setup\TEST.md"
