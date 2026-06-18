# scripts/lint.ps1 - flake8
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m flake8 .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
