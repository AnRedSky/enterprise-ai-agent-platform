$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Scheduler Lifecycle Gate'
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

Invoke-GateStep 'FastAPI Scheduler lifecycle unit tests' {
    uv run pytest -q tests/unit/test_app_lifespan.py
}

Write-Host '============================================================'
Write-Host 'Scheduler Lifecycle Gate completed.'
Write-Host 'Only locally executed test results are reported.'
Write-Host '============================================================'
