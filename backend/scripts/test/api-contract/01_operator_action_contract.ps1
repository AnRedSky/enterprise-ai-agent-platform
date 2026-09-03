$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Operator Action API Contract Gate'
Write-Host 'Scope: HTTP authentication -> request contract -> idempotency header -> conflict mapping'
Write-Host 'Service policy: this gate never creates, starts, restarts, or stops protected services.'
Write-Host 'Test data policy: Contract tests generate their own UUID/token fixtures; no manual values are required.'
Write-Host '============================================================'

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Push-Location $backendRoot
try {
    Write-Host '[1/2] Execute Operator Action API Contract tests'
    & uv run pytest -q -W error tests/api_contract/test_api_operator_actions.py tests/api_contract/test_api_workflows_endpoints.py -s
    if ($LASTEXITCODE -ne 0) {
        throw 'Operator Action API Contract tests failed.'
    }

    Write-Host '[2/2] Report service lifecycle boundary'
    Write-Host '[PASS] Operator Action API Contract gate completed.'
    Write-Host '[INFO] Contract tests use ASGI transport and do not require a running API, PostgreSQL, Redis, Worker, or Scheduler.'
    Write-Host '[INFO] No service was created, started, restarted, or stopped by this gate.'
} finally {
    Pop-Location
}
