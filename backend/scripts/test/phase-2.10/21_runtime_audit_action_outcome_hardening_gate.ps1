$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $backendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Runtime Audit Action + Outcome Hardening Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: tests generate all required identifiers and audit facts automatically."

Write-Host "[1/5] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Migration/head verification failed." }

Write-Host "[2/5] Migration upgrade verification"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Migration upgrade verification failed." }

Write-Host "[3/5] Runtime Audit action + outcome unit/API contract"
uv run pytest -q tests/api_contract/test_runtime_operations_audit_query_contract.py tests/api_contract/test_runtime_operations_audit_actor_filter_contract.py tests/api_contract/test_runtime_operations_audit_actor_action_contract.py
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit action/outcome unit or API contract tests failed." }

Write-Host "[4/5] Runtime Audit action + outcome real PostgreSQL acceptance"
uv run pytest -q -m real_api tests/api_real/test_runtime_audit_query_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit action/outcome real PostgreSQL acceptance failed." }

Write-Host "[5/5] Service startup boundary"
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was created or stopped by this gate."
Write-Host "[PASS] Phase 2.10-II Runtime Audit Action + Outcome Hardening Gate completed."
