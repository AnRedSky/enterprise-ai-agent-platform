# Phase 2.4 — Durable Scheduler

> 状态：**生产实现继续收口中；Backend Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire、API/Scheduler 进程解耦、Scheduler Service 双循环生命周期监督均已实现。完整 Gate / Acceptance 按当前开发策略暂不作为主线阻塞条件。**
> 评估日期：2026-08-27
> 优先级：**P1**

## 1. 方案决策

Phase 2.4 采用“**Contract-first + MVP 边界 + 可替换实现**”：

- 首版解决已发布 Workflow Scheduled Trigger 的持久化、恢复、lease、多实例 ownership、misfire、幂等和审计追踪。
- `next_run_at` 使用 UTC 持久化，调度配置保存 IANA timezone。
- 多实例 ownership 优先使用 PostgreSQL 原子 UPDATE / 行锁。
- 不引入 MQ/Kafka、Temporal、复杂 DAG 或通用任务平台。
- 当前已完成 API Service 与 Scheduler Service 的物理进程解耦；本阶段不提前实现 Worker Service。

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

backend/app/entrypoints/
└── scheduler.py     # Scheduler Service 进程生命周期编排

backend/run.py          # API Service
backend/run_scheduler.py # Scheduler Service
```

`__init__.py` 负责稳定导出；领域规则按职责拆分，禁止继续向公共 `app/services/` 零散增加同功能文件。`app/entrypoints` 只负责进程启动，不承载 Scheduler 业务规则。

## 3. Contract 范围

当前覆盖：

1. `enabled / paused / disabled`；
2. IANA timezone 与 UTC 持久化；
3. 可注入 `SchedulerClock`；
4. DST 重复时间选择第一次、不存在时间拒绝；
5. `schedule_slot_key` 稳定幂等键；
6. lease owner / expiry 成对约束；
7. `skip / fire_once / catch_up` misfire；
8. Scheduled Trigger 配置可持久化 `misfire_policy / catch_up_limit`；
9. API Service / Scheduler Service 独立进程生命周期；
10. Scheduler Dispatch / Durable Recovery Scan 双循环统一生命周期监督。

## 4. Persistence 第一版

已存在：

- `WorkflowSchedule`：调度状态、next/last run、lease、misfire 等持久化；
- `WorkflowScheduleSlot`：`schedule_slot_key` 唯一约束、planned time、owner 与 WorkflowExecution 关联；
- `0028_durable_scheduler_persistence` Migration；
- `workflow_scheduler/repository.py`：单条 UPDATE 原子 lease claim、owner 条件 release、PostgreSQL `ON CONFLICT DO NOTHING` slot claim、Execution 绑定；
- Repository 的 tenant + trigger scope；
- PostgreSQL Repository lease / release、tenant isolation 与 slot idempotency integration tests。

## 5. Durable Runtime 接入

Runtime 已从“进程内 interval recovery”切换为持久化 Scheduler 状态驱动：

1. Scheduled Trigger 首次进入 Runtime 时由 Repository 确保唯一 `WorkflowSchedule`；
2. 每个 Scheduler 实例拥有唯一 owner，通过 PostgreSQL 原子 lease claim 取得执行权；
3. 以持久化 `next_run_at` 生成稳定 `WorkflowScheduleSlot.schedule_slot_key`；
4. Execution 创建继续复用既有 `WorkflowTriggerService.invoke_scheduled`；
5. Execution 与 slot 绑定后，由 lease owner 原子推进 `next_run_at / last_run_at / last_execution_id` 并释放 lease；
6. Runtime 不复制 Trigger 校验、Execution 状态机或 Repository 规则；
7. Runtime 的 Execution idempotency key 统一由 `ScheduledTriggerScheduler.idempotency_key()` 生成，键空间与 interval slot Contract 保持一致。

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

## 7. Tenant isolation / misfire integration

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

## 8. API / Scheduler 服务化拆分

API Service 与 Scheduler Service 已完成物理解耦：

```text
API Service
    run.py → app.main:app
    └── 只负责 HTTP / Auth / API Router

Scheduler Service
    run_scheduler.py → app.entrypoints.scheduler
    ├── Scheduled Trigger Dispatch
    └── Durable Recovery Scan
```

API Service 不再导入或创建 `ScheduledTriggerScheduler`，因此 API 横向扩容不会同步创建新的后台 Scheduler。Scheduler 仍可通过 PostgreSQL lease + slot Contract 做多实例 ownership；服务化拆分不改变既有调度规则、数据库模型或 API Contract。

Worker Service 暂不实现。后续只有在 Task Contract、Queue/Broker、retry、lease、DLQ、cancellation 与 tenant boundary 明确后才建立正式 Worker 领域模块，禁止提前创建空壳或第二套 Runtime。

## 9. Scheduler Service 双循环生命周期监督

Scheduler Service 现在将 Scheduled Trigger Dispatch 与 Durable Recovery Scan 视为同一完整服务职责的两个长期循环，并由进程入口统一监督：

```text
Scheduler Service
   ├── Scheduled Trigger Dispatch
   └── Durable Recovery Scan
            ↓
      FIRST_EXCEPTION
            ↓
任一循环异常 → 停止另一循环 → 传播原始异常 → 进程失败收敛
```

该边界解决了 Recovery Scan 后台任务静默异常而 Scheduled Trigger Dispatch 继续运行的半存活状态。入口只负责生命周期监督，不复制 slot、lease、misfire、Recovery Policy 或 Runtime 规则。

正常停止时两个任务统一取消并等待完成；异常停止时不留下后台孤儿任务。

## 10. 当前测试策略

按当前项目主线策略，暂停完整测试流程，不以 Backend Full Regression、Real API、Frontend Gate 或 Browser E2E 阻塞生产代码推进。新增或修改的单元测试保持在 `backend/tests/unit/`，实际 PASS 只能由开发者本地执行结果确认。

本轮新增/更新：

```text
backend/tests/unit/test_service_entrypoints.py
```

覆盖：

- API Service 不创建 Scheduler；
- Scheduler Dispatch 异常时统一停止 Recovery Scan；
- Recovery Scan 异常时统一停止 Scheduled Dispatch；
- Scheduler Service 身份不依赖配置开关。

## 11. 当前交付状态

```text
Scheduler Persistence                         ✅
Scheduler Runtime                             ✅
Scheduler API Contract                        ✅
Tenant isolation / misfire                    ✅
API / Scheduler process separation            ✅
Scheduler dual-loop lifecycle supervision     ✅ 本轮

Phase 2.4 生产代码范围                        ✅
完整 Gate / Acceptance                        ← 按当前策略暂缓
```

## 12. 下一执行顺序

```text
1. 保持 Scheduler canonical implementation，不新增第二实现
2. 继续推进 Phase 2.4 尚未完成的生产代码缺口
3. 每个生产代码变更同步 targeted Unit Test
4. 暂停 Full Regression / Real API / E2E，不阻塞主线
5. 所有主线生产任务完成后，再集中执行开发者本地 Gate / Acceptance
```
