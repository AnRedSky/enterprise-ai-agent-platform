# Phase 2.6 Recovery Policy / Automatic Recovery Addendum

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-27
>
> 本文件是 `PHASE_2_6.md` 的自动恢复实现补充记录；阶段总体状态仍以 `docs/PROJECT_STATUS.md` 与对应 Acceptance 文档为准。

## 1. 当前目标

将 Durable Resume 从人工 HTTP Resume 推进到可观测、可策略控制、可由 Scheduler 自动触发的恢复执行链，并为后续 DAG 多 frontier Resume 保留稳定领域边界。

## 2. Recovery Policy / Domain

正式入口：

```text
WorkflowExecutionRecoveryPolicy
WorkflowExecutionRecoveryPolicyEvaluator
WorkflowExecutionAutomaticRecoveryService
```

默认策略：

```text
max_attempts = 3
cooldown_seconds = 60
```

Recovery Domain 负责 Candidate + Policy + Resume Contract；Scheduler 不复制这些业务规则，Worker 不直接启动恢复 Runtime。

## 3. Scheduler Recovery Scan

正式入口：

```text
WorkflowRecoveryScheduler.scan_once()
WorkflowRecoveryScheduler.run_forever()
```

Scheduler 只负责：

```text
发现 failed + worker_owner IS NULL
        ↓
Recovery Domain
        ↓
pending Resume Execution
        ↓
标准 Worker claim
```

每个候选使用独立 DB Session；多 Scheduler 并发最终依赖 Source row lock、deterministic idempotency key 与数据库唯一约束收敛。

## 4. Recovery Outcome Contract

自动恢复 Domain Result 现在显式携带：

```text
outcome = rejected | recovered
```

规则：

- `rejected`：Policy 不允许自动恢复，不创建 Resume；`reason_code` 给出拒绝原因；
- `recovered`：Resume Contract 返回新建或幂等命中的 Resume Execution，并提供 `resume_execution_id`；
- 当前不在 Domain 外部猜测 `created` 与 `idempotency_hit`；这一区分必须由 Resume Domain 正式返回。

这样 Scheduler 可以消费稳定 outcome，而不需要根据对象时间、状态或异常类型旁路推断幂等竞争。

## 5. Recovery Observability Contract

正式入口：

```text
WorkflowRecoveryEvent
WorkflowRecoveryEventLogger
```

事件名称：

```text
workflow.recovery.attempt
workflow.recovery.scan.completed
```

自动恢复每次 attempt 都输出：

```text
execution_id
resume_execution_id
reason_code
attempt_count
max_attempts
occurred_at
```

Scheduler 每轮 Scan 输出：

```text
candidates
eligible
recovered
rejected
contention
failed
scan_limit
```

事件模型只允许记录恢复控制面信息；Checkpoint `state_data`、Secret、Provider credential、完整业务 payload 等敏感内容禁止进入事件。

后续 Metrics / Trace 接入必须复用该事件 Contract，不建立平行 Recovery 日志字段体系。

当前 `contention` 仍是聚合维度；在 Domain 能够可靠区分 row-lock / idempotency contention 前，禁止 Scheduler 根据异常类型猜测并计数。

## 6. Scheduler 生命周期

`backend/app/entrypoints/scheduler.py` 当前同时运行：

```text
ScheduledTriggerScheduler
WorkflowRecoveryScheduler
```

两条循环共享进程但不共享 DB Session；Recovery Scan 异常不会直接终止 Scheduled Trigger Dispatch。

## 7. 单元测试

覆盖：

```text
backend/tests/unit/test_workflow_recovery_policy.py
backend/tests/unit/test_workflow_automatic_recovery_service.py
backend/tests/unit/test_workflow_recovery_scheduler.py
backend/tests/unit/test_workflow_recovery_observability.py
```

本轮新增覆盖：

- `rejected` outcome；
- `recovered` outcome；
- `workflow.recovery.attempt` 事件；
- reason_code / attempt_count / max_attempts；
- Resume execution lineage 字段。

当前环境未实际执行新增测试，因此不得记录为“已通过”。

## 8. API / Real Worker 主线

保留并继续推进真实链路：

```text
Real HTTP
   ↓
PostgreSQL failed Execution + Checkpoint
   ↓
Recovery Scheduler / Domain
   ↓
Resume pending Execution
   ↓
独立 Worker claim / lease
   ↓
Resume Runtime
   ↓
新 Checkpoint / terminal state
```

Real API 测试当前不作为主线阻塞条件。

## 9. 下一任务

1. 将 Recovery Event Contract 接入项目已有统一 observability / trace 基础设施；若当前没有统一基础设施，则先保持领域事件出口，不新增平行 exporter；
2. 修改 Resume Domain，使其显式返回 `created` / `idempotency_hit` outcome；
3. 基于正式 outcome 精确收敛 recovery contention / idempotency convergence；
4. 增加自动恢复 Real HTTP + PostgreSQL + 独立 Worker 测试入口；
5. 冻结 DAG Branch State Merge Contract；
6. 实现多 frontier Resume；
7. 完成 Phase 2.6 Closure 后进入下一阶段主线能力。