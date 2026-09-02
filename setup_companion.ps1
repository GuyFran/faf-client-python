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

# -- 1) Find a WORKING Python 3.14 ------------------------------------------------------
# Broken shims exist in the wild (e.g. a stale chocolatey python3.14.exe pointing at a
# deleted install), so every candidate must be verified by actually executing it.
function Test-Python($exe) {
    if (-not $exe) { return $false }
    try {
        $v = & $exe --version 2>&1
        return ($LASTEXITCODE -eq 0 -and "$v" -match "3\.14")
    } catch { return $false }
}

function Find-Python {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "C:\Program Files\Python314\python.exe",
        "C:\Python314\python.exe"
    )
    foreach ($c in $candidates) {
        if ((Test-Path $c) -and (Test-Python $c)) { return $c }
    }
    # py launcher
    try {
        $v = & py -3.14 --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$v" -match "3\.14") {
            return (& py -3.14 -c "import sys; print(sys.executable)").Trim()
        }
    } catch {}
    # PATH entries (shims included) — only accepted if they actually run
    foreach ($name in @("python3.14", "python3", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and (Test-Python $cmd.Source)) { return $cmd.Source }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "No working Python 3.14 found - installing via winget..." -ForegroundColor Cyan
    winget install --id Python.Python.3.14 --accept-package-agreements --accept-source-agreements --silent
    $py = Find-Python
    if (-not $py) {
        throw "Python 3.14 still not found after install. Install it from python.org, then re-run. (Tip: a broken 'python3.14' shim in chocolatey\bin can shadow real installs - remove the shim or run: choco uninstall python314.)"
    }
}
Write-Host "Python: $py" -ForegroundColor Green

# -- 2) venv + dependencies -------------------------------------------------------------
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    if (Test-Path ".\.venv") { Remove-Item -Recurse -Force ".\.venv" }  # clear a broken half-venv
    Write-Host "Creating venv + installing dependencies (PyQt6 etc. - takes a few minutes)..." -ForegroundColor Cyan
    & $py -m venv .venv
    if (-not (Test-Path $venvPy)) { throw "venv creation failed (using $py). See errors above." }
    & $venvPy -m pip install --quiet --upgrade pip
    & $venvPy -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed. See errors above." }
}
Write-Host "Dependencies ready." -ForegroundColor Green

# -- 3) Launch with the companion relay enabled ----------------------------------------
$env:FAF_COMPANION_ENABLED = "1"
Write-Host ""
Write-Host "Launching the FAF client (companion relay enabled)..." -ForegroundColor Cyan
Write-Host "  1. Log into FAF in the client window."
Write-Host "  2. Pairing values for the phone are in:  $HOME\faf_companion_pairing.txt"
Write-Host "  3. If Windows Firewall asks about python/port 6900: Allow (private networks)."
Write-Host ""
& $venvPy -m src
