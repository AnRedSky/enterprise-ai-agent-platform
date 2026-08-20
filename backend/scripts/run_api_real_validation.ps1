$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Real API Validation"
Write-Host "External HTTP API only; no ASGI TestClient"
Write-Host "Prerequisites are bootstrapped automatically"
Write-Host "============================================================"

if (-not $env:API_BASE_URL) {
    $env:API_BASE_URL = "http://127.0.0.1:8000/api/v1"
}

$envFile = Join-Path $PSScriptRoot ".api_real_validation.env.json"

try {
    Write-Host "[1/3] Bootstrap real API test identity"
    uv run python .\scripts\bootstrap_api_real_validation.py
    if ($LASTEXITCODE -ne 0) {
        throw "Real API prerequisite bootstrap failed. Frontend/backend integration is blocked."
    }

    if (-not (Test-Path $envFile)) {
        throw "Real API bootstrap did not produce the temporary environment file."
    }

    $bootstrapEnv = Get-Content $envFile -Raw | ConvertFrom-Json
    $env:ACCESS_TOKEN = [string]$bootstrapEnv.ACCESS_TOKEN
    $env:WORKFLOW_ID = [string]$bootstrapEnv.WORKFLOW_ID
    $env:WORKFLOW_EXECUTION_ID = [string]$bootstrapEnv.WORKFLOW_EXECUTION_ID

    Write-Host "[2/3] Real HTTP workflow / governance API tests"
    uv run pytest -q tests/api_real -m real_api
    if ($LASTEXITCODE -ne 0) {
        throw "Real API validation failed. Frontend/backend integration is blocked."
    }

    Write-Host "[3/3] API gate passed"
    Write-Host "Real API validation completed successfully. Frontend/backend integration may proceed."
}
finally {
    if (Test-Path $envFile) {
        Remove-Item $envFile -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:WORKFLOW_EXECUTION_ID -ErrorAction SilentlyContinue
}
