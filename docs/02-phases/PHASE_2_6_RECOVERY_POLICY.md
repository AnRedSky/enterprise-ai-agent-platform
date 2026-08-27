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

## 4. Recovery Observability Contract

新增正式领域入口：

```text
WorkflowRecoveryEvent
WorkflowRecoveryEventLogger
```

事件名称：

```text
workflow.recovery.attempt
workflow.recovery.scan.completed
```

统一字段包括：

```text
execution_id
resume_execution_id
reason_code
attempt_count
max_attempts
candidates
eligible
recovered
rejected
contention
failed
scan_limit
occurred_at
```

事件模型只允许记录恢复控制面信息；Checkpoint `state_data`、Secret、Provider credential、完整业务 payload 等敏感内容禁止进入事件。

Recovery Scan 每轮输出 `workflow.recovery.scan.completed`；单候选评估/恢复输出 `workflow.recovery.attempt`。后续 Metrics / Trace 接入必须复用该事件 Contract，不建立平行 Recovery 日志字段体系。

当前 `contention` 仍是聚合维度；在 Domain 能够可靠区分 row-lock / idempotency contention 前，禁止 Scheduler 根据异常类型猜测并计数。

## 5. Scheduler 生命周期

`backend/app/entrypoints/scheduler.py` 当前同时运行：

```text
ScheduledTriggerScheduler
WorkflowRecoveryScheduler
```

两条循环共享进程但不共享 DB Session；Recovery Scan 异常不会直接终止 Scheduled Trigger Dispatch。

## 6. 单元测试

覆盖：

```text
backend/tests/unit/test_workflow_recovery_policy.py
backend/tests/unit/test_workflow_automatic_recovery_service.py
backend/tests/unit/test_workflow_recovery_scheduler.py
backend/tests/unit/test_workflow_recovery_observability.py
```

测试重点：Policy eligibility、lineage、cooldown、Domain delegation、Scheduler aggregate、结构化事件字段与敏感字段边界。

本轮代码提交时不虚构测试通过结果；只有开发者本地实际执行结果才允许写入“通过”。

## 7. API / Real Worker 主线

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

Real API 测试可以作为当前交付验证，但不阻塞本轮主线代码继续向下推进；服务生命周期必须由开发者人工启动、停止和重启。

## 8. 下一任务

1. 增加自动恢复 Real HTTP + PostgreSQL + 独立 Worker 测试入口；
2. 将 Recovery Event Contract 接入项目已有统一 observability / trace 基础设施；若当前没有统一基础设施，则先保持领域事件出口，不新增平行 exporter；
3. 精确区分 recovery contention / idempotency convergence；
4. 冻结 DAG Branch State Merge Contract；
5. 实现多 frontier Resume；
6. 完成 Phase 2.6 Closure 后进入下一阶段主线能力。