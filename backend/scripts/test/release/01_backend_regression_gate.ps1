$ErrorActionPreference="Stop"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Backend Regression Gate"
Write-Host "Scope: backend regression -> migration -> tenant-safe real API"
Write-Host "Frontend tests/build are intentionally NOT executed here."
Write-Host "============================================================"

Push-Location $backendRoot
try {
    Write-Host "[1/3] Backend regression"
    uv run pytest -q
    if($LASTEXITCODE -ne 0){throw "Backend regression failed. Backend gate is blocked."}

    Write-Host "[2/3] Database migration/head verification"
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1
    if($LASTEXITCODE -ne 0){throw "Database migration verification failed. Backend gate is blocked."}

    Write-Host "[3/3] Mandatory tenant-safe real HTTP API gate"
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
    if($LASTEXITCODE -ne 0){throw "Tenant-safe real API validation failed. Backend gate is blocked."}

    Write-Host "============================================================"
    Write-Host "[PASS] Backend regression gate completed. Frontend remains an independent gate."
    Write-Host "============================================================"
} finally {
    Pop-Location
}
