# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration、API / Scheduler 进程解耦已完成开发；Scheduler Misfire / Lease Gate 已由开发者本地实际通过；Scheduler Runtime Real PostgreSQL Acceptance 已新增，待本轮开发者执行后再更新最终状态。**
> 验收基线：`main`
> 评估日期：2026-09-02

## 1. 当前 Gate

| 项目 | 状态 |
|---|---|
| Contract / timezone / DST | 本地 Gate 已通过：13 passed（上一轮） |
| Scheduler 持久化模型 | 本地 Migration Gate 已通过（上一轮） |
| Alembic `0028_durable_scheduler_persistence` | 本地 `current` 为 head（上一轮） |
| 原子 lease claim / release | PostgreSQL Repository integration 已通过 |
| schedule slot 幂等 claim | PostgreSQL Repository integration 已覆盖 |
| WorkflowExecution 绑定 | Runtime Gate 已覆盖（上一轮） |
| Tenant / Organization scope | Repository lease/slot 与状态查询 tenant isolation 已覆盖 |
| Scheduler Runtime persistence 闭环 | **新增 Real PostgreSQL Acceptance，待本轮本地执行** |
| Misfire policy Runtime integration | **Scheduler Misfire / Lease Gate 已通过：5 unit + 1 PostgreSQL acceptance** |
| Lease expiry recovery | **Scheduler Misfire / Lease Gate 已通过：expired lease reclaim + stale owner fencing** |
| API / Scheduler Service 进程解耦 | 已实现，服务职责单元 Gate 待集中回归 |
| Scheduler Dispatch / Recovery Scan 生命周期监督 | 已实现，对应 Unit Test 待集中回归 |
| Backend default regression | 服务化后待重新执行 |
| Tenant Safe Real API acceptance | 服务化后待重新执行 |
| Scheduler Restart Acceptance | 服务化后待重新执行 |

## 2. Scheduler Runtime Real PostgreSQL Acceptance

本轮新增真实 PostgreSQL Runtime 验收覆盖：

```text
WorkflowTrigger
    ↓
WorkflowSchedule lease claim
    ↓
misfire catch_up
    ↓
ScheduleSlot × N
    ↓
WorkflowExecution × N
    ↓
Durable Frontier × N
    ↓
AuditLog / WorkflowTraceEvent
    ↓
next_run_at advance + lease release
```

测试数据由测试自身生成 UUID tenant/user/workflow/version/trigger/schedule；测试结束后显式删除本次创建的持久化事实。测试不启动 API、Scheduler、Worker、PostgreSQL 或 Redis。

## 3. 自动化验证入口

Scheduler Misfire / Lease Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\21_scheduler_misfire_lease_gate.ps1
```

Scheduler Runtime Real PostgreSQL Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\22_scheduler_runtime_gate.ps1
```

服务职责边界单元测试：

```powershell
cd backend
uv run pytest -q tests/unit/test_service_entrypoints.py
```

Backend 完整 Regression：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Tenant Safe Real API：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Scheduler Restart Acceptance：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

## 4. 服务化边界

API Service：

```text
backend/run.py
→ app.main:app
→ HTTP / Auth / API Router
→ 不创建 Scheduler
```

Scheduler Service：

```text
backend/run_scheduler.py
→ app.entrypoints.scheduler
→ ScheduledTriggerScheduler + WorkflowRecoveryScheduler
→ 不注册 HTTP Router
```

固定服务身份由启动入口唯一确定，不通过 `SCHEDULER_ENABLED` 等角色开关切换。

## 5. 启动联调流程

### Terminal A — API Service

```powershell
cd backend
uv run python run.py
```

验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

期望包含：

```json
{"status":"ok","service":"api"}
```

### Terminal B — Scheduler Service

确认 PostgreSQL 已启动并完成：

```powershell
cd backend
uv run alembic upgrade head
uv run python run_scheduler.py
```

Scheduler Service 不提供 HTTP 入口；运行证据来自 PostgreSQL Scheduler 状态、WorkflowExecution、Audit/Trace 与 Acceptance。

## 6. 当前结论

**Phase 2.4 尚不能标记 Passed。**

Scheduler Misfire / Lease Gate 已有开发者本地实际通过结果；当前下一步是执行新增 Scheduler Runtime Real PostgreSQL Gate，确认真实 Runtime 闭环、Audit/Trace 关联以及 lease/slot/execution 持久化边界。未执行的 Runtime Acceptance 不得记录为通过。
