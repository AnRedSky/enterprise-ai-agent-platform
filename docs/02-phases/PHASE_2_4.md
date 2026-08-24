# Phase 2.4 — Durable Scheduler

> 状态：**Persistence、Runtime 与 Scheduler API Contract 已由开发者本地 Gate 实际通过；当前推进 tenant isolation / misfire integration，新增实现尚待本地 Gate。**
> 评估日期：2026-08-24
> 优先级：**P1**

## 1. 方案决策

Phase 2.4 采用“**Contract-first + MVP 边界 + 可替换实现**”：

- 首版解决已发布 Workflow Scheduled Trigger 的持久化、恢复、lease、多实例 ownership、misfire、幂等和审计追踪。
- `next_run_at` 使用 UTC 持久化，调度配置保存 IANA timezone。
- 多实例 ownership 优先使用 PostgreSQL 原子 UPDATE / 行锁。
- 不提前引入 MQ/Kafka、Temporal、独立 Scheduler 服务、复杂 DAG 或通用任务平台。

## 2. 当前实现结构

```text
backend/app/services/workflow_scheduler/
├── __init__.py      # 稳定公开入口
├── contract.py      # 薄入口，不重复实现领域规则
├── models.py        # 状态、misfire、lease、slot 数据模型
├── time.py          # UTC、IANA timezone、DST 时间语义
├── lease.py         # lease 可抢占判断
├── misfire.py       # misfire 槽位规划
├── repository.py    # PostgreSQL 原子 lease / slot 持久化
└── runtime.py       # Scheduled Trigger 持久化调度器
```

`__init__.py` 负责稳定导出；领域规则按职责拆分，禁止继续向公共 `app/services/` 零散增加同功能文件。

## 3. Contract 范围

当前覆盖：

1. `enabled / paused / disabled`；
2. IANA timezone 与 UTC 持久化；
3. 可注入 `SchedulerClock`；
4. DST 重复时间选择第一次、不存在时间拒绝；
5. `schedule_slot_key` 稳定幂等键；
6. lease owner / expiry 成对约束；
7. `skip / fire_once / catch_up` misfire；
8. Scheduled Trigger 配置可持久化 `misfire_policy / catch_up_limit`。

对应测试：`backend/tests/unit/test_workflow_scheduler_contract.py` 与 Runtime misfire targeted tests。

## 4. Persistence 第一版

已存在：

- `WorkflowSchedule`：调度状态、next/last run、lease、misfire 等持久化；
- `WorkflowScheduleSlot`：`schedule_slot_key` 唯一约束、planned time、owner 与 WorkflowExecution 关联；
- `0028_durable_scheduler_persistence` Migration；
- `workflow_scheduler/repository.py`：单条 UPDATE 原子 lease claim、owner 条件 release、PostgreSQL `ON CONFLICT DO NOTHING` slot claim、Execution 绑定；
- Repository 的 tenant + trigger scope；
- PostgreSQL Repository lease / release、tenant isolation 与 slot idempotency integration tests。

开发者本地已实际执行 Persistence Gate：Migration heads/current、13 个 Contract tests、2 个 Repository PostgreSQL integration tests、Backend Regression 均通过。

本轮不新增 Migration，因为 misfire 字段已经存在于 `0028_durable_scheduler_persistence` 的持久化模型。

## 5. Durable Runtime 接入

Runtime 已从“进程内 interval recovery”切换为持久化 Scheduler 状态驱动：

1. Scheduled Trigger 首次进入 Runtime 时由 Repository 确保唯一 `WorkflowSchedule`；
2. 每个 Scheduler 实例拥有唯一 owner，通过 PostgreSQL 原子 lease claim 取得执行权；
3. 以持久化 `next_run_at` 生成稳定 `WorkflowScheduleSlot.schedule_slot_key`；
4. Execution 创建继续复用既有 `WorkflowTriggerService.invoke_scheduled`；
5. Execution 与 slot 绑定后，由 lease owner 原子推进 `next_run_at / last_run_at / last_execution_id` 并释放 lease；
6. Runtime 不复制 Trigger 校验、Execution 状态机或 Repository 规则。

开发者本地 Runtime Gate 已实际通过：

```text
Scheduler Runtime targeted tests：4 passed
Alembic current：0028_durable_scheduler_persistence (head) (mergepoint)
Scheduler contract targeted tests：13 passed
Scheduler repository PostgreSQL integration：2 passed
Backend default regression：385 passed, 2 skipped, 35 deselected
```

## 6. Scheduler API Contract / 状态可观测性

只读状态查询：

```text
GET /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/schedule
```

职责边界：

- API 只负责认证、tenant/workflow/trigger scope 校验和响应转换；
- Scheduler 状态读取统一复用 `WorkflowSchedulerRepository.get_schedule_for_trigger`；
- 不在 API 层复制 next_run、lease、misfire 或 slot 计算；
- 不暴露 Scheduler worker owner，仅返回 `lease_active` 与 `lease_expires_at`；
- 非 Scheduled Trigger 或尚未初始化的 Scheduler 状态返回 404。

开发者本地 API Contract Gate 已实际通过：

```text
Scheduler API Contract tests：6 passed
Backend default regression：385 passed, 2 skipped, 35 deselected
```

## 7. Tenant isolation / misfire integration（当前开发任务）

### Tenant isolation

- Repository 查询必须同时携带 `tenant_id + trigger_id`；
- lease claim / release / advance 必须同时携带 tenant scope；
- slot 查询保持 tenant scope；
- 新增真实 PostgreSQL 状态查询隔离测试，验证错误 tenant 无法读取正确 tenant 的 Scheduler 状态。

### Misfire integration

Scheduled Trigger Contract 新增：

```text
misfire_policy: skip | fire_once | catch_up
catch_up_limit: 1..100，默认 10
```

运行语义：

- `skip`：历史积压全部跳过，下一运行恢复到未来 interval；
- `fire_once`：历史积压只补一次，随后恢复到未来 interval；
- `catch_up`：最多补跑 `catch_up_limit` 个历史槽位，若仍有积压则由下一 tick 继续有界处理；
- 每个槽位继续通过 `schedule_slot_key` 和既有 WorkflowTriggerService idempotency 收敛重复执行。

misfire 计算统一位于 `workflow_scheduler/misfire.py`，Runtime 不复制规则。

## 8. 当前新增 Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\04_scheduler_tenant_misfire_gate.ps1
```

Gate 顺序：

```text
Application import
      ↓
Scheduler misfire unit tests
      ↓
Scheduler tenant PostgreSQL integration
      ↓
Scheduler API Contract tests
      ↓
Backend Regression
```

**该 Gate 尚未由开发者本地执行，不记录 Passed。**

## 9. 下一执行顺序

```text
Tenant isolation / misfire integration Gate
      ↓
Tenant Safe Real API Gate
      ↓
多实例 lease / misfire / Execution / Audit Trace / restart recovery Acceptance
      ↓
Backend Regression Gate
      ↓
Frontend API / UI（如存在明确用户操作范围）
      ↓
Browser E2E（如存在对应 UI 用户链路）
```

未完成上述 Gate 前，不记录 Phase 2.4 Passed。
