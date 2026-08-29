param()

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$Repository = Split-Path -Parent $Backend
Set-Location $Backend

function Assert-ExitCode([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}

function Assert-NoExternalWorkerProcesses {
    $backendMarker = ($Backend -replace '\\', '/')
    $isWindowsHost = $env:OS -eq "Windows_NT"
    if ($isWindowsHost) {
        $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
            $commandLine = [string]$_.CommandLine
            if ([string]::IsNullOrWhiteSpace($commandLine)) { return $false }
            $normalized = $commandLine.Replace('\', '/')
            $isBackendProcess = $normalized.IndexOf($backendMarker, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
            $isWorker = $normalized -match '(?i)(^|[\\/\s"''])(run_worker\.py)(?=$|[\s"''])'
            $isScheduler = $normalized -match '(?i)(^|[\\/\s"''])(run_scheduler\.py)(?=$|[\s"''])'
            return $isBackendProcess -and ($isWorker -or $isScheduler)
        })
    } elseif (Get-Command pgrep -ErrorAction SilentlyContinue) {
        $processes = @(pgrep -af "run_worker\.py|run_scheduler\.py" 2>$null)
    } else {
        return
    }

    if ($processes.Count -gt 0) {
        Write-Host "Detected external service consumers:" -ForegroundColor Yellow
        if ($isWindowsHost) {
            foreach ($process in $processes) {
                Write-Host ("  PID={0} Name={1} CommandLine={2}" -f $process.ProcessId, $process.Name, $process.CommandLine) -ForegroundColor Yellow
            }
        } else {
            $processes | ForEach-Object { Write-Host ("  " + $_) -ForegroundColor Yellow }
        }
        throw "External Worker/Scheduler process detected. B6 Real API acceptance must run without background Worker/Scheduler consumers because they can legitimately claim the test-created Delegation before the explicit acceptance Workers. The gate never starts or stops services."
    }
}

function Assert-PrerequisiteServices {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is required to run the Phase 2.8 multi-worker runtime gate."
    }

    Push-Location $Repository
    try {
        $services = docker compose ps --services --filter "status=running"
        Assert-ExitCode "Unable to inspect local Docker services."
        $running = @($services | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        foreach ($required in @("postgres", "redis")) {
            if ($running -notcontains $required) {
                throw "Required service '$required' is not running. The gate never starts, restarts, or stops services. Start the documented local prerequisite environment before running the gate."
            }
        }
    } finally {
        Pop-Location
    }

    $healthUrl = "http://127.0.0.1:8000/health"
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5
    } catch {
        throw "Backend API is not healthy at $healthUrl. The gate never starts the API service; start the documented local backend service before running the gate."
    }
    if ($response.status -ne "ok") {
        throw "Backend API health check returned an unexpected status."
    }
}

function Get-AutomatedAccessToken([string]$ApiUrl) {
    $suffix = [Guid]::NewGuid().ToString("N")
    $username = "phase28-b6-$suffix"
    $password = "Phase28B6-$suffix-A9!"
    $body = @{ username = $username; password = $password } | ConvertTo-Json
    Invoke-RestMethod -Uri "$ApiUrl/auth/register" -Method Post -ContentType "application/json" -Body $body | Out-Null
    $login = Invoke-RestMethod -Uri "$ApiUrl/auth/login" -Method Post -ContentType "application/json" -Body $body
    if (-not $login.access_token) { throw "Automated B6 test-user login returned no access_token." }
    return $login.access_token
}

try {
    Write-Host "============================================================"
    Write-Host "Enterprise AI Agent Platform - Phase 2.8 B6 Multi-Worker Runtime Gate"
    Write-Host "============================================================"

    Write-Host "[0/4] Local prerequisite service verification (no service startup)"
    Assert-PrerequisiteServices
    Assert-NoExternalWorkerProcesses

    Write-Host "[1/4] Delegation Claim + Worker dispatch Unit/Contract"
    uv run pytest -q tests/unit/test_agent_delegation_runtime_bridge.py tests/unit/test_agent_delegation_lifecycle.py tests/unit/test_agent_delegation_timeout.py tests/unit/test_delegation_worker_dispatch.py tests/unit/test_workflow_worker_entrypoint.py tests/unit/test_worker_entrypoint.py tests/unit/test_frontier_lease_terminalization.py tests/unit/test_execution_frontier_terminalization.py
    Assert-ExitCode "B6 targeted unit gate failed."

    Write-Host "[2/4] Backend default regression"
    uv run pytest -q
    Assert-ExitCode "Backend default regression failed."

    Write-Host "[3/4] Migration/head verification"
    uv run alembic upgrade head
    Assert-ExitCode "Alembic upgrade head failed."
    uv run alembic current
    Assert-ExitCode "Alembic current failed."

    Write-Host "[4/4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime"
    $ApiBaseUrl = "http://127.0.0.1:8000/api/v1"
    $env:API_BASE_URL = $ApiBaseUrl
    $env:ACCESS_TOKEN = Get-AutomatedAccessToken $ApiBaseUrl
    uv run pytest -q -o "addopts=" -m real_api tests/api_real/test_agent_delegation_multi_worker_api.py tests/api_real/test_agent_delegation_claim_api.py tests/api_real/test_agent_delegation_bridge_api.py
    Assert-ExitCode "B6 multi-worker Delegation Runtime real acceptance failed."

    Write-Host "[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed."
} finally {
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
}
