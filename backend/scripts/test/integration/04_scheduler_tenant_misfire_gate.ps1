$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Scheduler Tenant / Misfire Gate'
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

Invoke-GateStep 'Scheduler misfire unit tests' {
    uv run pytest -q tests/unit/test_workflow_scheduler_contract.py tests/unit/test_workflow_scheduler_runtime.py
}

Invoke-GateStep 'Scheduler tenant PostgreSQL integration' {
    $env:RUN_DATABASE_INTEGRATION = '1'
    try {
        uv run pytest -q tests/integration/test_workflow_scheduler_repository.py tests/integration/test_workflow_scheduler_tenant_isolation.py
    }
    finally {
        Remove-Item Env:RUN_DATABASE_INTEGRATION -ErrorAction SilentlyContinue
    }
}

Invoke-GateStep 'Scheduler API Contract tests' {
    uv run pytest -q tests/api_contract/test_api_scheduled_triggers.py
}

Invoke-GateStep 'Backend default regression' {
    uv run pytest -q
}

Write-Host '============================================================'
Write-Host 'Scheduler Tenant / Misfire Gate completed.'
Write-Host 'Only locally executed test results are reported.'
Write-Host '============================================================'
