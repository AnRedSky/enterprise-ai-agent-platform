$ErrorActionPreference="Stop"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$repoRoot = (Resolve-Path (Join-Path $backendRoot "..")).Path

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Full Regression Gate"
Write-Host "Required order: backend regression -> migration -> real API -> frontend test/build"
Write-Host "============================================================"

Push-Location $backendRoot
try {
    Write-Host "[1/4] Backend regression"
    uv run pytest -q
    if($LASTEXITCODE -ne 0){throw "Backend regression failed. Full regression is blocked."}

    Write-Host "[2/4] Database migration/head verification"
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1
    if($LASTEXITCODE -ne 0){throw "Database migration verification failed. Full regression is blocked."}

    Write-Host "[3/4] Mandatory real HTTP API gate"
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
    if($LASTEXITCODE -ne 0){throw "Real API validation failed. Full regression is blocked."}

    Write-Host "[4/4] Frontend automated regression and production build"
    Push-Location (Join-Path $repoRoot "frontend")
    try {
        npm test
        if($LASTEXITCODE -ne 0){throw "Frontend tests failed."}
        npm run build
        if($LASTEXITCODE -ne 0){throw "Frontend production build failed."}
    } finally {
        Pop-Location
    }

    Write-Host "============================================================"
    Write-Host "[PASS] Full regression gate completed. Browser E2E remains a separate integration layer."
    Write-Host "============================================================"
} finally {
    Pop-Location
}
