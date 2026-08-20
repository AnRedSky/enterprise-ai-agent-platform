$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Real API Validation"
Write-Host "External HTTP API only; no ASGI TestClient"
Write-Host "============================================================"

if (-not $env:ACCESS_TOKEN) {
    throw "ACCESS_TOKEN is required. Set a real Bearer token before running API validation."
}
if (-not $env:WORKFLOW_ID) {
    throw "WORKFLOW_ID is required. Set an existing workflow ID visible to the authenticated user."
}

if (-not $env:API_BASE_URL) {
    $env:API_BASE_URL = "http://127.0.0.1:8000/api/v1"
}

Write-Host "[1/2] Real HTTP workflow / governance API tests"
uv run pytest -q tests/api_real -m real_api
if ($LASTEXITCODE -ne 0) {
    throw "Real API validation failed. Frontend/backend integration is blocked."
}

Write-Host "[2/2] API gate passed"
Write-Host "Real API validation completed successfully. Frontend/backend integration may proceed."
