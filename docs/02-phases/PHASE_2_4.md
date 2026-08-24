# Phase 2.4 — Durable Scheduler

> 状态：**Contract-first、Persistence 第一版与 Scheduler Runtime 已完成本地 Gate；当前推进 Scheduler API Contract / 状态可观测性。**
> 评估日期：2026-08-24
> 优先级：**P1**

## 1. 方案决策

Phase 2.4 采用“**Contract-first + MVP 边界 + 可替换实现**”：

- 首版只解决已发布 Workflow Scheduled Trigger 的持久化、恢复、lease、多实例 ownership、misfire、幂等和审计追踪。
- `next_run_at` 使用 UTC 持久化，调度配置保存 IANA timezone。
- 多实例 ownership 优先使用 PostgreSQL 原子 UPDATE / 行锁。
- 不提前引入 MQ/Kafka、Temporal、独立 Scheduler 服务、复杂 DAG 或通用任务平台。

## 2. 当前实现结构

Scheduler 已统一收敛到功能子模块，并遵循当前阶段模块化规则：

```text
backend/app/services/workflow_scheduler/
├── __init__.py      # 稳定公开入口
├── contract.py      # 薄入口，不重复实现领域规则
├── models.py        # 状态、misfire、lease、slot 数据模型
├── time.py          # UTC、IANA timezone、DST 时间语义
├── lease.py         # lease 可抢占判断
├── misfire.py       # misfire 槽位选择
├── repository.py    # PostgreSQL 原子 lease / slot 持久化
└── runtime.py       # Scheduled Trigger 持久化调度器
```

`__init__.py` 负责稳定导出；领域规则按职责拆分，禁止继续向公共 `app/services/` 零散增加同功能文件。

## 3. Contract 范围

当前已覆盖：

1. `enabled / paused / disabled`；
2. IANA timezone 与 UTC 持久化；
3. 可注入 `SchedulerClock`；
4. DST 重复时间选择第一次、不存在时间拒绝；
5. `schedule_slot_key` 稳定幂等键；
6. lease owner / expiry 成对约束；
7. `skip / fire_once / catch_up` misfire。

对应测试：`backend/tests/unit/test_workflow_scheduler_contract.py`。

## 4. Persistence 第一版

已存在：

- `WorkflowSchedule`：调度状态、next/last run、lease、misfire 等持久化；
- `WorkflowScheduleSlot`：`schedule_slot_key` 唯一约束、planned time、owner 与 WorkflowExecution 关联；
- `0028_durable_scheduler_persistence` Migration；
- `workflow_scheduler/repository.py`：单条 UPDATE 原子 lease claim、owner 条件 release、PostgreSQL `ON CONFLICT DO NOTHING` slot claim、Execution 绑定；
- `tests/integration/test_workflow_scheduler_repository.py`：真实 PostgreSQL Repository lease / release、tenant isolation 与 slot idempotency 测试；
- `scripts/test/integration/01_scheduler_persistence_gate.ps1`：Migration、Contract targeted、Repository PostgreSQL integration、Backend Regression 固定编排。

开发者本地已实际执行 Persistence Gate：Migration heads/current、13 个 Contract tests、2 个 Repository PostgreSQL integration tests、Backend Regression 均通过，未报告警告。

## 5. Durable Runtime 接入

Runtime 已从“进程内 interval recovery”切换为持久化 Scheduler 状态驱动：

1. Scheduled Trigger 首次进入 Runtime 时由 Repository 确保唯一 `WorkflowSchedule`；
2. 每个 Scheduler 实例拥有唯一 owner，通过 PostgreSQL 原子 lease claim 取得执行权；
3. 以持久化 `next_run_at` 生成稳定 `WorkflowScheduleSlot.schedule_slot_key`；
4. Execution 创建继续复用既有 `WorkflowTriggerService.invoke_scheduled`；
5. Execution 与 slot 绑定后，由 lease owner 原子推进 `next_run_at / last_run_at / last_execution_id` 并释放 lease；
6. 首版 `misfire=skip` 保持明确边界：历史积压不逐槽补发，下一次运行从未来时间重新计算；
7. `tests/unit/test_workflow_scheduler_runtime.py` 与 `scripts/test/integration/02_scheduler_runtime_gate.ps1` 已完成。

## 6. Runtime Gate 实际结果

开发者本地已执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\02_scheduler_runtime_gate.ps1
```

实际结果：

```text
Scheduler Runtime targeted tests：4 passed
Alembic current：0028_durable_scheduler_persistence (head) (mergepoint)
Scheduler contract targeted tests：13 passed
Scheduler repository PostgreSQL integration：2 passed
Backend default regression：384 passed, 2 skipped, 35 deselected
```

**Runtime Gate 已关闭。**

## 7. Scheduler API Contract / 状态可观测性

本轮新增只读状态查询：

```text
GET /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/schedule
```

职责边界：

- API 只负责认证、tenant/workflow/trigger scope 校验和响应转换；
- Scheduler 状态读取统一复用 `WorkflowSchedulerRepository.get_schedule_for_trigger`；
- 不在 API 层复制 next_run、lease、misfire 或 slot 计算；
- 不暴露 Scheduler worker owner，仅返回 `lease_active` 与 `lease_expires_at`；
- 非 Scheduled Trigger 或尚未初始化的 Scheduler 状态返回 404。

对应 Contract 测试：`backend/tests/api_contract/test_api_scheduled_triggers.py`。
固定 Gate：`backend/scripts/test/integration/03_scheduler_api_contract_gate.ps1`。

**当前 API Contract 尚待开发者本地执行 Gate，不预填通过结果。**

## 8. 下一执行顺序

```text
Scheduler API Contract / 状态可观测性
      ↓
Tenant isolation / misfire integration
      ↓
Tenant Safe Real API Gate
      ↓
Backend Regression Gate
      ↓
Frontend API / UI（如存在明确用户操作范围）
      ↓
Browser E2E（如存在对应 UI 用户链路）
```

未完成上述 Gate 前，不记录 Phase 2.4 Passed。
