param(
    [switch]$SkipRealApi
)

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $Backend

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.8 Delegation Gate"
Write-Host "============================================================"
Write-Host "[1/4] Unit: Delegation identity / budget"
uv run pytest -q tests/unit/test_agent_delegation_identity.py
if ($LASTEXITCODE -ne 0) { throw "Delegation unit gate failed." }

Write-Host "[2/4] Backend default regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend default regression failed." }

Write-Host "[3/4] Migration/head verification"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

if ($SkipRealApi) {
    Write-Host "[4/4] Real API skipped by explicit -SkipRealApi."
    exit 0
}

Write-Host "[4/4] Real HTTP + PostgreSQL Delegation Contract"
if (-not $env:ACCESS_TOKEN) { throw "ACCESS_TOKEN is required for the Real API gate." }
uv run pytest -q tests/api_real/test_agent_delegation_api.py
if ($LASTEXITCODE -ne 0) { throw "Delegation Real API gate failed." }

Write-Host "[PASS] Phase 2.8 Delegation Contract gate completed."
