[CmdletBinding()]
param(
    [ValidateSet("api", "unit", "frontend", "all")]
    [string]$Mode = "api",
    [string]$BaseUrl = $(if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }),
    [string]$Username = "TestUser",
    [string]$Password = "TestPassword123!"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir
$projectDir = Split-Path -Parent $backendDir
$frontendDir = Join-Path $projectDir "frontend"
$scenarioScript = Join-Path $scriptDir "run_api_scenario.ps1"
$frontendScript = Join-Path $frontendDir "scripts\run_manual_frontend_suite.ps1"

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - Manual Test Suite" -ForegroundColor White
Write-Host "Mode    : $Mode" -ForegroundColor Gray
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray

function Invoke-ApiScenario {
    if (-not (Test-Path $scenarioScript)) {
        throw "API scenario script not found: $scenarioScript"
    }

    Write-Host "[RUN ] API scenario: Health -> Auth -> Agents -> Chat -> Runtime -> Tools" -ForegroundColor Cyan
    & powershell -ExecutionPolicy Bypass -File $scenarioScript -BaseUrl $BaseUrl -Username $Username -Password $Password
    if ($LASTEXITCODE -ne 0) {
        throw "API scenario failed with exit code $LASTEXITCODE."
    }
    Write-Host "[ OK  ] API scenario" -ForegroundColor Green
}

function Invoke-UnitTests {
    Push-Location $backendDir
    try {
        if (-not (Get-Command pytest -ErrorAction SilentlyContinue)) {
            throw "pytest was not found. Activate backend .venv first."
        }

        $testPaths = @(
            "tests/test_api_health_endpoint.py",
            "tests/test_api_auth_endpoints.py",
            "tests/test_api_agents_endpoints.py",
            "tests/test_api_chat_endpoints.py",
            "tests/test_api_runtime_endpoints.py",
            "tests/test_api_tools_endpoints.py",
            "tests/test_runtime_api_contract.py",
            "tests/test_runtime_http_rbac.py",
            "tests/test_model_gateway.py",
            "tests/test_tool_runtime.py",
            "tests/test_memory_context.py",
            "tests/test_memory_service.py",
            "tests/test_memory_governance.py",
            "tests/test_observability.py"
        )

        $existing = @($testPaths | Where-Object { Test-Path $_ })
        if ($existing.Count -eq 0) {
            throw "No expected pytest files were found."
        }

        Write-Host "[RUN ] Backend regression tests ($($existing.Count) test files)" -ForegroundColor Cyan
        & pytest -q @existing
        if ($LASTEXITCODE -ne 0) {
            throw "Backend regression tests failed with exit code $LASTEXITCODE."
        }
        Write-Host "[ OK  ] Backend regression tests" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

function Invoke-FrontendTests {
    if (-not (Test-Path $frontendScript)) {
        throw "Frontend manual test script not found: $frontendScript"
    }

    Write-Host "[RUN ] Frontend tests + production build" -ForegroundColor Cyan
    & powershell -ExecutionPolicy Bypass -File $frontendScript
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend test suite failed with exit code $LASTEXITCODE."
    }
    Write-Host "[ OK  ] Frontend tests + production build" -ForegroundColor Green
}

switch ($Mode) {
    "api"      { Invoke-ApiScenario }
    "unit"     { Invoke-UnitTests }
    "frontend" { Invoke-FrontendTests }
    "all"      { Invoke-ApiScenario; Invoke-UnitTests; Invoke-FrontendTests }
}

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "[PASS] Manual test suite completed: $Mode" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor DarkGray
