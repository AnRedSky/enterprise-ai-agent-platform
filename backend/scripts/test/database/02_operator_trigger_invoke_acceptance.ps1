$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Trigger Invoke PostgreSQL Acceptance'
Write-Host 'Scope: manual Trigger Invoke -> Result Resource -> Idempotency -> Audit/Trace atomicity'
Write-Host 'Service policy: this gate never creates, starts, restarts, or stops protected services.'
Write-Host 'Test data policy: all Tenant/User/Workflow/Trigger/Execution records are generated and cleaned automatically.'
Write-Host '============================================================'

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Push-Location $backendRoot
try {
    Write-Host '[1/3] Verify PostgreSQL dependency'
    Write-Host '[INFO] Database connection is resolved by the project backend configuration; no manual test data or connection value is requested.'

    Write-Host '[2/3] Verify migration head'
    & uv run alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw 'Alembic migration/head verification failed.'
    }

    Write-Host '[3/3] Execute Trigger Invoke PostgreSQL acceptance'
    $env:RUN_DATABASE_INTEGRATION = '1'
    try {
        & uv run pytest -q -W error tests/integration/test_operator_trigger_invoke.py -s
        if ($LASTEXITCODE -ne 0) {
            throw 'Trigger Invoke PostgreSQL acceptance failed.'
        }
    }
    finally {
        Remove-Item Env:RUN_DATABASE_INTEGRATION -ErrorAction SilentlyContinue
    }

    Write-Host '[PASS] Trigger Invoke PostgreSQL acceptance gate completed.'
    Write-Host '[INFO] No service was created, started, restarted, or stopped by this gate.'
}
finally {
    Pop-Location
}
