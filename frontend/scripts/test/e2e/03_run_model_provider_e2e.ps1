$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Model Provider Browser E2E Gate"
Write-Host "Scope: real Browser -> Vue Model Provider/Profile UI -> Backend HTTP -> Organization Governance"
Write-Host "Backend and Frontend regression gates are intentionally NOT executed here."
Write-Host "Each Browser scenario is isolated with a local database reset."
Write-Host "============================================================"

if ([string]::IsNullOrWhiteSpace($env:FRONTEND_BASE_URL)) {
    $env:FRONTEND_BASE_URL = "http://127.0.0.1:5173"
}
if ([string]::IsNullOrWhiteSpace($env:API_BASE_URL)) {
    $env:API_BASE_URL = "http://127.0.0.1:8000/api/v1"
} else {
    $env:API_BASE_URL = $env:API_BASE_URL.TrimEnd('/')
    if (-not $env:API_BASE_URL.EndsWith('/api/v1')) {
        $env:API_BASE_URL = "$($env:API_BASE_URL)/api/v1"
    }
}

$isolatedRunner = Join-Path $PSScriptRoot "00_run_isolated_test.ps1"
$scenarios = @(
    "Model Provider/Profile owner browser contract uses organization scoped real APIs",
    "Model Provider/Profile management button is hidden from organization members"
)

Write-Host "FRONTEND_BASE_URL: $env:FRONTEND_BASE_URL"
Write-Host "API_BASE_URL: $env:API_BASE_URL"
Write-Host "[1/1] Run isolated model provider browser E2E scenarios"
foreach ($scenario in $scenarios) {
    & $isolatedRunner -Spec "model-provider-governance.spec.ts" -Grep $scenario
    if ($LASTEXITCODE -ne 0) {
        throw "Model Provider Browser E2E scenario failed: $scenario"
    }
}

Write-Host "============================================================"
Write-Host "[PASS] Model Provider browser E2E gate completed."
Write-Host "Backend and Frontend regression gates remain independent."
Write-Host "============================================================"
