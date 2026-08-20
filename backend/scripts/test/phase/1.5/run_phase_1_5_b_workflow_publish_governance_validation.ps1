$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.5-B Workflow Publish Governance"
Write-Host "Backend local manual validation only"
Write-Host "============================================================"

Write-Host "[1/4] Database migration to head"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

Write-Host "[2/4] Workflow publish governance contract"
uv run pytest -q tests/test_workflow_publish_governance.py tests/test_api_workflows_endpoints.py
if ($LASTEXITCODE -ne 0) { throw "Workflow governance tests failed." }

Write-Host "[3/4] Full backend regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend regression failed." }

Write-Host "[4/4] Result summary"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "============================================================"
Write-Host "Phase 1.5-B backend validation completed."
Write-Host "No frontend tests or GitHub Actions workflow are invoked."
Write-Host "============================================================"
