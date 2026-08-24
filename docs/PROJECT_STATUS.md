# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Persistence、Runtime、Scheduler API Contract 已完成开发者本地 Gate；当前推进 tenant isolation / misfire integration。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮基于远端 `main` 最新提交 `78c4e52` 继续开发；该提交修正 Scheduler API 对 canonical `WorkflowSchedulerRepository` 子模块的 import。

用户本地已实际反馈：

```text
05_backend_refactor_closure_gate.ps1：REFACTOR_CLOSURE_IMPORT_OK
02_scheduler_runtime_gate.ps1：Scheduler Runtime targeted tests 4 passed
Scheduler Persistence Gate：Alembic current = 0028_durable_scheduler_persistence (head)
Scheduler contract targeted tests：13 passed
Scheduler repository PostgreSQL integration：2 passed
03_scheduler_api_contract_gate.ps1：Scheduler API Contract tests 6 passed
Backend default regression：385 passed, 2 skipped, 35 deselected
uv run pytest -q：385 passed, 2 skipped, 35 deselected
```

以上均为用户本地实际反馈；本轮新增 tenant isolation / misfire integration 代码尚未由开发者本地重新执行，不预填通过结果。

## Backend 模块化重构收口

API v1、Runtime Boundary 以及各领域 Service / Runtime / Provider 迁移已经完成；最终 Closure Gate 已确认旧扁平领域实现、旧 import 路径和重复 Provider 入口均已收口，正式领域包具备中文职责 / 边界说明。

**状态：Backend 模块化重构全部 Closure Gate 已完成，不再阻塞主线。**

## Phase 2.4 当前推进

Durable Scheduler 已完成 Contract-first + Persistence + Runtime + Scheduler 状态 API 第一阶段。

当前新增实现聚焦两个未完成边界：

1. **Tenant isolation**
   - `WorkflowSchedulerRepository.get_schedule_for_trigger()` 继续以 `tenant_id + trigger_id` 作为强制查询边界；
   - 新增真实 PostgreSQL tenant isolation integration test，验证错误 tenant 无法读取同一 trigger 的 Scheduler 状态；
   - Runtime 的 lease、slot claim、advance、release 均继续显式携带 tenant，不创建第二套隔离实现。

2. **Misfire integration**
   - Scheduled Trigger Contract 新增 `misfire_policy` 与 `catch_up_limit`，默认保持 `skip` / `10`；
   - 已有 `WorkflowSchedule.misfire_policy` / `catch_up_limit` 字段直接作为持久化边界，本轮不新增 Migration；
   - Runtime 统一复用 `workflow_scheduler/misfire.py` 计算到期槽位，不在 Runtime 复制 misfire 规则；
   - `skip`：历史积压全部跳过并恢复未来 interval；
   - `fire_once`：历史积压只补一次，随后直接恢复未来 interval；
   - `catch_up`：按 `catch_up_limit` 有界补跑，仍有积压时保留下一槽位供下一 tick 继续处理；
   - 每个补跑槽位继续使用既有 `schedule_slot_key` + WorkflowTriggerService idempotency，避免重复创建 Execution。

## 本轮代码交付边界

```text
Trigger Config
    ↓
WorkflowSchedule 持久化配置
    ↓
WorkflowSchedulerRepository
    ↓
workflow_scheduler/misfire.py
    ↓
ScheduledTriggerScheduler
    ↓
既有 WorkflowTriggerService.invoke_scheduled
```

没有新增第二套 Scheduler、Repository、Provider 或 Workflow Execution 实现，也没有新增 Alembic Migration。

## 本轮新增测试编排

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\04_scheduler_tenant_misfire_gate.ps1
```

该 Gate 依次执行：

```text
Application import
    ↓
Scheduler misfire unit tests
    ↓
Scheduler tenant PostgreSQL integration
    ↓
Scheduler API Contract tests
    ↓
Backend default regression
```

本地执行前不得记录为 Passed。

## 下一步

1. 开发者本地执行 `04_scheduler_tenant_misfire_gate.ps1`；
2. 若 Gate 通过，再执行 Tenant Safe Real API Gate；
3. 根据真实 Real API 结果继续补齐多实例 lease、misfire、Execution、Audit / Trace 与服务重启恢复验收；
4. 完成后再更新 Phase Acceptance 与 Project Status 为实际结果；
5. 仍然不创建兼容垫片、旧入口转发或第二套调度实现。
