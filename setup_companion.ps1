# FAF Mobile companion — one-shot setup & launch for the forked desktop client.
# Run this ON YOUR PHYSICAL COMPUTER (NOT a VM — the anti-smurf check fingerprints the
# machine at FAF login, and VM fingerprints can flag your account).
#
# Usage (PowerShell, from the repo root):
#   .\setup_companion.ps1          # first run: installs Python 3.14 + deps, then launches
#   .\setup_companion.ps1          # later runs: just launches
#
# After launch: log into FAF in the client window, then read your pairing values from
#   $HOME\faf_companion_pairing.txt   (IP / PORT / TOKEN)
# and enter them in the phone app: Play tab -> gear icon.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1) Python 3.14
$py = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
if (-not (Test-Path $py)) {
    $sys = Get-Command python3.14 -ErrorAction SilentlyContinue
    if ($sys) { $py = $sys.Source }
}
if (-not (Test-Path $py)) {
    Write-Host "Installing Python 3.14 via winget..." -ForegroundColor Cyan
    winget install --id Python.Python.3.14 --accept-package-agreements --accept-source-agreements --silent
    $py = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
    if (-not (Test-Path $py)) { throw "Python 3.14 install failed - install it manually from python.org, then re-run." }
}
Write-Host "Python: $py" -ForegroundColor Green

# 2) venv + dependencies
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating venv + installing dependencies (PyQt6 etc. - takes a few minutes)..." -ForegroundColor Cyan
    & $py -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
Write-Host "Dependencies ready." -ForegroundColor Green

# 3) Launch with the companion relay enabled
$env:FAF_COMPANION_ENABLED = "1"
Write-Host ""
Write-Host "Launching the FAF client (companion relay enabled)..." -ForegroundColor Cyan
Write-Host "  1. Log into FAF in the client window."
Write-Host "  2. Pairing values for the phone are in:  $HOME\faf_companion_pairing.txt"
Write-Host "  3. If Windows Firewall asks about python/port 6900: Allow (private networks)."
Write-Host ""
& .\.venv\Scripts\python.exe -m src
