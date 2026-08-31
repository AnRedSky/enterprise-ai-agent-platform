$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $backendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Runtime Audit / Trace Correlation Contract Hardening Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: unit/API Contract tests require no manual IDs or business data."

Write-Host "[1/4] Runtime correlation unit regression"
uv run pytest -q tests/unit/test_runtime_audit_trace_correlation.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime correlation unit regression failed." }

Write-Host "[2/4] Runtime correlation API Contract hardening"
uv run pytest -q tests/api_contract/test_runtime_correlations_contract.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime correlation API Contract hardening failed." }

Write-Host "[3/4] Backend targeted regression"
uv run pytest -q tests/unit/test_runtime_audit_trace_correlation.py tests/api_contract/test_runtime_correlations_contract.py tests/api_contract/test_api_runtime_endpoints.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Backend targeted regression failed." }

Write-Host "[4/4] Service startup boundary"
Write-Host "[NOT EXECUTED] No service startup is permitted by this gate."
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was created, started, restarted, or stopped by this gate."
Write-Host "[PASS] Runtime Audit / Trace Correlation Contract Hardening Gate completed."
