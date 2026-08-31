$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Worker/Scheduler Diagnostics Unit Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: unit/contract tests do not require manually entered IDs or business data."

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required but was not found in PATH."
}
if (-not (Test-Path ".\\pyproject.toml")) {
    throw "Run this gate from the backend directory."
}

Write-Host "[1/4] Migration/head verification"
uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic head verification failed." }

Write-Host "[2/4] Runtime Diagnostics unit + API contract"
uv run pytest -q tests/unit/test_runtime_diagnostics.py tests/api_contract/test_runtime_diagnostics_contract.py
if ($LASTEXITCODE -ne 0) { throw "Runtime Diagnostics unit/contract tests failed." }

Write-Host "[3/4] Backend targeted regression"
uv run pytest -q tests/unit/test_global_runtime_operations.py tests/unit/test_runtime_metric_contract.py tests/unit/test_runtime_telemetry.py
if ($LASTEXITCODE -ne 0) { throw "Backend targeted regression failed." }

Write-Host "[4/4] Service prerequisite policy"
Write-Host "[NOT EXECUTED] Real API execution is intentionally not started by this gate."
Write-Host "[INFO] A future Diagnostics Real Acceptance must require services already running and generate its own test identities."
Write-Host "[PASS] Phase 2.10-II Worker/Scheduler Diagnostics Unit Gate completed."
