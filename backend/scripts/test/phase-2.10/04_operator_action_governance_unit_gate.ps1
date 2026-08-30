$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Operator Action Governance Unit Gate"
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

Write-Host "[2/4] Operator Action unit regression"
uv run pytest -q tests/unit/test_operator_action_governance.py
if ($LASTEXITCODE -ne 0) { throw "Operator Action unit tests failed." }

Write-Host "[3/4] Operator Action API contract regression"
uv run pytest -q tests/api_contract/test_api_operator_actions.py
if ($LASTEXITCODE -ne 0) { throw "Operator Action API contract tests failed." }

Write-Host "[4/4] Service prerequisite policy"
Write-Host "[NOT EXECUTED] Real API execution is intentionally not started by this gate."
Write-Host "[INFO] When Phase 2.10-II Real Acceptance is added, required services must already be running."
Write-Host "[INFO] No test data entry is required; acceptance fixtures must create and clean up their own identities and business data."
Write-Host "[PASS] Phase 2.10-II Operator Action Governance Unit Gate completed."
