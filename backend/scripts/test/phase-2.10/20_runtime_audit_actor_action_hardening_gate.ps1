$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Runtime Audit Actor + Action Hardening Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: tests generate all required identifiers and audit facts automatically."

Write-Host "[1/5] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/5] Migration upgrade verification"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }

Write-Host "[3/5] Actor + action unit/API contract"
uv run pytest -q tests/unit/test_runtime_operations_audit_query.py tests/api_contract/test_runtime_operations_audit_actor_filter_contract.py tests/api_contract/test_runtime_operations_audit_query_contract.py
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit actor/action unit or API contract tests failed." }

Write-Host "[4/5] Real PostgreSQL tenant isolation + compound operational filtering"
uv run pytest -q -m real_api tests/api_real/test_runtime_audit_query_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit actor/action PostgreSQL acceptance failed." }

Write-Host "[5/5] Service startup boundary"
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was created or stopped by this gate."
Write-Host "[PASS] Phase 2.10-II Runtime Audit Actor + Action Hardening Gate completed."
