# scripts/format.ps1 - black 格式化全部 source
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m black .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
