[CmdletBinding()]
param(
    [string]$FrontendDir = $(if ($env:FRONTEND_DIR) { $env:FRONTEND_DIR } else { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path })
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - Frontend Manual Test Suite" -ForegroundColor White
Write-Host "Frontend: $FrontendDir" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray

if (-not (Test-Path $FrontendDir)) {
    throw "Frontend directory not found: $FrontendDir"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js/npm before running frontend acceptance tests."
}

Push-Location $FrontendDir
try {
    if (-not (Test-Path "package.json")) {
        throw "package.json was not found in $FrontendDir"
    }

    Write-Host "[RUN ] Frontend Vitest" -ForegroundColor Cyan
    & npm test
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend Vitest failed with exit code $LASTEXITCODE."
    }
    Write-Host "[ OK  ] Frontend Vitest" -ForegroundColor Green

    Write-Host "[RUN ] Frontend production build" -ForegroundColor Cyan
    & npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed with exit code $LASTEXITCODE."
    }
    Write-Host "[ OK  ] Frontend production build" -ForegroundColor Green
}
finally {
    Pop-Location
}

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "[PASS] Frontend manual test suite completed" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor DarkGray
