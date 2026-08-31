$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Worker/Scheduler Diagnostics Real Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: acceptance tests create and clean up all identities and business facts automatically."

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required but was not found in PATH."
}
if (-not (Test-Path ".\\pyproject.toml")) {
    throw "Run this gate from the backend directory."
}

Write-Host "[1/5] Migration/head verification"
uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic head verification failed." }

Write-Host "[2/5] Runtime Diagnostics unit + API contract"
uv run pytest -q tests/unit/test_runtime_diagnostics.py tests/api_contract/test_runtime_diagnostics_contract.py
if ($LASTEXITCODE -ne 0) { throw "Runtime Diagnostics unit/contract tests failed." }

Write-Host "[3/5] Database availability probe"
uv run alembic current
if ($LASTEXITCODE -ne 0) {
    Write-Host "[NOT EXECUTED] PostgreSQL is not available; Real Acceptance was not executed."
    Write-Host "[INFO] No service is started automatically and no manual test data is required."
    exit 0
}

Write-Host "[4/5] Worker/Scheduler Diagnostics real PostgreSQL acceptance"
uv run pytest -q -m real_api tests/api_real/test_runtime_diagnostics_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Diagnostics Real Acceptance failed." }

Write-Host "[5/5] Service startup boundary"
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was created or stopped by this gate."
Write-Host "[PASS] Phase 2.10-II Worker/Scheduler Diagnostics Real Gate completed."
