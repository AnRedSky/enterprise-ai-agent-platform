# Phase 1.7-B — Scheduler Execution / Persistence Integration

## 1. 目标

在不重复实现 Phase 1.7-A 已完成能力的前提下，确认并收口 Scheduled Trigger 从调度 slot 到 `workflow_executions` 持久化、Runtime 执行、Audit / Trace 的真实业务闭环。

本阶段不引入 MQ、Event Bus、独立 Worker、Cron Engine、Temporal / Airflow，也不为已经存在的多 worker slot convergence 再增加旁路实现。

## 2. 远端 main 基线审计

截至 `ad0ca3d930a5dd9e1b196fa5879b88c091d99074`，Phase 1.7-A 的实现已经明显超过原 `PROJECT_STATUS.md` 所记录的 A-01 Contract 状态：

| 能力 | main 当前实现 | 结论 |
|---|---|---|
| Scheduled Trigger config | `timezone + interval_seconds` 校验 | 已存在，不重复实现 |
| Scheduler background task | FastAPI lifespan 启停 | 已存在，不重复实现 |
| Candidate selection | enabled + scheduled + published Workflow | 已存在，不重复实现 |
| Interval slot | UTC epoch / interval | 已存在，不重复实现 |
| Slot Idempotency-Key | `scheduled:{trigger_id}:{slot}` | 已存在，不重复实现 |
| Recovery | bounded recovery slots | 已存在，不重复实现 |
| Recovery governance | audit / trace + `recovery` input marker | 已存在，不重复实现 |
| Execution persistence | `WorkflowExecutionService.create()` + DB unique constraint | 已存在，本阶段做验收收口 |
| Runtime execution | `WorkflowExecutionService.run()` | 已存在，本阶段做验收收口 |
| Audit / Trace | Governance service | 已存在，本阶段做验收收口 |
| Multi-worker convergence | PostgreSQL advisory transaction lock + existing idempotency constraint | 已存在；不再追加并发旁路方案 |

因此，Phase 1.7-B 的开发重点不是重新写 Scheduler，而是把现有实现整理成明确、可验收的 persistence contract，并补齐失败、恢复、重启和数据库持久化语义的验证。

## 3. 当前真实执行链路

```text
FastAPI lifespan
    ↓
ScheduledTriggerScheduler.tick_once()
    ↓
WorkflowTrigger / published Workflow 查询
    ↓
interval slot + idempotency key
    ↓
workflow_executions 唯一性边界
    ↓
WorkflowTriggerService.invoke_scheduled()
    ↓
WorkflowExecutionService.create()
    ↓
created audit + execution trace
    ↓
WorkflowExecutionService.run()
    ↓
node/runtime execution
    ↓
completed / failed Execution
    ↓
terminal audit + trace
```

## 4. Persistence Contract

### 4.1 Trigger 状态

- `workflow_triggers.status=enabled` 才能进入 scheduler candidate。
- `trigger_type=scheduled` 才能走 scheduled dispatch。
- Workflow 必须为 `published` 且存在 `published_version_id`。

### 4.2 Execution 持久化

Scheduled slot 不直接写独立 scheduler state 表；当前 persistence boundary 为：

```text
workflow_executions.tenant_id
workflow_executions.workflow_id
workflow_executions.workflow_version_id
workflow_executions.idempotency_key
workflow_executions.status
workflow_executions.input_data
```

`input_data` 保存 `scheduled_slot` 与 `recovery`，使 Execution 本身可以解释其调度来源。

### 4.3 去重

数据库唯一约束 `(tenant_id, idempotency_key)` 是最终持久化去重边界。Scheduler 的 pre-check 只是优化，不能作为正确性的唯一依据。

### 4.4 Runtime 失败

Execution 必须先持久化为 `pending`，再进入 Runtime。Runtime 失败时通过既有 Execution 状态机进入 `failed`，不得因为 scheduler tick 失败而丢失 Execution 记录。

### 4.5 Recovery

Recovery slot 与 current slot 使用相同的 Execution persistence contract，只通过 `input_data.recovery` 和 governance event 区分来源；不得建立第二套 Execution 表或旁路执行链。

## 5. 本阶段开发任务

### B-01 基线审计

- 核对 A-01～A-04 已有代码、migration、tests、Real API contract。
- 更新 `PROJECT_STATUS.md`，纠正已经落后于 main 实现的阶段描述。

### B-02 Persistence contract

- 明确 `workflow_executions` 是 Scheduled Trigger 的 execution persistence boundary。
- 确认 slot、recovery、idempotency metadata 可从 Execution 记录恢复解释。
- 不新增 migration，除非验收发现现有 schema 无法满足 contract。

### B-03 Failure / Recovery verification

至少覆盖：

- scheduled dispatch 创建 pending Execution 后进入 Runtime；
- Runtime completed 后 Execution 持久化为 completed；
- Runtime failure 后 Execution 持久化为 failed；
- recovery dispatch 使用同一 Execution persistence boundary；
- 同 slot 重复 tick 不创建第二条 Execution；
- scheduler restart 后历史 slot 不产生重复 Execution。

### B-04 Real HTTP persistence verification

真实 API Gate 必须验证数据库真实记录，而不是 JSON fixture 或内存状态。

重点检查：

```text
Trigger
  ↓
Scheduler
  ↓
workflow_executions row
  ↓
status / idempotency_key / input_data
  ↓
Execution API / Audit / Trace
```

## 6. Migration Decision

当前不新增 migration。原因是 main 已经具备：

- `workflow_executions.idempotency_key`；
- tenant + idempotency unique constraint；
- Execution status state machine；
- execution input / output / error 字段；
- audit / trace persistence。

如果后续要求持久化 `next_run_at`、scheduler lease、misfire policy、per-trigger last-run state 或独立 schedule state，再单独设计 migration，不在本阶段预埋。

## 7. 测试 Gate

按 `docs/DEVELOPMENT.md` 执行，测试结果只记录实际执行结果：

```powershell
cd backend
uv run pytest -q
```

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

如涉及数据库 migration，必须实际执行：

```powershell
cd backend
uv run alembic upgrade head
```

Frontend / Browser Gate 不因本阶段 Backend persistence 工作而混入 Backend 测试脚本；若本阶段未修改 Frontend，则不新增 Frontend 测试任务。

## 8. 已知问题与边界

历史 Real API multi-worker contract 曾出现 SQLAlchemy `MissingGreenlet`，根因是并发 IntegrityError 处理路径中继续访问已失效 ORM 实例属性，触发隐式 lazy reload。该问题已经在 main 的 scheduler slot claim 收口过程中处理；本阶段不再为该问题增加新的并发旁路设计。

本阶段只验证当前 main 的真实 persistence contract 是否稳定。

## 9. 下一阶段

Phase 1.7-B 完成后进入：

```text
Phase 1.7-C — Frontend Schedule Governance UI Contract
```
