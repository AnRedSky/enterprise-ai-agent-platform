 # Phase 2.9-C Reliable Delivery PostgreSQL Real Gate
$ErrorActionPreference = "Stop"
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\.." )).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.9-C Reliable Delivery PostgreSQL Gate"
Write-Host "============================================================"
Write-Host "[0/3] Local prerequisite verification (no service startup)"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed or is not available on PATH."
}

$envFile = Join-Path $BackendRoot ".env"
$envDevFile = Join-Path $BackendRoot ".env.dev"
if (-not (Test-Path $envFile) -and -not (Test-Path $envDevFile)) {
    throw "No backend/.env or backend/.env.dev was found; PostgreSQL connection configuration cannot be verified."
}

Write-Host "Service policy: this Gate never starts or stops API, Worker, Scheduler, Redis, or PostgreSQL."
Write-Host "Test data policy: tests generate tenant, event, and idempotency data automatically; no manual test input is required."

Write-Host "[1/3] Migration/head verification"
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/3] Phase 2.9-C PostgreSQL concurrency/recovery tests"
& uv run pytest -q tests/api_real/test_integration_event_delivery_postgres.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Phase 2.9-C PostgreSQL Real Gate failed." }

Write-Host "[3/3] Targeted delivery unit regression"
& uv run pytest -q tests/unit/test_integration_event_contract.py tests/unit/test_integration_event_persistence.py tests/unit/test_integration_event_delivery.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Phase 2.9-C targeted unit regression failed." }

Write-Host "[PASS] Phase 2.9-C Reliable Delivery PostgreSQL Real Gate completed."
