# scripts/test.ps1 - pytest
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m pytest tests -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
