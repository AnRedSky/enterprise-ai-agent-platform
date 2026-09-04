param()

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$Repository = Split-Path -Parent $Backend
Set-Location $Backend

function Assert-ExitCode([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}

function Require-Environment([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required real Provider setting '$Name' is missing. Configure it in the uncommitted backend/.env or process environment; never commit credentials."
    }
    return $value
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
        throw "External Worker/Scheduler process detected. Real Provider multi-worker acceptance must run without background consumers so the two explicit test Workers own the generated Delegations. The gate never starts or stops services."
    }
}

function Assert-Prerequisites {
    Require-Environment "DELEGATION_REAL_PROVIDER_ENDPOINT" | Out-Null
    Require-Environment "DELEGATION_REAL_PROVIDER_MODEL" | Out-Null
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is required to inspect PostgreSQL/Redis readiness."
    }
    Push-Location $Repository
    try {
        $services = docker compose ps --services --filter "status=running"
        Assert-ExitCode "Unable to inspect local Docker services."
        $running = @($services | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        foreach ($required in @("postgres", "redis")) {
            if ($running -notcontains $required) {
                throw "Required service '$required' is not running. The gate never starts, restarts, or stops services."
            }
        }
    } finally {
        Pop-Location
    }
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 5
    } catch {
        throw "Backend API is not healthy at http://127.0.0.1:8000/health. The gate never starts the API service."
    }
    if ($response.status -ne "ok") { throw "Backend API health check returned an unexpected status." }
    Assert-NoExternalWorkerProcesses
}

function Get-AutomatedAccessToken([string]$ApiUrl) {
    $suffix = [Guid]::NewGuid().ToString("N")
    $username = "phase28-real-provider-$suffix"
    $password = "Phase28RealProvider-$suffix-A9!"
    $body = @{ username = $username; password = $password } | ConvertTo-Json
    Invoke-RestMethod -Uri "$ApiUrl/auth/register" -Method Post -ContentType "application/json" -Body $body | Out-Null
    $login = Invoke-RestMethod -Uri "$ApiUrl/auth/login" -Method Post -ContentType "application/json" -Body $body
    if (-not $login.access_token) { throw "Automated real Provider test-user login returned no access_token." }
    return $login.access_token
}

try {
    Write-Host "============================================================"
    Write-Host "Enterprise AI Agent Platform - Phase 2.8 Multi-Worker Real Provider Gate"
    Write-Host "============================================================"

    Write-Host "[0/5] Local prerequisites and real Provider configuration"
    Assert-Prerequisites
    $ApiBaseUrl = "http://127.0.0.1:8000/api/v1"
    $env:API_BASE_URL = $ApiBaseUrl
    $env:ACCESS_TOKEN = Get-AutomatedAccessToken $ApiBaseUrl

    Write-Host "[1/5] Provider/Delegation unit regression"
    uv run pytest -q -W error tests/unit/test_model_gateway.py tests/unit/test_agent_delegation_runtime_bridge.py tests/unit/test_delegation_worker_dispatch.py
    Assert-ExitCode "Provider/Delegation targeted unit regression failed."

    Write-Host "[2/5] PostgreSQL migration/head verification"
    uv run alembic upgrade head
    Assert-ExitCode "Alembic upgrade head failed."
    uv run alembic heads
    Assert-ExitCode "Alembic heads failed."

    Write-Host "[3/5] PostgreSQL Delegation persistence acceptance"
    $env:RUN_DATABASE_INTEGRATION = "1"
    uv run pytest -q -W error -o "addopts=" -m real_api tests/api_real/test_agent_delegation_bridge_api.py
    Assert-ExitCode "Delegation PostgreSQL acceptance failed."

    Write-Host "[4/5] Two independent Workers -> real Provider -> PostgreSQL Durable Frontier"
    uv run pytest -q -W error -o "addopts=" -m real_api tests/api_real/test_agent_delegation_multi_worker_real_provider.py
    Assert-ExitCode "Multi-worker real Provider acceptance failed."

    Write-Host "[5/5] Service startup boundary"
    Assert-NoExternalWorkerProcesses
    Write-Host "[PASS] Production Runtime already routes Delegation through Model Governance and ModelGateway; no parallel Provider implementation was introduced."
    Write-Host "[PASS] Target Agent published version carries the governed Model Profile into Delegation and Worker Runtime."
    Write-Host "[PASS] Multiple independent Workers consumed Durable Delegation Frontiers against the configured real Provider."
    Write-Host "[PASS] PostgreSQL persisted Delegation -> Worker Execution -> Frontier completion facts."
    Write-Host "[PASS] No protected service process appeared during the gate."
    Write-Host "[PASS] Multi-Worker Real Provider Gate completed."
} finally {
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:RUN_DATABASE_INTEGRATION -ErrorAction SilentlyContinue
}
