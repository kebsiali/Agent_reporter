$ErrorActionPreference = "SilentlyContinue"

Get-Process | Where-Object {
  $_.ProcessName -eq "python" -or $_.ProcessName -eq "powershell"
} | ForEach-Object {
  try {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    if ($cmd -match "reporter_agent gui" -or $cmd -match "run_gui_guardian.ps1") {
      Stop-Process -Id $_.Id -Force
      Write-Host "[OK] Stopped process $($_.Id)"
    }
  } catch {}
}

Write-Host "[INFO] Stop sequence complete."

