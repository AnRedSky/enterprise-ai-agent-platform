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
WorkflowExecutionResumeContractService
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
Resume Outcome Contract
   ┌────┴────────────┐
   ↓                 ↓
created       idempotency_hit
   └────┬────────────┘
        ↓
pending Resume Execution
        ↓
标准 Worker claim
```

每个候选使用独立 DB Session。Resume Contract 首先锁定 Source Execution 并检查确定性幂等键，然后委托既有 `WorkflowExecutionService.resume_from_latest_checkpoint()` 执行真正创建；数据库唯一约束继续作为最终安全兜底。

## 4. Recovery Outcome Contract

正式入口：

```text
WorkflowExecutionResumeOutcome
WorkflowExecutionResumeContractService
```

正式 outcome：

```text
rejected
created
idempotency_hit
```

规则：

- `rejected`：Recovery Policy 不允许自动恢复，不创建 Resume；`reason_code` 给出拒绝原因；
- `created`：本次 Resume Contract 创建新的 Resume Execution；
- `idempotency_hit`：本次 Resume Contract 命中已经存在且与 Source / Checkpoint 完全匹配的 Resume Execution；
- Source row lock 保证同一 Recovery Source 的 outcome 判断与创建处于同一并发串行边界；
- DB unique constraint 是最终安全兜底，不依赖应用层时间戳或对象状态猜测 outcome。

`WorkflowExecutionService.resume_from_latest_checkpoint()` 仍是唯一 Resume 持久化创建实现；Outcome Contract 不复制创建、审计、Trace 逻辑。

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

单次 Recovery Attempt：

```text
execution_id
resume_execution_id
outcome
reason_code
attempt_count
max_attempts
occurred_at
```

Scheduler Scan Aggregate：

```text
candidates
eligible
recovered
rejected
contention
failed
scan_limit
occurred_at
```

`contention` 当前严格由 `idempotency_hit` 驱动；禁止 Scheduler 根据异常类型猜测 row-lock / database contention。

事件模型只允许记录恢复控制面信息；Checkpoint `state_data`、Secret、Provider credential、完整业务 payload 等敏感内容禁止进入事件。

Recovery Attempt 只由 Recovery Domain 统一发射一次，Scheduler 不重复发射同一 Attempt Event。

后续 Metrics / Trace 接入必须复用该事件 Contract，不建立平行 Recovery 日志字段体系。

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
backend/tests/unit/test_workflow_resume_contract.py
backend/tests/unit/test_workflow_recovery_scheduler.py
backend/tests/unit/test_workflow_recovery_observability.py
```

本轮新增覆盖：

- `created` outcome；
- `idempotency_hit` outcome；
- Source / Checkpoint 匹配校验；
- Recovery Attempt outcome 传播；
- Scheduler `created / idempotency_hit / contention` 聚合；
- Scheduler 不重复发射 Attempt Event。

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
Resume Outcome Contract
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

1. 将 Recovery Event Contract 接入项目已有统一 observability / trace 基础设施；若当前没有统一基础设施，则保持领域事件出口，不新增平行 exporter；
2. 增加自动恢复 Real HTTP + PostgreSQL + 独立 Worker 测试入口，但不作为当前主线阻塞项；
3. 冻结 DAG Branch State Merge Contract；
4. 实现多 frontier Resume；
5. 完成 Phase 2.6 Closure 后进入下一阶段主线能力。