$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Controlled Batch Operations Real Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: acceptance tests create and clean up all identities and business facts automatically."

Write-Host "[1/5] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/5] Controlled Batch Operations unit + API contract"
uv run pytest -q `
  tests/unit/test_batch_operator_actions.py `
  tests/api_contract/test_batch_operator_actions_contract.py
if ($LASTEXITCODE -ne 0) { throw "Controlled Batch Operations unit/contract tests failed." }

Write-Host "[3/5] Database availability probe"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Database availability probe failed." }

Write-Host "[4/5] Controlled Batch Operations real PostgreSQL acceptance"
uv run pytest -q -m real_api tests/api_real/test_batch_operator_actions_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Controlled Batch Operations real PostgreSQL acceptance failed." }

Write-Host "[5/5] Service startup boundary"
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was created or stopped by this gate."
Write-Host "[PASS] Phase 2.10-II Controlled Batch Operations Real Gate completed."
