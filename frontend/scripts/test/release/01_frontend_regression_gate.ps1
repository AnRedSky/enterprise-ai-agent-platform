$ErrorActionPreference="Stop"

$frontendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Frontend Regression Gate"
Write-Host "Scope: frontend Vitest -> production build"
Write-Host "Backend tests, migration and Real API are intentionally NOT executed here."
Write-Host "============================================================"

Push-Location $frontendRoot
try {
    Write-Host "[1/2] Frontend automated regression"
    npm test
    if($LASTEXITCODE -ne 0){throw "Frontend tests failed. Frontend gate is blocked."}

    Write-Host "[2/2] Frontend production build"
    npm run build
    if($LASTEXITCODE -ne 0){throw "Frontend production build failed. Frontend gate is blocked."}

    Write-Host "============================================================"
    Write-Host "[PASS] Frontend regression gate completed. Backend remains an independent gate."
    Write-Host "============================================================"
} finally {
    Pop-Location
}
