$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$Spec,
    [Parameter(Mandatory = $true)]
    [string]$Grep
)

$frontendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$backendRoot = Join-Path $frontendRoot "backend"

Write-Host "[E2E] Reset local Browser E2E database"
Set-Location $backendRoot
uv run python .\scripts\test\e2e\00_reset_browser_e2e_database.py
if ($LASTEXITCODE -ne 0) {
    throw "Browser E2E database reset failed."
}

Set-Location $frontendRoot
Write-Host "[E2E] Run isolated test: $Spec / $Grep"
npm run test:e2e -- --project="Desktop Chrome" $Spec --grep "$Grep"
if ($LASTEXITCODE -ne 0) {
    throw "Browser E2E test failed: $Spec / $Grep"
}
