$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$FrontendRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $FrontendRoot

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Frontend Phase 1.3 Gate'
Write-Host '============================================================'

if (-not (Test-Path 'package.json')) {
    throw "frontend/package.json not found. Current directory: $(Get-Location)"
}

Write-Host '[1/4] Verify Node and npm'
node --version
npm --version

Write-Host '[2/4] Install locked dependencies'
if (Test-Path 'package-lock.json') {
    npm ci
} else {
    throw 'package-lock.json is required for the reproducible frontend gate.'
}

Write-Host '[3/4] Run frontend unit tests'
npm test -- --run
if ($LASTEXITCODE -ne 0) {
    throw 'Vitest failed.'
}

Write-Host '[4/4] Run production build'
npm run build
if ($LASTEXITCODE -ne 0) {
    throw 'Vite production build failed.'
}

Write-Host ''
Write-Host 'Frontend Phase 1.3 gate PASSED.' -ForegroundColor Green
