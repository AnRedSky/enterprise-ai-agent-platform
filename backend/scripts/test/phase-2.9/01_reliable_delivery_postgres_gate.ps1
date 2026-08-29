# Phase 2.9-C Reliable Delivery PostgreSQL Real Gate
$ErrorActionPreference = "Stop"

# 当前脚本位于 backend/scripts/test/phase-2.9；向上三级才是 backend 根目录。
# 使用脚本自身位置计算路径，避免从调用工作目录推断项目结构。
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
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

    # 从 HEAD 树检查 backend/.env.example，而不是检查 Git index；这样即使本地 index 暂时未同步，
    # 也不会把一个已经存在于当前 main 提交中的配置基线误判为缺失。
    & git cat-file -e "HEAD:backend/.env.example"
    if ($LASTEXITCODE -ne 0) {
        throw "backend/.env.example is not tracked by the current main commit; synchronize main before running the Gate."
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
# pyproject.toml 的默认 addopts 会排除 real_api；此 Gate 必须显式覆盖该默认筛选，
# 否则 pytest 会把 5 个真实 PostgreSQL 验收测试全部 deselect，造成“脚本成功执行但实际未验收”的假阴性。
& uv run pytest -q tests/api_real/test_integration_event_delivery_postgres.py --tb=short -m real_api
if ($LASTEXITCODE -ne 0) { throw "Phase 2.9-C PostgreSQL Real Gate failed." }

Write-Host "[3/3] Targeted delivery unit regression"
& uv run pytest -q tests/unit/test_integration_event_contract.py tests/unit/test_integration_event_persistence.py tests/unit/test_integration_event_delivery.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Phase 2.9-C targeted unit regression failed." }

Write-Host "[PASS] Phase 2.9-C Reliable Delivery PostgreSQL Real Gate completed."
