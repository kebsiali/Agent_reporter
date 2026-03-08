param(
  [string]$Host = "127.0.0.1",
  [int]$Port = 8000,
  [int]$RestartDelaySeconds = 3
)

$ErrorActionPreference = "Continue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

Write-Host "[INFO] GUI guardian started. Host=$Host Port=$Port"

while ($true) {
  $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $stdoutLog = Join-Path $logDir "gui_stdout_$timestamp.log"
  $stderrLog = Join-Path $logDir "gui_stderr_$timestamp.log"

  Write-Host "[INFO] Starting GUI server at $timestamp ..."
  $proc = Start-Process python `
    -ArgumentList "-m reporter_agent gui --host $Host --port $Port" `
    -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

  $proc.WaitForExit()
  $code = $proc.ExitCode
  Write-Host "[WARN] GUI process exited with code $code. Restarting in $RestartDelaySeconds seconds."
  Start-Sleep -Seconds $RestartDelaySeconds
}

