# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Persistence、Runtime、Scheduler API Contract 已完成；tenant isolation / misfire integration 正在修复 Gate 暴露的问题。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮基于远端 `main` 最新提交 `a77d9e6` 继续开发；此前 `09b3811` 集成 Scheduler tenant isolation 与 misfire policies，后续已修复循环导入，并在 `a77d9e6` 记录了 misfire blocker 与恢复路径。

开发者本地最新实际结果表明：

```text
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"：APP_IMPORT_OK
05_backend_refactor_closure_gate.ps1：REFACTOR_CLOSURE_IMPORT_OK
04_scheduler_tenant_misfire_gate.ps1：20 个 misfire unit tests 通过；2 个 PostgreSQL tenant integration tests 中 1 个失败
01_run_real_api_tests_tenant_safe.ps1：35 个测试中 3 个失败
uv run pytest -q：388 passed, 3 failed, 3 skipped, 35 deselected
```

失败均已完成根因分析并记录到 `docs/04-errors/2026-08-24-scheduler-tenant-misfire-gate.md`，因此当前 Phase 2.4 不能标记 Passed。

## Backend 模块化重构收口

API v1、Runtime Boundary 以及各领域 Service / Runtime / Provider 迁移已经完成；最终 Closure Gate 已确认旧扁平领域实现、旧 import 路径和重复 Provider 入口均已收口，正式领域包具备中文职责 / 边界说明。

**状态：Backend 模块化重构全部 Closure Gate 已完成，不再阻塞主线。**

## Phase 2.4 当前推进

Durable Scheduler 已完成 Contract-first + Persistence + Runtime + Scheduler 状态 API 第一阶段。

当前继续收口两个边界：

1. **Tenant isolation**
   - `WorkflowSchedulerRepository.get_schedule_for_trigger()` 继续以 `tenant_id + trigger_id` 作为强制查询边界；
   - Runtime 的 lease、slot claim、advance、release 均继续显式携带 tenant；
   - PostgreSQL tenant isolation 测试已发现测试 fixture 未显式 flush Trigger 的数据准备问题，本轮已修正测试实现。

2. **Misfire integration**
   - Scheduled Trigger Contract 正式包含 `misfire_policy` 与 `catch_up_limit`，默认 `skip` / `10`；
   - `WorkflowSchedule.misfire_policy` / `catch_up_limit` 继续作为持久化边界，本轮不新增 Migration；
   - Runtime 统一复用 `workflow_scheduler/misfire.py` 计算到期槽位；
   - Runtime 的 Execution idempotency key 已统一复用 `ScheduledTriggerScheduler.idempotency_key()`，避免 `planned_at` 时间戳键与 interval slot 键并存；
   - Runtime 按单个槽位判断 recovery，历史槽位标记 `true`，当前槽位标记 `false`；
   - Real API Recovery 场景改为真实回拨 `workflow_schedules.next_run_at` 验证持久化 misfire，不再依赖进程内 recovery slot 假设。

## 本轮修复边界

```text
workflow_scheduler.runtime
        ↓
ScheduledTriggerScheduler.idempotency_key
        ↓
WorkflowScheduleSlot / WorkflowExecution
```

以及：

```text
Trigger Contract defaults
        ↓
Unit / Real API assertions
```

与：

```text
Tenant fixture
        ↓
WorkflowTrigger flush
        ↓
WorkflowSchedule FK insert
```

没有新增第二套 Scheduler、Repository、Provider、Execution 或幂等键实现，没有新增 Alembic Migration。

## 下一步

1. 开发者本地重新执行 tenant / misfire Gate，确认 PostgreSQL fixture 与 Scheduler slot key 修复；
2. 执行 Tenant Safe Real API Gate，确认配置 Contract、多实例幂等与真实持久化 misfire recovery；
3. 执行 `uv run pytest -q`，确认默认 Backend regression 无回归；
4. 根据真实结果继续补齐多实例 lease、misfire、Execution、Audit / Trace 与服务重启恢复验收；
5. 完成后再更新 Phase Acceptance 与 Project Status 为实际结果；
6. 仍然不创建兼容垫片、旧入口转发或第二套调度实现。
