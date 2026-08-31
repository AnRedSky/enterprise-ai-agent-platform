$ErrorActionPreference = "Stop"
$frontend = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $frontend
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Runtime Audit Contract Alignment Frontend Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: Vitest uses deterministic mocked API contracts; no manual IDs, credentials, or business data are required."
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm is required but was not found in PATH." }

Write-Host "[1/4] Runtime Audit targeted contract regression"
npm exec vitest run tests/views/OperationsConsole.test.ts --reporter=dot
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit frontend targeted tests failed." }

Write-Host "[2/4] Frontend regression"
npm test -- --reporter=dot
if ($LASTEXITCODE -ne 0) { throw "Frontend regression failed." }

Write-Host "[3/4] Production build"
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }

Write-Host "[4/4] Service startup boundary"
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was created, started, restarted, or stopped by this gate."
Write-Host "[PASS] Phase 2.10-II Runtime Audit Contract Alignment Frontend Gate completed."
Write-Host "[INFO] Real API / Browser acceptance remains a separate local integration step and is never auto-started by this gate."
