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
Write-Host "Service policy: this Gate starts and stops only the Scheduler and Worker required by this runtime acceptance."

Write-Host "[1/6] Migration/head verification"
& uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic heads failed." }
& uv run alembic upgrade heads
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade heads failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/6] Targeted regression before service startup"
& uv run pytest -q tests/unit/test_migration_graph.py tests/api_real/test_alert_notification_runtime_acceptance.py --collect-only --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Notification test collection failed." }

$oldMaxAttempts = $env:WEBHOOK_WORKER_MAX_ATTEMPTS
$oldPoll = $env:WEBHOOK_WORKER_POLL_INTERVAL
$oldConcurrency = $env:WEBHOOK_WORKER_CONCURRENCY
$oldAcceptanceFlag = $env:PHASE_210_I_RUNTIME_SERVICES_STARTED
$scheduler = $null
$worker = $null
try {
    $env:WEBHOOK_WORKER_MAX_ATTEMPTS = "1"
    $env:WEBHOOK_WORKER_POLL_INTERVAL = "0.1"
    $env:WEBHOOK_WORKER_CONCURRENCY = "2"
    $env:PHASE_210_I_RUNTIME_SERVICES_STARTED = "1"

    Write-Host "[3/6] Starting Scheduler Service"
    $scheduler = Start-Process -FilePath "uv" -ArgumentList "run","python","run_scheduler.py" -WorkingDirectory $BackendRoot -PassThru
    Start-Sleep -Seconds 2
    if ($scheduler.HasExited) { throw "Scheduler Service exited during startup." }

    Write-Host "[4/6] Starting Worker Service"
    $worker = Start-Process -FilePath "uv" -ArgumentList "run","python","run_worker.py" -WorkingDirectory $BackendRoot -PassThru
    Start-Sleep -Seconds 2
    if ($worker.HasExited) { throw "Worker Service exited during startup." }

    Write-Host "[5/6] Alert -> Notification -> Worker Runtime Acceptance"
    & uv run pytest -q tests/api_real/test_alert_notification_runtime_acceptance.py --tb=short
    if ($LASTEXITCODE -ne 0) { throw "Alert Notification Runtime Acceptance failed." }

    Write-Host "[6/6] Runtime lifecycle handoff"
    Write-Host "Verified: Alert Evaluation -> Firing/Recovery -> Policy -> Group/Dedup/Cooldown -> Provider Routing -> Worker -> Outcome -> Fallback -> SLO/Metrics -> Audit."
    Write-Host "[PASS] Phase 2.10-I Runtime Notification Lifecycle Real Gate completed."
}
finally {
    if ($worker -and -not $worker.HasExited) { Stop-Process -Id $worker.Id -Force -ErrorAction SilentlyContinue }
    if ($scheduler -and -not $scheduler.HasExited) { Stop-Process -Id $scheduler.Id -Force -ErrorAction SilentlyContinue }
    if ($null -eq $oldMaxAttempts) { Remove-Item Env:WEBHOOK_WORKER_MAX_ATTEMPTS -ErrorAction SilentlyContinue } else { $env:WEBHOOK_WORKER_MAX_ATTEMPTS = $oldMaxAttempts }
    if ($null -eq $oldPoll) { Remove-Item Env:WEBHOOK_WORKER_POLL_INTERVAL -ErrorAction SilentlyContinue } else { $env:WEBHOOK_WORKER_POLL_INTERVAL = $oldPoll }
    if ($null -eq $oldConcurrency) { Remove-Item Env:WEBHOOK_WORKER_CONCURRENCY -ErrorAction SilentlyContinue } else { $env:WEBHOOK_WORKER_CONCURRENCY = $oldConcurrency }
    if ($null -eq $oldAcceptanceFlag) { Remove-Item Env:PHASE_210_I_RUNTIME_SERVICES_STARTED -ErrorAction SilentlyContinue } else { $env:PHASE_210_I_RUNTIME_SERVICES_STARTED = $oldAcceptanceFlag }
}
