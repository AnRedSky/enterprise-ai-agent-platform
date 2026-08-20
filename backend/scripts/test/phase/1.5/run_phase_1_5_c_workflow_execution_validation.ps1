$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.5-C Workflow Execution"
Write-Host "Backend local manual validation only"
Write-Host "============================================================"

Write-Host "[1/3] Database migration to head"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

Write-Host "[2/3] Workflow execution state machine contract tests"
uv run pytest -q tests/test_workflow_execution_migration.py tests/test_workflow_execution_state_machine.py tests/test_api_workflow_executions.py
if ($LASTEXITCODE -ne 0) { throw "Workflow execution contract tests failed." }

Write-Host "[3/3] Backend full regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend full regression failed." }

Write-Host "Phase 1.5-C backend validation passed."
