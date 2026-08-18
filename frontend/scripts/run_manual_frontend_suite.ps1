[CmdletBinding()]
param(
    [string]$FrontendDir = ""
)

$ErrorActionPreference = "Stop"

# Resolve the frontend directory from the explicit parameter, environment,
# or this script's own location. Avoid evaluating Join-Path with an empty
# PSScriptRoot when the script is invoked through an unusual PowerShell host.
if ([string]::IsNullOrWhiteSpace($FrontendDir)) {
    if (-not [string]::IsNullOrWhiteSpace($env:FRONTEND_DIR)) {
        $FrontendDir = $env:FRONTEND_DIR
    }
    elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $FrontendDir = Join-Path -Path $PSScriptRoot -ChildPath ".."
    }
    else {
        $FrontendDir = Join-Path -Path (Get-Location).Path -ChildPath "..\frontend"
    }
}

$FrontendDir = (Resolve-Path -Path $FrontendDir).Path

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - Frontend Manual Test Suite" -ForegroundColor White
Write-Host "Frontend: $FrontendDir" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray

if (-not (Test-Path -Path $FrontendDir -PathType Container)) {
    throw "Frontend directory not found: $FrontendDir"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js/npm before running frontend acceptance tests."
}

Push-Location $FrontendDir
try {
    if (-not (Test-Path -Path "package.json" -PathType Leaf)) {
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
