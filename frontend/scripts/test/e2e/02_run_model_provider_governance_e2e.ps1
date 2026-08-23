$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.2-E-4 Model Provider Browser Gate"
Write-Host "Scope: real Browser -> Vue Provider/Profile UI -> Backend HTTP -> Organization Governance"
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

Write-Host "FRONTEND_BASE_URL: $env:FRONTEND_BASE_URL"
Write-Host "API_BASE_URL: $env:API_BASE_URL"
Write-Host "[1/1] Run model provider/profile browser governance contract"
npm run test:e2e -- --project="Desktop Chrome" model-provider-governance.spec.ts
if ($LASTEXITCODE -ne 0) {
    throw "Model Provider/Profile Browser E2E gate failed."
}

Write-Host "============================================================"
Write-Host "[PASS] Phase 2.2-E-4 Model Provider/Profile Browser contract completed."
Write-Host "Backend and Frontend regression gates remain independent."
Write-Host "============================================================"
