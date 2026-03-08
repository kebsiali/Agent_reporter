param(
  [string]$Host = "127.0.0.1",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "[INFO] Checking health endpoint first..."
try {
  $health = Invoke-WebRequest -UseBasicParsing -Uri "http://$Host`:$Port/api/health" -TimeoutSec 2
  if ($health.StatusCode -eq 200) {
    Write-Host "[OK] GUI already running on http://$Host`:$Port"
    Start-Process "http://$Host`:$Port"
    exit 0
  }
} catch {
  # Not running yet
}

Write-Host "[INFO] Starting GUI guardian..."
Start-Process powershell `
  -ArgumentList "-ExecutionPolicy Bypass -File `"$repoRoot\scripts\run_gui_guardian.ps1`" -Host $Host -Port $Port" `
  -WindowStyle Minimized

Write-Host "[INFO] Waiting for GUI to become healthy..."
$maxAttempts = 30
for ($i = 0; $i -lt $maxAttempts; $i++) {
  Start-Sleep -Milliseconds 500
  try {
    $health = Invoke-WebRequest -UseBasicParsing -Uri "http://$Host`:$Port/api/health" -TimeoutSec 2
    if ($health.StatusCode -eq 200) {
      Write-Host "[OK] GUI is up at http://$Host`:$Port"
      Start-Process "http://$Host`:$Port"
      exit 0
    }
  } catch {}
}

Write-Host "[ERROR] GUI did not become healthy within timeout. Check logs\\gui_*.log"
exit 1

