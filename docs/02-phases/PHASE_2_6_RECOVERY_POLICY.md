# Phase 2.6 Recovery Policy / Automatic Recovery Addendum

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-26
>
> 本文件是 `PHASE_2_6.md` 的自动恢复实现补充记录；阶段总体状态仍以 `docs/PROJECT_STATUS.md` 与 `docs/02-phases/PHASE_2_6.md` 为准。

## 1. 本轮开发目标

将 Durable Resume 从“人工 HTTP Resume Contract”继续推进到“可由 Scheduler 自动发现并安全创建 Resume Execution”的 Domain 边界。

核心原则：

```text
Scheduler
    = 什么时候检查

Recovery Policy
    = 是否允许自动恢复

Automatic Recovery Domain
    = 如何把 Policy + Candidate 串成 Resume Contract

WorkflowExecutionService
    = 如何安全创建 pending Resume Execution

Worker
    = 如何 claim / lease / execute
```

## 2. Recovery Policy

正式入口：

```text
WorkflowExecutionRecoveryPolicy
WorkflowExecutionRecoveryPolicyEvaluator
```

默认值：

```text
max_attempts = 3
cooldown_seconds = 60
```

自动恢复必须同时满足：

1. Execution 状态为 `failed`；
2. 当前没有 `worker_owner`；
3. Checkpoint Recovery Candidate 合法；
4. Resume lineage 未达到最大恢复次数；
5. Source failed 后已经超过 cooldown。

任何条件不满足均返回明确 `reason_code`，不产生数据库副作用。

## 3. Automatic Recovery Domain

正式入口：

```text
WorkflowExecutionAutomaticRecoveryService
```

执行链：

```text
failed Execution
      ↓
Checkpoint Candidate
      ↓
resume lineage count
      ↓
Recovery Policy
      ↓
eligible
      ↓
WorkflowExecutionService.resume_from_latest_checkpoint()
      ↓
pending Resume Execution
```

明确禁止：

- Source failed → pending 直接状态覆盖；
- Recovery Domain 直接抢 Worker ownership；
- Recovery Domain 直接启动 Runtime；
- Scheduler 复制 Recovery Policy；
- 普通 Retry 与 Resume attempt count 混用。

## 4. Scheduler Recovery Scan

正式入口：

```text
WorkflowRecoveryScheduler.scan_once()
```

职责仅限：

```text
发现 failed + worker_owner IS NULL
        ↓
调用 Recovery Domain
        ↓
记录 candidates / eligible / recovered / rejected / contention / failed
```

扫描器不包含恢复业务规则。

每个 Execution 使用独立数据库 Session，避免跨候选循环形成长事务。

多 Scheduler 实例并发扫描同一 Execution 时，最终收敛依赖：

```text
Source Execution row lock
        +
deterministic Resume idempotency key
        +
Database unique constraint
```

## 5. 当前尚未接入

本轮已经实现 `WorkflowRecoveryScheduler.scan_once()`，但**尚未把 Recovery Scan 接入 `ScheduledTriggerScheduler.run_forever()` 主循环**。

原因是需要保持 Scheduled Trigger Dispatch 与 Recovery Scan 两套职责、计数器、异常边界和轮询节奏独立，下一提交再完成 Runtime 编排接入，避免在同一修改中复制生命周期控制逻辑。

## 6. 单元测试

新增：

```text
backend/tests/unit/test_workflow_recovery_policy.py
backend/tests/unit/test_workflow_automatic_recovery_service.py
backend/tests/unit/test_workflow_recovery_scheduler.py
```

覆盖：

- 自动恢复关闭；
- failed / 非 failed；
- Worker ownership；
- Checkpoint Candidate；
- cooldown；
- 最大恢复次数；
- lineage 次数；
- Scheduler Domain delegation；
- Scheduler rejected / recovered / failed 聚合计数。

当前环境未实际执行新增测试，因此文档不得把这些测试记录为已通过。

## 7. 下一任务

1. 将 `WorkflowRecoveryScheduler.scan_once()` 接入 Scheduler Runtime 主循环；
2. 为 Recovery Scan 增加独立 poll interval / scan limit 配置 Contract；
3. 将 recovery counters 接入 Scheduler observability；
4. 单元测试通过后，再进行自动恢复 Real API / Worker 验收；
5. 自动恢复稳定后进入 DAG 分支状态合并 Contract 与多 frontier Resume。
