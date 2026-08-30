$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-I Runtime Notification Lifecycle Real Gate"
Write-Host "============================================================"
Write-Host "[0/8] Local precondition checks"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv was not found." }
if (-not (Test-Path (Join-Path $BackendRoot ".env.example"))) { throw "backend/.env.example was not found." }
Write-Host "Configuration baseline: backend/.env.example"
Write-Host "Test data: the acceptance tests create and clean up their own test identities and business data."
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."

function Test-SchedulerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_scheduler\.py'
    })
    if ($processes.Count -eq 0) {
        Write-Host "[NOT EXECUTED] Scheduler Service is not running."
        return $false
    }
    Write-Host "[PASS] Scheduler Service is available: $($processes.Count) process(es)."
    return $true
}

function Test-WorkerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_worker\.py'
    })
    if ($processes.Count -eq 0) {
        Write-Host "[NOT EXECUTED] Worker Service is not running."
        return $false
    }
    Write-Host "[PASS] Worker Service is available: $($processes.Count) process(es)."
    return $true
}

Write-Host "[1/8] Migration/head verification"
& uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic heads check failed." }
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current check failed." }

Write-Host "[2/8] Runtime unit regression"
& uv run pytest -q `
    tests/unit/test_migration_graph.py `
    tests/unit/test_webhook_delivery_repository.py `
    tests/unit/test_webhook_delivery_worker.py `
    tests/unit/test_integration_publisher.py `
    tests/unit/test_alert_lifecycle_tenant_scope.py `
    tests/unit/test_runtime_metric_contract.py `
    --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime unit regression failed." }

Write-Host "[3/8] Targeted migration/runtime test collection"
& uv run pytest -q `
    tests/unit/test_migration_graph.py `
    tests/unit/test_webhook_delivery_repository.py `
    tests/unit/test_webhook_delivery_worker.py `
    tests/unit/test_integration_publisher.py `
    tests/unit/test_alert_lifecycle_tenant_scope.py `
    tests/unit/test_runtime_metric_contract.py `
    tests/api_real/test_alert_notification_runtime_acceptance.py `
    tests/api_real/test_webhook_delivery_claim_acceptance.py `
    tests/api_real/test_runtime_operations_acceptance.py `
    tests/api_real/test_runtime_enterprise_acceptance.py `
    --collect-only --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Notification test collection failed." }

Write-Host "[4/8] Runtime service checks (no automatic startup)"
$schedulerReady = Test-SchedulerAvailable
$workerReady = Test-WorkerAvailable
if (-not ($schedulerReady -and $workerReady)) {
    Write-Host "[NOT EXECUTED] Runtime Notification Lifecycle Real Acceptance was not executed because required services were not already running."
    Write-Host "[INFO] This gate never starts or stops services and never requires manual test data entry."
    exit 0
}

Write-Host "[5/8] Alert -> Notification -> Worker Runtime Acceptance"
& uv run pytest -q -m real_api `
    tests/api_real/test_alert_notification_runtime_acceptance.py `
    tests/api_real/test_webhook_delivery_claim_acceptance.py `
    tests/api_real/test_runtime_operations_acceptance.py `
    tests/api_real/test_runtime_enterprise_acceptance.py `
    --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Enterprise Acceptance failed." }

Write-Host "[6/8] Migration graph regression"
& uv run pytest -q tests/unit/test_migration_graph.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Migration graph regression failed." }

Write-Host "[7/8] Runtime metric export regression"
& uv run pytest -q tests/unit/test_runtime_metric_contract.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime metric export regression failed." }

Write-Host "[8/8] Runtime lifecycle handoff"
Write-Host "Verified lifecycle: Alert Evaluation -> Firing/Recovery -> Policy -> Group/Dedup/Cooldown -> Provider Routing -> Worker -> Claim Competition -> Outcome -> Fallback -> SLO/Metrics -> Prometheus/OTLP Export -> Audit."
Write-Host "[PASS] Phase 2.10-I Runtime Notification Lifecycle Real Gate completed."
Write-Host "[INFO] This gate never starts or stops services and automatically generates all test identities and business data."