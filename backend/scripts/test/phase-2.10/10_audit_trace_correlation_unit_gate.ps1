$ErrorActionPreference = "Stop"
$backend = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $backend

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Audit / Trace Correlation Unit Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: unit/contract tests do not require manually entered IDs or business data."

Write-Host "[1/4] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/4] Audit / Trace correlation unit + API contract"
uv run pytest -q tests/unit/test_runtime_audit_trace_correlation.py tests/api_contract/test_runtime_audit_trace_correlation_contract.py
if ($LASTEXITCODE -ne 0) { throw "Audit / Trace correlation unit/contract tests failed." }

Write-Host "[3/4] Backend targeted regression"
uv run pytest -q tests/unit/test_runtime_operations_audit.py tests/unit/test_runtime_diagnostics.py tests/unit/test_global_runtime_operations.py
if ($LASTEXITCODE -ne 0) { throw "Backend targeted regression failed." }

Write-Host "[4/4] Service prerequisite policy"
Write-Host "[NOT EXECUTED] Real PostgreSQL/API execution is intentionally not started by this gate."
Write-Host "[INFO] Real Acceptance must use already-running local services and automatically generated fixtures."
Write-Host "[PASS] Phase 2.10-II Audit / Trace Correlation Unit Gate completed."
