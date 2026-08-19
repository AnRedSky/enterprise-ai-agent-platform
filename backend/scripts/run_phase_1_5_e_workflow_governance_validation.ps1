$ErrorActionPreference = "Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.5-E Governance Audit Trace"
Write-Host "Backend local manual validation only"
Write-Host "============================================================"

Write-Host "[1/4] Database migration to head"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

Write-Host "[2/4] Governance / Audit / Trace contract tests"
uv run pytest -q tests/test_workflow_governance.py
if ($LASTEXITCODE -ne 0) { throw "Governance contract tests failed." }

Write-Host "[3/4] Backend full regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend full regression failed." }

Write-Host "[4/4] Migration head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Migration current failed." }

Write-Host "Phase 1.5-E Backend validation completed."
