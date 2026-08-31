$ErrorActionPreference = "Stop"
$frontend = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $frontend
Write-Host "[P2.10-I] Runtime Operations targeted Gate"
Write-Host "[1/3] Vitest: Runtime diagnostics API"
npm exec vitest run tests/api/runtimeDiagnostics.test.ts --reporter=dot
if ($LASTEXITCODE -ne 0) { throw "Runtime diagnostics API tests failed." }
Write-Host "[2/3] Vitest: Global Runtime Operations view"
npm exec vitest run tests/views/GlobalRuntimeOperations.test.ts --reporter=dot
if ($LASTEXITCODE -ne 0) { throw "Global Runtime Operations tests failed." }
Write-Host "[3/3] Production build"
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
Write-Host "P2.10-I targeted Gate completed. Real backend/API acceptance remains a separate local integration step."
