# Phase 2.4 — Durable Scheduler

> 状态：**Persistence、Runtime 与 Scheduler API Contract 已由开发者本地 Gate 实际完成；tenant isolation / misfire integration 当前因本轮真实 Gate 暴露的测试数据依赖、Contract 断言与 Runtime 幂等键问题正在修复。**
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
├── contract.py      # 薄的领域聚合入口，不实现具体规则
├── models.py        # 状态、misfire、lease、slot 数据模型
├── time.py          # UTC、IANA timezone、DST 时间语义与槽位构造
├── lease.py         # lease 可抢占判断
├── misfire.py       # misfire 槽位规划
├── repository.py    # PostgreSQL 原子 lease / slot 持久化
└── runtime.py       # Scheduled Trigger 持久化调度器
```

`__init__.py` 负责稳定导出；领域规则按职责拆分，禁止继续向公共 `app/services/` 零散增加同功能文件。`misfire.py` 只依赖 `models.py` 与 `time.py`，不反向依赖聚合入口，避免形成循环依赖。

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
6. Runtime 不复制 Trigger 校验、Execution 状态机或 Repository 规则；
7. Runtime 的 Execution idempotency key 统一由 `ScheduledTriggerScheduler.idempotency_key()` 生成，键空间与 interval slot Contract 保持一致。

开发者本地 Runtime 基础 Gate 已实际通过；本轮新的 tenant / misfire Gate 暴露问题后，尚未重新形成最终通过结果。

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

开发者本地 API Contract 基础 Gate 已实际通过；新的 tenant / misfire Gate 尚未最终通过。

## 7. Tenant isolation / misfire integration（当前开发任务）

### Tenant isolation

- Repository 查询必须同时携带 `tenant_id + trigger_id`；
- lease claim / release / advance 必须同时携带 tenant scope；
- slot 查询保持 tenant scope；
- PostgreSQL 状态查询隔离测试验证错误 tenant 无法读取正确 tenant 的 Scheduler 状态；
- 测试数据准备必须先 flush `WorkflowTrigger`，再写入引用它的 `WorkflowSchedule`，显式建立真实 FK 前置条件。

### Misfire integration

Scheduled Trigger Contract：

```text
misfire_policy: skip | fire_once | catch_up
catch_up_limit: 1..100，默认 10
```

运行语义：

- `skip`：历史积压全部跳过，下一运行恢复到未来 interval；
- `fire_once`：历史积压只补一次，随后恢复到未来 interval；
- `catch_up`：最多补跑 `catch_up_limit` 个历史槽位，若仍有积压则由下一 tick 继续有界处理；
- 每个槽位继续通过统一 `schedule_slot_key` 和既有 WorkflowTriggerService idempotency 收敛重复执行；
- 单个 slot 的 `recovery` 元数据只在该 slot 的 `planned_at < now` 时为 `true`，当前槽位不继承整轮 tick 的 misfire 状态。

misfire 计算统一位于 `workflow_scheduler/misfire.py`，Runtime 不复制规则。

## 8. 当前问题与修复

提交 `09b3811` 后首先发现 Scheduler misfire 循环导入，已通过 `misfire.py` 直接依赖 `workflow_scheduler.time` 修复，详见 `docs/04-errors/2026-08-24-scheduler-misfire-circular-import.md`。

修复循环导入后，开发者本地实际 Gate 又发现：

1. PostgreSQL tenant isolation fixture 在 Schedule FK 写入前未显式 flush Trigger；
2. Scheduled Trigger Contract 新增默认字段后，旧测试仍精确断言旧配置；
3. Runtime 使用 `planned_at` 秒级时间戳生成 Execution key，与公开 interval slot key 不一致；
4. Recovery Real API 测试依赖旧的进程内 recovery slot 假设，没有从真实 `workflow_schedules.next_run_at` 构造持久化 misfire。

以上问题已完成代码 / 测试修复并记录到 `docs/04-errors/2026-08-24-scheduler-tenant-misfire-gate.md`；修复后的本地 Gate 尚未重新执行，因此不得记录为 Passed。

## 9. 当前 Gate

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

Tenant Safe Real API：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

**当前只记录开发者已实际反馈的失败结果；修复后的结果必须重新执行后才能更新为 Passed。**

## 10. 下一执行顺序

```text
修复后 Application import
      ↓
Tenant isolation / misfire integration Gate
      ↓
Tenant Safe Real API Gate
      ↓
Backend default regression
      ↓
多实例 lease / misfire / Execution / Audit Trace / restart recovery Acceptance
      ↓
Frontend API / UI（如存在明确用户操作范围）
      ↓
Browser E2E（如存在对应 UI 用户链路）
```

未完成上述 Gate 前，不记录 Phase 2.4 Passed。
