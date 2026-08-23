# Phase 2.3 Real API Bootstrap Tenant Boundary

## 发生时间

2026-08-23

## 问题

`backend/scripts/test/api-real/01_run_real_api_tests.ps1` 在 bootstrap 阶段失败。`00_bootstrap_real_api.py` 创建 retry/circuit breaker Workflow fixtures 后立即执行 `/workflows/executions/{id}/run`，测试预期这些 deterministic fixtures 返回 `404` / `503` 等运行时边界；实际返回：

```text
403: {"detail":"当前用户没有有效的 Organization membership"}
```

因此 Real API 测试套件尚未开始执行。

## 根因

Phase 2.3 Runtime 已将 Organization membership 纳入 Workflow execution 的 tenant governance boundary，但 Real API bootstrap 的 fixture 创建顺序仍沿用旧的“先创建 Workflow，再创建 Organization”流程：

1. 登录测试用户；
2. 创建可执行 Workflow、retry/circuit fixtures；
3. 立即执行 Workflow；
4. 最后才创建 Organization 和 member fixture。

这使得 bootstrap 创建的执行 fixture 在运行时没有有效的 active Organization membership，导致新的 governance boundary 与旧 bootstrap 顺序冲突。

## 修复

直接基于 `main` 修复 `backend/scripts/test/api-real/00_bootstrap_real_api.py`：

1. 登录后立即创建本次 Real API Organization fixture；
2. 在 Organization tenant 已建立后创建所有需要执行的 Workflow/Execution fixtures；
3. 不再复用可能来自旧 tenant 状态的历史 executable workflow，而是每次 bootstrap 创建专用 executable workflow；
4. 保留 member token / organization id 等上下文供后续 governance API 测试使用。

## 验证要求

开发者必须重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

在该命令实际返回全套测试通过前，不得把 Real API Gate 标记为 Passed。

同时建议完成 Backend Gate：

```powershell
cd backend
uv run pytest -q
```

若本轮涉及 migration 之外的 fixture/bootstrap 修复，无需新增 Alembic migration；但 migration/head verification 是否通过仍应以开发者实际执行结果为准。

## 设计意图

Real API bootstrap 必须先建立与 Runtime execution 一致的 Organization tenant boundary，再创建依赖该 boundary 的可执行 fixture。测试 fixture 不得通过绕过鉴权/租户校验来恢复旧的预期 HTTP 状态。
