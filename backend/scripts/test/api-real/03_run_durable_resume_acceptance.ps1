$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Durable Resume Acceptance'
Write-Host '============================================================'
Write-Host '[INFO] This gate never starts, stops, or restarts API, Scheduler, or Worker.'

if (-not $env:API_BASE_URL) {
    $env:API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
}

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$contextFile = Join-Path $backendRoot 'scripts\test\api-real\.real_api_context.json'

function Assert-ApiAvailable {
    $healthUrl = ($env:API_BASE_URL -replace '/api/v1$', '') + '/health'
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 3
        if ($response.StatusCode -ne 200) {
            throw "API health check returned HTTP $($response.StatusCode)."
        }
    } catch {
        throw "Required API Service is unavailable. Start it manually first: uv run python run.py"
    }
}

function Assert-WorkerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_worker\.py'
    })
    if ($processes.Count -eq 0) {
        throw 'Required Worker Service is not running. Start it manually first: uv run python run_worker.py'
    }
    $processes | ForEach-Object { Write-Host "[INFO] Existing Worker PID=$($_.ProcessId) CommandLine=$($_.CommandLine)" }
}

Push-Location $backendRoot
try {
    Write-Host '[1/4] Verify Real API source baseline'
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $backendRoot 'scripts/dev/verify_real_api_source_baseline.ps1')
    if ($LASTEXITCODE -ne 0) {
        throw 'Real API source baseline verification failed.'
    }

    Write-Host '[2/4] Verify manually managed API / Worker services'
    Assert-ApiAvailable
    Assert-WorkerAvailable

    Write-Host '[3/4] Prepare tenant-safe real API context'
    & uv run python (Join-Path $backendRoot 'scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'Real API bootstrap failed.'
    }
    & uv run python (Join-Path $backendRoot 'scripts/test/api-real/00_grant_admin_fixture.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'Real API admin fixture preparation failed.'
    }
    if (-not (Test-Path $contextFile)) {
        throw "Real API context file was not created: $contextFile"
    }

    $context = Get-Content $contextFile -Raw | ConvertFrom-Json
    $env:ACCESS_TOKEN = [string]$context.ACCESS_TOKEN
    $env:ADMIN_ACCESS_TOKEN = [string]$context.ADMIN_ACCESS_TOKEN
    $env:ORGANIZATION_ID = [string]$context.ORGANIZATION_ID

    Write-Host '[4/4] Execute real PostgreSQL + independent Worker Resume acceptance'
    & uv run pytest -q tests/api_real/test_workflow_resume_api.py -m real_api
    if ($LASTEXITCODE -ne 0) {
        throw 'Durable Resume acceptance failed.'
    }

    Write-Host '[PASS] Durable Resume acceptance completed.'
    Write-Host '[INFO] Source failed after a persisted checkpoint; Resume was created through WorkflowExecutionService; Worker consumed the new pending Execution; only remaining nodes were executed.'
} finally {
    Pop-Location
    if (Test-Path $contextFile) {
        Remove-Item $contextFile -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ORGANIZATION_ID -ErrorAction SilentlyContinue
}
