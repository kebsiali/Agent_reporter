param(
  [string]$TaskName = "ReporterAgentGUI",
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$startScript = Join-Path $repoRoot "scripts\start_gui.ps1"

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-ExecutionPolicy Bypass -File `"$startScript`" -BindHost $BindHost -Port $Port"

$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Start Reporter Agent GUI with guardian on logon" `
  -Force | Out-Null

Write-Host "[OK] Startup task '$TaskName' installed."
