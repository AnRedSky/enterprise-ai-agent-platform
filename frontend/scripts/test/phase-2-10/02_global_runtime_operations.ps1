$ErrorActionPreference = "Stop"
$frontend = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $frontend
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Global Runtime Operations Frontend Gate"
Write-Host "============================================================"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: frontend tests use deterministic mocked API contracts and require no manual IDs or business data."
Write-Host "[1/3] Global Runtime Operations component contract"
npm exec vitest run tests/views/GlobalRuntimeOperations.test.ts --reporter=dot
if ($LASTEXITCODE -ne 0) { throw "Global Runtime Operations component tests failed." }
Write-Host "[2/3] Frontend regression"
npm test -- --reporter=dot
if ($LASTEXITCODE -ne 0) { throw "Frontend regression failed." }
Write-Host "[3/3] Production build"
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
Write-Host "[PASS] Phase 2.10-II Global Runtime Operations Frontend Gate completed."
Write-Host "[INFO] Real backend/API acceptance remains a separate local integration step and is never auto-started by this gate."
