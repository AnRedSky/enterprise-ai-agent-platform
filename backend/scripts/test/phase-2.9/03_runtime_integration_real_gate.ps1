$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.9-E Runtime Integration Real Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local prerequisite verification (no service startup)"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv is required." }
if (-not (Test-Path (Join-Path $BackendRoot ".env.example"))) { throw "backend/.env.example is required as the unified test configuration baseline." }
Write-Host "Configuration policy: backend/.env.example is the unified local test configuration baseline."
Write-Host "Service policy: this Gate never starts or stops API, Worker, Scheduler, Redis, or PostgreSQL."
Write-Host "Test data policy: the acceptance test creates tenant-scoped fixtures automatically; no manual input is required."

Write-Host "[1/4] Migration/head verification"
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/4] Runtime Integration real PostgreSQL acceptance"
& uv run pytest -q tests/api_real/test_runtime_integration_acceptance.py --tb=short -m real_api
if ($LASTEXITCODE -ne 0) { throw "Runtime Integration real acceptance failed." }

Write-Host "[3/4] Runtime Integration contract/unit regression"
& uv run pytest -q tests/unit/test_integration_event_contract.py tests/unit/test_integration_event_persistence.py tests/unit/test_integration_event_delivery.py tests/unit/test_webhook_provider.py tests/unit/test_webhook_security.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Integration targeted regression failed." }

Write-Host "[4/4] Webhook Real Acceptance handoff"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptRoot "02_webhook_delivery_real_gate.ps1")
if ($LASTEXITCODE -ne 0) { throw "Phase 2.9-D Webhook Real Acceptance failed." }

Write-Host "[PASS] Phase 2.9-E Runtime Integration + Phase 2.9-D Webhook Real Acceptance completed."
