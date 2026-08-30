$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-I Runtime Notification Lifecycle Real Gate"
Write-Host "============================================================"
Write-Host "[0/6] Local precondition checks"
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

Write-Host "[1/6] Migration/head verification"
& uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic heads check failed." }
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current check failed." }

Write-Host "[2/6] Targeted migration/runtime test collection"
& uv run pytest -q tests/unit/test_migration_graph.py tests/api_real/test_alert_notification_runtime_acceptance.py --collect-only --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Notification test collection failed." }

Write-Host "[3/6] Runtime service checks (no automatic startup)"
$schedulerReady = Test-SchedulerAvailable
$workerReady = Test-WorkerAvailable
if (-not ($schedulerReady -and $workerReady)) {
    Write-Host "[NOT EXECUTED] Runtime Notification Lifecycle Real Acceptance was not executed because required services were not already running."
    Write-Host "[INFO] This gate never starts or stops services and never requires manual test data entry."
    exit 0
}

Write-Host "[4/6] Alert -> Notification -> Worker Runtime Acceptance"
& uv run pytest -q tests/api_real/test_alert_notification_runtime_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Alert Notification Runtime Acceptance failed." }

Write-Host "[5/6] Migration graph regression"
& uv run pytest -q tests/unit/test_migration_graph.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Migration graph regression failed." }

Write-Host "[6/6] Runtime lifecycle handoff"
Write-Host "Verified lifecycle: Alert Evaluation -> Firing/Recovery -> Policy -> Group/Dedup/Cooldown -> Provider Routing -> Worker -> Outcome -> Fallback -> SLO/Metrics -> Audit."
Write-Host "[PASS] Phase 2.10-I Runtime Notification Lifecycle Real Gate completed."
Write-Host "[INFO] This gate never starts or stops services and automatically generates all test identities and business data."
