param(
    [string]$Machine = $(if ($env:COMPUTERNAME -eq 'VENGEANCE') { 'VENGEANCE' } else { 'GreenParrots' }),
    [ValidateSet('auto', 'writer', 'feeder')][string]$Role = 'auto',
    [switch]$NoPush,      # test: do everything except git push (writer still commits locally)
    [switch]$Force,       # writer: rerate and republish even when no replay is new
    [string]$Demos = '',  # test overrides: replay folder, inbox clone, sync state folder
    [string]$InboxDir = '',
    [string]$StateDir = '',
    [switch]$TestAlert   # send a test alert (toast + private GitHub issue), then close it, and exit
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
    if ($code -ne 0) { Log "FAILED ($code): $what"; Problem "$what failed (exit $code)" $out } else { Log "ok: $what" }
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

# ---- problem logging and alerts (owner 2026-11-14: a silent 22-hour export failure must never happen again) ----
# Every failed run adds one line to <SyncDir>\issues.log. After AlertAfter failed runs in a row: a Windows notification, <SyncDir>\ALERT.txt,
# and an issue in the PRIVATE repo Barscrewl/BarbOS-inbox (GitHub e-mails the owner). A run that succeeds closes the issue and clears the alert.
$AlertAfter = 2
$script:Problem = $null; $script:ProblemDetail = @()
function Problem([string]$what, $detail = @()) {
    if (-not $script:Problem) { $script:Problem = $what; $script:ProblemDetail = @($detail | Where-Object { "$_".Trim() } | Select-Object -Last 25) }
}
function Toast([string]$title, [string]$text) {
    try {
        [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
        $x = New-Object Windows.Data.Xml.Dom.XmlDocument
        $esc = { param($s) [Security.SecurityElement]::Escape($s) }
        $x.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$(& $esc $title)</text><text>$(& $esc $text)</text></binding></visual></toast>")
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe').Show([Windows.UI.Notifications.ToastNotification]::new($x))
    } catch { Log "toast failed: $($_.Exception.Message)" }
}
function Gh([string[]]$a) {
    $gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
    if (-not $gh) { foreach ($p in "$env:ProgramFiles\GitHub CLI\gh.exe", "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe") { if (Test-Path $p) { $gh = $p } } }
    if (-not $gh) { Log 'gh not found: no GitHub issue alert'; return $null }
    $o = & $gh @a 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE) { Log "gh $($a[0..1] -join ' ') failed: $($o -join ' ')"; return $null }
    $o
}
function Read-FailState { $f = "$SyncDir\fail_state.json"; if (Test-Path $f) { try { return Get-Content $f -Raw | ConvertFrom-Json } catch {} }; [pscustomobject]@{ count = 0; first = $null; problem = $null; issue = $null } }
function Report-Outcome {
    $f = "$SyncDir\fail_state.json"; $st = Read-FailState
    if ($script:Problem) {
        $now = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        $last = @($script:ProblemDetail | Where-Object { $_ -match 'Error|error|fatal|denied|Exception' })[-1]; if (-not $last) { $last = @($script:ProblemDetail)[-1] }
        Add-Content "$SyncDir\issues.log" ("[{0}] {1} {2}: {3} | {4}" -f $now, $Machine, $Role, $script:Problem, "$last".Trim()) -Encoding UTF8
        $st.count = [int]$st.count + 1; if (-not $st.first) { $st.first = $now }
        $changed = ($st.problem -ne "$($script:Problem) | $last".Trim()); $st.problem = "$($script:Problem) | $last".Trim()
        if ($st.count -ge $AlertAfter) {
            $title = "BarbOS sync failing on $Machine"
            $text = "$($st.count) runs in a row since $($st.first): $($script:Problem). $last"
            Set-Content "$SyncDir\ALERT.txt" "$now`r`n$text`r`nLog: $LogFile`r`nIssues: $SyncDir\issues.log" -Encoding UTF8
            if ($st.count -eq $AlertAfter -or $changed) {
                Toast $title $text
                $body = "**$($st.count) failed runs in a row** on $Machine ($Role), first at $($st.first) PT.`n`nFailing step: $($script:Problem)`n`n``````n$($script:ProblemDetail -join "`n")`n```````n`nThe sync keeps retrying every 30 minutes; on failure the writer restores matches.json, so no data is lost. Log: ``$LogFile``. This issue closes itself after the next successful run."
                if ($st.issue) { [void](Gh @('issue', 'comment', "$($st.issue)", '-R', 'Barscrewl/BarbOS-inbox', '-b', $body)) }
                else { $u = Gh @('issue', 'create', '-R', 'Barscrewl/BarbOS-inbox', '-t', "$title`: $($script:Problem)", '-b', $body); if ($u) { $st.issue = (@($u)[-1] -split '/')[-1]; Log "alert issue #$($st.issue) opened" } }
            }
        }
        $st | ConvertTo-Json | Set-Content $f -Encoding UTF8
    } elseif ([int]$st.count -gt 0) {
        Add-Content "$SyncDir\issues.log" ("[{0:yyyy-MM-dd HH:mm:ss}] {1} {2}: RECOVERED after {3} failed run(s) since {4}" -f (Get-Date), $Machine, $Role, $st.count, $st.first) -Encoding UTF8
        if ($st.issue) { [void](Gh @('issue', 'close', "$($st.issue)", '-R', 'Barscrewl/BarbOS-inbox', '-c', "Recovered at $(Get-Date -Format 'yyyy-MM-dd HH:mm') PT after $($st.count) failed run(s).")) }
        if ([int]$st.count -ge $AlertAfter) { Toast "BarbOS sync recovered on $Machine" "Working again after $($st.count) failed runs." }
        Remove-Item "$SyncDir\ALERT.txt", $f -ErrorAction SilentlyContinue
    }
}

$mutex = New-Object Threading.Mutex($false, 'Global\BarbOSSync')
$got = $false; try { $got = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $got = $true }
if (-not $got) { Log 'another sync is running; exiting'; return }
try {
    try { [Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal' } catch {}
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd_HH-mm-ss')
    Log "=== sync start: $Machine as $Role$(if ($NoPush) { ' (NoPush)' })$(if ($Force) { ' (Force)' })"
    if ($TestAlert) {
        Toast 'BarbOS sync test alert' "Alerts work on $Machine. This is only a test."
        $u = Gh @('issue', 'create', '-R', 'Barscrewl/BarbOS-inbox', '-t', "BarbOS sync test alert from $Machine", '-b', 'Test of the failure alert. Closed automatically.')
        if ($u) { Log "test issue: $(@($u)[-1])"; [void](Gh @('issue', 'close', (@($u)[-1] -split '/')[-1], '-R', 'Barscrewl/BarbOS-inbox', '-c', 'Test done.')) }
        return
    }
    if (-not (Test-Path "$Inbox\.git")) { Log "inbox clone missing at $Inbox (git clone https://github.com/Barscrewl/BarbOS-inbox $Inbox)"; Problem "inbox clone missing at $Inbox"; return }
    if (-not (G $Inbox @('pull', '--ff-only', '-q'))) { Log 'inbox pull failed; continuing with the local copy'; Problem 'inbox pull failed' $script:LastOut }

    if ($Role -eq 'feeder') {
        # Feeders keep their BarbOS code current (the writer's clone is where code is edited, so it never pulls itself).
        if (-not (G $Repo @('pull', '--ff-only', '-q'))) { Log 'BarbOS code pull failed; using the local copy' }
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
        if (Push $Inbox) { Log "pushed $rel to BarbOS-inbox" } else { Log 'push failed; will retry next run'; Problem 'push to BarbOS-inbox failed' }
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
    Log "commit $head $(if ($pushed) { 'pushed to main' } else { 'NOT pushed' })"; if (-not $pushed -and -not $NoPush) { Problem 'push to BarbOS main failed' }
    $cur = "$Repo\BARBOS-CURRENT.txt"
    if (Test-Path $cur) {
        $line = "Last auto-sync: {0:yyyy-MM-dd HH:mm} PT, commit {1} ({2}), {3} -> {4} matches" -f (Get-Date), $head, $(if ($pushed) { 'pushed' } else { 'NOT pushed' }), $before, $after
        $t = @(Get-Content $cur | Where-Object { $_ -notmatch '^Last auto-sync:' }); Set-Content $cur (@($t[0], $line) + @($t | Select-Object -Skip 1)) -Encoding UTF8
    }
    Get-ChildItem "$SyncDir\out" -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -ErrorAction SilentlyContinue
} catch { Log "SYNC CRASHED: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; Problem 'sync script crashed' @("$($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)") }
finally { try { if (-not $TestAlert) { Report-Outcome } } catch { Log "alert step failed: $($_.Exception.Message)" }; Log '=== sync end'; $mutex.ReleaseMutex(); $mutex.Dispose() }
