# Phase 2.4 — Durable Scheduler

> 状态：**Contract-first 已完成；持久化模型、Migration 与原子仓储第一版已实现，尚未完成本地 Persistence Gate、API Contract 与 Durable Scheduler Runtime。**
> 评估日期：2026-08-23
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
├── contract.py      # 薄兼容入口，不重复实现领域规则
├── models.py        # 状态、misfire、lease、slot 数据模型
├── time.py          # UTC、IANA timezone、DST 时间语义
├── lease.py         # lease 可抢占判断
├── misfire.py       # misfire 槽位选择
├── repository.py    # PostgreSQL 原子 lease / slot 持久化
└── runtime.py       # Scheduled Trigger 轮询器
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
- `workflow_scheduler/repository.py`：单条 UPDATE 原子 lease claim、owner 条件 release、PostgreSQL `ON CONFLICT DO NOTHING` slot claim、Execution 绑定。

当前 Repository 尚未完成本地 Persistence Gate，也未接入完整 Scheduler Runtime 业务闭环。

## 5. Contract / Persistence Gate 剩余项

必须本地确认：

1. Migration heads 可重复升级；
2. Repository lease claim / release 的原子语义；
3. slot 幂等 claim 与 Execution 绑定竞态；
4. Tenant / Organization scope；
5. paused / enabled / disabled 与 lease 清理；
6. misfire 与实时槽位排序、catch-up 上限；
7. Audit / Trace 关联字段；
8. API Contract 与 Tenant Safe Real API acceptance。

## 6. 下一执行顺序

```text
Persistence Gate
      ↓
Scheduler API Contract
      ↓
Scheduler Runtime 接入 persistence / lease / slot
      ↓
Unit / Integration / API Contract
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
