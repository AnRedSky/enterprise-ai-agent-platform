$ErrorActionPreference = "Stop"

# Resolve paths from the script location, not the caller's current directory.
$frontendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$results = @()

function Record-Result([string]$Name, [string]$Status, [string]$Detail) {
    $script:results += [pscustomobject]@{ Step = $Name; Status = $Status; Detail = $Detail }
}

function Invoke-Step([string]$Name, [string]$Command, [string[]]$Arguments) {
    Write-Host "[$Name] $Command $($Arguments -join ' ')"
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        Record-Result $Name "FAILED" "Exit code $LASTEXITCODE"
        throw "$Name failed."
    }
    Record-Result $Name "PASS" "Completed"
}

function Test-Url([string]$Name, [string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            Record-Result $Name "READY" $Url
            return $true
        }
    } catch { }
    Record-Result $Name "NOT EXECUTED" "$Url is not reachable. Start required services using the project's normal local runbook, then rerun this script."
    return $false
}

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Local Frontend Full Regression"
Write-Host "This script NEVER starts or stops API, Scheduler, Worker, PostgreSQL or Redis."
Write-Host "No manual test data is required. Browser E2E uses isolated scenario runners with generated fixtures."
Write-Host "============================================================"

Push-Location $frontendRoot
try {
    if (-not (Test-Path "package.json")) { throw "frontend/package.json not found." }
    if (-not (Test-Path "node_modules/.bin/vitest.cmd")) { throw "Project dependencies are not installed. Run npm ci first." }
    if (-not (Test-Path "node_modules/.bin/vite.cmd")) { throw "Vite is missing from node_modules. Run npm ci first." }
    if (-not (Test-Path "node_modules/.bin/playwright.cmd")) { throw "Playwright is missing from node_modules. Run npm ci first." }
    Record-Result "Dependency preflight" "PASS" "Vitest, Vite and Playwright executables are present"

    Invoke-Step "Targeted AuditLog" "npm" @("test", "--", "tests/views/AuditLog.test.ts")
    Invoke-Step "Full Vitest" "npm" @("test")
    Invoke-Step "Production build" "npm" @("run", "build")
    Invoke-Step "Frontend regression gate" "npm" @("run", "test:gate")

    $apiReady = Test-Url "Backend API readiness" "http://127.0.0.1:8000/health"
    $frontendReady = Test-Url "Frontend E2E readiness" "http://127.0.0.1:5173/"
    if ($apiReady -and $frontendReady) {
        $e2eRunner = Join-Path $PSScriptRoot "e2e\00_run_isolated_test.ps1"
        $organizationGate = Join-Path $PSScriptRoot "e2e\02_run_organization_e2e.ps1"
        $modelProviderGate = Join-Path $PSScriptRoot "e2e\03_run_model_provider_e2e.ps1"
        $workflowTriggerGate = Join-Path $PSScriptRoot "e2e\01_run_workflow_trigger_e2e.ps1"

        Invoke-Step "Organization Browser E2E" "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $organizationGate)
        Invoke-Step "Model Provider Browser E2E" "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $modelProviderGate)
        Invoke-Step "Workflow Trigger Browser E2E" "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $workflowTriggerGate)
        Invoke-Step "Webhook Governance Browser E2E" "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $e2eRunner, "-Spec", "workflow-webhook-governance.spec.ts", "-Grep", "Workflow Trigger Governance completes the real webhook browser contract")
        Invoke-Step "Webhook Runtime Browser E2E" "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $e2eRunner, "-Spec", "workflow-webhook-runtime.spec.ts", "-Grep", "Webhook browser runtime converges duplicate events and enforces lifecycle security")
    } else {
        Write-Host "E2E: NOT EXECUTED because required existing services are unavailable."
    }

    Write-Host "============================================================"
    $results | Format-Table -AutoSize
    Write-Host "============================================================"
} finally {
    Pop-Location
}
