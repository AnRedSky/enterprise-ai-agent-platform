$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Scheduled Trigger Real Test Gate'
Write-Host '============================================================'
Write-Host '[INFO] 本 Gate 不启动、停止或重启任何 API / Worker / Scheduler 服务。'
Write-Host '[INFO] 本 Gate 自动准备 tenant-safe Real API context，避免直接 pytest 缺少测试上下文。'

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
        throw 'Required API Service is unavailable. Start it manually first: uv run uvicorn app.main:app --host 127.0.0.1 --port 8000'
    }
}

function Get-CurrentMainWorkers {
    @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_worker\.py' -and $_.CommandLine -match [regex]::Escape($backendRoot)
    })
}

function Get-CurrentMainSchedulers {
    @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_scheduler\.py' -and $_.CommandLine -match [regex]::Escape($backendRoot)
    })
}

function Assert-CurrentMainServices {
    $workers = Get-CurrentMainWorkers
    $schedulers = Get-CurrentMainSchedulers
    if ($workers.Count -eq 0) {
        throw 'Required current-main Worker is not running. Start it manually first: uv run python run_worker.py'
    }
    if ($schedulers.Count -eq 0) {
        throw 'Required current-main Scheduler is not running. Start it manually first: uv run python run_scheduler.py'
    }
    Write-Host "[PASS] Current-project Worker processes available: $($workers.Count)"
    Write-Host "[PASS] Current-project Scheduler processes available: $($schedulers.Count)"
    Write-Host '[INFO] Multiple Worker/Scheduler processes are intentionally supported; durable claim/slot idempotency is part of this acceptance.'
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
    Invoke-RequiredCommand -FilePath 'powershell' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $backendRoot 'scripts/dev/verify_real_api_source_baseline.ps1')) -FailureMessage 'Real API source baseline verification failed.'

    Write-Host '[2/5] Verify manually managed API / Worker / Scheduler services'
    Assert-ApiAvailable
    Assert-CurrentMainServices

    Write-Host '[3/5] Prepare tenant-safe Real API context'
    Invoke-RequiredCommand -FilePath 'uv' -ArgumentList @('run', 'python', (Join-Path $backendRoot 'scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py')) -FailureMessage 'Real API bootstrap failed.'
    Invoke-RequiredCommand -FilePath 'uv' -ArgumentList @('run', 'python', (Join-Path $backendRoot 'scripts/test/api-real/00_grant_admin_fixture.py')) -FailureMessage 'Real API admin fixture preparation failed.'
    if (-not (Test-Path $contextFile)) {
        throw "Real API context file was not created: $contextFile"
    }

    $context = Get-Content $contextFile -Raw | ConvertFrom-Json
    $env:ACCESS_TOKEN = [string]$context.ACCESS_TOKEN
    $env:ADMIN_ACCESS_TOKEN = [string]$context.ADMIN_ACCESS_TOKEN
    $env:ORGANIZATION_ID = [string]$context.ORGANIZATION_ID
    $env:TRIGGER_WORKFLOW_ID = [string]$context.TRIGGER_WORKFLOW_ID
    $env:TRIGGER_ID = [string]$context.TRIGGER_ID

    if (-not $env:TRIGGER_WORKFLOW_ID) {
        throw 'Tenant-safe bootstrap did not provide TRIGGER_WORKFLOW_ID.'
    }

    Write-Host '[4/5] Execute Scheduled Trigger real_api tests'
    Invoke-RequiredCommand -FilePath 'uv' -ArgumentList @('run', 'pytest', '-q', 'tests/api_real/test_scheduled_trigger_api.py', '-m', 'real_api', '-W', 'error', '--tb=long') -FailureMessage 'Scheduled Trigger real_api test suite failed.'

    Write-Host '[5/5] Verify generated Trigger context was consumed'
    Write-Host "[PASS] TRIGGER_WORKFLOW_ID=$env:TRIGGER_WORKFLOW_ID"
    Write-Host '[PASS] Scheduled Trigger real_api gate completed.'
} finally {
    Pop-Location
    if (Test-Path $contextFile) {
        Remove-Item $contextFile -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ORGANIZATION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:TRIGGER_WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:TRIGGER_ID -ErrorAction SilentlyContinue
}
