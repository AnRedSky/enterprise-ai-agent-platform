$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.5-B Tenant Contract"
Write-Host "Backend local manual validation only"
Write-Host "============================================================"

Write-Host "[1/3] Database migration to head"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

Write-Host "[2/3] Tenant contract / workflow isolation tests"
uv run pytest -q tests/test_tenant_contract.py tests/test_api_workflows_endpoints.py
if ($LASTEXITCODE -ne 0) { throw "Tenant contract tests failed." }

Write-Host "[3/3] Backend regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend regression failed." }

Write-Host "Tenant contract validation passed."
