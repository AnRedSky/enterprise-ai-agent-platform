$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Frontend/Backend Integration Gate"
Write-Host "Required order: backend regression -> migration -> real API -> frontend"
Write-Host "============================================================"
Write-Host "[1/4] Backend regression"
uv run pytest -q
if($LASTEXITCODE -ne 0){throw "Backend regression failed. Integration is blocked."}
Write-Host "[2/4] Database migration"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1
if($LASTEXITCODE -ne 0){throw "Database migration failed. Integration is blocked."}
Write-Host "[3/4] Mandatory real HTTP API gate"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
if($LASTEXITCODE -ne 0){throw "Real API validation failed. Frontend/backend integration is blocked."}
Write-Host "[4/4] Frontend automated regression"
Push-Location ..\..\..\frontend
try{ npm test; if($LASTEXITCODE -ne 0){throw "Frontend tests failed."}; npm run build; if($LASTEXITCODE -ne 0){throw "Frontend production build failed."} }finally{Pop-Location}
Write-Host "============================================================"
Write-Host "Automated integration gate passed. Proceed to browser-level scenarios."
Write-Host "============================================================"
