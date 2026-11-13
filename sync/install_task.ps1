param(
    [int]$Minutes = 30,
    [switch]$Remove,
    [switch]$RunNow,
    [string]$Machine = ''          # passed through to barbos_sync.ps1 (default: VENGEANCE on VENGEANCE, else GreenParrots)
)
# Registers (or removes) the "BarbOS replay sync" scheduled task for the logged-on user: barbos_sync.ps1 every $Minutes min.
# Runs only while the user is logged on, so git can use the user's stored GitHub sign-in. Starts through wscript and
# sync_hidden.vbs so no console window pops over the game.
$name = 'BarbOS replay sync'
if ($Remove) { Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue; "removed '$name'"; return }
$vbs = Join-Path $PSScriptRoot 'sync_hidden.vbs'
$arg = "`"$vbs`""; if ($Machine) { $arg += " -Machine $Machine" }
$action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\wscript.exe" -Argument $arg -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $Minutes)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Priority 7
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'BarbOS: extract new BAR replays and sync them (Barscrewl/BarbOS sync\barbos_sync.ps1). Log: BAR\BarbOS-sync\sync.log' -Force | Out-Null
"registered '$name' every $Minutes min"
if ($RunNow) { Start-ScheduledTask -TaskName $name; 'started once now' }
Get-ScheduledTask -TaskName $name | Select-Object TaskName, State, @{ n = 'NextRun'; e = { (Get-ScheduledTaskInfo $_).NextRunTime } } | Format-Table -AutoSize
