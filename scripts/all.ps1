# scripts/all.ps1 - 一鍵跑完整流程（format + lint + type + test）
# 用法：pwsh scripts/all.ps1 [-SkipFmt] [-SkipType]
param(
    [switch]$SkipFmt,
    [switch]$SkipType
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$scripts = @{
    fmt  = "format.ps1"
    lint = "lint.ps1"
    type = "type.ps1"
    test = "test.ps1"
}

$runOrder = @("fmt", "lint", "type", "test")
if ($SkipFmt)  { $runOrder = $runOrder | Where-Object { $_ -ne "fmt" } }
if ($SkipType) { $runOrder = $runOrder | Where-Object { $_ -ne "type" } }

foreach ($step in $runOrder) {
    Write-Host ""
    Write-Host "==== $step ====" -ForegroundColor Cyan
    & "$PSScriptRoot\$($scripts[$step])"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: $step" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "ALL PASS" -ForegroundColor Green
