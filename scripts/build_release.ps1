param(
  [string]$OutDir = "dist",
  [string]$Version = "dev"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$releaseName = "reporter-agent-$Version"
$staging = Join-Path $root $releaseName
$dist = Join-Path $root $OutDir
$zipPath = Join-Path $dist "$releaseName.zip"

if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
if (-not (Test-Path $dist)) { New-Item -ItemType Directory -Path $dist | Out-Null }
New-Item -ItemType Directory -Path $staging | Out-Null

$include = @(
  "README.md",
  "requirements.txt",
  "requirements-dev.txt",
  "reporter_agent",
  "docs",
  "scripts"
)

foreach ($item in $include) {
  $src = Join-Path $root $item
  if (Test-Path $src) {
    Copy-Item -Path $src -Destination $staging -Recurse -Force
  }
}

$removePatterns = @(
  "__pycache__",
  "*.pyc",
  ".pytest_cache",
  "data\test_tmp",
  ".git"
)

foreach ($pattern in $removePatterns) {
  Get-ChildItem -Path $staging -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like $pattern -or $_.FullName -like "*\$pattern*" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $staging

Write-Host "[OK] Release package created: $zipPath"
