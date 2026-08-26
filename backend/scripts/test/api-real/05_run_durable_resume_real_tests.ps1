$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Durable Resume Real Test Gate'
Write-Host '============================================================'
Write-Host '[INFO] This gate never starts, stops, or restarts API, Scheduler, or Worker.'
Write-Host '[INFO] It creates one tenant-safe context and runs both durable Resume real_api tests.'

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
        throw 'Required API Service is unavailable. Start it manually first: uv run python run.py'
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

function Invoke-RequiredCommand {
    param(
        [Parameter(Mandatory = $true)] [string] $FilePath,
        [Parameter(Mandatory = $true)] [string[]] $ArgumentList,
        [Parameter(Mandatory = $true)] [string] $FailureMessage
    )
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

Push-Location $backendRoot
try {
    Write-Host '[1/5] Verify Real API source baseline'
    Invoke-RequiredCommand -FilePath 'powershell' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', (Join-Path $backendRoot 'scripts/dev/verify_real_api_source_baseline.ps1')
    ) -FailureMessage 'Real API source baseline verification failed.'

    Write-Host '[2/5] Verify manually managed API / Worker services'
    Assert-ApiAvailable
    Assert-WorkerAvailable

    Write-Host '[3/5] Prepare tenant-safe real API context'
    Invoke-RequiredCommand -FilePath 'uv' -ArgumentList @(
        'run', 'python', (Join-Path $backendRoot 'scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py')
    ) -FailureMessage 'Real API bootstrap failed.'
    Invoke-RequiredCommand -FilePath 'uv' -ArgumentList @(
        'run', 'python', (Join-Path $backendRoot 'scripts/test/api-real/00_grant_admin_fixture.py')
    ) -FailureMessage 'Real API admin fixture preparation failed.'
    if (-not (Test-Path $contextFile)) {
        throw "Real API context file was not created: $contextFile"
    }

    $context = Get-Content $contextFile -Raw | ConvertFrom-Json
    $env:ACCESS_TOKEN = [string]$context.ACCESS_TOKEN
    $env:ADMIN_ACCESS_TOKEN = [string]$context.ADMIN_ACCESS_TOKEN
    $env:ORGANIZATION_ID = [string]$context.ORGANIZATION_ID

    Write-Host '[4/5] Execute durable Resume success real_api test'
    Invoke-RequiredCommand -FilePath 'uv' -ArgumentList @(
        'run', 'pytest', '-q', 'tests/api_real/test_workflow_resume_api.py', '-m', 'real_api'
    ) -FailureMessage 'Durable Resume success real_api test failed.'

    Write-Host '[5/5] Execute durable Resume failure-boundary real_api test'
    Invoke-RequiredCommand -FilePath 'uv' -ArgumentList @(
        'run', 'pytest', '-q', 'tests/api_real/test_workflow_resume_failure_api.py', '-m', 'real_api'
    ) -FailureMessage 'Durable Resume failure-boundary real_api test failed.'

    Write-Host '[PASS] Both durable Resume real_api tests completed.'
    Write-Host '[INFO] ORGANIZATION_ID and access tokens were supplied only for this gate lifetime.'
} finally {
    Pop-Location
    if (Test-Path $contextFile) {
        Remove-Item $contextFile -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ORGANIZATION_ID -ErrorAction SilentlyContinue
}
