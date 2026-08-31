$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Runtime Audit Query Unit Gate"
Write-Host "============================================================"
Write-Host "[0/4] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: unit/contract tests do not require manually entered IDs or business data."

Write-Host "[1/4] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "[2/4] Runtime Audit Query unit + API contract"
uv run pytest -q tests/unit/test_runtime_operations_audit_query.py tests/api_contract/test_runtime_operations_audit_query_contract.py
if ($LASTEXITCODE -ne 0) { throw "Runtime Audit Query unit/contract tests failed." }

Write-Host "[3/4] Backend targeted regression"
# Runtime Operations 已按领域子模块拆分；不要引用已经删除的旧聚合测试路径。
# 这里复用当前正式 Runtime Audit Query 单元测试 + Runtime API 总体 Contract，覆盖查询规则与 Runtime 路由装配边界。
uv run pytest -q tests/unit/test_runtime_operations_audit_query.py tests/api_contract/test_api_runtime_endpoints.py
if ($LASTEXITCODE -ne 0) { throw "Runtime targeted regression failed." }

Write-Host "[4/4] Service prerequisite policy"
Write-Host "[NOT EXECUTED] Real API execution is intentionally not started by this gate."
Write-Host "[INFO] Real Acceptance, if required, must use already-running local services and automatically generated fixtures."
Write-Host "[PASS] Phase 2.10-II Runtime Audit Query Unit Gate completed."
