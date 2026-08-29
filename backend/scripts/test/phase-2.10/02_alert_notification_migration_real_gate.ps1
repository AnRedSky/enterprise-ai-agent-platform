$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-I Migration Real Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local prerequisite verification (no service startup)"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv is required." }
if (-not (Test-Path (Join-Path $BackendRoot ".env.example"))) { throw "backend/.env.example is required." }
Write-Host "Configuration policy: backend/.env.example is the unified local test configuration baseline."
Write-Host "Service policy: this Gate never starts or stops API, Worker, Scheduler, Redis, or PostgreSQL."
Write-Host "Test data policy: no manual tenant, event, provider, destination, or credential input is required."

Write-Host "[1/5] Alembic topology verification"
& uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic heads failed." }
& uv run pytest -q tests/unit/test_migration_graph.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Migration topology regression failed." }

Write-Host "[2/5] Database migration upgrade"
& uv run alembic upgrade heads
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade heads failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[3/5] Phase 2.10-I runtime alert targeted regression"
& uv run pytest -q tests/unit/test_runtime_operations_lifecycle_api.py tests/api_real/test_runtime_operations_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime alert operations regression failed." }

Write-Host "[4/5] Backend default regression"
& uv run pytest -q --tb=short
if ($LASTEXITCODE -ne 0) { throw "Backend default regression failed." }

Write-Host "[5/5] Migration handoff"
Write-Host "Required final state: 0046_alert_rule_escalation is the single Alembic head and 0045 is reachable only after both 0044 branches."
Write-Host "[PASS] Phase 2.10-I Migration Real Gate completed."
