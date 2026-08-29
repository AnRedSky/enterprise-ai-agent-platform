# Phase 2.9-C Reliable Delivery PostgreSQL Real Gate
$ErrorActionPreference = "Stop"
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\.." )).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.9-C Reliable Delivery PostgreSQL Gate"
Write-Host "============================================================"
Write-Host "[0/3] Local prerequisite verification (no service startup)"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed or is not available on PATH."
}

# 项目统一使用 backend/.env.example 提供可复现的本地开发默认配置。
# Gate 不要求开发者创建、复制或手工填写 .env/.env.dev；若版本库中的基线文件仅因本地工作区缺失，则自动从当前 HEAD 恢复。
$envExampleFile = Join-Path $BackendRoot ".env.example"
if (-not (Test-Path $envExampleFile)) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "backend/.env.example is missing and git is not available to restore the tracked configuration baseline."
    }

    & git ls-files --error-unmatch -- .env.example *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "backend/.env.example is not tracked by the current main checkout; synchronize main before running the Gate."
    }

    Write-Host "backend/.env.example is missing from the working tree; restoring the tracked main baseline automatically."
    & git restore --source=HEAD -- .env.example
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $envExampleFile)) {
        throw "Failed to restore backend/.env.example from the current main checkout."
    }
}

Write-Host "Configuration policy: backend/.env.example is the unified local test configuration baseline."
Write-Host "Service policy: this Gate never starts or stops API, Worker, Scheduler, Redis, or PostgreSQL."
Write-Host "Test data policy: tests generate tenant, event, and idempotency data automatically; no manual test input is required."

Write-Host "[1/3] Migration/head verification"
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/3] Phase 2.9-C PostgreSQL concurrency/recovery tests"
& uv run pytest -q tests/api_real/test_integration_event_delivery_postgres.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Phase 2.9-C PostgreSQL Real Gate failed." }

Write-Host "[3/3] Targeted delivery unit regression"
& uv run pytest -q tests/unit/test_integration_event_contract.py tests/unit/test_integration_event_persistence.py tests/unit/test_integration_event_delivery.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Phase 2.9-C targeted unit regression failed." }

Write-Host "[PASS] Phase 2.9-C Reliable Delivery PostgreSQL Real Gate completed."
