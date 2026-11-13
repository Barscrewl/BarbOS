param([string]$Machine = 'GreenParrots', [string]$Bar = "$env:USERPROFILE\BAR")
# One-time setup of a feeder PC (e.g. GreenParrots): clone BarbOS (public) and BarbOS-inbox (private; needs the
# Barscrewl GitHub sign-in, e.g. `gh auth login` then `gh auth setup-git`), build the venv, test one sync, install the task.
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $Bar | Out-Null
foreach ($r in 'BarbOS', 'BarbOS-inbox') {
    $d = Join-Path $Bar $r
    if (Test-Path "$d\.git") { git -C $d pull --ff-only } else { git clone "https://github.com/Barscrewl/$r.git" $d }
    if ($LASTEXITCODE) { throw "git failed for $r (is this PC signed in to GitHub as Barscrewl?)" }
}
$repo = Join-Path $Bar 'BarbOS'
if (-not (Test-Path "$repo\.venv\Scripts\python.exe")) { python -m venv "$repo\.venv"; if ($LASTEXITCODE) { throw 'python -m venv failed' } }
& "$repo\.venv\Scripts\python.exe" -m pip install -q -r "$repo\requirements.txt"; if ($LASTEXITCODE) { throw 'pip install failed' }
& powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\sync\barbos_sync.ps1" -Machine $Machine
& powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\sync\install_task.ps1" -Machine $Machine
Get-Content (Join-Path $Bar 'BarbOS-sync\sync.log') -Tail 12
