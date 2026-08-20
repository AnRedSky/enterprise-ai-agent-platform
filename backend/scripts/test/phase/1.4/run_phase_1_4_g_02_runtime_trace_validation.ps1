$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.4-G-02 Runtime Trace"
Write-Host "Local manual validation only"
Write-Host "============================================================"

Write-Host "[1/4] Database migration to head"
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

Write-Host "[2/4] Runtime trace + retrieval metadata contract"
& uv run pytest -q tests/test_runtime_trace_metadata.py tests/test_api_runtime_endpoints.py tests/test_observability.py
if ($LASTEXITCODE -ne 0) { throw "Runtime trace backend tests failed." }

Write-Host "[3/4] Frontend Runtime timeline contract"
Push-Location (Join-Path $PSScriptRoot "..\..\frontend")
try {
    & npm test -- --run tests/views/Runtime.test.ts
    if ($LASTEXITCODE -ne 0) { throw "Frontend Runtime tests failed." }

    Write-Host "[4/4] Frontend production build"
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
} finally {
    Pop-Location
}

Write-Host "============================================================"
Write-Host "Phase 1.4-G-02 local validation completed."
Write-Host "Runtime execution detail now returns the persisted event timeline."
Write-Host "Retrieval spans persist knowledge-base, top-k, citation and source metadata."
Write-Host "No GitHub Actions workflow is invoked by this script."
Write-Host "============================================================"
