[CmdletBinding()]
param(
    [ValidateSet("api", "knowledge", "unit", "all")]
    [string]$Mode = "api",
    [string]$BaseUrl = $(if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }),
    [string]$Username = "TestUser",
    [string]$Password = "TestPassword123!"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir
$scenarioScript = Join-Path $scriptDir "run_api_scenario.ps1"
$knowledgeScenarioScript = Join-Path $scriptDir "run_knowledge_registry_scenario.ps1"
$ingestionScenarioScript = Join-Path $scriptDir "run_knowledge_ingestion_scenario.ps1"

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - Backend Manual Test Suite" -ForegroundColor White
Write-Host "Mode    : $Mode" -ForegroundColor Gray
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray

function Invoke-ApiScenario {
    if (-not (Test-Path $scenarioScript)) { throw "API scenario script not found: $scenarioScript" }
    Write-Host "[RUN ] Backend API scenario: Health -> Auth -> Agents -> Chat -> Runtime -> Tools" -ForegroundColor Cyan
    & powershell -ExecutionPolicy Bypass -File $scenarioScript -BaseUrl $BaseUrl -Username $Username -Password $Password
    if ($LASTEXITCODE -ne 0) { throw "Backend API scenario failed with exit code $LASTEXITCODE." }
    Write-Host "[ OK  ] Backend API scenario" -ForegroundColor Green
}

function Invoke-KnowledgeScenarios {
    foreach ($script in @($knowledgeScenarioScript, $ingestionScenarioScript)) {
        if (-not (Test-Path $script)) { throw "Knowledge scenario script not found: $script" }
        Write-Host "[RUN ] Backend Knowledge scenario: $(Split-Path -Leaf $script)" -ForegroundColor Cyan
        & powershell -ExecutionPolicy Bypass -File $script -BaseUrl $BaseUrl -Password $Password
        if ($LASTEXITCODE -ne 0) { throw "Knowledge scenario failed with exit code $LASTEXITCODE." }
        Write-Host "[ OK  ] $(Split-Path -Leaf $script)" -ForegroundColor Green
    }
}

function Invoke-UnitTests {
    Push-Location $backendDir
    try {
        if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv was not found. Install uv before running backend tests." }
        $testPaths = @(
            "tests/unit",
            "tests/integration",
            "tests/api_contract"
        )
        $existing = @($testPaths | Where-Object { Test-Path $_ })
        if ($existing.Count -eq 0) { throw "No expected backend test directories were found." }
        Write-Host "[RUN ] Backend regression tests through uv ($($existing.Count) test directories)" -ForegroundColor Cyan
        & uv run pytest -q @existing
        if ($LASTEXITCODE -ne 0) { throw "Backend regression tests failed with exit code $LASTEXITCODE." }
        Write-Host "[ OK  ] Backend regression tests" -ForegroundColor Green
    }
    finally { Pop-Location }
}

switch ($Mode) {
    "api"       { Invoke-ApiScenario }
    "knowledge" { Invoke-KnowledgeScenarios }
    "unit"      { Invoke-UnitTests }
    "all"       { Invoke-ApiScenario; Invoke-KnowledgeScenarios; Invoke-UnitTests }
}

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "[PASS] Backend manual test suite completed: $Mode" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor DarkGray
