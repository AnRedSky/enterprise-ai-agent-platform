$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $backendRoot

function Invoke-GateStep {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "[Gate] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Gate failed: $Name (exit=$LASTEXITCODE)" }
}

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Scheduler Persistence Gate'
Write-Host '============================================================'

Invoke-GateStep 'Alembic upgrade heads' { uv run alembic upgrade heads }
Invoke-GateStep 'Alembic current' { uv run alembic current }
Invoke-GateStep 'Scheduler contract targeted tests' {
    uv run pytest -q tests/unit/test_workflow_scheduler_contract.py
}

# 真实 PostgreSQL 持久化测试必须显式开启，避免普通 Backend Regression 隐式依赖数据库。
$previousDatabaseIntegration = $env:RUN_DATABASE_INTEGRATION
try {
    $env:RUN_DATABASE_INTEGRATION = '1'
    Invoke-GateStep 'Scheduler repository PostgreSQL integration' {
        uv run pytest -q tests/integration/test_workflow_scheduler_repository.py
    }
}
finally {
    if ($null -eq $previousDatabaseIntegration) {
        Remove-Item Env:RUN_DATABASE_INTEGRATION -ErrorAction SilentlyContinue
    }
    else {
        $env:RUN_DATABASE_INTEGRATION = $previousDatabaseIntegration
    }
}

Invoke-GateStep 'Backend default regression' { uv run pytest -q }

Write-Host '============================================================'
Write-Host 'Scheduler Persistence Gate completed.'
Write-Host 'Only locally executed test results are reported.'
Write-Host '============================================================'
