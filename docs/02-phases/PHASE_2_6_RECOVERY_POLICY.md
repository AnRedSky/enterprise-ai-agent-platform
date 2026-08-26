# Phase 2.6 Recovery Policy / Automatic Recovery Addendum

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-26
>
> 本文件是 `PHASE_2_6.md` 的自动恢复实现补充记录；阶段总体状态仍以 `docs/PROJECT_STATUS.md` 与 `docs/02-phases/PHASE_2_6.md` 为准。

## 1. 本轮开发目标

将 Durable Resume 从“人工 HTTP Resume Contract”继续推进到“可由 Scheduler 自动发现并安全创建 Resume Execution”的完整进程边界。

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
WorkflowRecoveryScheduler.run_forever()
```

职责仅限：

```text
Scheduler loop
        ↓
发现 failed + worker_owner IS NULL
        ↓
调用 Recovery Domain
        ↓
记录 candidates / eligible / recovered / rejected / contention / failed
```

扫描器不包含恢复业务规则。

每个 Execution 使用独立数据库 Session，避免跨候选循环形成长事务。

多个 Scheduler 实例并发扫描同一 Execution 时，最终收敛依赖：

```text
Source Execution row lock
        +
deterministic Resume idempotency key
        +
Database unique constraint
```

## 5. Scheduler Service 生命周期接入

Recovery Scan 已接入 `backend/app/entrypoints/scheduler.py` 的独立 Scheduler Service 生命周期：

```text
Scheduler Service Process
    ├── ScheduledTriggerScheduler.run_forever()
    │      └── Scheduled Trigger Dispatch
    │
    └── WorkflowRecoveryScheduler.run_forever()
           └── Durable Recovery Scan
```

两条循环：

- 共享同一 Scheduler 进程；
- 不共享数据库 Session；
- 不复制业务规则；
- Recovery Scan 异常不会直接修改 Scheduled Trigger Dispatch 状态；
- Scheduled Trigger Scheduler 停止时，Recovery Scheduler 同步收到 stop/cancel；
- Recovery Scan 使用 `settings.scheduler_poll_interval_seconds` 作为默认轮询周期，避免建立第二套配置入口。

## 6. Scheduler Observability

Recovery Scan 每轮完成后输出一条结构化 INFO 日志，消息固定为 `Workflow automatic recovery scan completed`，并携带：

```text
candidates
eligible
recovered
rejected
contention
failed
scan_limit
```

该日志只记录聚合结果，不记录输入数据、Checkpoint `state_data`、Secret 或其他业务敏感内容。单 Execution 异常仍保留 `execution_id + error_type` 的结构化异常日志，并继续处理下一候选。

当前 `contention` 字段保留为 Scan Contract 的并发竞争指标；后续当 Recovery Domain 明确区分 row-lock / idempotency contention 与普通 rejection 后，再增加精确分类，不在 Scheduler 中猜测异常类型。

## 7. 单元测试

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
- Scheduler rejected / recovered / failed 聚合计数；
- Scheduler 聚合日志字段。

当前环境未实际执行新增测试，因此文档不得把这些测试记录为已通过。

## 8. 下一任务

1. 增加自动恢复真实 HTTP + PostgreSQL + 独立 Worker 验收入口，但当前不以该验收阻塞主线；
2. 验证 Recovery Scan 与 Scheduled Trigger Dispatch 的并发 / Session 隔离；
3. 将 Recovery Scan 聚合指标接入项目统一 observability / trace 入口（如已有统一入口则复用，不新增平行 metrics 系统）；
4. 自动恢复稳定后冻结 DAG 分支状态合并 Contract 与多 frontier Resume。