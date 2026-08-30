$ErrorActionPreference="Stop"

$frontendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Final Frontend Release Gate"
Write-Host "Scope: full Vitest regression -> production build"
Write-Host "E2E/Real API remains an explicit manual acceptance step."
Write-Host "============================================================"

Push-Location $frontendRoot
try {
    Write-Host "[1/2] Full frontend automated regression"
    npm test
    if($LASTEXITCODE -ne 0){throw "Frontend tests failed. Release gate is blocked."}

    Write-Host "[2/2] Production build"
    npm run build
    if($LASTEXITCODE -ne 0){throw "Frontend production build failed. Release gate is blocked."}

    Write-Host "============================================================"
    Write-Host "[PASS] Final frontend automated gate completed."
    Write-Host "Next: execute manual UI, responsive and Real API acceptance from frontend/docs/FINAL_UI_RELEASE_HARDENING.md."
    Write-Host "============================================================"
} finally {
    Pop-Location
}
