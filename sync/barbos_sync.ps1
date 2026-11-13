param(
    [string]$Machine = $(if ($env:COMPUTERNAME -eq 'VENGEANCE') { 'VENGEANCE' } else { 'GreenParrots' }),
    [ValidateSet('auto', 'writer', 'feeder')][string]$Role = 'auto',
    [switch]$NoPush,      # test: do everything except git push (writer still commits locally)
    [switch]$Force,       # writer: rerate and republish even when no replay is new
    [string]$Demos = '',  # test overrides: replay folder, inbox clone, sync state folder
    [string]$InboxDir = '',
    [string]$StateDir = ''
)
# BarbOS replay sync (scheduled every 30 min by sync\install_task.ps1).
#   feeder (Green Parrots): extract new replays -> <inbox>\<Machine>\<stamp>.json.gz -> commit + push to the PRIVATE repo
#           Barscrewl/BarbOS-inbox. Those files include chat, so they never go to the public BarbOS repo.
#   writer (VENGEANCE, the only PC that holds data\matches.json): pull the inbox, extract its own new replays, merge all by
#           start time (merge_matches.py), rerate (barbos.py rate, varying_ratings.py), regenerate report/exports/leaderboard
#           and the chat-free data\matches.json.gz, verify, then commit + push only the public outputs to Barscrewl/BarbOS main.
# Runs at BelowNormal priority (children inherit) so a game on this PC keeps the CPU. Log: <SyncDir>\sync.log.
$ErrorActionPreference = 'Continue'
if ($Role -eq 'auto') { $Role = if ($Machine -eq 'VENGEANCE') { 'writer' } else { 'feeder' } }
$Repo = Split-Path -Parent $PSScriptRoot
$BarDir = Split-Path -Parent $Repo
$Inbox = if ($InboxDir) { $InboxDir } else { Join-Path $BarDir 'BarbOS-inbox' }
$SyncDir = if ($StateDir) { $StateDir } else { Join-Path $BarDir 'BarbOS-sync' }
$DemoArg = if ($Demos) { @('--demos', $Demos) } else { @() }
$Py = Join-Path $Repo '.venv\Scripts\python.exe'; if (-not (Test-Path $Py)) { $Py = 'python' }
New-Item -ItemType Directory -Force $SyncDir, "$SyncDir\out" | Out-Null
$LogFile = "$SyncDir\sync.log"
function Log([string]$m) { $l = '[{0:yyyy-MM-dd HH:mm:ss}] {1}' -f (Get-Date), $m; Write-Host $l; Add-Content -Path $LogFile -Value $l -Encoding UTF8 }
function Run([string]$what, [string]$exe, [string[]]$a) {
    # Runs a native command, logs its output, returns $true on exit code 0.
    $out = & $exe @a 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    foreach ($l in $out) { if ($l.Trim()) { Add-Content -Path $LogFile -Value "    $l" -Encoding UTF8 } }
    if ($code -ne 0) { Log "FAILED ($code): $what" } else { Log "ok: $what" }
    $script:LastOut = $out
    return ($code -eq 0)
}
function G([string]$dir, [string[]]$a) { Run "git $($a -join ' ')" 'git.exe' (@('-C', $dir) + $a) }
function Push([string]$dir) {
    if ($NoPush) { Log "NoPush: skipped push of $dir"; return $false }
    for ($i = 0; $i -lt 5; $i++) {
        if ($i) { Start-Sleep -Seconds (4 * [math]::Pow(2, $i - 1)) }
        [void](G $dir @('fetch', 'origin'))
        if (-not (G $dir @('rebase', '--autostash', 'origin/main'))) { [void](G $dir @('rebase', '--abort')); Log 'rebase onto origin/main failed; not pushing'; return $false }
        if (G $dir @('push', 'origin', 'HEAD:main')) { return $true }
    }
    $false
}
function Ahead([string]$dir) { $n = & git -C $dir rev-list --count origin/main..HEAD 2>$null; [int]("0$n".Trim()) }

$mutex = New-Object Threading.Mutex($false, 'Global\BarbOSSync')
$got = $false; try { $got = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $got = $true }
if (-not $got) { Log 'another sync is running; exiting'; return }
try {
    try { [Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal' } catch {}
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd_HH-mm-ss')
    Log "=== sync start: $Machine as $Role$(if ($NoPush) { ' (NoPush)' })$(if ($Force) { ' (Force)' })"
    if (-not (Test-Path "$Inbox\.git")) { Log "inbox clone missing at $Inbox (git clone https://github.com/Barscrewl/BarbOS-inbox $Inbox)"; return }
    if (-not (G $Inbox @('pull', '--ff-only', '-q'))) { Log 'inbox pull failed; continuing with the local copy' }

    if ($Role -eq 'feeder') {
        if ((Ahead $Inbox) -gt 0) { Log "inbox has $(Ahead $Inbox) unpushed commit(s) from an earlier run"; [void](Push $Inbox) }
        $rel = "$Machine\$stamp.json.gz"; $out = Join-Path $Inbox $rel
        New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
        if (-not (Run 'extract new replays' $Py (@("$Repo\extract_new.py", 'scan', '--machine', $Machine, '--state', "$SyncDir\state.json", '--out', $out) + $DemoArg))) { return }
        Log "extract: $(@($script:LastOut | Where-Object { $_ -match '^\{"files"' })[-1])"
        if (-not (Test-Path $out)) { Log 'nothing new'; return }
        [void](G $Inbox @('add', '--', $rel))
        if (-not (G $Inbox @('commit', '-q', '-m', "$Machine replays $stamp"))) { return }
        # The commit is durable, so record the files as handed off now; an unpushed commit is pushed by the next run.
        [void](Run 'mark handed-off files' $Py @("$Repo\extract_new.py", 'mark', '--state', "$SyncDir\state.json", $out))
        if (Push $Inbox) { Log "pushed $rel to BarbOS-inbox" } else { Log 'push failed; will retry next run' }
        return
    }

    # ---- writer ----
    $mergedList = "$SyncDir\merged_inbox.txt"
    $merged = @{}; if (Test-Path $mergedList) { Get-Content $mergedList | Where-Object { $_ } | ForEach-Object { $merged[$_] = 1 } }
    $inboxNew = @(Get-ChildItem $Inbox -Recurse -File -Filter '*.json.gz' | Where-Object { $_.FullName -notmatch '\\\.git\\' } |
        ForEach-Object { $_.FullName.Substring($Inbox.Length + 1) } | Where-Object { -not $merged.ContainsKey($_) } | Sort-Object)
    $own = "$SyncDir\out\$Machine-$stamp.json.gz"
    if (-not (Run 'extract new replays' $Py (@("$Repo\extract_new.py", 'scan', '--machine', $Machine, '--state', "$Repo\data\scan_manifest.json", '--out', $own) + $DemoArg))) { return }
    Log "own extract: $(@($script:LastOut | Where-Object { $_ -match '^\{"files"' })[-1]); inbox files to merge: $($inboxNew.Count)"
    $files = @(); if (Test-Path $own) { $files += $own }; $files += @($inboxNew | ForEach-Object { Join-Path $Inbox $_ })
    if (-not $files.Count -and -not $Force) {
        if ((Ahead $Repo) -gt 0) { Log 'unpushed BarbOS commit from an earlier run'; [void](Push $Repo) }
        Log 'nothing new'; return
    }
    $bak = "$SyncDir\backup-pre-merge"; New-Item -ItemType Directory -Force $bak | Out-Null
    Copy-Item "$Repo\data\matches.json", "$Repo\data\scan_manifest.json" $bak -Force
    $before = (& $Py -c "import json;print(len(json.load(open(r'$Repo\data\matches.json',encoding='utf8'))['matches']))").Trim()
    $ok = $true
    Push-Location $Repo
    try {
        if ($files.Count) { $ok = Run 'merge' $Py (@("$Repo\merge_matches.py", "sync-$stamp") + $files) }
        foreach ($step in @(@('barbos.py', 'rate'), @('varying_ratings.py'), @('report.py'), @('export_public.py'), @('leaderboard.py'), @('publish_dataset.py'), @('verify_data.py'))) {
            if (-not $ok) { break }
            $ok = Run ($step -join ' ') $Py (@("$Repo\$($step[0])") + @($step | Select-Object -Skip 1))
        }
    } finally { Pop-Location }
    if (-not $ok) {
        Log 'pipeline failed: restoring matches.json + scan_manifest.json and the published files; inbox files stay unmerged'
        Copy-Item "$bak\matches.json", "$bak\scan_manifest.json" "$Repo\data" -Force
        [void](G $Repo @('checkout', '--', 'public', 'data/matches.json.gz', 'data/matches_index.csv', 'RESULTS.md'))
        return
    }
    if ($inboxNew.Count) { Add-Content -Path $mergedList -Value $inboxNew -Encoding UTF8 }
    $after = (& $Py -c "import json;print(len(json.load(open(r'$Repo\data\matches.json',encoding='utf8'))['matches']))").Trim()
    Log "matches: $before -> $after"
    [void](G $Repo @('add', '--', 'public', 'data/matches.json.gz', 'data/matches_index.csv', 'RESULTS.md'))
    & git -C $Repo diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { Log 'no public change to commit'; return }
    $msg = "BarbOS sync $stamp UTC: $before -> $after matches`n`nAutomatic replay sync (sync/barbos_sync.ps1): merged $($files.Count) extract file(s), rerated and republished.`n`nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    if (-not (G $Repo @('commit', '-q', '-m', $msg, '--', 'public', 'data/matches.json.gz', 'data/matches_index.csv', 'RESULTS.md'))) { return }
    $head = (& git -C $Repo rev-parse --short HEAD).Trim()
    $pushed = Push $Repo
    $head = (& git -C $Repo rev-parse --short HEAD).Trim()
    Log "commit $head $(if ($pushed) { 'pushed to main' } else { 'NOT pushed' })"
    $cur = "$Repo\BARBOS-CURRENT.txt"
    if (Test-Path $cur) {
        $line = "Last auto-sync: {0:yyyy-MM-dd HH:mm} PT, commit {1} ({2}), {3} -> {4} matches" -f (Get-Date), $head, $(if ($pushed) { 'pushed' } else { 'NOT pushed' }), $before, $after
        $t = @(Get-Content $cur | Where-Object { $_ -notmatch '^Last auto-sync:' }); Set-Content $cur (@($t[0], $line) + @($t | Select-Object -Skip 1)) -Encoding UTF8
    }
    Get-ChildItem "$SyncDir\out" -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -ErrorAction SilentlyContinue
} catch { Log "SYNC CRASHED: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)" }
finally { Log '=== sync end'; $mutex.ReleaseMutex(); $mutex.Dispose() }
