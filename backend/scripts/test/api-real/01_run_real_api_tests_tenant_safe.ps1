$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Real API Test Gate (Tenant Safe)'
Write-Host '============================================================'

# 本 Gate 只执行测试，不负责启动或停止任何 API / Worker / Scheduler 服务。
# API、Worker 与 Scheduler 必须由开发者提前手动启动；Gate 不抢占或污染开发者已有进程。
# Worker / Scheduler 数量不构成失败条件：只要至少有一个实例，测试即可运行并覆盖并发 claim/lease/slot 语义。
if (-not $env:API_BASE_URL) {
    $env:API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
}

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$contextFile = Join-Path $PSScriptRoot '.real_api_context.json'

function Assert-ApiAvailable {
    $healthUrl = ($env:API_BASE_URL -replace '/api/v1$', '') + '/health'
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 3
        if ($response.StatusCode -ne 200) {
            throw "API health check returned HTTP $($response.StatusCode)."
        }
    } catch {
        throw "Required API Service is not available at $env:API_BASE_URL. Start it manually before running this gate: uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
    }
}

function Assert-WorkerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_worker\.py'
    })
    if ($processes.Count -eq 0) {
        throw 'Required Worker Service is not running. Start it manually before running this gate: uv run python run_worker.py'
    }
    Write-Host "[PASS] Worker Service is available: $($processes.Count) Worker process(es) detected."
    $processes | ForEach-Object {
        Write-Host "[INFO] Worker PID=$($_.ProcessId) CommandLine=$($_.CommandLine)"
    }
    Write-Host '[PASS] Multiple Worker processes are allowed; real API tests must remain valid under concurrent Worker execution.'
}

function Assert-SchedulerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_scheduler\.py'
    })
    if ($processes.Count -eq 0) {
        throw 'Required Scheduler Service is not running. Start it manually before running this gate: uv run python run_scheduler.py'
    }
    Write-Host "[PASS] Scheduler Service is available: $($processes.Count) Scheduler process(es) detected."
    $processes | ForEach-Object {
        Write-Host "[INFO] Scheduler PID=$($_.ProcessId) CommandLine=$($_.CommandLine)"
    }
    Write-Host '[PASS] Multiple Scheduler processes are allowed; scheduled slot claim/idempotency tests exercise concurrent Scheduler execution.'
}

Push-Location $backendRoot
try {
    Write-Host '[0/4] Verify Real API source baseline'
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $backendRoot 'scripts/dev/verify_real_api_source_baseline.ps1')
    if ($LASTEXITCODE -ne 0) {
        throw 'Real API source baseline verification failed. Gate is blocked.'
    }

    Write-Host '[1/4] Verify required external services (no service is started by this gate)'
    Assert-ApiAvailable
    Assert-WorkerAvailable
    Assert-SchedulerAvailable

    Write-Host '[2/4] Prepare tenant-safe real API test context'
    & uv run python (Join-Path $backendRoot 'scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'Real API bootstrap failed.'
    }
    if (-not (Test-Path $contextFile)) {
        throw "Real API context file was not created: $contextFile"
    }

    & uv run python (Join-Path $backendRoot 'scripts/test/api-real/00_grant_admin_fixture.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'Real API admin fixture preparation failed.'
    }

    $context = Get-Content $contextFile -Raw | ConvertFrom-Json
    $env:ACCESS_TOKEN = [string]$context.ACCESS_TOKEN
    $env:ADMIN_ACCESS_TOKEN = [string]$context.ADMIN_ACCESS_TOKEN
    $env:WORKFLOW_ID = [string]$context.WORKFLOW_ID
    $env:WORKFLOW_EXECUTION_ID = [string]$context.WORKFLOW_EXECUTION_ID
    $env:TRIGGER_WORKFLOW_ID = [string]$context.TRIGGER_WORKFLOW_ID
    $env:TRIGGER_ID = [string]$context.TRIGGER_ID
    $env:RETRY_WORKFLOW_ID = [string]$context.RETRY_WORKFLOW_ID
    $env:RETRY_EXECUTION_ID = [string]$context.RETRY_EXECUTION_ID
    $env:RETRY_BUDGET_WORKFLOW_ID = [string]$context.RETRY_BUDGET_WORKFLOW_ID
    $env:RETRY_BUDGET_EXECUTION_ID = [string]$context.RETRY_BUDGET_EXECUTION_ID
    $env:RETRY_DEADLINE_WORKFLOW_ID = [string]$context.RETRY_DEADLINE_WORKFLOW_ID
    $env:RETRY_DEADLINE_EXECUTION_ID = [string]$context.RETRY_DEADLINE_EXECUTION_ID
    $env:CIRCUIT_OPEN_WORKFLOW_ID = [string]$context.CIRCUIT_OPEN_WORKFLOW_ID
    $env:CIRCUIT_OPEN_EXECUTION_ID = [string]$context.CIRCUIT_OPEN_EXECUTION_ID
    $env:CIRCUIT_RECOVERY_WORKFLOW_ID = [string]$context.CIRCUIT_RECOVERY_WORKFLOW_ID
    $env:ORGANIZATION_ID = [string]$context.ORGANIZATION_ID
    $env:ORGANIZATION_MEMBERSHIP_ID = [string]$context.ORGANIZATION_MEMBERSHIP_ID
    $env:ORGANIZATION_MEMBER_USER_ID = [string]$context.ORGANIZATION_MEMBER_USER_ID
    $env:ORGANIZATION_MEMBER_ACCESS_TOKEN = [string]$context.ORGANIZATION_MEMBER_ACCESS_TOKEN

    Write-Host '[3/4] Execute tenant-safe real HTTP API tests'
    & uv run pytest -q tests/api_real -m real_api --ignore=tests/api_real/test_scheduler_restart_api.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Real API test suite failed.'
    }

    Write-Host '[PASS] Tenant-safe Real API gate completed.'
    Write-Host '[INFO] This gate never starts or stops API, Worker, or Scheduler processes.'
} finally {
    Pop-Location
    if (Test-Path $contextFile) {
        Remove-Item $contextFile -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:WORKFLOW_EXECUTION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:TRIGGER_WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:TRIGGER_ID -ErrorAction SilentlyContinue
    Remove-Item Env:RETRY_WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:RETRY_EXECUTION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:RETRY_BUDGET_WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:RETRY_BUDGET_EXECUTION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:RETRY_DEADLINE_WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:RETRY_DEADLINE_EXECUTION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:CIRCUIT_OPEN_WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:CIRCUIT_OPEN_EXECUTION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:CIRCUIT_RECOVERY_WORKFLOW_ID -ErrorAction SilentlyContinue
    Remove-Item Env:ORGANIZATION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:ORGANIZATION_MEMBERSHIP_ID -ErrorAction SilentlyContinue
    Remove-Item Env:ORGANIZATION_MEMBER_USER_ID -ErrorAction SilentlyContinue
    Remove-Item Env:ORGANIZATION_MEMBER_ACCESS_TOKEN -ErrorAction SilentlyContinue
}
