# Phase 2.9-C Reliable Delivery PostgreSQL Real Gate
$ErrorActionPreference = "Stop"
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\.." )).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.9-C Reliable Delivery PostgreSQL Gate"
Write-Host "============================================================"
Write-Host "[0/3] Local prerequisite verification (no service startup)"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv 未安装或不在 PATH 中。"
}

$envFile = Join-Path $BackendRoot ".env"
$envDevFile = Join-Path $BackendRoot ".env.dev"
if (-not (Test-Path $envFile) -and -not (Test-Path $envDevFile)) {
    throw "未找到 backend/.env 或 backend/.env.dev，无法确定 PostgreSQL 连接配置。"
}

Write-Host "服务策略：本 Gate 不启动、不停止 API / Worker / Scheduler / Redis / PostgreSQL。"
Write-Host "测试数据策略：测试自动生成租户、事件及幂等键，不要求手工填写测试信息。"

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
