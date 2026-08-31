$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Runtime Audit Query Hardening Real Gate"
Write-Host "============================================================"
Write-Host "[0/6] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: acceptance tests create and clean up all identities and audit facts automatically."

Write-Host "[1/6] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/6] Migration upgrade verification"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }

Write-Host "[3/6] Runtime Audit Query unit + API contract"
uv run pytest -q tests/unit/test_runtime_operations_audit_query.py tests/api_contract/test_runtime_operations_audit_query_contract.py
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit Query unit/contract tests failed." }

Write-Host "[4/6] Database availability probe"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Database availability probe failed." }

Write-Host "[5/6] Runtime Audit Query real PostgreSQL acceptance"
uv run pytest -q -m real_api tests/api_real/test_runtime_audit_query_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit Query real PostgreSQL acceptance failed." }

Write-Host "[6/6] Service startup boundary"
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process is created, started, restarted, or stopped by this gate."
Write-Host "[PASS] Phase 2.10-II Runtime Audit Query Hardening Real Gate completed."
