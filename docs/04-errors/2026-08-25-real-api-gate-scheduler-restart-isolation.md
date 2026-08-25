# 2026-08-25 Real API Gate 与 Scheduler Restart 生命周期隔离

## 1. 现象

开发者执行 Backend Regression Gate 时出现：

- Backend default regression：397 passed，3 skipped，36 deselected；
- Tenant Safe Real API Gate：Scheduler restart 场景首次失败，`test_scheduled_trigger_recovers_after_real_service_restart` 最终得到 `[]`；
- 随后独立重新执行 Tenant Safe Real API Gate：36 passed；
- API 服务日志同时出现 `Scheduled Trigger dispatch failed`，其中一次原因是 `Workflow definition 必须包含非空 nodes`。

该现象表现为 Real API restart 验收存在非确定性，而不是普通 API Contract 本身稳定失败。

## 2. 根因

`tests/api_real/test_scheduler_restart_api.py` 本身会启动、停止并重新启动临时 Uvicorn 进程，但它操作的 PostgreSQL 是整个本地测试环境共享数据库。

正常 Tenant Safe Real API Gate 如果同时存在一个已经运行的 API/Scheduler 进程，那么这个外部 Scheduler 也会扫描同一个数据库中的 Scheduled Trigger。restart 测试创建目标 Trigger 后：

```text
正常 API/Scheduler 进程
        │
        ├── 扫描同一 PostgreSQL
        │
        └── 可能抢占测试 Trigger 的 lease / slot

restart acceptance 临时进程
        │
        ├── 停止自身
        ├── 回拨 next_run_at
        └── 重新启动并等待 recovery
```

这使“真实服务停止后由新进程恢复历史 slot”的验收边界被第二个 Scheduler 破坏。执行时序不同会导致一次成功、一次失败。

因此，restart acceptance 不应混入普通 Real API Gate，也不能让测试自身启动的多个 Scheduler worker 竞争同一目标 slot。

## 3. 修复

### 3.1 Tenant Safe Real API Gate

`backend/scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1` 不再执行：

```text
tests/api_real/test_scheduler_restart_api.py
```

普通 Real API Gate 继续验证真实 HTTP + PostgreSQL 的业务 API；Scheduler 真实进程停止/重启属于独立生命周期 Acceptance。

### 3.2 Scheduler Restart Acceptance 的端口自动化

旧版 `backend/scripts/test/api-real/02_run_scheduler_restart_acceptance.ps1` 固定使用 `127.0.0.1:8000` 启动 fixture bootstrap 服务。当开发环境已有 API/Scheduler 监听 8000 时，脚本会在真正执行 Acceptance 前直接失败。

本轮将 bootstrap 改为动态申请本机空闲 TCP 端口：

- 启动前由 PowerShell `TcpListener(..., 0)` 申请临时端口；
- 将该端口注入 `API_BASE_URL`，仅用于真实 HTTP fixture bootstrap；
- bootstrap 完成后停止并释放临时服务；
- 后续 `test_scheduler_restart_api.py` 继续自行申请新的空闲端口进行真实 Uvicorn 生命周期测试；
- finally 清理 `API_BASE_URL`、`ACCESS_TOKEN`、`TRIGGER_WORKFLOW_ID` 和临时 context 文件。

因此开发环境即使已有 `127.0.0.1:8000` API 服务，也不再因为无关的固定端口状态阻断该 Gate。

### 3.3 修复边界

该修复只解除测试 bootstrap 对固定端口的无必要依赖，不放宽 Scheduler restart 的真实生命周期边界：

- bootstrap 临时 Scheduler 必须在 Acceptance 开始前退出；
- PostgreSQL 仍是真实持久化数据库；
- restart 测试仍然真实停止、启动、重启 Uvicorn；
- slot recovery、lease、idempotency、WorkflowExecution、Audit/Trace 仍由真实服务验证；
- 不使用 Mock、JSON fixture 或进程内 Scheduler 重建替代真实生命周期。

## 4. 关于 `Workflow definition 必须包含非空 nodes`

该日志说明本地数据库中至少存在一个已发布 Workflow 的 definition 不满足当前 Runtime Contract，并且该 Workflow 上存在 Scheduled Trigger。

这属于独立的数据/发布治理问题，不能作为忽略 restart failure 的理由，也不应通过放宽 `WorkflowRuntime.validate_definition()` 掩盖。

本轮修复不改变 Runtime definition Contract；后续应单独评估“发布 Workflow 时是否必须执行 Runtime definition 校验”的领域治理边界，避免无效 Scheduled Trigger 持续进入 Scheduler。

## 5. 新的本地验收流程

普通 Real API Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

独立 Scheduler Restart Acceptance：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

不再要求开发者手工停止 8000 端口上的普通 API 服务；脚本会自动为 bootstrap 申请临时端口。真正 Acceptance 的临时 Uvicorn 端口由测试代码自行动态申请，并在测试结束后清理。

两个 Gate 仍不得同时启动多个 Scheduler worker 竞争同一测试 slot。
