# scripts/type.ps1 - mypy
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
