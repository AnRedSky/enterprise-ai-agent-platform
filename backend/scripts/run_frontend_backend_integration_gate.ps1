$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Frontend/Backend Integration Gate"
Write-Host "Required order: backend regression -> real API -> frontend tests/build"
Write-Host "============================================================"

if (-not $env:ACCESS_TOKEN) {
    throw "ACCESS_TOKEN is required for the real API gate."
}
if (-not $env:WORKFLOW_ID) {
    throw "WORKFLOW_ID is required for the real API gate."
}

Write-Host "[1/4] Backend unit/contract regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend regression failed. Integration is blocked." }

Write-Host "[2/4] Database migration head"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed. Integration is blocked." }
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Migration head verification failed. Integration is blocked." }

Write-Host "[3/4] Real HTTP API validation (mandatory before frontend/backend integration)"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_real_validation.ps1
if ($LASTEXITCODE -ne 0) { throw "Real API validation failed. Frontend/backend integration is blocked." }

Write-Host "[4/4] Frontend automated regression"
Push-Location ..\frontend
try {
    npm test
    if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
}
finally {
    Pop-Location
}

Write-Host "============================================================"
Write-Host "Automated integration gate passed. Proceed to browser-level frontend/backend scenarios."
Write-Host "============================================================"
