param()

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$Repository = Split-Path -Parent $Backend
Set-Location $Backend

function Assert-ExitCode([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}

function Assert-PrerequisiteServices {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is required to run the Phase 2.8 B4 acceptance gate."
    }
    Push-Location $Repository
    try {
        $services = docker compose ps --services --filter "status=running"
        Assert-ExitCode "Unable to inspect local Docker services."
        $running = @($services | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        foreach ($required in @("postgres", "redis")) {
            if ($running -notcontains $required) {
                throw "Required service '$required' is not running. The gate never starts services; start the project prerequisite environment before running the gate."
            }
        }
    } finally {
        Pop-Location
    }

    $healthUrl = "http://127.0.0.1:8000/health"
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5
    } catch {
        throw "Backend API is not healthy at $healthUrl. The gate never starts services; start the project prerequisite environment before running the gate."
    }
    if ($response.status -ne "ok") {
        throw "Backend API health check returned an unexpected status."
    }
}

function Get-AutomatedAccessToken([string]$ApiUrl) {
    $suffix = [Guid]::NewGuid().ToString("N")
    $username = "phase28-b4-$suffix"
    $password = "Phase28B4-$suffix-A9!"
    $body = @{ username = $username; password = $password } | ConvertTo-Json
    Invoke-RestMethod -Uri "$ApiUrl/auth/register" -Method Post -ContentType "application/json" -Body $body | Out-Null
    $login = Invoke-RestMethod -Uri "$ApiUrl/auth/login" -Method Post -ContentType "application/json" -Body $body
    if (-not $login.access_token) { throw "Automated B4 test-user login returned no access_token." }
    return $login.access_token
}

try {
    Write-Host "============================================================"
    Write-Host "Enterprise AI Agent Platform - Phase 2.8 B4 Delegation Timeout/Cancel Gate"
    Write-Host "============================================================"

    Write-Host "[0/4] Local prerequisite service verification (no service startup)"
    Assert-PrerequisiteServices

    Write-Host "[1/4] Delegation timeout Unit"
    uv run pytest -q tests/unit/test_agent_delegation_lifecycle.py tests/unit/test_agent_delegation_timeout.py
    Assert-ExitCode "Delegation timeout unit gate failed."

    Write-Host "[2/4] Backend default regression"
    uv run pytest -q
    Assert-ExitCode "Backend default regression failed."

    Write-Host "[3/4] Migration/head verification"
    uv run alembic upgrade head
    Assert-ExitCode "Alembic upgrade head failed."
    uv run alembic current
    Assert-ExitCode "Alembic current failed."

    Write-Host "[4/4] Real HTTP + PostgreSQL B4 timeout/cancel/parent semantics"
    $ApiBaseUrl = "http://127.0.0.1:8000/api/v1"
    $env:API_BASE_URL = $ApiBaseUrl
    $env:ACCESS_TOKEN = Get-AutomatedAccessToken $ApiBaseUrl
    uv run pytest -q -o "addopts=" -m real_api tests/api_real/test_agent_delegation_b4_api.py tests/api_real/test_agent_delegation_bridge_api.py
    Assert-ExitCode "B4 Delegation timeout/cancel/parent real acceptance failed."

    Write-Host "[PASS] Phase 2.8 B4 Delegation timeout/cancel/parent gate completed."
} finally {
    Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
}
