$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-I Runtime Notification Lifecycle Real Gate"
Write-Host "============================================================"
Write-Host "[0/6] Local prerequisite verification"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv is required." }
if (-not (Test-Path (Join-Path $BackendRoot ".env.example"))) { throw "backend/.env.example is required." }
Write-Host "Configuration policy: backend/.env.example is the unified local test baseline."
Write-Host "Test data policy: acceptance creates and cleans all tenant/rule/policy/destination data automatically."
Write-Host "Service policy: this Gate NEVER starts or stops API, Scheduler, or Worker processes."

function Assert-SchedulerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_scheduler\.py'
    })
    if ($processes.Count -eq 0) {
        throw "Required Scheduler Service is not running. Start it manually before this Gate: uv run python run_scheduler.py"
    }
    Write-Host "[PASS] Scheduler Service available: $($processes.Count) process(es)."
}

function Assert-WorkerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_worker\.py'
    })
    if ($processes.Count -eq 0) {
        throw "Required Worker Service is not running. Start it manually before this Gate: uv run python run_worker.py"
    }
    Write-Host "[PASS] Worker Service available: $($processes.Count) process(es)."
}

Write-Host "[1/6] Migration/head verification"
& uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic heads failed." }
& uv run alembic upgrade heads
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade heads failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/6] Targeted migration/runtime test collection"
& uv run pytest -q tests/unit/test_migration_graph.py tests/api_real/test_alert_notification_runtime_acceptance.py --collect-only --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Notification test collection failed." }

Write-Host "[3/6] Verify required runtime services (no service is started by this Gate)"
Assert-SchedulerAvailable
Assert-WorkerAvailable

Write-Host "[4/6] Alert -> Notification -> Worker Runtime Acceptance"
& uv run pytest -q tests/api_real/test_alert_notification_runtime_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Alert Notification Runtime Acceptance failed." }

Write-Host "[5/6] Migration graph regression"
& uv run pytest -q tests/unit/test_migration_graph.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Migration graph regression failed." }

Write-Host "[6/6] Runtime lifecycle handoff"
Write-Host "Verified by the acceptance suite: Alert Evaluation -> Firing/Recovery -> Policy -> Group/Dedup/Cooldown -> Provider Routing -> Worker -> Outcome -> Fallback -> SLO/Metrics -> Audit."
Write-Host "[PASS] Phase 2.10-I Runtime Notification Lifecycle Real Gate completed."
Write-Host "[INFO] This Gate never starts or stops any service and generates all test identities/data automatically."
