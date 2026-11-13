' Starts barbos_sync.ps1 with no visible window (used by the "BarbOS replay sync" scheduled task).
' Any arguments are passed through, e.g. -Machine GreenParrots.
Set sh = CreateObject("WScript.Shell")
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
args = ""
For Each a In WScript.Arguments
  args = args & " " & a
Next
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & dir & "\barbos_sync.ps1""" & args, 0, True
