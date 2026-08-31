$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Runtime Audit Query Hardening Unit Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: unit/contract tests do not require manually entered IDs or business data."

Write-Host "[1/5] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/5] Migration upgrade verification"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }

Write-Host "[3/5] Runtime Audit Query unit + API contract"
uv run pytest -q tests/unit/test_runtime_operations_audit_query.py tests/api_contract/test_runtime_operations_audit_query_contract.py
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit Query unit/contract tests failed." }

Write-Host "[4/5] Backend targeted regression"
uv run pytest -q tests/unit/test_runtime_operations_audit_query.py tests/api_contract/test_api_runtime_endpoints.py
if ($LASTEXITCODE -ne 0) { throw "Runtime targeted regression failed." }

Write-Host "[5/5] Service prerequisite policy"
Write-Host "[NOT EXECUTED] Real API execution is intentionally not started by this gate."
Write-Host "[INFO] Real Acceptance, if required, must use already-running local services and automatically generated fixtures."
Write-Host "[PASS] Phase 2.10-II Runtime Audit Query Hardening Unit Gate completed."
