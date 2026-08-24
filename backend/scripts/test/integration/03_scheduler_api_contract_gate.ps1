$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Scheduler API Contract Gate'
Write-Host '============================================================'

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $backendRoot

function Invoke-GateStep {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "[Gate] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Gate failed: $Name (exit=$LASTEXITCODE)" }
}

Invoke-GateStep 'Application import' {
    uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
}

Invoke-GateStep 'Scheduler API Contract tests' {
    uv run pytest -q tests/api_contract/test_api_scheduled_triggers.py
}

Invoke-GateStep 'Backend default regression' {
    uv run pytest -q
}

Write-Host '============================================================'
Write-Host 'Scheduler API Contract Gate completed.'
Write-Host 'Only locally executed test results are reported.'
Write-Host '============================================================'
