param(
    [switch]$SkipRealApi
)

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $Backend

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.8 Delegation Gate"
Write-Host "============================================================"

Write-Host "[1/5] Unit: Delegation identity / lifecycle / budget"
uv run pytest -q tests/unit/test_agent_delegation_identity.py tests/unit/test_agent_delegation_lifecycle.py
if ($LASTEXITCODE -ne 0) { throw "Delegation unit gate failed." }

Write-Host "[2/5] Backend default regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend default regression failed." }

Write-Host "[3/5] Migration/head verification"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

if ($SkipRealApi) {
    Write-Host "[4/5] Real API skipped by explicit -SkipRealApi."
    Write-Host "[5/5] B1 PostgreSQL concurrency acceptance skipped with Real API."
    exit 0
}

Write-Host "[4/5] Real HTTP + PostgreSQL Delegation Contract"
if (-not $env:ACCESS_TOKEN) { throw "ACCESS_TOKEN is required for the Real API gate." }
uv run pytest -q tests/api_real/test_agent_delegation_api.py
if ($LASTEXITCODE -ne 0) { throw "Delegation Real API contract gate failed." }

Write-Host "[5/5] B1 Atomic Claim: real PostgreSQL two-worker race"
uv run pytest -q tests/api_real/test_agent_delegation_claim_api.py
if ($LASTEXITCODE -ne 0) { throw "B1 Atomic Claim PostgreSQL concurrency gate failed." }

Write-Host "[PASS] Phase 2.8 Delegation + B1 Atomic Claim gate completed."
