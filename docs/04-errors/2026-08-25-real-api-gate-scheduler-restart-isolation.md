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

因此，restart acceptance 不应混入普通 Real API Gate，也不能在已有 Scheduler 进程运行时直接启动第二个 Scheduler。

## 3. 修复

### 3.1 Tenant Safe Real API Gate

`backend/scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1` 不再执行：

```text
tests/api_real/test_scheduler_restart_api.py
```

普通 Real API Gate 继续验证真实 HTTP + PostgreSQL 的业务 API；Scheduler 真实进程停止/重启属于独立生命周期 Acceptance。

### 3.2 Scheduler Restart Acceptance

`backend/scripts/test/api-real/02_run_scheduler_restart_acceptance.ps1` 增加独占端口检查：

- 运行前检查 `127.0.0.1:8000`；
- 如果已有 API/Scheduler 进程监听该端口，立即失败并明确要求先停止现有服务；
- 只有端口空闲时才启动临时 Uvicorn；
- 该脚本继续负责独立的真实服务启动、停止、重启与 PostgreSQL recovery 验收。

该边界不是为了规避测试，而是为了保证 Scheduler restart Acceptance 的唯一 worker ownership 前提真实成立。

## 4. 关于 `Workflow definition 必须包含非空 nodes`

该日志说明本地数据库中至少存在一个已发布 Workflow 的 definition 不满足当前 Runtime Contract，并且该 Workflow 上存在 Scheduled Trigger。

这属于独立的数据/发布治理问题，不能作为忽略 restart failure 的理由，也不应通过放宽 `WorkflowRuntime.validate_definition()` 掩盖。

本轮修复不改变 Runtime definition Contract；后续应单独评估“发布 Workflow 时是否必须执行 Runtime definition 校验”的领域治理边界，避免无效 Scheduled Trigger 持续进入 Scheduler。

## 5. 验收边界

普通 Real API Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

独立 Scheduler Restart Acceptance：

```powershell
# 必须先停止当前正在运行的 API/Scheduler 服务
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

两个 Gate 不得同时启动多个 Scheduler worker 共享同一测试数据库执行 restart acceptance。
