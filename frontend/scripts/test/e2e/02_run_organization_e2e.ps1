$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.1-F Browser E2E Gate"
Write-Host "Scope: real Browser -> Vue Organization UI -> Backend HTTP -> Organization/Membership Governance"
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
    "Organization management completes the real owner browser contract",
    "Organization browser governance enforces member and suspended-member boundaries",
    "Organization owner transfer exposes owner-only browser controls"
)

Write-Host "FRONTEND_BASE_URL: $env:FRONTEND_BASE_URL"
Write-Host "API_BASE_URL: $env:API_BASE_URL"
Write-Host "[1/1] Run isolated organization browser E2E scenarios"
foreach ($scenario in $scenarios) {
    & $isolatedRunner -Spec "organization-management.spec.ts" -Grep $scenario
    if ($LASTEXITCODE -ne 0) {
        throw "Organization Browser E2E scenario failed: $scenario"
    }
}

Write-Host "============================================================"
Write-Host "[PASS] Phase 2.1-F organization browser E2E contract completed."
Write-Host "Backend and Frontend regression gates remain independent."
Write-Host "============================================================"
