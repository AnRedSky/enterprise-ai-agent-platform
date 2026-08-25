$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.4 Browser E2E Gate"
Write-Host "Scope: real Browser -> Vue Workflow Trigger UI -> Backend HTTP -> Scheduler status"
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

Write-Host "FRONTEND_BASE_URL: $env:FRONTEND_BASE_URL"
Write-Host "API_BASE_URL: $env:API_BASE_URL"
Write-Host "[1/1] Run isolated Workflow Trigger browser E2E"
& (Join-Path $PSScriptRoot "00_run_isolated_test.ps1") `
    -Spec "workflow-trigger-governance.spec.ts" `
    -Grep "Workflow Trigger Governance completes the real scheduled browser contract"
if ($LASTEXITCODE -ne 0) {
    throw "Workflow Trigger Browser E2E gate failed."
}

Write-Host "============================================================"
Write-Host "[PASS] Phase 2.4 Workflow Trigger browser E2E gate completed."
Write-Host "Backend and Frontend regression gates remain independent."
Write-Host "============================================================"
