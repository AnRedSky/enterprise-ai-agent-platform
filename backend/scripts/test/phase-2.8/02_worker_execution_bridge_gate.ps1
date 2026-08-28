param()

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$Repository = Split-Path -Parent $Backend
Set-Location $Backend

function Assert-ExitCode([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}

function Wait-Api([string]$Url, [int]$TimeoutSeconds = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 3
            if ($response.status -eq "ok") { return }
        } catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)
    throw "API Service did not become healthy: $Url"
}

function Ensure-Infrastructure {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is required to run the Phase 2.8 B2 acceptance gate."
    }
    Push-Location $Repository
    try {
        docker compose up -d postgres redis
        Assert-ExitCode "PostgreSQL/Redis infrastructure startup failed."
    } finally {
        Pop-Location
    }
}

function Ensure-ApiService {
    $apiUrl = "http://127.0.0.1:8000/api/v1"
    $healthUrl = "http://127.0.0.1:8000/health"
    try {
        Wait-Api $healthUrl 5
        return $apiUrl
    } catch {
        Write-Host "API Service is not running; starting a local uvicorn process."
        $logDir = Join-Path $Backend ".phase-2.8-gate"
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        $stdout = Join-Path $logDir "b2-api.stdout.log"
        $stderr = Join-Path $logDir "b2-api.stderr.log"
        $script:ApiProcess = Start-Process -FilePath "uv" -ArgumentList "run","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $Backend -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
        Wait-Api $healthUrl 60
    }
    return $apiUrl
}

function Get-AutomatedAccessToken([string]$ApiUrl) {
    $suffix = [Guid]::NewGuid().ToString("N")
    $username = "phase28-b2-$suffix"
    $password = "Phase28B2-$suffix-A9!"
    $body = @{ username = $username; password = $password } | ConvertTo-Json
    Invoke-RestMethod -Uri "$ApiUrl/auth/register" -Method Post -ContentType "application/json" -Body $body | Out-Null
    $login = Invoke-RestMethod -Uri "$ApiUrl/auth/login" -Method Post -ContentType "application/json" -Body $body
    if (-not $login.access_token) { throw "Automated B2 test-user login returned no access_token." }
    return $login.access_token
}

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.8 B2 Worker Bridge Gate"
Write-Host "============================================================"

Write-Host "[1/4] B2 bridge Unit"
uv run pytest -q tests/unit/test_agent_delegation_runtime_bridge.py
Assert-ExitCode "B2 bridge unit gate failed."

Write-Host "[2/4] Backend default regression"
uv run pytest -q
Assert-ExitCode "Backend default regression failed."

Write-Host "[3/4] Migration/head verification"
uv run alembic upgrade head
Assert-ExitCode "Alembic upgrade head failed."
uv run alembic current
Assert-ExitCode "Alembic current failed."

Write-Host "[4/4] Real HTTP + PostgreSQL B2 Worker Execution Bridge"
Ensure-Infrastructure
$ApiBaseUrl = Ensure-ApiService
$env:API_BASE_URL = $ApiBaseUrl
$env:ACCESS_TOKEN = Get-AutomatedAccessToken $ApiBaseUrl
uv run pytest -q -o "addopts=" -m real_api tests/api_real/test_agent_delegation_bridge_api.py
Assert-ExitCode "B2 Worker Execution Bridge real acceptance failed."

Write-Host "[PASS] Phase 2.8 B2 Worker Execution Bridge gate completed."

if ($script:ApiProcess) {
    Stop-Process -Id $script:ApiProcess.Id -Force -ErrorAction SilentlyContinue
}
