$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# phase-2.9 -> test -> scripts -> backend
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.9-D Webhook Delivery Real Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local prerequisite verification (no service startup)"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv is required." }
if (-not (Test-Path (Join-Path $BackendRoot ".env.example"))) { throw "backend/.env.example is required as the unified test configuration baseline." }
Write-Host "Configuration policy: backend/.env.example is the unified local test configuration baseline."
Write-Host "Service policy: this Gate never starts or stops API, Worker, Scheduler, Redis, or PostgreSQL."
Write-Host "Test data policy: the acceptance test generates and cleans tenant/event/delivery data automatically."

Write-Host "[1/4] Migration/head verification"
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/4] Webhook security + provider regression"
& uv run pytest -q tests/unit/test_webhook_security.py tests/unit/test_webhook_provider.py
if ($LASTEXITCODE -ne 0) { throw "Webhook security/provider regression failed." }

Write-Host "[3/4] Real HTTP + PostgreSQL delivery/replay/audit acceptance"
& uv run pytest -q tests/api_real/test_webhook_delivery_acceptance.py -m real_api
if ($LASTEXITCODE -ne 0) { throw "Webhook Delivery real acceptance failed." }

Write-Host "[4/4] Targeted webhook regression"
& uv run pytest -q tests/unit/test_integration_event_contract.py tests/unit/test_integration_event_persistence.py tests/unit/test_integration_event_delivery.py tests/unit/test_webhook_provider.py tests/unit/test_webhook_security.py
if ($LASTEXITCODE -ne 0) { throw "Targeted webhook regression failed." }

Write-Host "[PASS] Phase 2.9-D Webhook Delivery Real Gate completed."
