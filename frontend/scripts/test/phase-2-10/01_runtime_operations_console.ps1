$ErrorActionPreference = "Stop"
$frontend = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $frontend
Write-Host "[P2.10-I] Runtime Operations Console targeted Gate"
Write-Host "[1/2] Vitest: OperationsConsole"
npm exec vitest run tests/views/OperationsConsole.test.ts --reporter=dot
if ($LASTEXITCODE -ne 0) { throw "OperationsConsole targeted tests failed." }
Write-Host "[2/2] Production build"
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
Write-Host "P2.10-I targeted Gate completed. Real backend/API acceptance remains a separate local integration step."
