# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Persistence、Runtime、Scheduler API Contract 已完成开发者本地 Gate；当前 tenant isolation / misfire integration 因应用循环导入问题阻塞，修复后待重新 Gate。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮基于远端 `main` 最新提交 `09b3811` 继续开发；该提交集成 Scheduler tenant isolation 与 misfire policies。

用户本地实际反馈表明 `09b3811` 引入后发生 Scheduler misfire 循环导入，导致应用启动失败。该问题已在 `fix(scheduler): remove misfire circular import` 中修复，并已同步记录到 `docs/04-errors/2026-08-24-scheduler-misfire-circular-import.md`。

修复前用户本地实际结果：

```text
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"：ImportError
04_scheduler_tenant_misfire_gate.ps1：Application import 失败
01_run_real_api_tests_tenant_safe.ps1：/auth/register -> 503
uv run pytest -q：28 errors during collection，32 deselected
```

以上均为用户本地实际反馈。修复提交后的 Gate 尚未重新由开发者本地执行，因此不得记录为通过。

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

## 本轮修复边界

```text
workflow_scheduler.contract
        ↓
workflow_scheduler.misfire
        ↓
workflow_scheduler.time
```

`misfire.py` 只依赖其职责归属的 `models.py` 与 `time.py`，不再反向依赖聚合入口 `contract.py`。没有新增第二套 Scheduler、Repository、Provider 或 Workflow Execution 实现，也没有新增 Alembic Migration。

## 下一步

1. 开发者本地重新执行应用 import，确认循环导入已经消除；
2. 执行 `04_scheduler_tenant_misfire_gate.ps1`；
3. Gate 通过后执行 Tenant Safe Real API Gate；
4. 根据真实 Real API 结果继续补齐多实例 lease、misfire、Execution、Audit / Trace 与服务重启恢复验收；
5. 完成后再更新 Phase Acceptance 与 Project Status 为实际结果；
6. 仍然不创建兼容垫片、旧入口转发或第二套调度实现。
