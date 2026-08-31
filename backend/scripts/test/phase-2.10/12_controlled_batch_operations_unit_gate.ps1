$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Controlled Batch Operations Unit Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: unit/contract tests do not require manually entered IDs or business data."

Write-Host "[1/4] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/4] Controlled Batch Operations unit + API contract"
uv run pytest -q `
  tests/unit/test_batch_operator_actions.py `
  tests/api_contract/test_batch_operator_actions_contract.py
if ($LASTEXITCODE -ne 0) { throw "Controlled Batch Operations unit/contract tests failed." }

Write-Host "[3/4] Backend targeted regression"
uv run pytest -q `
  tests/unit/test_operator_action_governance.py `
  tests/unit/test_global_runtime_operations.py `
  tests/unit/test_runtime_diagnostics.py `
  tests/unit/test_runtime_metric_contract.py `
  tests/unit/test_runtime_telemetry.py
if ($LASTEXITCODE -ne 0) { throw "Controlled Batch Operations targeted regression failed." }

Write-Host "[4/4] Service prerequisite policy"
Write-Host "[NOT EXECUTED] Real API execution is intentionally not started by this gate."
Write-Host "[INFO] Real Acceptance requires services already running and acceptance fixtures must generate all test identities and business facts."
Write-Host "[PASS] Phase 2.10-II Controlled Batch Operations Unit Gate completed."
