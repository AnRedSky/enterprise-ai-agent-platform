$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.6-C Browser E2E Gate"
Write-Host "Scope: real Browser -> Vue UI -> Backend HTTP -> Workflow Trigger Governance"
Write-Host "Backend and Frontend regression gates are intentionally NOT executed here."
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

Write-Host "API_BASE_URL: $env:API_BASE_URL"
Write-Host "[1/2] Run browser E2E contract"
npm run test:e2e -- --project="Desktop Chrome"
if ($LASTEXITCODE -ne 0) {
    throw "Browser E2E gate failed."
}

Write-Host "[2/2] Browser E2E contract completed"
Write-Host "============================================================"
Write-Host "[PASS] Phase 1.6-C browser E2E gate completed."
Write-Host "Backend and Frontend regression gates remain independent."
Write-Host "============================================================"
